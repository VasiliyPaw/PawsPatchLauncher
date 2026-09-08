-- Only the account Edge Function can mutate these fields or access avatar objects.
alter table public.paw_profiles
 add column email_changed_at timestamptz,
 add column password_changed_at timestamptz,
 add column avatar_changed_at timestamptz,
 add column deletion_pending boolean not null default false;
grant select(email_changed_at, password_changed_at, avatar_changed_at, deletion_pending)
 on public.paw_profiles to authenticated;

create table paw_private.account_actions (
 player_id uuid primary key references public.paw_profiles(id) on delete cascade,
 lease uuid,
 lease_until timestamptz,
 operation text,
 previous_changed_at timestamptz
);
alter table paw_private.account_actions enable row level security;
revoke all on paw_private.account_actions from public, anon, authenticated;

-- Private, bounded, non-versioned; no client write policies. One fixed JPEG per player.
insert into storage.buckets(id, name, public, file_size_limit, allowed_mime_types)
 values ('paw-avatars', 'paw-avatars', false, 204800, array['image/jpeg']);

create function public.paw_account_session_active(player uuid, session uuid) returns boolean
language sql stable security definer set search_path = ''
as $$
 select exists(select 1 from auth.sessions s join auth.users u on u.id=s.user_id
 join public.paw_profiles p on p.id=u.id
 where s.id=session and s.user_id=player and u.deleted_at is null
 and u.email_confirmed_at is not null
 and (s.not_after is null or s.not_after > now()));
$$;

create function public.paw_begin_account_action(player uuid, action text) returns jsonb
language plpgsql security definer set search_path = ''
as $$
declare
 p public.paw_profiles;
 a paw_private.account_actions;
 stamp timestamptz := clock_timestamp();
 changed timestamptz;
 key uuid := gen_random_uuid();
begin
 if action not in ('email','password','avatar_set','avatar_remove','delete') then
  return jsonb_build_object('status','invalid_action');
 end if;
 select * into p from public.paw_profiles where id=player for update;
 if not found then return jsonb_build_object('status','profile_missing'); end if;
 if p.deletion_pending and action <> 'delete' then
  return jsonb_build_object('status','account_deletion_pending');
 end if;
 insert into paw_private.account_actions(player_id) values(player) on conflict do nothing;
 select * into a from paw_private.account_actions where player_id=player for update;
 if a.lease_until > stamp then return jsonb_build_object('status','account_busy'); end if;
 changed := case action when 'email' then p.email_changed_at when 'password' then p.password_changed_at end;
 if changed + interval '5 minutes' > stamp then
  return jsonb_build_object('status',action || '_cooldown');
 end if;
 update paw_private.account_actions set lease=key, lease_until=stamp+interval '2 minutes',
  operation=action, previous_changed_at=changed where player_id=player;
 -- Reserve the cooldown durably before calling Auth. A crash cannot bypass the interval.
 -- A definitively rejected request restores the previous timestamp in finish.
 if action='email' then update public.paw_profiles set email_changed_at=stamp where id=player; end if;
 if action='password' then update public.paw_profiles set password_changed_at=stamp where id=player; end if;
 return jsonb_build_object('status','ok','lease',key);
end;
$$;

create function public.paw_mark_account_deleting(player uuid, key uuid) returns boolean
language plpgsql security definer set search_path = ''
as $$
begin
 perform 1 from public.paw_profiles where id=player for update;
 if not exists(select 1 from paw_private.account_actions where player_id=player and lease=key
  and operation='delete' and lease_until > clock_timestamp()) then return false; end if;
 update public.paw_profiles set deletion_pending=true where id=player;
 return true;
end;
$$;

create function public.paw_finish_account_action(player uuid, key uuid, succeeded boolean) returns void
language plpgsql security definer set search_path = ''
as $$
declare a paw_private.account_actions;
begin
 perform 1 from public.paw_profiles where id=player for update;
 select * into a from paw_private.account_actions where player_id=player and lease=key for update;
 if not found then return; end if;
 if a.operation='email' then update public.paw_profiles set email_changed_at=
  case when succeeded then clock_timestamp() else a.previous_changed_at end where id=player; end if;
 if a.operation='password' then update public.paw_profiles set password_changed_at=
  case when succeeded then clock_timestamp() else a.previous_changed_at end where id=player; end if;
 if succeeded and a.operation in ('avatar_set','avatar_remove') then
  update public.paw_profiles set avatar_changed_at=clock_timestamp() where id=player;
 end if;
 update paw_private.account_actions set lease=null,lease_until=null,operation=null,previous_changed_at=null
 where player_id=player and lease=key;
end;
$$;

revoke all on function public.paw_account_session_active(uuid,uuid),
 public.paw_begin_account_action(uuid,text), public.paw_mark_account_deleting(uuid,uuid),
 public.paw_finish_account_action(uuid,uuid,boolean) from public,anon,authenticated;
grant execute on function public.paw_account_session_active(uuid,uuid),
 public.paw_begin_account_action(uuid,text), public.paw_mark_account_deleting(uuid,uuid),
 public.paw_finish_account_action(uuid,uuid,boolean) to service_role;

-- No lookup from a deleted account's still-unexpired JWT, and no results pending deletion.
create or replace function public.paw_find_player(candidate text) returns table(id uuid,nickname text)
language sql stable security definer set search_path = ''
as $$
 select p.id,p.nickname from public.paw_profiles p
 where exists(select 1 from public.paw_profiles caller where caller.id=(select auth.uid()) and not caller.deletion_pending)
 and not p.deletion_pending and paw_private.nickname_valid(candidate)
 and p.nickname_key=paw_private.nickname_key(candidate) collate "C"
 and exists(select 1 from auth.users u where u.id=p.id and u.email_confirmed_at is not null and u.deleted_at is null)
 limit 1;
$$;
