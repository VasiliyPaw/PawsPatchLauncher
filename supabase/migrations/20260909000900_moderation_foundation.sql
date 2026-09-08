-- Trusted roles, email sanctions and seven-day deletion. No client table writes.
create or replace function paw_private.nickname_valid(value text) returns boolean
language sql immutable set search_path='' as $$
 select value is not null and char_length(value) between 3 and 24
 and value ~ '^[A-Za-z0-9]' and value !~ '[^A-Za-z0-9_.-]';
$$;
-- Validate existing data explicitly; never silently rename an existing player.
do $$ begin
 if exists(select 1 from public.paw_profiles where not paw_private.nickname_valid(nickname)) then
  raise exception 'Existing non-ASCII usernames require an explicit migration';
 end if;
end; $$;

alter table public.paw_profiles
 add column admin_level smallint not null default 0 check(admin_level between 0 and 2),
 add column protected_admin boolean not null default false,
 add column banned_at timestamptz,
 add column ban_until timestamptz,
 add column ban_reason text,
 add column deleted_at timestamptz,
 add column purge_started_at timestamptz,
 add constraint paw_protected_admin check(not protected_admin or admin_level=2);
grant select(admin_level,protected_admin,banned_at,ban_until,ban_reason,deleted_at,purge_started_at) on public.paw_profiles to authenticated;
create index paw_profiles_registration on public.paw_profiles(created_at desc,id);
create index paw_profiles_deletion on public.paw_profiles(deleted_at) where deleted_at is not null;

create table paw_private.email_bans(
 id uuid primary key default gen_random_uuid(), email_key text not null,
 created_at timestamptz not null default clock_timestamp(), until_at timestamptz,
 reason text not null check(char_length(reason) between 1 and 500),
 actor_id uuid not null, revoked_at timestamptz, revoked_by uuid,
 check(until_at is null or until_at>created_at));
create unique index paw_current_email_ban on paw_private.email_bans(email_key) where revoked_at is null;
create table paw_private.moderation_audit(
 id bigint generated always as identity primary key, at timestamptz not null default clock_timestamp(),
 actor_id uuid, target_id uuid, action text not null, details jsonb not null default '{}');
create table paw_private.player_identities(id uuid primary key, deleted_at timestamptz, finalized_at timestamptz);
insert into paw_private.player_identities(id) select id from public.paw_profiles;
create table paw_private.hidden_chats(owner_id uuid references public.paw_profiles on delete cascade,
 peer_id uuid references paw_private.player_identities on delete cascade, primary key(owner_id,peer_id));
create table paw_private.archived_chats(owner_id uuid references public.paw_profiles on delete cascade,
 peer_id uuid references paw_private.player_identities, primary key(owner_id,peer_id));
create table paw_private.official_chats(low_id uuid references public.paw_profiles on delete cascade,
 high_id uuid references public.paw_profiles on delete cascade, opened_by uuid not null,
 created_at timestamptz not null default clock_timestamp(), primary key(low_id,high_id),check(low_id<high_id));
do $$ declare tab text; begin
 foreach tab in array array['email_bans','moderation_audit','player_identities','hidden_chats','archived_chats','official_chats'] loop
  execute format('alter table paw_private.%I enable row level security',tab);
  execute format('revoke all on paw_private.%I from public,anon,authenticated',tab);
 end loop;
end; $$;
revoke all on sequence paw_private.moderation_audit_id_seq from public,anon,authenticated;

-- Message participant IDs survive Auth/profile purge without retaining profile data.
alter table public.paw_messages drop constraint paw_messages_sender_id_fkey, drop constraint paw_messages_recipient_id_fkey;
alter table public.paw_messages add foreign key(sender_id) references paw_private.player_identities(id),
 add foreign key(recipient_id) references paw_private.player_identities(id);
alter table paw_private.social_receipts drop constraint social_receipts_peer_id_fkey;
alter table paw_private.social_receipts add foreign key(peer_id) references paw_private.player_identities(id);
create function paw_private.profile_identity() returns trigger language plpgsql security definer set search_path='' as $$
begin insert into paw_private.player_identities(id) values(new.id) on conflict do nothing; return new; end; $$;
create trigger paw_profile_identity after insert on public.paw_profiles for each row execute function paw_private.profile_identity();
create function paw_private.protect_founder() returns trigger language plpgsql security definer set search_path='' as $$
begin
 if old.protected_admin and (tg_op='DELETE' or not new.protected_admin or new.admin_level<>2
  or new.deletion_pending or new.deleted_at is not null or new.banned_at is not null) then raise exception 'protected_account';end if;
 if tg_op='DELETE' then return old;end if;return new;
end; $$;
create trigger paw_protect_founder before update or delete on public.paw_profiles for each row execute function paw_private.protect_founder();

create function paw_private.email_key(address text) returns text language sql immutable set search_path='' as $$
 select lower(btrim(address)) collate "C"; -- No unsafe provider-independent dot/plus rewriting.
$$;
create function paw_private.email_banned(address text) returns boolean language sql stable security definer set search_path='' as $$
 select exists(select 1 from paw_private.email_bans where email_key=paw_private.email_key(address)
 and revoked_at is null and (until_at is null or until_at>now()));
$$;
create function paw_private.player_banned(player uuid) returns boolean language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.paw_profiles where id=player and banned_at is not null and (ban_until is null or ban_until>now()));
$$;
create function paw_private.player_live(player uuid) returns boolean language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.paw_profiles where id=player and not deletion_pending and not paw_private.player_banned(player));
$$;
create or replace function paw_private.social_actor() returns uuid language sql stable security definer set search_path='' as $$
 select p.id from public.paw_profiles p where p.id=paw_private.launcher_actor() and paw_private.player_live(p.id);
$$;
create function paw_private.admin_level(player uuid) returns smallint language sql stable security definer set search_path='' as $$
 select coalesce((select admin_level from public.paw_profiles where id=player and paw_private.player_live(player)),0)::smallint;
$$;

-- Auth remains usable for a restricted sign-in and local gameplay. Sensitive Auth
-- changes and signup are independently guarded even outside the launcher/Edge UI.
create function paw_private.auth_moderation_guard() returns trigger language plpgsql security definer set search_path='' as $$
begin
 if tg_op='INSERT' then
  if paw_private.email_banned(new.email) then raise exception 'email_banned';end if;
 elsif new.email is distinct from old.email or new.email_change is distinct from old.email_change
  or new.encrypted_password is distinct from old.encrypted_password then
  perform 1 from public.paw_profiles where id=old.id for update;
  if paw_private.player_banned(old.id) or exists(select 1 from public.paw_profiles where id=old.id and deletion_pending)
   then raise exception 'account_restricted';end if;
  if (new.email is distinct from old.email and paw_private.email_banned(new.email))
   or (coalesce(new.email_change,'')<>'' and paw_private.email_banned(new.email_change)) then raise exception 'email_banned';end if;
 end if;
 return new;
end; $$;
create trigger paw_auth_moderation before insert or update of email,email_change,encrypted_password on auth.users
 for each row execute function paw_private.auth_moderation_guard();
create function public.paw_registration_check(address text,candidate text) returns jsonb language plpgsql stable security definer set search_path='' as $$
begin
 if address is null or char_length(address)>254 then return jsonb_build_object('status','invalid_email');end if;
 if not paw_private.nickname_valid(candidate) then return jsonb_build_object('status','invalid_nickname');end if;
 if paw_private.email_banned(address) then return jsonb_build_object('status','email_banned');end if;
 return jsonb_build_object('status','ok');
end; $$;
create function public.paw_account_action_allowed(player uuid,action text,address text default null) returns text
language sql stable security definer set search_path='' as $$
 select case
 when action='delete' and exists(select 1 from public.paw_profiles where id=player and protected_admin) then 'protected_account'
 when action<>'delete' and exists(select 1 from public.paw_profiles where id=player and deletion_pending) then 'account_deletion_pending'
 when action not in('delete','avatar_get') and paw_private.player_banned(player) then 'account_banned'
 when action='email' and paw_private.email_banned(address) then 'email_banned'
 else 'ok' end;
$$;
create or replace function public.paw_begin_launcher_action(player uuid,session uuid,launcher uuid,action text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare allowed text;
begin
 perform 1 from public.paw_profiles where id=player for update;
 if not public.paw_account_session_active(player,session,launcher) then return jsonb_build_object('status','session_replaced');end if;
 allowed:=public.paw_account_action_allowed(player,action);
 if allowed<>'ok' then return jsonb_build_object('status',allowed);end if;
 return public.paw_begin_account_action(player,action);
end; $$;

create function paw_private.soft_delete(player uuid,actor uuid) returns boolean language plpgsql security definer set search_path='' as $$
begin
 perform 1 from public.paw_profiles where id=player for update;
 if not found or exists(select 1 from public.paw_profiles where id=player and protected_admin) then return false;end if;
 insert into paw_private.archived_chats(owner_id,peer_id)
 select case when low_id=player then high_id else low_id end,player from public.paw_friendships where player in(low_id,high_id) and accepted
 union select case when low_id=player then high_id else low_id end,player from paw_private.official_chats where player in(low_id,high_id)
 on conflict do nothing;
 update public.paw_profiles set deleted_at=coalesce(deleted_at,clock_timestamp()),deletion_pending=true where id=player;
 update paw_private.player_identities set deleted_at=(select deleted_at from public.paw_profiles where id=player) where id=player;
 delete from paw_private.social_presence where player_id=player;
 update paw_private.social_offers set state='failed' where player in(sender_id,recipient_id) and state in('uploading','pending','applying');
 insert into paw_private.moderation_audit(actor_id,target_id,action) values(actor,player,'delete');
 return true;
end; $$;
create or replace function public.paw_mark_account_deleting(player uuid,key uuid) returns boolean
language plpgsql security definer set search_path='' as $$
begin
 perform 1 from public.paw_profiles where id=player for update;
 if not exists(select 1 from paw_private.account_actions where player_id=player and lease=key and operation='delete' and lease_until>clock_timestamp()) then return false;end if;
 return paw_private.soft_delete(player,player);
end; $$;

-- Roles and email addresses never come from user_metadata or caller-supplied role claims.
create function public.paw_admin_action(action text,target uuid,reason text default '',until_at timestamptz default null,level integer default null)
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
   if level is null or level not between 0 and 2 or p.deletion_pending or paw_private.player_banned(target) then return jsonb_build_object('status','invalid_action');end if;
   update public.paw_profiles set admin_level=level where id=target;
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

create function public.paw_admin_list(section text,query text default '',page integer default 0) returns jsonb
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
   select id,nickname,display_name,created_at,admin_level,protected_admin,banned_at,ban_until,ban_reason,deleted_at,purge_started_at,
    created_at>now()-interval '24 hours' is_new,avatar_changed_at avatar_revision
   from public.paw_profiles where (section='deleted')=deletion_pending
    and (strpos(lower(nickname),lower(ltrim(btrim(query),'@')))>0 or strpos(lower(display_name),lower(btrim(query)))>0)
   order by created_at desc,id limit 51 offset page*50) t;
 else return jsonb_build_object('status','invalid_request');end if;
 return jsonb_build_object('status','ok','items',items,'server_time',now());
end; $$;

revoke all on function paw_private.profile_identity(),paw_private.protect_founder(),paw_private.email_key(text),paw_private.email_banned(text),
 paw_private.player_banned(uuid),paw_private.player_live(uuid),paw_private.admin_level(uuid),paw_private.auth_moderation_guard(),paw_private.soft_delete(uuid,uuid),
 public.paw_registration_check(text,text),public.paw_account_action_allowed(uuid,text,text),public.paw_admin_action(text,uuid,text,timestamptz,integer),public.paw_admin_list(text,text,integer)
 from public,anon,authenticated;
grant execute on function public.paw_registration_check(text,text) to anon,authenticated;
grant execute on function public.paw_account_action_allowed(uuid,text,text) to service_role;
grant execute on function public.paw_admin_action(text,uuid,text,timestamptz,integer),public.paw_admin_list(text,text,integer) to authenticated;
