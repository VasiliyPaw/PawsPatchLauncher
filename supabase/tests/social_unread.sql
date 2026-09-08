-- Three disposable users; all fixtures roll back. No real messages/accounts are read.
begin;
do $$
declare a uuid:=gen_random_uuid(); b uuid:=gen_random_uuid(); c uuid:=gen_random_uuid();
 sa uuid:=gen_random_uuid(); sb uuid:=gen_random_uuid(); sc uuid:=gen_random_uuid();
 m1 uuid:=gen_random_uuid(); m2 uuid:=gen_random_uuid(); m3 uuid:=gen_random_uuid(); reply uuid:=gen_random_uuid();
 na text:='ReadA'||left(replace(a::text,'-',''),12); nb text:='ReadB'||left(replace(b::text,'-',''),12);
 nc text:='ReadC'||left(replace(c::text,'-',''),12); result jsonb; n integer;
begin
 insert into auth.users(id,email,email_confirmed_at,raw_user_meta_data) values
 (a,a::text||'@example.invalid',now(),jsonb_build_object('nickname',na)),
 (b,b::text||'@example.invalid',now(),jsonb_build_object('nickname',nb)),
 (c,c::text||'@example.invalid',now(),jsonb_build_object('nickname',nc));
 insert into auth.sessions(id,user_id) values(sa,a),(sb,b),(sc,c);
 insert into paw_private.launcher_sessions(player_id,session_id,session_started_at,launcher_id)
 values(a,sa,now(),'99999999-9999-4999-8999-999999999999'),(b,sb,now(),'99999999-9999-4999-8999-999999999999'),(c,sc,now(),'99999999-9999-4999-8999-999999999999');
 perform set_config('request.headers','{"x-paw-launcher":"99999999-9999-4999-8999-999999999999"}',true);
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a,'session_id',sa,'role','authenticated')::text,true);
 set local role authenticated;
 if public.paw_friend_action('request',candidate:=nb)->>'status'<>'ok' then raise exception 'request'; end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',b,'session_id',sb,'role','authenticated')::text,true);
 if public.paw_friend_action('accept',a)->>'status'<>'ok' then raise exception 'accept'; end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a,'session_id',sa,'role','authenticated')::text,true);
 if public.paw_send_message(b,m1,'first')->>'status'<>'ok' then raise exception 'send first'; end if;
 if public.paw_send_message(b,m2,'second')->>'status'<>'ok' then raise exception 'send second'; end if;
 if (public.paw_social_list()->'players'->0->>'unread')::int<>0 then raise exception 'outgoing counted unread'; end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',b,'session_id',sb,'role','authenticated')::text,true);
 if (public.paw_social_list()->'players'->0->>'unread')::int<>2 then raise exception 'incoming count'; end if;
 result:=public.paw_read_messages(a);
 if jsonb_array_length(result->'messages')<>2 or (result->'messages'->0->>'ordinal')::bigint<=0 then raise exception 'snapshot/ordinal'; end if;
 -- Reading a server response alone must not mark it as seen in the launcher.
 if (public.paw_social_list()->'players'->0->>'unread')::int<>2 then raise exception 'fetch marked read'; end if;
 if public.paw_send_message(a,reply,'outgoing reply')->>'status'<>'ok' then raise exception 'reply'; end if;
 if public.paw_mark_messages_read(a,reply)->>'status'<>'invalid_message' then raise exception 'outgoing marker accepted'; end if;
 if public.paw_mark_messages_read(a,gen_random_uuid())->>'status'<>'invalid_message' then raise exception 'random marker accepted'; end if;
 begin
  insert into paw_private.social_receipts(owner_id,peer_id,last_ordinal) values(b,a,9223372036854775807);
  raise exception 'direct cursor write';
 exception when insufficient_privilege then null; end;
 begin
  perform last_ordinal from paw_private.social_receipts;
  raise exception 'private receipts readable';
 exception when insufficient_privilege then null; end;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',c,'session_id',sc,'role','authenticated')::text,true);
 if public.paw_mark_messages_read(a,m1)->>'status'<>'friend_required' then raise exception 'outsider acknowledgement'; end if;
 select count(*) into n from public.paw_messages where sender_id in(a,b); if n<>0 then raise exception 'outsider message access'; end if;
 if jsonb_array_length(public.paw_social_list()->'players')<>0 then raise exception 'outsider unread leak'; end if;
 -- A message arrives after the displayed snapshot, before its acknowledgement.
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a,'session_id',sa,'role','authenticated')::text,true);
 if public.paw_send_message(b,m3,'arrived later')->>'status'<>'ok' then raise exception 'send late'; end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',b,'session_id',sb,'role','authenticated')::text,true);
 result:=public.paw_mark_messages_read(a,m2);
 if result->>'status'<>'ok' or (result->>'unread')::int<>1 then raise exception 'late arrival lost'; end if;
 if (public.paw_social_list()->'players'->0->>'unread')::int<>1 then raise exception 'receipt not persisted'; end if;
 if (public.paw_mark_messages_read(a,m1)->>'unread')::int<>1 then raise exception 'older receipt moved backwards'; end if;
 if (public.paw_mark_messages_read(a,m2)->>'unread')::int<>1 then raise exception 'retry changed cursor'; end if;
 if (public.paw_mark_messages_read(a,m3)->>'unread')::int<>0 then raise exception 'latest not acknowledged'; end if;
 -- A new valid session observes the same server receipt.
 reset role;
 delete from auth.sessions where id=sb and user_id=b;
 sb:=gen_random_uuid(); insert into auth.sessions(id,user_id) values(sb,b);
 update paw_private.launcher_sessions set session_id=sb where player_id=b;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',b,'session_id',sb,'role','authenticated')::text,true);
 set local role authenticated;
 result:=public.paw_social_list();
 if result->>'status'<>'ok' or (result->'players'->0->>'unread')::int is distinct from 0 then raise exception 'restart lost receipt'; end if;
 if public.paw_friend_action('block',a)->>'status'<>'ok' then raise exception 'block'; end if;
 if public.paw_mark_messages_read(a,m3)->>'status'<>'friend_required' then raise exception 'blocked acknowledgement'; end if;
 if (public.paw_social_list()->'players'->0->>'unread')::int<>0 then raise exception 'blocked unread'; end if;
 reset role;
 delete from auth.sessions where id=sb and user_id=b;
 set local role authenticated;
 if public.paw_mark_messages_read(a,m3)->>'status'<>'session_expired' then raise exception 'revoked session acknowledgement'; end if;
 reset role;
end $$;
select 'SOCIAL UNREAD PASS: snapshot markers, late arrival, idempotency, persisted receipts, direct/outsider/blocked/revoked denial' as result;
rollback;
