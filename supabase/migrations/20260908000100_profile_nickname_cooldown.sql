-- Keep identity stable when a player renames. Only this RPC can update a nickname.
alter table public.paw_profiles add column nickname_changed_at timestamptz;
grant select (created_at, nickname_changed_at) on public.paw_profiles to authenticated;

create function public.paw_change_nickname(candidate text) returns jsonb
language plpgsql security definer set search_path = ''
as $$
declare
 player_id uuid := auth.uid();
 profile public.paw_profiles;
 server_time timestamptz;
begin
 if player_id is null then raise exception 'Authentication required' using errcode = '42501'; end if;
 if not paw_private.nickname_valid(candidate) then return jsonb_build_object('status', 'invalid_nickname'); end if;
 select * into profile from public.paw_profiles where id = player_id for update;
 if not found then return jsonb_build_object('status', 'profile_missing'); end if;
 server_time := clock_timestamp();
 if profile.nickname = candidate then return jsonb_build_object('status', 'unchanged'); end if;
 if profile.nickname_changed_at is not null and profile.nickname_changed_at + interval '5 minutes' > server_time then
   return jsonb_build_object('status', 'nickname_cooldown', 'retry_after',
     ceil(extract(epoch from profile.nickname_changed_at + interval '5 minutes' - server_time))::int);
 end if;
 begin
   update public.paw_profiles set nickname = candidate, nickname_changed_at = server_time where id = player_id;
 exception when unique_violation then return jsonb_build_object('status', 'nickname_taken');
 end;
 return jsonb_build_object('status', 'ok');
end;
$$;
revoke all on function public.paw_change_nickname(text) from public, anon, authenticated;
grant execute on function public.paw_change_nickname(text) to authenticated;
