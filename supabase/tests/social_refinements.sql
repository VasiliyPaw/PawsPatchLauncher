-- Disposable identities only; all fixture writes are rolled back.
begin;
do $$
declare a uuid:=gen_random_uuid();b uuid:=gen_random_uuid();c uuid:=gen_random_uuid();
 sa uuid:=gen_random_uuid();sb uuid:=gen_random_uuid();sc uuid:=gen_random_uuid();instance uuid:=gen_random_uuid();
 na text:='ЁЖA'||left(replace(a::text,'-',''),12);nb text:='PeerB'||left(replace(b::text,'-',''),12);
 nc text:='PeerC'||left(replace(c::text,'-',''),12);renamed text:='NewЁЖ'||left(replace(a::text,'-',''),12);
 code text:='PAW-BETA-IW0-SP2-RM1-SG0-LM1-RU1-CL0-OOS1';
 different text:='PAW-BETA-IW0-SP4-RM1-SG0-LM1-RU1-CL0-OOS1';
 offered uuid:=gen_random_uuid();result jsonb;stamp timestamptz;
begin
 insert into auth.users(id,email,email_confirmed_at,raw_user_meta_data) values
 (a,a||'@example.invalid',now(),jsonb_build_object('nickname',na,'display_name','Mixed CASE display')),
 (b,b||'@example.invalid',now(),jsonb_build_object('nickname',nb)),
 (c,c||'@example.invalid',now(),jsonb_build_object('nickname',nc));
 if(select nickname from public.paw_profiles where id=a)<>paw_private.nickname_key(na) then raise exception 'signup username not canonical';end if;
 if(select display_name from public.paw_profiles where id=a)<>'Mixed CASE display'
 or(select display_name from public.paw_profiles where id=b)<>nb then raise exception 'display case lost';end if;
 begin
  insert into auth.users(id,email,raw_user_meta_data) values(gen_random_uuid(),'duplicate@example.invalid',jsonb_build_object('nickname',lower(na)));
  raise exception 'duplicate uppercase identifier accepted';
 exception when unique_violation then null;
 end;
 insert into auth.sessions(id,user_id) values(sa,a),(sb,b),(sc,c);
 insert into paw_private.launcher_sessions(player_id,session_id,session_started_at,launcher_id)
 values(a,sa,now(),instance),(b,sb,now(),instance),(c,sc,now(),instance);
 perform set_config('request.headers',jsonb_build_object('x-paw-launcher',instance)::text,true);
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a,'session_id',sa,'role','authenticated')::text,true);
 set local role authenticated;
 if public.paw_change_nickname(na)->>'status'<>'unchanged' then raise exception 'case-only rename changed';end if;
 if(select nickname_changed_at from public.paw_profiles where id=a) is not null then raise exception 'case-only starts cooldown';end if;
 if public.paw_change_nickname(nb)->>'status'<>'nickname_taken' then raise exception 'rename duplicate allowed';end if;
 if public.paw_change_nickname(renamed)->>'status'<>'ok' then raise exception 'rename uppercase rejected';end if;
 select nickname_changed_at into stamp from public.paw_profiles where id=a;
 if(select nickname from public.paw_profiles where id=a)<>lower(renamed) then raise exception 'rename persisted uppercase';end if;
 if public.paw_change_nickname(upper(renamed))->>'status'<>'unchanged' then raise exception 'case-only blocked by cooldown';end if;
 if(select nickname_changed_at from public.paw_profiles where id=a) is distinct from stamp then raise exception 'case-only resets timer';end if;
 if public.paw_change_nickname('NextName')->>'status'<>'nickname_cooldown' then raise exception 'rename cooldown bypass';end if;
 if public.paw_friend_action('request',candidate:=upper(nb))->>'status'<>'ok' then raise exception 'uppercase friend request';end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',b,'session_id',sb,'role','authenticated')::text,true);
 if public.paw_friend_action('accept',a)->>'status'<>'ok' then raise exception 'accept';end if;
 if public.paw_presence(true,'beta','{}',code)->>'status'<>'ok' then raise exception 'recipient configuration';end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a,'session_id',sa,'role','authenticated')::text,true);
 if public.paw_offer_create(b,gen_random_uuid(),'config',code,null,null,null)->>'status'<>'configuration_matches' then raise exception 'identical allowed';end if;
 if public.paw_offer_create(b,gen_random_uuid(),'config',code||'-PS1',null,null,null)->>'status'<>'configuration_matches' then raise exception 'explicit legacy default bypass';end if;
 if public.paw_offer_create(b,gen_random_uuid(),'config',code||'-PS0',null,null,null)->>'status'<>'ok' then raise exception 'powers change wrongly equal';end if;
 if public.paw_offer_create(b,offered,'config',different,null,null,null)->>'status'<>'ok' then raise exception 'different offer failed';end if;
 if public.paw_offer_create(b,gen_random_uuid(),'save',null,'fixture.rsg',16,repeat('a',64))->>'status'<>'ok' then raise exception 'save blocked by configuration/game';end if;
 -- A legitimate retry must work even if the recipient now has the offered settings.
 reset role;
 update paw_private.social_presence set configuration=different where player_id=b;
 set local role authenticated;
 if public.paw_offer_create(b,offered,'config',different,null,null,null)->>'status'<>'ok' then raise exception 'retry lost idempotency';end if;
 if public.paw_offer_create(b,gen_random_uuid(),'config',different,null,null,null)->>'status'<>'configuration_matches' then raise exception 'fresh identical offer after recipient change';end if;
 reset role;
 if(select count(*) from public.paw_messages where sender_id=a and message_id=offered)<>1 then raise exception 'retry duplicate';end if;
 set local role authenticated;
 perform set_config('request.headers',jsonb_build_object('x-paw-launcher',gen_random_uuid())::text,true);
 if public.paw_change_nickname(renamed)->>'status'<>'session_replaced' then raise exception 'stale rename allowed';end if;
 if public.paw_offer_create(b,gen_random_uuid(),'config',code,null,null,null)->>'status'<>'session_expired' then raise exception 'stale offer allowed';end if;
 perform set_config('request.headers',jsonb_build_object('x-paw-launcher',instance)::text,true);
 perform set_config('request.jwt.claims',jsonb_build_object('sub',c,'session_id',sc,'role','authenticated')::text,true);
 if public.paw_offer_create(b,gen_random_uuid(),'config',different,null,null,null)->>'status'<>'friend_required' then raise exception 'outsider configuration disclosure';end if;
 if public.paw_offers(b)->>'status'<>'friend_required' then raise exception 'outsider offer read';end if;
 begin perform paw_private.normalize_profile_username();raise exception 'private trigger exposed';exception when insufficient_privilege then null;end;
 reset role;
end;$$;
rollback;
