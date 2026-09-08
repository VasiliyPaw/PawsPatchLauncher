-- Bounded shared conversation history. No existing messages are removed by this migration.
create table paw_private.conversation_history (
 low_id uuid not null, high_id uuid not null, revision bigint not null default 0,
 removed_count bigint not null default 0, trimmed_at timestamptz,
 primary key(low_id,high_id), check(low_id<high_id)
);
alter table paw_private.conversation_history enable row level security;
revoke all on paw_private.conversation_history from public,anon,authenticated;
create index paw_message_dialog_history on public.paw_messages
 (least(sender_id,recipient_id),greatest(sender_id,recipient_id),created_at desc,ordinal desc);

create function paw_private.offer_in_progress(o paw_private.social_offers) returns boolean
language sql stable set search_path='' as $$
 select coalesce(o.state in('uploading','pending') and o.expires_at>now()
  or o.state='applying' and o.apply_until>now(),false);
$$;
create function paw_private.trim_conversation(a uuid,b uuid) returns integer
language plpgsql security definer set search_path='' as $$
declare removed integer;
begin
 perform paw_private.social_lock(a,b);
 if (select count(*) from public.paw_messages where least(sender_id,recipient_id)=least(a,b)
  and greatest(sender_id,recipient_id)=greatest(a,b))<10000 then return 0;end if;
 with victims as (
  select m.ordinal from public.paw_messages m
  where least(m.sender_id,m.recipient_id)=least(a,b) and greatest(m.sender_id,m.recipient_id)=greatest(a,b)
   and not exists(select 1 from paw_private.social_offers o where o.id=m.message_id and o.sender_id=m.sender_id and paw_private.offer_in_progress(o))
  order by m.created_at,m.ordinal limit 5000
 ) delete from public.paw_messages m using victims v where m.ordinal=v.ordinal;
 get diagnostics removed=row_count;
 if removed>0 then
  insert into paw_private.conversation_history(low_id,high_id,revision,removed_count,trimmed_at)
  values(least(a,b),greatest(a,b),1,removed,clock_timestamp())
  on conflict(low_id,high_id) do update set revision=conversation_history.revision+1,
   removed_count=conversation_history.removed_count+excluded.removed_count,trimmed_at=excluded.trimmed_at;
  -- Save objects are deleted ONLY by the existing authenticated storage cleanup, never by SQL.
  delete from paw_private.social_offers o where least(o.sender_id,o.recipient_id)=least(a,b)
   and greatest(o.sender_id,o.recipient_id)=greatest(a,b) and o.storage_cleaned and not paw_private.offer_in_progress(o)
   and not exists(select 1 from public.paw_messages m where m.sender_id=o.sender_id and m.message_id=o.id);
 end if;
 return removed;
end;$$;
create function paw_private.trim_inserted_conversation() returns trigger
language plpgsql security definer set search_path='' as $$
begin perform paw_private.trim_conversation(new.sender_id,new.recipient_id);return new;end;$$;
create trigger paw_message_history_retention after insert on public.paw_messages
 for each row execute function paw_private.trim_inserted_conversation();
revoke all on function paw_private.offer_in_progress(paw_private.social_offers),paw_private.trim_conversation(uuid,uuid),
 paw_private.trim_inserted_conversation() from public,anon,authenticated;

-- Keep existing authorization, participant serialization, minute limits and deduplication.
do $$ declare def text; needle text; signature text;begin
 foreach signature in array array['public.paw_send_message(uuid,uuid,text,text)',
  'public.paw_offer_create(uuid,uuid,text,text,text,bigint,text)'] loop
  def:=pg_get_functiondef(signature::regprocedure);
  needle:='if (select count(*) from public.paw_messages where sender_id=actor)>=10000';
  if strpos(def,needle)=0 then raise exception 'Review message quota drift: %',signature;end if;
  def:=regexp_replace(def,'if \(select count\(\*\) from public.paw_messages where sender_id=actor\)>=10000\s*then return jsonb_build_object\(''status'',''message_limit''\);\s*end if;','','g');
  if strpos(def,needle)>0 then raise exception 'Message quota removal failed';end if;
  execute def;
 end loop;
end;$$;

create function public.paw_read_message_page(target uuid,before_time timestamptz default null,before_ordinal bigint default null) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare actor uuid:=paw_private.social_actor(); items jsonb; extra boolean; offers jsonb; rev bigint;
begin
 if actor is null then return jsonb_build_object('status','session_expired');end if;
 if not paw_private.history_allowed(actor,target) then return jsonb_build_object('status','friend_required');end if;
 if (before_time is null)<>(before_ordinal is null) or before_ordinal<=0 then return jsonb_build_object('status','invalid_message');end if;
 with page as (
  select * from public.paw_messages where least(sender_id,recipient_id)=least(actor,target) and greatest(sender_id,recipient_id)=greatest(actor,target)
   and (before_time is null or (created_at,ordinal)<(before_time,before_ordinal))
  order by created_at desc,ordinal desc limit 51
 ), numbered as (select *,row_number() over(order by created_at desc,ordinal desc) n from page)
 select coalesce(jsonb_agg(to_jsonb(t)-'n' order by created_at,ordinal) filter(where n<=50),'[]'::jsonb),count(*)>50 into items,extra from numbered t;
 select coalesce(jsonb_agg(paw_private.offer_view(o)),'[]'::jsonb) into offers from paw_private.social_offers o
 where exists(select 1 from jsonb_array_elements(items) m where (m->>'message_id')::uuid=o.id and (m->>'sender_id')::uuid=o.sender_id);
 select revision into rev from paw_private.conversation_history where low_id=least(actor,target) and high_id=greatest(actor,target);
 return jsonb_build_object('status','ok','messages',items,'offers',offers,'more',extra,'history_revision',coalesce(rev,0),'trimmed',coalesce(rev,0)>0);
end;$$;
revoke all on function public.paw_read_message_page(uuid,timestamptz,bigint) from public,anon,authenticated;
grant execute on function public.paw_read_message_page(uuid,timestamptz,bigint) to authenticated;

-- Refresh active cards already loaded from older pages without downloading their text again.
create function public.paw_read_offer_states(target uuid,offer_ids uuid[]) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare actor uuid:=paw_private.social_actor(); items jsonb;
begin
 if actor is null then return jsonb_build_object('status','session_expired');end if;
 if not paw_private.history_allowed(actor,target) then return jsonb_build_object('status','friend_required');end if;
 if coalesce(cardinality(offer_ids),0) not between 1 and 200 then return jsonb_build_object('status','invalid_offer');end if;
 select coalesce(jsonb_agg(paw_private.offer_view(o)),'[]'::jsonb) into items
 from paw_private.social_offers o where o.id=any(offer_ids)
  and least(o.sender_id,o.recipient_id)=least(actor,target) and greatest(o.sender_id,o.recipient_id)=greatest(actor,target)
  and exists(select 1 from public.paw_messages m where m.sender_id=o.sender_id and m.message_id=o.id);
 return jsonb_build_object('status','ok','offers',items);
end;$$;
revoke all on function public.paw_read_offer_states(uuid,uuid[]) from public,anon,authenticated;
grant execute on function public.paw_read_offer_states(uuid,uuid[]) to authenticated;

-- Retire metadata only after the Storage API acknowledged physical file cleanup.
create or replace function public.paw_transfer_cleaned(paths text[]) returns void
language sql security definer set search_path='' as $$
 update paw_private.social_offers o set storage_cleaned=true where o.sender_id::text||'/'||o.id::text||'.rsg'=any(paths)
  and not paw_private.offer_in_progress(o);
 delete from paw_private.social_offers o where o.sender_id::text||'/'||o.id::text||'.rsg'=any(paths)
  and o.storage_cleaned and not paw_private.offer_in_progress(o)
  and not exists(select 1 from public.paw_messages m where m.sender_id=o.sender_id and m.message_id=o.id);
$$;

-- Provider totals may be imported by a server-side integration; never trust client counters.
create table paw_private.resource_usage (
 metric text primary key check(metric in('egress','cached_egress','functions','emails_daily','emails_monthly')),
 used bigint check(used>=0), quota bigint check(quota>0), checked_at timestamptz not null,
 period_end timestamptz, source text not null check(length(source) between 1 and 80)
);
alter table paw_private.resource_usage enable row level security;
revoke all on paw_private.resource_usage from public,anon,authenticated;
grant select,insert,update,delete on paw_private.resource_usage to service_role;
create function public.paw_admin_resources() returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare actor uuid:=paw_private.social_actor(); metrics jsonb;
begin
 if paw_private.admin_level(actor)<1 then return jsonb_build_object('status','admin_required');end if;
 select coalesce(jsonb_agg(to_jsonb(u)),'[]'::jsonb) into metrics from paw_private.resource_usage u;
 return jsonb_build_object('status','ok','checked_at',now(),'database_bytes',pg_database_size(current_database()),
  'messages_bytes',pg_total_relation_size('public.paw_messages'),'messages_count',(select count(*) from public.paw_messages),
  'offers_bytes',pg_total_relation_size('paw_private.social_offers'),
  'avatars_bytes',(select coalesce(sum(case when metadata->>'size' ~ '^[0-9]+$' then (metadata->>'size')::bigint else 0 end),0) from storage.objects where bucket_id='paw-avatars'),
  'saves_bytes',(select coalesce(sum(case when metadata->>'size' ~ '^[0-9]+$' then (metadata->>'size')::bigint else 0 end),0) from storage.objects where bucket_id='paw-social-saves'),
  'storage_bytes',(select coalesce(sum(case when metadata->>'size' ~ '^[0-9]+$' then (metadata->>'size')::bigint else 0 end),0) from storage.objects),
  'removed_messages',(select coalesce(sum(removed_count),0) from paw_private.conversation_history),
  'dialog_limit',10000,'cleanup_batch',5000,'provider_metrics',metrics,
  'quota_source','free_reference_not_verified','database_reference_limit',524288000,'storage_reference_limit',1073741824);
end;$$;
revoke all on function public.paw_admin_resources() from public,anon,authenticated;
grant execute on function public.paw_admin_resources() to authenticated;
