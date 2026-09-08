-- Canonicalize the public identifier, not the display name, UUID or rename timer.
create function paw_private.normalize_profile_username() returns trigger
language plpgsql security definer set search_path='' as $$
begin
 new.nickname:=paw_private.nickname_key(new.nickname);
 return new;
end;$$;
revoke all on function paw_private.normalize_profile_username() from public,anon,authenticated;
create trigger paw_profile_username_normalize before insert or update of nickname on public.paw_profiles
for each row execute function paw_private.normalize_profile_username();

update public.paw_profiles set nickname=paw_private.nickname_key(nickname)
where nickname collate "C" <> paw_private.nickname_key(nickname) collate "C";
alter table public.paw_profiles add constraint paw_profile_username_lowercase
check(nickname collate "C" = paw_private.nickname_key(nickname) collate "C");

-- Case-only requests are unchanged, even during the five-minute rename cooldown.
create or replace function public.paw_change_nickname(candidate text) returns jsonb
language plpgsql security definer set search_path='' as $$
begin
 perform 1 from public.paw_profiles where id=auth.uid() for update;
 if paw_private.social_actor() is null then return jsonb_build_object('status','session_replaced');end if;
 return paw_private.change_nickname_impl(paw_private.nickname_key(candidate));
end;$$;
revoke all on function public.paw_change_nickname(text) from public,anon,authenticated;
grant execute on function public.paw_change_nickname(text) to authenticated;
