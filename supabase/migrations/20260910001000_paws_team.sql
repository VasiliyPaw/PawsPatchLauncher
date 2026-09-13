-- Paw's Team is a non-administrative membership. It never changes moderation power.
-- Role RPC values: -1 Team, 0 User, 1 Admin, 2 Senior Admin. Stored admin_level stays 0..2.
alter table public.paw_profiles add column paws_team boolean not null default false;
grant select(paws_team) on public.paw_profiles to authenticated;
-- No INSERT/UPDATE grant is added; user_metadata does not assign trusted membership.

create or replace function public.paw_admin_action(action text,target uuid,reason text default '',until_at timestamptz default null,level integer default null)
returns jsonb language plpgsql security definer set search_path='' as $$
declare actor uuid; power integer; p public.paw_profiles; address text; bid uuid;
begin
 perform pg_advisory_xact_lock(73190422); -- Serialize grants/revocations before profile locks.
 actor:=paw_private.social_actor();power:=paw_private.admin_level(actor);
 if actor is null or power<1 then return jsonb_build_object('status','admin_required');end if;
 perform paw_private.social_lock(actor,target);
 if paw_private.social_actor() is distinct from actor or paw_private.admin_level(actor)<>power then return jsonb_build_object('status','admin_required');end if;
 select * into p from public.paw_profiles where id=target;
 if action='unban' then
  select email_key into address from paw_private.email_bans where id=target and revoked_at is null for update;
  if address is null then return jsonb_build_object('status','ok');end if;
  -- A normal admin cannot moderate an administrator indirectly through an email record.
  if power<2 and exists(select 1 from auth.users u join public.paw_profiles q on q.id=u.id where paw_private.email_key(u.email)=address and q.admin_level>0)
   then return jsonb_build_object('status','higher_role_required');end if;
  update paw_private.email_bans set revoked_at=clock_timestamp(),revoked_by=actor where id=target;
  update public.paw_profiles set banned_at=null,ban_until=null,ban_reason=null where id in(select id from auth.users where paw_private.email_key(email)=address);
 elsif action in('role','ban','delete','restore') then
  if p.id is null then return jsonb_build_object('status','player_unavailable');end if;
  if p.protected_admin then return jsonb_build_object('status','protected_account');end if;
  if action<>'restore' and target=actor then return jsonb_build_object('status','self_moderation');end if;
  if (action='role' and power<2) or (p.admin_level>0 and power<2) then return jsonb_build_object('status','higher_role_required');end if;
  if exists(select 1 from paw_private.account_actions where player_id=target and lease_until>clock_timestamp()) then return jsonb_build_object('status','account_busy');end if;
  if action='role' then
   if level is null or level not between -1 and 2 or p.deletion_pending or paw_private.player_banned(target) then return jsonb_build_object('status','invalid_action');end if;
   update public.paw_profiles set admin_level=greatest(level,0),paws_team=(level=-1) where id=target;
   if level>0 then delete from public.paw_blocks where target_id=target;end if;
  elsif action='ban' then
   if reason is null or char_length(btrim(reason)) not between 1 and 500 or reason ~ '[[:cntrl:]]'
    or (until_at is not null and (not isfinite(until_at) or until_at<=clock_timestamp())) then return jsonb_build_object('status','invalid_ban');end if;
   select paw_private.email_key(email) into address from auth.users where id=target;
   if address is null then return jsonb_build_object('status','player_unavailable');end if;
   update paw_private.email_bans set revoked_at=clock_timestamp(),revoked_by=actor where email_key=address and revoked_at is null;
   insert into paw_private.email_bans(email_key,until_at,reason,actor_id) values(address,until_at,btrim(reason),actor) returning id into bid;
   update public.paw_profiles set banned_at=clock_timestamp(),ban_until=paw_admin_action.until_at,ban_reason=btrim(reason) where id=target;
   delete from paw_private.social_presence where player_id=target;
   update paw_private.social_offers set state='failed' where target in(sender_id,recipient_id) and state in('uploading','pending','applying');
  elsif action='delete' then
   if not paw_private.soft_delete(target,actor) then return jsonb_build_object('status','player_unavailable');end if;
  else
   if p.deleted_at is null or p.deleted_at+interval '7 days'<=clock_timestamp() or p.purge_started_at is not null then return jsonb_build_object('status','restore_expired');end if;
   update public.paw_profiles set deleted_at=null,deletion_pending=false where id=target;
   update paw_private.player_identities set deleted_at=null where id=target;
  end if;
 else return jsonb_build_object('status','invalid_action');end if;
 insert into paw_private.moderation_audit(actor_id,target_id,action,details) values(actor,target,action,jsonb_build_object('level',level,'until',until_at,'reason',left(reason,500)));
 return jsonb_build_object('status','ok');
end; $$;

create or replace function public.paw_admin_list(section text,query text default '',page integer default 0) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare actor uuid:=paw_private.social_actor(); items jsonb;
begin
 if paw_private.admin_level(actor)<1 then return jsonb_build_object('status','admin_required');end if;
 if page is null or page<0 or page>10000 or query is null or char_length(query)>64 then return jsonb_build_object('status','invalid_request');end if;
 if section='bans' then
  select coalesce(jsonb_agg(to_jsonb(t) order by t.created_at desc,t.id),'[]') into items from (
   select id,email_key email,created_at,until_at,reason from paw_private.email_bans
   where revoked_at is null and (until_at is null or until_at>now()) and strpos(lower(email_key),lower(btrim(query)))>0
   order by created_at desc,id limit 51 offset page*50) t;
 elsif section in('users','deleted') then
  select coalesce(jsonb_agg(to_jsonb(t) order by t.created_at desc,t.id),'[]') into items from (
   select id,nickname,display_name,created_at,admin_level,paws_team,protected_admin,banned_at,ban_until,ban_reason,deleted_at,purge_started_at,
    created_at>now()-interval '24 hours' is_new,avatar_changed_at avatar_revision
   from public.paw_profiles where (section='deleted')=deletion_pending
    and (strpos(lower(nickname),lower(ltrim(btrim(query),'@')))>0 or strpos(lower(display_name),lower(btrim(query)))>0)
   order by created_at desc,id limit 51 offset page*50) t;
 else return jsonb_build_object('status','invalid_request');end if;
 return jsonb_build_object('status','ok','items',items,'server_time',now());
end; $$;

create or replace function paw_private.player_summary(actor uuid,target uuid) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare p public.paw_profiles; stamp timestamptz; state jsonb;
begin
 select * into p from public.paw_profiles where id=target;
 select deleted_at into stamp from paw_private.player_identities where id=target;
 if stamp is not null then return jsonb_build_object('id',target,'nickname','deleted','display_name','Удалённый аккаунт',
  'deleted_at',stamp,'presence','offline','admin_level',0,'paws_team',false,'unread',0,'components','{}'::jsonb,'channel','unknown');end if;
 if p.id is null then return null;end if;
 state:=paw_private.friend_presence(actor,target);
 return state||jsonb_build_object('id',p.id,'nickname',p.nickname,'display_name',p.display_name,'created_at',p.created_at,
  'admin_level',p.admin_level,'paws_team',p.paws_team,'avatar_revision',p.avatar_changed_at,'deleted_at',null,
  'banned_at',case when paw_private.player_banned(p.id) then p.banned_at end,
  'ban_until',case when paw_private.player_banned(p.id) then p.ban_until end,
  'ban_reason',case when paw_private.player_banned(p.id) then p.ban_reason end,
  'presence',case when paw_private.player_banned(p.id) then 'offline' else coalesce(state->>'presence','offline') end);
end; $$;

revoke all on function public.paw_admin_action(text,uuid,text,timestamptz,integer),
 public.paw_admin_list(text,text,integer),paw_private.player_summary(uuid,uuid) from public,anon,authenticated;
grant execute on function public.paw_admin_action(text,uuid,text,timestamptz,integer),
 public.paw_admin_list(text,text,integer) to authenticated;
