-- Disposable fixtures; no real users/sessions/messages are inspected or changed.
begin;
do $$
declare a uuid:=gen_random_uuid(); b uuid:=gen_random_uuid();
 sa uuid:=gen_random_uuid(); sa2 uuid:=gen_random_uuid(); sa3 uuid:=gen_random_uuid(); sb uuid:=gen_random_uuid();
 la uuid:=gen_random_uuid(); la2 uuid:=gen_random_uuid(); la3 uuid:=gen_random_uuid(); lb uuid:=gen_random_uuid();
 mid uuid:=gen_random_uuid(); result jsonb; reservation jsonb; n integer;
 na text:='LeaseA'||left(replace(a::text,'-',''),12); nb text:='LeaseB'||left(replace(b::text,'-',''),12);
begin
 insert into auth.users(id,email,email_confirmed_at,raw_user_meta_data) values
 (a,a::text||'@example.invalid',now(),jsonb_build_object('nickname',na)),
 (b,b::text||'@example.invalid',now(),jsonb_build_object('nickname',nb));
 insert into auth.sessions(id,user_id,created_at) values(sa,a,now()-interval '3 minutes'),
 (sa2,a,now()-interval '2 minutes'),(sa3,a,now()-interval '1 minute'),(sb,b,now());
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a,'session_id',sa,'role','authenticated')::text,true);
 perform set_config('request.headers','{}',true);
 set local role authenticated;
 if public.paw_launcher_session('claim')->>'status'<>'session_expired' then raise exception 'missing launcher allowed'; end if;
 perform set_config('request.headers',jsonb_build_object('x-paw-launcher',la)::text,true);
 if public.paw_launcher_session('claim')->>'status'<>'ok' then raise exception 'first claim'; end if;
 if public.paw_launcher_session('claim')->>'status'<>'ok' then raise exception 'retry not idempotent'; end if;
 if public.paw_friend_action('request',candidate:=nb)->>'status'<>'ok' then raise exception 'friend request'; end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',b,'session_id',sb,'role','authenticated')::text,true);
 perform set_config('request.headers',jsonb_build_object('x-paw-launcher',lb)::text,true);
 if public.paw_launcher_session('claim')->>'status'<>'ok' then raise exception 'second account claim'; end if;
 if public.paw_friend_action('accept',a)->>'status'<>'ok' then raise exception 'accept'; end if;
 if public.paw_send_message(a,mid,'private fixture')->>'status'<>'ok' then raise exception 'active friend send'; end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a,'session_id',sa,'role','authenticated')::text,true);
 perform set_config('request.headers',jsonb_build_object('x-paw-launcher',la)::text,true);
 if jsonb_array_length(public.paw_read_messages(b)->'messages')<>1 then raise exception 'active read'; end if;
 -- A second process shares the same saved Auth session but has a new instance ID.
 perform set_config('request.headers',jsonb_build_object('x-paw-launcher',la2)::text,true);
 if public.paw_launcher_session('resume',la2)->>'status'<>'session_replaced' then raise exception 'resume without current proof'; end if;
 if public.paw_launcher_session('resume',la)->>'status'<>'ok' then raise exception 'remembered restart'; end if;
 if public.paw_launcher_session('resume',la)->>'status'<>'ok' then raise exception 'lost-response retry'; end if;
 perform set_config('request.headers',jsonb_build_object('x-paw-launcher',la)::text,true);
 if public.paw_launcher_session('check')->>'status'<>'session_replaced' then raise exception 'old process still active'; end if;
 if public.paw_launcher_session('resume',la)->>'status'<>'session_replaced' then raise exception 'poll reclaimed ownership'; end if;
 if public.paw_launcher_session('claim')->>'status'<>'session_replaced' then raise exception 'same session bypass'; end if;
 if public.paw_launcher_session('release')->>'status'<>'session_replaced' then raise exception 'stale logout killed winner'; end if;
 if public.paw_send_message(b,gen_random_uuid(),'stale')->>'status'<>'session_expired' then raise exception 'old send'; end if;
 if public.paw_read_messages(b)->>'status'<>'session_expired' then raise exception 'old read'; end if;
 if public.paw_mark_messages_read(b,mid)->>'status'<>'session_expired' then raise exception 'old read receipt'; end if;
 if public.paw_friend_action('block',b)->>'status'<>'session_expired' then raise exception 'old block'; end if;
 if public.paw_change_nickname(na||'x')->>'status'<>'session_replaced' then raise exception 'old rename'; end if;
 select count(*) into n from public.paw_profiles where id=a; if n<>0 then raise exception 'old profile RLS'; end if;
 select count(*) into n from public.paw_messages; if n<>0 then raise exception 'old messages RLS'; end if;
 select count(*) into n from public.paw_friendships; if n<>0 then raise exception 'old friends RLS'; end if;
 select count(*) into n from public.paw_find_player(nb); if n<>0 then raise exception 'old lookup'; end if;
 begin
  perform public.paw_account_session_active(a,sa,la2); raise exception 'client invoked service guard';
 exception when insufficient_privilege then null; end;
 begin
  select count(*) into n from paw_private.launcher_sessions; raise exception 'client read other lease';
 exception when insufficient_privilege then null; end;
 reset role;
 if public.paw_account_session_active(a,sa,la) then raise exception 'old edge guard'; end if;
 if not public.paw_account_session_active(a,sa,la2) then raise exception 'winner edge guard'; end if;
 if public.paw_begin_launcher_action(a,sa,la,'avatar_set')->>'status'<>'session_replaced' then raise exception 'old avatar mutation'; end if;
 reservation:=public.paw_begin_launcher_action(a,sa,la2,'password');
 if reservation->>'status'<>'ok' then raise exception 'password reservation'; end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a,'session_id',sa2,'role','authenticated')::text,true);
 perform set_config('request.headers',jsonb_build_object('x-paw-launcher',la3)::text,true);
 set local role authenticated;
 if public.paw_launcher_session('claim')->>'status'<>'account_busy' then raise exception 'takeover during reserved action'; end if;
 reset role;
 if not public.paw_rotate_launcher_session(a,(reservation->>'lease')::uuid,sa,la2,sa2) then raise exception 'password rotation'; end if;
 perform public.paw_finish_account_action(a,(reservation->>'lease')::uuid,true);
 if not public.paw_account_session_active(a,sa2,la2) or public.paw_account_session_active(a,sa,la2) then raise exception 'rotation ownership'; end if;
 -- Real new login (newer server-created Auth session) displaces the old one.
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a,'session_id',sa3,'role','authenticated')::text,true);
 set local role authenticated;
 if public.paw_launcher_session('claim')->>'status'<>'ok' then raise exception 'new login'; end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a,'session_id',sa2,'role','authenticated')::text,true);
 perform set_config('request.headers',jsonb_build_object('x-paw-launcher',la2)::text,true);
 if public.paw_launcher_session('claim')->>'status'<>'session_replaced' then raise exception 'delayed older login won'; end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a,'session_id',sa3,'role','authenticated')::text,true);
 perform set_config('request.headers',jsonb_build_object('x-paw-launcher',la3)::text,true);
 if public.paw_launcher_session('release')->>'status'<>'ok' then raise exception 'release'; end if;
 if public.paw_launcher_session('resume',la3)->>'status'<>'session_replaced' then raise exception 'released session resurrected'; end if;
 -- Another account remains unaffected and cannot read the revoked account's profile.
 perform set_config('request.jwt.claims',jsonb_build_object('sub',b,'session_id',sb,'role','authenticated')::text,true);
 perform set_config('request.headers',jsonb_build_object('x-paw-launcher',lb)::text,true);
 if public.paw_launcher_session('check')->>'status'<>'ok' then raise exception 'other account kicked'; end if;
 select count(*) into n from public.paw_profiles where id=a; if n<>0 then raise exception 'foreign profile'; end if;
 reset role;
 delete from auth.sessions where id=sb;
 set local role authenticated;
 if public.paw_launcher_session('check')->>'status'<>'session_expired' then raise exception 'Auth revocation ignored'; end if;
 reset role;
end;
$$;
select 'SINGLE LAUNCHER PASS: restart, takeover, stale JWT, RLS, Edge guard, password rotation, logout and isolation' as result;
rollback;
