-- Synthetic identities only. No email is sent; every data change is rolled back.
begin;
do $$
declare a uuid:=gen_random_uuid();b uuid:=gen_random_uuid();c uuid:=gen_random_uuid();d uuid:=gen_random_uuid();
 sa uuid:=gen_random_uuid();instance uuid:=gen_random_uuid(); first_id uuid:=gen_random_uuid();last_id uuid:=gen_random_uuid();
 stamp timestamptz:=now()-interval '1 hour'; wanted bigint; result jsonb; item jsonb;
begin
 insert into auth.users(id,email,email_confirmed_at,raw_user_meta_data)
 select id,id||'@example.invalid',now(),jsonb_build_object('nickname','activity'||left(replace(id::text,'-',''),12))
 from unnest(array[a,b,c,d]) id;
 insert into auth.sessions(id,user_id) values(sa,a);
 insert into paw_private.launcher_sessions(player_id,session_id,session_started_at,launcher_id) values(a,sa,now(),instance);
 insert into public.paw_friendships(low_id,high_id,requester,accepted)
 values(least(a,b),greatest(a,b),a,true),(least(a,c),greatest(a,c),a,false);
 insert into public.paw_messages(sender_id,message_id,recipient_id,body,kind,created_at) values
 (a,first_id,b,'synthetic outgoing','text',stamp),(b,last_id,a,'synthetic incoming','text',stamp),
 (c,gen_random_uuid(),d,'unrelated newer message','text',stamp+interval '1 minute'),
 (a,gen_random_uuid(),c,'old non-friend history','text',stamp);
 select ordinal into wanted from public.paw_messages where sender_id=b and message_id=last_id;
 perform set_config('request.headers',jsonb_build_object('x-paw-launcher',instance)::text,true);
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a,'session_id',sa,'role','authenticated')::text,true);
 set local role authenticated;
 result:=public.paw_social_list();
 if result->>'status'<>'ok' then raise exception 'list rejected';end if;
 select p into item from jsonb_array_elements(result->'players') p where p->>'id'=b::text;
 if (item->>'last_message_at')::timestamptz is distinct from stamp or (item->>'last_message_ordinal')::bigint is distinct from wanted
 then raise exception 'bidirectional/tie activity mismatch';end if;
 select p into item from jsonb_array_elements(result->'players') p where p->>'id'=c::text;
 if item->>'last_message_at' is not null or (item->>'last_message_ordinal')::bigint is distinct from 0
 then raise exception 'request leaked history activity';end if;
 if exists(select 1 from jsonb_array_elements(result->'players') p where p->>'id'=d::text) then raise exception 'outsider leak';end if;
 reset role;
 update public.paw_messages set created_at=stamp+interval '2 minutes' where sender_id=a and message_id=first_id;
 select ordinal into wanted from public.paw_messages where sender_id=a and message_id=first_id;
 set local role authenticated;
 select p into item from jsonb_array_elements(public.paw_social_list()->'players') p where p->>'id'=b::text;
 if (item->>'last_message_ordinal')::bigint is distinct from wanted then raise exception 'own latest message ignored';end if;
 if public.paw_friend_action('block',b)->>'status'<>'ok' then raise exception 'block failed';end if;
 select p into item from jsonb_array_elements(public.paw_social_list()->'players') p where p->>'id'=b::text;
 if item->>'last_message_at' is not null or item->>'relation'<>'blocked' then raise exception 'blocked metadata leak';end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a,'session_id',gen_random_uuid(),'role','authenticated')::text,true);
 if public.paw_social_list()->>'status'='ok' then raise exception 'invalid session accepted';end if;
 reset role;
 if has_function_privilege('anon','public.paw_social_list()','execute') then raise exception 'anon grant changed';end if;
 if not has_function_privilege('authenticated','public.paw_social_list()','execute') then raise exception 'authenticated grant missing';end if;
end $$;
rollback;
select 'CHAT ACTIVITY PASS: both directions, equal-time tie, unrelated peers, pending/blocked privacy, session guard and preserved grants; fixtures rolled back' as result;
