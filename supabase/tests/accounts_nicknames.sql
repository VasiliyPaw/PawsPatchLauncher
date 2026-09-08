begin;
do $$
declare a uuid := gen_random_uuid(); b uuid := gen_random_uuid(); n text;
begin
 perform set_config('paw_test.a', a::text, true);
 perform set_config('paw_test.b', b::text, true);
 foreach n in array array['', ' ', '   ', 'ab', ' Paw', 'Paw ', 'a b', 'a'||chr(9)||'b', 'a'||chr(10)||'b', 'a'||chr(8203)||'b', '.Paw', '_Paw', '😀Paw', repeat('a',25)] loop
   if paw_private.nickname_valid(n) or public.paw_nickname_available(n) then raise exception 'Invalid nickname accepted'; end if;
 end loop;
 foreach n in array array['Paw', 'Пав', 'Ёжик', 'Paw_123', 'Пав-2', 'Paw.Test', repeat('a',24)] loop
   if not paw_private.nickname_valid(n) then raise exception 'Valid nickname rejected'; end if;
 end loop;
 insert into auth.users(id,email,email_confirmed_at,raw_user_meta_data)
 values(a,'paw-test-'||a::text||'@example.invalid',now(),'{"nickname":"PawTestЁжик"}'::jsonb);
 if public.paw_nickname_available('pawtestёжик') then raise exception 'Case-insensitive nickname reservation failed'; end if;
 begin
   insert into auth.users(id,email,raw_user_meta_data) values(b,'paw-test-'||b::text||'@example.invalid','{"nickname":"pawtestёжик"}'::jsonb);
   raise exception 'Duplicate nickname accepted';
 exception when unique_violation then null;
 end;
 begin
   insert into auth.users(id,email,raw_user_meta_data) values(b,'paw-test-'||b::text||'@example.invalid','{"nickname":"   "}'::jsonb);
   raise exception 'Blank signup accepted';
 exception when check_violation then null;
 end;
 insert into auth.users(id,email,email_confirmed_at,raw_user_meta_data)
 values(b,'paw-test-'||b::text||'@example.invalid',now(),'{"nickname":"OtherTest"}'::jsonb);
 update auth.users set raw_user_meta_data='{"nickname":"OtherTest"}'::jsonb where id=a;
 if (select nickname from public.paw_profiles where id=a)<>'PawTestЁжик' then raise exception 'Mutable metadata changed identity'; end if;
end $$;
set local role authenticated;
select set_config('request.jwt.claim.sub',current_setting('paw_test.a'),true);
do $$
declare count_visible integer;
begin
 select count(id) into count_visible from public.paw_profiles;
 if count_visible<>1 then raise exception 'RLS exposed another profile'; end if;
 if (select nickname from public.paw_profiles) <> 'PawTestЁжик' then raise exception 'Wrong own profile'; end if;
 if (select nickname from public.paw_find_player('othertest')) <> 'OtherTest' then raise exception 'Exact nickname lookup failed'; end if;
 if exists(select 1 from public.paw_find_player('Other%')) then raise exception 'Pattern lookup allowed'; end if;
 begin
   update public.paw_profiles set nickname='StolenName' where id=current_setting('paw_test.a')::uuid;
   raise exception 'Direct nickname edit allowed';
 exception when insufficient_privilege then null;
 end;
 begin
   perform nickname_key from public.paw_profiles;
   raise exception 'Private column accessible';
 exception when insufficient_privilege then null;
 end;
end $$;
set local role anon;
select set_config('request.jwt.claim.sub','',true);
do $$
begin
 if public.paw_nickname_available('pawtestЁжик') then raise exception 'Availability leaked wrong case'; end if;
 begin
   perform id from public.paw_profiles;
   raise exception 'Guest could read profiles';
 exception when insufficient_privilege then null;
 end;
 begin
   perform * from public.paw_find_player('OtherTest');
   raise exception 'Guest could look up players';
 exception when insufficient_privilege then null;
 end;
end $$;
rollback;
select 'PASS: validation, case-insensitive unique reservation, signup trigger, immutable nickname, RLS, column grants, exact lookup, guest isolation; test accounts rolled back' as result;
