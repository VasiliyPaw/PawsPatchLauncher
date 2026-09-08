-- Disposable identities only. No real account, message, avatar or presence changes persist.
begin;
do $$
declare a uuid:=gen_random_uuid(); b uuid:=gen_random_uuid(); c uuid:=gen_random_uuid();
 sa uuid:=gen_random_uuid(); sb uuid:=gen_random_uuid(); sc uuid:=gen_random_uuid();
 instance uuid:=gen_random_uuid(); new_instance uuid:=gen_random_uuid();
 na text:='PresA'||left(replace(a::text,'-',''),12); nb text:='PresB'||left(replace(b::text,'-',''),12);
 nc text:='PresC'||left(replace(c::text,'-',''),12); result jsonb; started timestamptz;
begin
 insert into auth.users(id,email,email_confirmed_at,raw_user_meta_data) values
 (a,a::text||'@example.invalid',now(),jsonb_build_object('nickname',na)),
 (b,b::text||'@example.invalid',now(),jsonb_build_object('nickname',nb)),
 (c,c::text||'@example.invalid',now(),jsonb_build_object('nickname',nc));
 insert into auth.sessions(id,user_id) values(sa,a),(sb,b),(sc,c);
 insert into paw_private.launcher_sessions(player_id,session_id,session_started_at,launcher_id)
 values(a,sa,now(),instance),(b,sb,now(),instance),(c,sc,now(),instance);
 perform set_config('request.headers',jsonb_build_object('x-paw-launcher',instance)::text,true);
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a,'session_id',sa,'role','authenticated')::text,true);
 set local role authenticated;
 if public.paw_presence(true,'beta','{"core":true,"colors":false}')->>'status'<>'ok' then raise exception 'presence write'; end if;
 begin perform 1 from paw_private.social_presence;raise exception 'direct private read allowed';exception when insufficient_privilege then null;end;
 begin perform public.paw_friend_avatar_allowed(a,sa,instance,b);raise exception 'client can call service helper';exception when insufficient_privilege then null;end;
 if public.paw_presence(true,'evil','{}')->>'status'<>'invalid_presence' then raise exception 'channel validation'; end if;
 if public.paw_presence(true,'beta','{"path":"private"}')->>'status'<>'invalid_presence' then raise exception 'metadata validation'; end if;
 if public.paw_presence(true,'beta','{"core":"true"}')->>'status'<>'invalid_presence' then raise exception 'boolean validation'; end if;
 if public.paw_friend_action('request',candidate:=nb)->>'status'<>'ok' then raise exception 'request'; end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',b,'session_id',sb,'role','authenticated')::text,true);
 result:=public.paw_social_list()->'players'->0;
 if result?'presence' or result?'components' or result?'avatar_revision' then raise exception 'pending request leaks detail';end if;
 if public.paw_friend_action('accept',a)->>'status'<>'ok' then raise exception 'accept'; end if;
 result:=public.paw_social_list()->'players'->0;
 if result->>'presence'<>'playing' or result->>'channel'<>'beta' or result->'components'<>'{"core":true,"colors":false}'::jsonb
 or result->>'playing_since' is null then raise exception 'friend details missing';end if;
 started:=(result->>'playing_since')::timestamptz;
 reset role;
 if not public.paw_friend_avatar_allowed(b,sb,instance,a) then raise exception 'friend avatar denied';end if;
 if public.paw_friend_avatar_allowed(c,sc,instance,a) then raise exception 'stranger avatar permitted';end if;
 if paw_private.friend_presence(c,a)<>'{}'::jsonb then raise exception 'stranger presence permitted';end if;
 update paw_private.social_presence set seen_at=now()-interval '5 seconds' where player_id=a;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a,'session_id',sa,'role','authenticated')::text,true);
 set local role authenticated;
 perform public.paw_presence(true,'beta','{"core":true}');
 reset role;
 if (select playing_since from paw_private.social_presence where player_id=a)<>started then raise exception 'playing duration reset';end if;
 update paw_private.social_presence set seen_at=now()-interval '41 seconds' where player_id=a;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',b,'session_id',sb,'role','authenticated')::text,true);
 set local role authenticated;
 result:=public.paw_social_list()->'players'->0;
 if result->>'presence'<>'offline' or result->>'playing_since' is not null or result->>'last_seen' is null then raise exception 'TTL offline';end if;
 reset role;
 update paw_private.social_presence set seen_at=now() where player_id=a;
 update paw_private.launcher_sessions set launcher_id=new_instance where player_id=a;
 if paw_private.friend_presence(b,a)->>'presence'<>'offline' then raise exception 'takeover retained stale presence';end if;
 if public.paw_friend_avatar_allowed(a,sa,instance,b) then raise exception 'stale instance avatar permitted';end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a,'session_id',sa,'role','authenticated')::text,true);
 set local role authenticated;
 if public.paw_presence(false,'stable','{}')->>'status'<>'session_expired' then raise exception 'stale instance wrote presence';end if;
 reset role;
 update paw_private.launcher_sessions set launcher_id=instance where player_id=a;
 update paw_private.social_presence set seen_at=now()-interval '5 seconds' where player_id=a;
 set local role authenticated;
 perform public.paw_presence(false,'stable','{"core":true}');
 perform set_config('request.jwt.claims',jsonb_build_object('sub',b,'session_id',sb,'role','authenticated')::text,true);
 if public.paw_social_list()->'players'->0->>'presence'<>'online' then raise exception 'game exit online';end if;
 if public.paw_friend_action('block',a)->>'status'<>'ok' then raise exception 'block';end if;
 result:=public.paw_social_list()->'players'->0;
 if result?'presence' or result?'components' or result?'avatar_revision' then raise exception 'block leaks detail';end if;
 reset role;
 if public.paw_friend_avatar_allowed(b,sb,instance,a) or public.paw_friend_avatar_allowed(a,sa,instance,b) then raise exception 'block avatar access';end if;
 if paw_private.friend_presence(a,b)<>'{}'::jsonb or paw_private.friend_presence(b,a)<>'{}'::jsonb then raise exception 'block presence access';end if;
 raise notice 'FRIEND PRESENCE PASS: friend-only metadata/avatar, pending/stranger/block denial, no direct access, TTL, duration, game exit, takeover and bounded input';
end; $$;
rollback;
