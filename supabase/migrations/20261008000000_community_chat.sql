-- Public community text chat. No presence, email, private messages, or configuration
-- is exposed. Anonymous users may read; writes require a live launcher session.
begin;
create table paw_private.community_messages (
 ordinal bigint generated always as identity primary key,
 message_id uuid not null unique,
 sender_id uuid not null references auth.users(id) on delete cascade,
 channel text not null check(channel in ('ru','en')),
 body text not null check(char_length(body) between 1 and 1000),
 created_at timestamptz not null default clock_timestamp(),
 removed_at timestamptz
);
create index community_sender_time on paw_private.community_messages(sender_id,created_at desc);
create index community_channel_order on paw_private.community_messages(channel,ordinal desc);
alter table paw_private.community_messages enable row level security;
revoke all on paw_private.community_messages from public,anon,authenticated;
revoke all on sequence paw_private.community_messages_ordinal_seq from public,anon,authenticated;

create function paw_private.community_json(m paw_private.community_messages) returns jsonb
language sql stable security definer set search_path='' as $$
 select jsonb_build_object('ordinal',m.ordinal,'message_id',m.message_id,'sender_id',m.sender_id,
  'body',case when m.removed_at is not null then '' else m.body end,'removed',m.removed_at is not null,
  'created_at',m.created_at,'nickname',p.nickname,'display_name',p.display_name,'admin_level',p.admin_level)
 from public.paw_profiles p where p.id=m.sender_id and not p.deletion_pending;
$$;
revoke all on function paw_private.community_json(paw_private.community_messages) from public,anon,authenticated;

-- Each language has an independent retention policy. The history revision
-- invalidates cached older pages after a trim, moderation or identity change.
create table paw_private.community_history (
 channel text primary key check(channel in ('ru','en')),
 revision bigint not null default 0, removed_count bigint not null default 0
);
insert into paw_private.community_history(channel) values('ru'),('en');
alter table paw_private.community_history enable row level security;
revoke all on paw_private.community_history from public,anon,authenticated;

create function paw_private.community_deleted() returns trigger
language plpgsql security definer set search_path='' as $$
begin
 update paw_private.community_history h set revision=revision+1
 where h.channel in(select distinct channel from deleted_messages);
 return null;
end;$$;
create trigger community_deleted after delete on paw_private.community_messages
 referencing old table as deleted_messages for each statement execute function paw_private.community_deleted();

create function paw_private.community_profile_changed() returns trigger
language plpgsql security definer set search_path='' as $$
begin
 if tg_op='UPDATE' and (old.nickname,old.display_name,old.admin_level,old.deletion_pending)
  is not distinct from (new.nickname,new.display_name,new.admin_level,new.deletion_pending) then return new;end if;
 update paw_private.community_history h set revision=revision+1
 where exists(select 1 from paw_private.community_messages m where m.channel=h.channel and m.sender_id=old.id);
 return new;
end;$$;
create trigger community_profile_changed after update of nickname,display_name,admin_level,deletion_pending or delete
 on public.paw_profiles for each row execute function paw_private.community_profile_changed();
revoke all on function paw_private.community_deleted(),paw_private.community_profile_changed() from public,anon,authenticated;

create function public.paw_community_read(channel text,known_revision text default null,before_ordinal bigint default null) returns jsonb
language sql stable security definer set search_path='' as $$
 with recent as (select m.ordinal,paw_private.community_json(m) item from paw_private.community_messages m
  where m.channel=$1 and ($3 is null or m.ordinal<$3)
   and exists(select 1 from public.paw_profiles p where p.id=m.sender_id and not p.deletion_pending)
  order by m.ordinal desc limit 101),
 numbered as(select *,row_number() over(order by ordinal desc) n from recent),
 snapshot as (select coalesce(jsonb_agg(item order by ordinal) filter(where n<=100),'[]'::jsonb) messages,
  count(*)>100 more from numbered),
 result as(select s.*,h.revision history_revision,h.removed_count>0 trimmed,
  md5(s.messages::text||':'||h.revision::text||':'||s.more::text) etag
  from snapshot s join paw_private.community_history h on h.channel=$1)
 select case when $1 is null or $1 not in ('ru','en') or $3<=0 then jsonb_build_object('status','invalid_message') else
  coalesce((select jsonb_build_object('status','ok','revision',etag) ||
   case when etag=$2 and $3 is null then jsonb_build_object('unchanged',true)
   else jsonb_build_object('messages',messages,'more',more,'history_revision',history_revision,'trimmed',trimmed) end from result),
  jsonb_build_object('status','invalid_message')) end;
$$;
revoke all on function public.paw_community_read(text,text,bigint) from public;
grant execute on function public.paw_community_read(text,text,bigint) to anon,authenticated;

create function public.paw_community_send(channel text,message_id uuid,body text) returns jsonb
language plpgsql security definer set search_path='' as $$
#variable_conflict use_variable
declare actor uuid; previous paw_private.community_messages; result paw_private.community_messages;
begin
 -- Serialize sends with id allocation so polling cannot miss a late commit.
 perform pg_advisory_xact_lock(73190439);
 actor:=paw_private.social_actor();
 if actor is null then return jsonb_build_object('status',case when paw_private.player_banned(auth.uid()) then 'account_banned' else 'session_expired' end);end if;
 if channel is null or channel not in ('ru','en') or message_id is null or message_id='00000000-0000-0000-0000-000000000000'::uuid
  or body is null or char_length(body) not between 1 and 1000 or body !~ '[^[:space:]]'
  or body ~ '[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]' then return jsonb_build_object('status','invalid_message');end if;
 select * into previous from paw_private.community_messages m where m.message_id=message_id;
 if found then
  if previous.sender_id<>actor or previous.body<>body or previous.channel<>channel then return jsonb_build_object('status','message_conflict');end if;
  return jsonb_build_object('status','ok','message',paw_private.community_json(previous));
 end if;
 if exists(select 1 from paw_private.community_messages m where m.sender_id=actor and m.created_at>clock_timestamp()-interval '3 seconds')
  or (select count(*) from paw_private.community_messages m where m.sender_id=actor and m.created_at>clock_timestamp()-interval '1 minute')>=10
  then return jsonb_build_object('status','rate_limit');end if;
 insert into paw_private.community_messages(channel,message_id,sender_id,body) values(channel,message_id,actor,body) returning * into result;
 -- Same threshold as private conversations, independently for RU and EN.
 if (select count(*) from paw_private.community_messages m where m.channel=channel)>=10000 then
  delete from paw_private.community_messages m where m.ordinal in
   (select v.ordinal from paw_private.community_messages v where v.channel=channel order by v.ordinal limit 5000);
  update paw_private.community_history h set removed_count=removed_count+5000 where h.channel=channel;
 end if;
 return jsonb_build_object('status','ok','message',paw_private.community_json(result));
end; $$;
revoke all on function public.paw_community_send(text,uuid,text) from public,anon;
grant execute on function public.paw_community_send(text,uuid,text) to authenticated;

create function public.paw_community_remove(message_id uuid) returns jsonb
language plpgsql security definer set search_path='' as $$
#variable_conflict use_variable
declare actor uuid; target paw_private.community_messages;
begin
 perform pg_advisory_xact_lock(73190439);
 actor:=paw_private.social_actor();
 if actor is null then return jsonb_build_object('status','session_expired');end if;
 select * into target from paw_private.community_messages m where m.message_id=message_id for update;
 if not found then return jsonb_build_object('status','invalid_message');end if;
 if target.sender_id<>actor and (paw_private.admin_level(actor)<1
  or paw_private.admin_level(actor)<paw_private.admin_level(target.sender_id))
  then return jsonb_build_object('status','admin_required');end if;
 if target.removed_at is null then
  update paw_private.community_messages m set removed_at=clock_timestamp() where m.message_id=message_id;
  update paw_private.community_history h set revision=revision+1 where h.channel=target.channel;
 end if;
 return jsonb_build_object('status','ok');
end; $$;
revoke all on function public.paw_community_remove(uuid) from public,anon;
grant execute on function public.paw_community_remove(uuid) to authenticated;
notify pgrst, 'reload schema';
commit;
