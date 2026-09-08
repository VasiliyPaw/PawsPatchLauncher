-- Isolated test identities; all inserts and changes are rolled back.
begin;
do $$
declare a uuid:=gen_random_uuid();b uuid:=gen_random_uuid();c uuid:=gen_random_uuid();
 sa uuid:=gen_random_uuid();sb uuid:=gen_random_uuid();sc uuid:=gen_random_uuid();instance uuid:=gen_random_uuid();
 na text:='NameA'||left(replace(a::text,'-',''),12);nb text:='NameB'||left(replace(b::text,'-',''),12);
 nc text:='NameC'||left(replace(c::text,'-',''),12);result jsonb;offer uuid:=gen_random_uuid();attempt uuid:=gen_random_uuid();
 code text:='PAW-BETA-IW0-SP2-RM1-SG0-LM1-RU1-CL0-OOS1-PS0';
begin
 insert into auth.users(id,email,email_confirmed_at,raw_user_meta_data) values
 (a,a||'@example.invalid',now(),jsonb_build_object('nickname',na,'display_name','Same display')),
 (b,b||'@example.invalid',now(),jsonb_build_object('nickname',nb,'display_name','Same display')),
 (c,c||'@example.invalid',now(),jsonb_build_object('nickname',nc));
 if(select count(*) from public.paw_profiles where id in(a,b) and display_name='Same display')<>2 then raise exception 'duplicate display names';end if;
 if(select display_name from public.paw_profiles where id=c)<>nc then raise exception 'legacy signup fallback';end if;
 if public.paw_username_login_target(lower(na),repeat('a',64))->>'email'<>a||'@example.invalid' then raise exception 'private username resolution';end if;
 if public.paw_username_login_target('Missing'||left(replace(c::text,'-',''),12),repeat('b',64))->>'email' not like 'missing-%@example.invalid' then raise exception 'unknown name response';end if;
 insert into auth.sessions(id,user_id) values(sa,a),(sb,b),(sc,c);
 insert into paw_private.launcher_sessions(player_id,session_id,session_started_at,launcher_id)
 values(a,sa,now(),instance),(b,sb,now(),instance),(c,sc,now(),instance);
 perform set_config('request.headers',jsonb_build_object('x-paw-launcher',instance)::text,true);
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a,'session_id',sa,'role','authenticated')::text,true);
 set local role authenticated;
 begin perform public.paw_username_login_target(na,repeat('c',64));raise exception 'public email lookup allowed';exception when insufficient_privilege then null;end;
 begin perform public.paw_social_list_before_names();raise exception 'legacy list direct allowed';exception when insufficient_privilege then null;end;
 if public.paw_change_display_name(' ') ->>'status'<>'invalid_display_name' then raise exception 'blank display';end if;
 if public.paw_change_display_name('New display')->>'status'<>'ok' then raise exception 'change display';end if;
 if public.paw_change_display_name('Again')->>'status'<>'display_name_cooldown' then raise exception 'display cooldown';end if;
 if public.paw_friend_action('request',candidate:=nb)->>'status'<>'ok' then raise exception 'request';end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',b,'session_id',sb,'role','authenticated')::text,true);
 if public.paw_social_list()->'players'->0->>'display_name'<>'New display' then raise exception 'safe friend display';end if;
 if public.paw_friend_action('accept',a)->>'status'<>'ok' then raise exception 'accept';end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a,'session_id',sa,'role','authenticated')::text,true);
 if public.paw_offer_create(b,offer,'config',code,null,null,null)->>'status'<>'ok' then raise exception 'create offer';end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',b,'session_id',sb,'role','authenticated')::text,true);
 if public.paw_offer_action(offer,'cancel',null)->>'status'<>'offer_unavailable' then raise exception 'recipient can cancel sender offer';end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',c,'session_id',sc,'role','authenticated')::text,true);
 if public.paw_offer_action(offer,'cancel',null)->>'status'<>'offer_unavailable' then raise exception 'outsider cancel';end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a,'session_id',sa,'role','authenticated')::text,true);
 if public.paw_offer_action(offer,'cancel',null)->'offer'->>'state'<>'cancelled' then raise exception 'sender cancel';end if;
 if public.paw_offer_action(offer,'cancel',null)->'offer'->>'state'<>'cancelled' then raise exception 'cancel idempotency';end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',b,'session_id',sb,'role','authenticated')::text,true);
 if public.paw_offers(a)->'offers'->0->>'state'<>'cancelled' then raise exception 'receiver shared state';end if;
 if public.paw_offer_action(offer,'begin',attempt)->>'status'<>'offer_unavailable' then raise exception 'cancelled offer accepted';end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a,'session_id',sa,'role','authenticated')::text,true);
 offer:=gen_random_uuid();
 perform public.paw_offer_create(b,offer,'config',code,null,null,null);
 perform set_config('request.jwt.claims',jsonb_build_object('sub',b,'session_id',sb,'role','authenticated')::text,true);
 if public.paw_offer_action(offer,'begin',attempt)->'offer'->>'state'<>'applying' then raise exception 'begin with legacy wrapper';end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a,'session_id',sa,'role','authenticated')::text,true);
 if public.paw_offer_action(offer,'cancel',null)->>'status'<>'offer_unavailable' then raise exception 'sender interrupted application';end if;
 reset role;
end;$$;
rollback;
