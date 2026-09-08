-- Disposable fixtures only. No real accounts, emails or sessions are accessed.
begin;
do $$
declare a uuid:=gen_random_uuid(); b uuid:=gen_random_uuid(); c uuid:=gen_random_uuid();
 sa uuid:=gen_random_uuid(); sb uuid:=gen_random_uuid(); sc uuid:=gen_random_uuid(); mid uuid:=gen_random_uuid();
 na text:='TestA'||left(replace(a::text,'-',''),12); nb text:='TestB'||left(replace(b::text,'-',''),12);
 nc text:='TestC'||left(replace(c::text,'-',''),12); result jsonb; first_result jsonb; n integer;
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
 if public.paw_send_message(b,mid,'private fixture')->>'status'<>'friend_required' then raise exception 'stranger send'; end if;
 if public.paw_friend_action('request',candidate:=nb)->>'status'<>'ok' then raise exception 'request'; end if;
 if public.paw_friend_action('accept',b)->>'status'<>'request_missing' then raise exception 'self accept'; end if;
 if public.paw_read_messages(b)->>'status'<>'friend_required' then raise exception 'pending read'; end if;
 begin
  insert into public.paw_friendships(low_id,high_id,requester,accepted) values(least(a,c),greatest(a,c),a,true);
  raise exception 'direct friend write';
 exception when insufficient_privilege then null; end;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',b,'session_id',sb,'role','authenticated')::text,true);
 if public.paw_friend_action('request',candidate:=na)->>'status'<>'ok' then raise exception 'crossed request'; end if;
 if public.paw_send_message(a,mid,'still pending')->>'status'<>'friend_required' then raise exception 'crossed auto accepted'; end if;
 if public.paw_friend_action('accept',a)->>'status'<>'ok' then raise exception 'accept'; end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a,'session_id',sa,'role','authenticated')::text,true);
 first_result:=public.paw_send_message(b,mid,'private fixture');
 if first_result->>'status'<>'ok' then raise exception 'accepted send: %',first_result->>'status'; end if;
 result:=public.paw_send_message(b,mid,'private fixture');
 if result<>first_result then raise exception 'retry changed acknowledgement'; end if;
 if public.paw_send_message(b,mid,'changed')->>'status'<>'message_conflict' then raise exception 'id conflict'; end if;
 if public.paw_send_message(b,gen_random_uuid(),'   ')->>'status'<>'invalid_message' then raise exception 'blank accepted'; end if;
 if public.paw_send_message(b,gen_random_uuid(),repeat('x',2001))->>'status'<>'invalid_message' then raise exception 'oversize accepted'; end if;
 if public.paw_send_message(b,gen_random_uuid(),repeat('🙂',1001))->>'status'<>'invalid_message' then raise exception 'UTF16 mismatch'; end if;
 if public.paw_send_message(b,gen_random_uuid(),U&'\00A0\2000')->>'status'<>'invalid_message' then raise exception 'Unicode whitespace accepted'; end if;
 if public.paw_send_message(b,gen_random_uuid(),U&'\0001')->>'status'<>'invalid_message' then raise exception 'control accepted'; end if;
 if public.paw_send_message(b,gen_random_uuid(),U&'\0080')->>'status'<>'invalid_message' then raise exception 'C1 control accepted'; end if;
 begin
  perform public.paw_send_message(b,'00000000-0000-0000-0000-000000000000','zero ID');
  raise exception 'zero ID accepted';
 exception when check_violation then null; end;
 select count(*) into n from public.paw_messages; if n<>1 then raise exception 'dedup'; end if;
 begin
  insert into public.paw_messages(sender_id,message_id,recipient_id,body,kind) values(b,gen_random_uuid(),a,'spoof','text');
  raise exception 'direct message write';
 exception when insufficient_privilege then null; end;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',c,'session_id',sc,'role','authenticated')::text,true);
 select count(*) into n from public.paw_messages; if n<>0 then raise exception 'outsider direct read'; end if;
 select count(*) into n from public.paw_friendships; if n<>0 then raise exception 'outsider friendship read'; end if;
 if public.paw_read_messages(a)->>'status'<>'friend_required' then raise exception 'outsider RPC read'; end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',b,'session_id',sb,'role','authenticated')::text,true);
 if jsonb_array_length(public.paw_read_messages(a)->'messages')<>1 then raise exception 'recipient read'; end if;
 if public.paw_friend_action('block',a)->>'status'<>'ok' then raise exception 'block'; end if;
 select count(*) into n from public.paw_messages; if n<>0 then raise exception 'blocked history read'; end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a,'session_id',sa,'role','authenticated')::text,true);
 if public.paw_send_message(b,gen_random_uuid(),'blocked')->>'status'<>'friend_required' then raise exception 'blocked send'; end if;
 if public.paw_friend_action('request',candidate:=nb)->>'status'<>'player_unavailable' then raise exception 'blocked request'; end if;
 select count(*) into n from public.paw_blocks; if n<>0 then raise exception 'foreign block disclosed'; end if;
 if public.paw_friend_action('unblock',b)->>'status'<>'ok' then raise exception 'unblock own'; end if;
 if public.paw_friend_action('request',candidate:=nb)->>'status'<>'player_unavailable' then raise exception 'unblocked other party'; end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',b,'session_id',sb,'role','authenticated')::text,true);
 if public.paw_friend_action('unblock',a)->>'status'<>'ok' then raise exception 'unblock'; end if;
 if public.paw_read_messages(a)->>'status'<>'friend_required' then raise exception 'unblock restored friendship'; end if;
 if public.paw_friend_action('request',candidate:=na)->>'status'<>'ok' then raise exception 'new request'; end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a,'session_id',sa,'role','authenticated')::text,true);
 if public.paw_friend_action('accept',b)->>'status'<>'ok' then raise exception 'reaccept'; end if;
 if public.paw_friend_action('remove',b)->>'status'<>'ok' then raise exception 'remove'; end if;
 if public.paw_read_messages(b)->>'status'<>'friend_required' then raise exception 'removed read'; end if;
 if public.paw_friend_action('request',candidate:=nb)->>'status'<>'ok' then raise exception 'request for quota test'; end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',b,'session_id',sb,'role','authenticated')::text,true);
 if public.paw_friend_action('accept',a)->>'status'<>'ok' then raise exception 'accept for quota test'; end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a,'session_id',sa,'role','authenticated')::text,true);
 for i in 2..20 loop
  if public.paw_send_message(b,gen_random_uuid(),'quota fixture')->>'status'<>'ok' then raise exception 'message limit too early'; end if;
 end loop;
 if public.paw_send_message(b,gen_random_uuid(),'over limit')->>'status'<>'rate_limit' then raise exception 'message quota absent'; end if;
 if public.paw_send_message(b,mid,'private fixture')<>first_result then raise exception 'retry charged quota'; end if;
 for i in 1..18 loop
  if public.paw_friend_action('request',candidate:=nc)->>'status'<>'ok' then raise exception 'request quota too early'; end if;
  if public.paw_friend_action('cancel',c)->>'status'<>'ok' then raise exception 'cancel for quota'; end if;
 end loop;
 if public.paw_friend_action('request',candidate:=nc)->>'status'<>'rate_limit' then raise exception 'request quota absent'; end if;
 reset role;
 update public.paw_profiles set deletion_pending=true where id=a;
 set local role authenticated;
 if public.paw_social_list()->>'status'<>'session_expired' then raise exception 'deleting account social access'; end if;
 select count(*) into n from public.paw_messages; if n<>0 then raise exception 'deleting account direct read'; end if;
 reset role;
 update public.paw_profiles set deletion_pending=false where id=a;
 update auth.users set email_confirmed_at=null where id=c;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',c,'session_id',sc,'role','authenticated')::text,true);
 set local role authenticated;
 if public.paw_social_list()->>'status'<>'session_expired' then raise exception 'unconfirmed social access'; end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a,'session_id',sa,'role','authenticated')::text,true);
 reset role;
 delete from auth.sessions where id=sa;
 set local role authenticated;
 if public.paw_social_list()->>'status'<>'session_expired' then raise exception 'revoked session accepted'; end if;
 reset role;
 set local role anon;
 begin perform public.paw_social_list(); raise exception 'anon RPC'; exception when insufficient_privilege then null; end;
 begin perform count(*) from public.paw_messages; raise exception 'anon table'; exception when insufficient_privilege then null; end;
 reset role;
end $$;
rollback;
select 'SOCIAL ACCESS PASS: disposable participants + outsider; RLS, grants, live sessions, request lifecycle, block, immutable retries' as result;
