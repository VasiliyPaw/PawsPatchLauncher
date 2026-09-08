-- Run inside a transaction. No Auth API calls or emails; fixtures are rolled back.
begin;
do $$
declare
 a uuid := gen_random_uuid(); b uuid := gen_random_uuid();
 first_name text := 'QA_' || substr(replace(a::text, '-', ''), 1, 14);
 next_name text := 'QB_' || substr(replace(a::text, '-', ''), 1, 14);
 taken_name text := 'QC_' || substr(replace(b::text, '-', ''), 1, 14);
 result jsonb; stamp timestamptz;
begin
 insert into auth.users(id, email, raw_user_meta_data, email_confirmed_at)
 values (a, a::text || '@example.invalid', jsonb_build_object('nickname', first_name), now()),
        (b, b::text || '@example.invalid', jsonb_build_object('nickname', taken_name), now());
 perform set_config('request.jwt.claim.sub', a::text, true);
 set local role authenticated;
 result := public.paw_change_nickname(next_name);
 if result->>'status' != 'ok' then raise exception 'first rename failed'; end if;
 select nickname_changed_at into stamp from public.paw_profiles where id = a;
 if stamp is null then raise exception 'server timestamp not set'; end if;
 if public.paw_change_nickname(next_name)->>'status' != 'unchanged' then raise exception 'same-name no-op failed'; end if;
 result := public.paw_change_nickname(first_name);
 if result->>'status' != 'nickname_cooldown' or (result->>'retry_after')::int not between 1 and 300 then raise exception 'cooldown failed'; end if;
 if public.paw_change_nickname('  ')->>'status' != 'invalid_nickname' then raise exception 'validation failed'; end if;
 if exists(select 1 from public.paw_find_player(first_name)) then raise exception 'old lookup survived'; end if;
 if not exists(select 1 from public.paw_find_player(lower(next_name)) where id = a) then raise exception 'new lookup changed identity'; end if;
 begin
   update public.paw_profiles set nickname_changed_at = null where id = a;
   raise exception 'client bypassed cooldown';
 exception when insufficient_privilege then null;
 end;
 reset role;
 update public.paw_profiles set nickname_changed_at = now() - interval '301 seconds' where id = a;
 set local role authenticated;
 if public.paw_change_nickname(lower(taken_name))->>'status' != 'nickname_taken' then raise exception 'case-insensitive collision accepted'; end if;
 if public.paw_change_nickname(first_name)->>'status' != 'ok' then raise exception 'failed rename consumed cooldown'; end if;
 if (select count(*) from public.paw_profiles) != 1 then raise exception 'RLS isolation lost'; end if;
 reset role;
 if (select nickname from public.paw_profiles where id = b) != taken_name then raise exception 'other player changed'; end if;
 set local role anon;
 begin
   perform public.paw_change_nickname(next_name);
   raise exception 'guest allowed to rename';
 exception when insufficient_privilege then null;
 end;
 reset role;
 perform set_config('request.jwt.claim.sub', '', true);
 set local role authenticated;
 begin
   perform public.paw_change_nickname(next_name);
   raise exception 'missing identity allowed';
 exception when insufficient_privilege then null;
 end;
 reset role;
end;
$$;
rollback;
select 'PASS: rename, server cooldown, same-name no-op, invalid/taken names, case-insensitive lookup, stable id, self-only RLS, denied timestamp writes, anonymous denial; fixtures rolled back' as result;
