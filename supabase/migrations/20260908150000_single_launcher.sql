-- One active launcher per account. JWT expiry alone does not revoke access.
-- No Auth rows are edited: ownership is checked at every application data boundary.
create table paw_private.launcher_sessions (
 player_id uuid primary key references public.paw_profiles(id) on delete cascade,
 session_id uuid not null,
 session_started_at timestamptz not null,
 launcher_id uuid not null,
 released boolean not null default false
);
alter table paw_private.launcher_sessions enable row level security;
revoke all on paw_private.launcher_sessions from public, anon, authenticated;

create function paw_private.launcher_header() returns uuid
language plpgsql stable set search_path = '' as $$
declare value text;
begin
 value := current_setting('request.headers',true)::jsonb ->> 'x-paw-launcher';
 if value ~ '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
 then return value::uuid; end if;
 return null;
exception when others then return null;
end;
$$;

create function public.paw_launcher_session(action text, previous uuid default null) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
 player uuid := auth.uid(); instance uuid := paw_private.launcher_header();
 sid uuid; started timestamptz; old paw_private.launcher_sessions;
begin
 if player is null or instance is null or instance='00000000-0000-0000-0000-000000000000'::uuid
 then return jsonb_build_object('status','session_expired'); end if;
 -- Same row/lock order as social mutations and account-actions; takeovers cannot
 -- overtake a previously accepted mutation or a password-change reservation.
 perform 1 from public.paw_profiles where id=player for update;
 if not found then return jsonb_build_object('status','session_expired'); end if;
 select s.id,coalesce(s.created_at,'-infinity'::timestamptz) into sid,started
 from auth.sessions s join auth.users u on u.id=s.user_id
 where s.user_id=player and s.id::text=(auth.jwt()->>'session_id')
 and (s.not_after is null or s.not_after>now()) and u.deleted_at is null and u.email_confirmed_at is not null;
 if sid is null then return jsonb_build_object('status','session_expired'); end if;
 select * into old from paw_private.launcher_sessions where player_id=player;
 if action in ('check','release') then
  if old.player_id is null or old.session_id<>sid or old.launcher_id<>instance or old.released
  then return jsonb_build_object('status','session_replaced'); end if;
  if action='release' then
   if exists(select 1 from paw_private.account_actions where player_id=player and lease_until>clock_timestamp())
   then return jsonb_build_object('status','account_busy'); end if;
   update paw_private.launcher_sessions set released=true where player_id=player;
  end if;
  return jsonb_build_object('status','ok');
 end if;
 if action not in ('claim','resume') then return jsonb_build_object('status','invalid_action'); end if;
 if old.player_id is not null then
  -- Retry of the same claim is idempotent, including after a lost HTTP response.
  if old.session_id=sid and old.launcher_id=instance and not old.released then return jsonb_build_object('status','ok'); end if;
  if action='resume' then
   -- Only a restart holding the last protected lease can resume. A displaced
   -- launcher never grabs ownership back on a poll/network retry.
   if old.session_id<>sid or old.launcher_id is distinct from previous or old.released
   then return jsonb_build_object('status','session_replaced'); end if;
  elsif (started,sid)<=(old.session_started_at,old.session_id) then
   return jsonb_build_object('status','session_replaced');
  end if;
 end if;
 if exists(select 1 from paw_private.account_actions where player_id=player and lease_until>clock_timestamp())
 then return jsonb_build_object('status','account_busy'); end if;
 insert into paw_private.launcher_sessions values(player,sid,started,instance,false)
 on conflict(player_id) do update set session_id=excluded.session_id,session_started_at=excluded.session_started_at,
 launcher_id=excluded.launcher_id,released=false;
 return jsonb_build_object('status','ok');
end;
$$;

create function paw_private.launcher_actor() returns uuid
language sql stable security definer set search_path = '' as $$
 select l.player_id from paw_private.launcher_sessions l
 join auth.sessions s on s.id=l.session_id and s.user_id=l.player_id
 join auth.users u on u.id=l.player_id
 where l.player_id=(select auth.uid()) and s.id::text=(select auth.jwt()->>'session_id')
 and l.launcher_id=(select paw_private.launcher_header()) and not l.released
 and (s.not_after is null or s.not_after>now()) and u.deleted_at is null and u.email_confirmed_at is not null;
$$;
create or replace function paw_private.social_actor() returns uuid
language sql stable security definer set search_path = '' as $$
 select p.id from public.paw_profiles p where p.id=paw_private.launcher_actor() and not p.deletion_pending;
$$;
alter policy paw_profile_self on public.paw_profiles using ((select paw_private.launcher_actor())=id);

-- Keep nickname validation/cooldown implementation; guard it under the same lock.
alter function public.paw_change_nickname(text) rename to change_nickname_impl;
alter function public.change_nickname_impl(text) set schema paw_private;
revoke all on function paw_private.change_nickname_impl(text) from public,anon,authenticated;
create function public.paw_change_nickname(candidate text) returns jsonb
language plpgsql security definer set search_path = '' as $$
begin
 perform 1 from public.paw_profiles where id=auth.uid() for update;
 if paw_private.social_actor() is null then return jsonb_build_object('status','session_replaced'); end if;
 return paw_private.change_nickname_impl(candidate);
end;
$$;
create or replace function public.paw_find_player(candidate text) returns table(id uuid,nickname text)
language sql stable security definer set search_path = '' as $$
 select p.id,p.nickname from public.paw_profiles p
 where paw_private.social_actor() is not null and not p.deletion_pending and paw_private.nickname_valid(candidate)
 and p.nickname_key=paw_private.nickname_key(candidate) collate "C"
 and exists(select 1 from auth.users u where u.id=p.id and u.email_confirmed_at is not null and u.deleted_at is null) limit 1;
$$;

-- Service-only entry points. Old Edge versions fail closed until upgraded.
create or replace function public.paw_account_session_active(player uuid,session uuid) returns boolean
language sql stable security definer set search_path = '' as $$ select false; $$;
create function public.paw_account_session_active(player uuid,session uuid,launcher uuid) returns boolean
language sql stable security definer set search_path = '' as $$
 select exists(select 1 from paw_private.launcher_sessions l
 join auth.sessions s on s.id=l.session_id and s.user_id=l.player_id join auth.users u on u.id=l.player_id
 where l.player_id=player and l.session_id=session and l.launcher_id=launcher and not l.released
 and (s.not_after is null or s.not_after>now()) and u.deleted_at is null and u.email_confirmed_at is not null);
$$;
create function public.paw_begin_launcher_action(player uuid,session uuid,launcher uuid,action text) returns jsonb
language plpgsql security definer set search_path = '' as $$
begin
 perform 1 from public.paw_profiles where id=player for update;
 if not public.paw_account_session_active(player,session,launcher) then return jsonb_build_object('status','session_replaced'); end if;
 return public.paw_begin_account_action(player,action);
end;
$$;
create function public.paw_rotate_launcher_session(player uuid,key uuid,session uuid,launcher uuid,replacement uuid) returns boolean
language plpgsql security definer set search_path = '' as $$
declare started timestamptz;
begin
 perform 1 from public.paw_profiles where id=player for update;
 if not exists(select 1 from paw_private.account_actions where player_id=player and lease=key
   and operation='password' and lease_until>clock_timestamp()) then return false; end if;
 select coalesce(created_at,'-infinity'::timestamptz) into started from auth.sessions
 where id=replacement and user_id=player and (not_after is null or not_after>now());
 if not found then return false; end if;
 -- Auth may already have revoked the original session after changing the password.
 update paw_private.launcher_sessions set session_id=replacement,session_started_at=started
 where player_id=player and session_id=session and launcher_id=launcher and not released;
 return found;
end;
$$;
revoke all on function paw_private.launcher_header(),paw_private.launcher_actor(),
 public.paw_launcher_session(text,uuid),public.paw_change_nickname(text) from public,anon,authenticated;
grant execute on function paw_private.launcher_header(),paw_private.launcher_actor(),
 public.paw_launcher_session(text,uuid),public.paw_change_nickname(text) to authenticated;
revoke all on function public.paw_account_session_active(uuid,uuid,uuid),
 public.paw_begin_launcher_action(uuid,uuid,uuid,text),public.paw_rotate_launcher_session(uuid,uuid,uuid,uuid,uuid)
 from public,anon,authenticated;
grant execute on function public.paw_account_session_active(uuid,uuid,uuid),
 public.paw_begin_launcher_action(uuid,uuid,uuid,text),public.paw_rotate_launcher_session(uuid,uuid,uuid,uuid,uuid) to service_role;
