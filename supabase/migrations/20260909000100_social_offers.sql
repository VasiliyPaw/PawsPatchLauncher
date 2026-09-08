-- Conversation offers: immutable snapshots, recipient-only decisions, bounded private saves.
create table paw_private.social_offers (
 id uuid primary key, sender_id uuid not null references public.paw_profiles(id) on delete cascade,
 recipient_id uuid not null references public.paw_profiles(id) on delete cascade,
 kind text not null check(kind in('config','save')), configuration text,
 file_name text, file_size bigint, sha256 text,
 state text not null check(state in('uploading','pending','applying','accepted','declined','failed')),
 created_at timestamptz not null default clock_timestamp(), expires_at timestamptz not null default clock_timestamp()+interval '10 minutes',
 attempt uuid, started_at timestamptz, apply_until timestamptz, storage_cleaned boolean not null default false,
 check(sender_id<>recipient_id), check(id<>'00000000-0000-0000-0000-000000000000'::uuid)
);
create index social_offers_participants on paw_private.social_offers(recipient_id,sender_id,created_at desc);
alter table paw_private.social_offers enable row level security;
revoke all on paw_private.social_offers from public,anon,authenticated;

create function paw_private.offer_view(o paw_private.social_offers) returns jsonb
language sql stable security definer set search_path='' as $$
 select jsonb_build_object('id',o.id,'sender_id',o.sender_id,'recipient_id',o.recipient_id,'kind',o.kind,
 'configuration',o.configuration,'file_name',o.file_name,'file_size',o.file_size,'sha256',o.sha256,
 'state',case when o.state in('pending','uploading') and o.expires_at<=now() then 'expired'
 when o.state='applying' and o.apply_until<=now() then 'failed' else o.state end,
 'created_at',o.created_at,'expires_at',o.expires_at,'attempt',o.attempt,'apply_until',o.apply_until);
$$;
revoke all on function paw_private.offer_view(paw_private.social_offers) from public,anon,authenticated;

create function public.paw_offer_create(target uuid,offer_id uuid,offer_kind text,configuration text,file_name text,file_size bigint,sha256 text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare actor uuid:=paw_private.social_actor(); o paw_private.social_offers;
begin
 if actor is null then return jsonb_build_object('status','session_expired');end if;
 if target is null or offer_id is null or offer_id='00000000-0000-0000-0000-000000000000'::uuid or target=actor
 or offer_kind is null or offer_kind not in('config','save') then return jsonb_build_object('status','invalid_offer');end if;
 perform paw_private.social_lock(actor,target);
 if paw_private.social_actor() is null or not paw_private.social_allowed(actor,target) then return jsonb_build_object('status','friend_required');end if;
 if offer_kind='config' then
  if configuration is null or octet_length(configuration)>128 or configuration !~ '^PAW-(STABLE|BETA)-IW[01]-SP[124]-RM[01]-SG[01]-LM1-RU[01]-CL[01]-OOS[01](-PS[01])?$'
  or file_name is not null or file_size is not null or sha256 is not null then return jsonb_build_object('status','invalid_offer');end if;
 else
  if configuration is not null or file_name is null or length(file_name) not between 5 and 128
  or lower(right(file_name,4))<>'.rsg' or file_name ~ '[[:cntrl:]/\\:*?"<>|]' or left(file_name,1)='.'
  or file_size is null or file_size not between 16 and 20971520 or sha256 is null or sha256 !~ '^[0-9a-fA-F]{64}$'
  then return jsonb_build_object('status','invalid_save');end if;
 end if;
 select * into o from paw_private.social_offers where id=offer_id;
 if found then
  if o.sender_id<>actor or o.recipient_id<>target or o.kind<>offer_kind or o.configuration is distinct from configuration
  or o.file_name is distinct from file_name or o.file_size is distinct from file_size or lower(o.sha256) is distinct from lower(sha256)
  then return jsonb_build_object('status','message_conflict');end if;
  return jsonb_build_object('status','ok','offer',paw_private.offer_view(o));
 end if;
 if (select count(*) from paw_private.social_offers where sender_id=actor and created_at>now()-interval '1 minute')>=5
 or (select count(*) from paw_private.social_offers where sender_id=actor and state in('uploading','pending','applying') and expires_at>now())>=10
 then return jsonb_build_object('status','rate_limit');end if;
 if (select count(*) from public.paw_messages where sender_id=actor)>=10000 then return jsonb_build_object('status','message_limit');end if;
 if offer_kind='save' and coalesce((select sum(s.file_size) from paw_private.social_offers s where s.sender_id=actor and s.kind='save' and not storage_cleaned),0)+file_size>52428800
 then return jsonb_build_object('status','storage_limit');end if;
 insert into paw_private.social_offers(id,sender_id,recipient_id,kind,configuration,file_name,file_size,sha256,state,storage_cleaned)
 values(offer_id,actor,target,offer_kind,configuration,file_name,file_size,lower(sha256),case when offer_kind='config' then 'pending' else 'uploading' end,offer_kind='config') returning * into o;
 if offer_kind='config' then
  insert into public.paw_messages(sender_id,message_id,recipient_id,kind,body)
  values(actor,offer_id,target,'config','Предложение конфигурации · Configuration offer');
 end if;
 return jsonb_build_object('status','ok','offer',paw_private.offer_view(o));
end;$$;
revoke all on function public.paw_offer_create(uuid,uuid,text,text,text,bigint,text) from public,anon,authenticated;
grant execute on function public.paw_offer_create(uuid,uuid,text,text,text,bigint,text) to authenticated;

create function public.paw_offers(target uuid) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare actor uuid:=paw_private.social_actor();
begin
 if actor is null then return jsonb_build_object('status','session_expired');end if;
 if not paw_private.social_allowed(actor,target) then return jsonb_build_object('status','friend_required');end if;
 return jsonb_build_object('status','ok','offers',coalesce((select jsonb_agg(paw_private.offer_view(o)) from
 (select * from paw_private.social_offers where (sender_id=actor and recipient_id=target or sender_id=target and recipient_id=actor)
 and state<>'uploading' order by created_at desc limit 50) o),'[]'::jsonb));
end;$$;
revoke all on function public.paw_offers(uuid) from public,anon,authenticated;
grant execute on function public.paw_offers(uuid) to authenticated;

create function public.paw_offer_action(offer_id uuid,action text,attempt uuid) returns jsonb
language plpgsql security definer set search_path='' as $$
declare actor uuid:=paw_private.social_actor(); o paw_private.social_offers;
begin
 if actor is null then return jsonb_build_object('status','session_expired');end if;
 select * into o from paw_private.social_offers where id=offer_id;
 if not found or actor<>o.recipient_id then return jsonb_build_object('status','offer_unavailable');end if;
 perform paw_private.social_lock(o.sender_id,o.recipient_id);
 select * into o from paw_private.social_offers where id=offer_id for update;
 if paw_private.social_actor() is null or not paw_private.social_allowed(o.sender_id,o.recipient_id) then return jsonb_build_object('status','friend_required');end if;
 if action is null or action not in('begin','decline','touch','complete','fail') then return jsonb_build_object('status','invalid_offer');end if;
 if action<>'decline' and (attempt is null or attempt='00000000-0000-0000-0000-000000000000'::uuid) then return jsonb_build_object('status','invalid_offer');end if;
 if o.state='applying' and o.apply_until<=clock_timestamp() then
  update paw_private.social_offers set state='failed' where id=o.id returning * into o;
 end if;
 if o.state='pending' and o.expires_at<=clock_timestamp() then return jsonb_build_object('status','offer_expired','offer',paw_private.offer_view(o));end if;
 if action='decline' and o.state='pending' then
  update paw_private.social_offers set state='declined' where id=o.id returning * into o;
 elsif action='begin' and o.state='pending' then
  update paw_private.social_offers set state='applying',attempt=paw_offer_action.attempt,started_at=clock_timestamp(),apply_until=clock_timestamp()+interval '2 minutes' where id=o.id returning * into o;
 elsif action='touch' and o.state='applying' and o.attempt=attempt then
  update paw_private.social_offers set apply_until=least(clock_timestamp()+interval '2 minutes',started_at+interval '30 minutes') where id=o.id returning * into o;
 elsif action in('complete','fail') and o.state='applying' and o.attempt=attempt then
  update paw_private.social_offers set state=case when action='complete' then 'accepted' else 'failed' end where id=o.id returning * into o;
 elsif not (action='begin' and o.state='applying' and o.attempt=attempt
  or action='complete' and o.state='accepted' and o.attempt=attempt
  or action='fail' and o.state='failed' and o.attempt=attempt
  or action='decline' and o.state='declined') then return jsonb_build_object('status','offer_unavailable','offer',paw_private.offer_view(o));end if;
 return jsonb_build_object('status','ok','offer',paw_private.offer_view(o));
end;$$;
revoke all on function public.paw_offer_action(uuid,text,uuid) from public,anon,authenticated;
grant execute on function public.paw_offer_action(uuid,text,uuid) to authenticated;

insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
values('paw-social-saves','paw-social-saves',false,20971520,array['application/octet-stream']);
-- No client Storage policies: all bytes pass the verified Edge handler and active friendship checks.
create function public.paw_transfer_authorize(player uuid,session uuid,launcher uuid,offer_id uuid,action text) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare o paw_private.social_offers;
begin
 if not public.paw_account_session_active(player,session,launcher) then return jsonb_build_object('status','session_replaced');end if;
 select * into o from paw_private.social_offers where id=offer_id and kind='save';
 if not found or not paw_private.social_allowed(o.sender_id,o.recipient_id) then return jsonb_build_object('status','offer_unavailable');end if;
 if not (action='upload' and o.sender_id=player and o.state in('uploading','pending') and o.expires_at>now()
 or action='download' and o.recipient_id=player and o.state='applying' and o.apply_until>now())
 then return jsonb_build_object('status','offer_unavailable');end if;
 return jsonb_build_object('status','ok','offer',paw_private.offer_view(o),'object_path',o.sender_id::text||'/'||o.id::text||'.rsg');
end;$$;
revoke all on function public.paw_transfer_authorize(uuid,uuid,uuid,uuid,text) from public,anon,authenticated;
grant execute on function public.paw_transfer_authorize(uuid,uuid,uuid,uuid,text) to service_role;

create function public.paw_transfer_ready(player uuid,session uuid,launcher uuid,offer_id uuid) returns jsonb
language plpgsql security definer set search_path='' as $$
declare o paw_private.social_offers; result jsonb;
begin
 select * into o from paw_private.social_offers where id=offer_id;
 if not found then return jsonb_build_object('status','offer_unavailable');end if;
 perform paw_private.social_lock(o.sender_id,o.recipient_id);
 result:=public.paw_transfer_authorize(player,session,launcher,offer_id,'upload');
 if result->>'status'<>'ok' then return result;end if;
 select * into o from paw_private.social_offers where id=offer_id for update;
 if o.state='uploading' then
  update paw_private.social_offers set state='pending',created_at=clock_timestamp(),expires_at=clock_timestamp()+interval '10 minutes' where id=o.id returning * into o;
  insert into public.paw_messages(sender_id,message_id,recipient_id,kind,body)
  values(o.sender_id,o.id,o.recipient_id,'config','Сохранение · Save: '||o.file_name);
 end if;
 return jsonb_build_object('status','ok','offer',paw_private.offer_view(o));
end;$$;
revoke all on function public.paw_transfer_ready(uuid,uuid,uuid,uuid) from public,anon,authenticated;
grant execute on function public.paw_transfer_ready(uuid,uuid,uuid,uuid) to service_role;

create function public.paw_transfer_cleanup_candidates() returns jsonb
language sql stable security definer set search_path='' as $$
 select coalesce(jsonb_agg(path),'[]'::jsonb) from (
 select sender_id::text||'/'||id::text||'.rsg' path from paw_private.social_offers
 where kind='save' and not storage_cleaned and (state in('accepted','declined','failed')
 or state in('uploading','pending') and expires_at<=now() or state='applying' and apply_until<=now())
 union
 select s.name from storage.objects s where s.bucket_id='paw-social-saves' and s.created_at<now()-interval '5 minutes'
 and not exists(select 1 from paw_private.social_offers o where o.sender_id::text||'/'||o.id::text||'.rsg'=s.name)
 limit 20) q;
$$;
create function public.paw_transfer_cleaned(paths text[]) returns void
language sql security definer set search_path='' as $$
 update paw_private.social_offers set storage_cleaned=true where sender_id::text||'/'||id::text||'.rsg'=any(paths)
 and (state in('accepted','declined','failed') or state in('uploading','pending') and expires_at<=now() or state='applying' and apply_until<=now());
$$;
revoke all on function public.paw_transfer_cleanup_candidates(),public.paw_transfer_cleaned(text[]) from public,anon,authenticated;
grant execute on function public.paw_transfer_cleanup_candidates(),public.paw_transfer_cleaned(text[]) to service_role;
