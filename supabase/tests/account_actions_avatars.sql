begin;
do $$
declare
 player uuid := gen_random_uuid();
 other uuid := gen_random_uuid();
 a jsonb; b jsonb; old_stamp timestamptz;
begin
 if has_function_privilege('authenticated','public.paw_begin_account_action(uuid,text)','execute')
  or has_function_privilege('anon','public.paw_mark_account_deleting(uuid,uuid)','execute')
  or has_function_privilege('authenticated','public.paw_finish_account_action(uuid,uuid,boolean)','execute')
 then raise exception 'Privileged account RPC exposed'; end if;
 if has_column_privilege('authenticated','public.paw_profiles','email_changed_at','update')
  or has_column_privilege('authenticated','public.paw_profiles','deletion_pending','update')
 then raise exception 'Client can edit protected fields'; end if;
 insert into auth.users(id,email,raw_user_meta_data,email_confirmed_at)
 values(player,'fixture-'||player||'@example.invalid',jsonb_build_object('nickname','Fx'||substr(replace(player::text,'-',''),1,20)),now()),
 (other,'fixture-'||other||'@example.invalid',jsonb_build_object('nickname','Fx'||substr(replace(other::text,'-',''),1,20)),now());
 a:=public.paw_begin_account_action(player,'email');
 if a->>'status'<>'ok' then raise exception 'Email reservation failed'; end if;
 b:=public.paw_begin_account_action(player,'password');
 if b->>'status'<>'account_busy' then raise exception 'Concurrent mutation permitted'; end if;
 perform public.paw_finish_account_action(player,(a->>'lease')::uuid,false);
 if (select email_changed_at is not null from public.paw_profiles where id=player) then raise exception 'Rejected request consumed cooldown'; end if;
 a:=public.paw_begin_account_action(player,'email');
 perform public.paw_finish_account_action(player,(a->>'lease')::uuid,true);
 b:=public.paw_begin_account_action(player,'email');
 if b->>'status'<>'email_cooldown' then raise exception 'Email cooldown bypass'; end if;
 a:=public.paw_begin_account_action(player,'password');
 if a->>'status'<>'ok' then raise exception 'Email cooldown blocked password'; end if;
 perform public.paw_finish_account_action(player,(a->>'lease')::uuid,true);
 b:=public.paw_begin_account_action(player,'password');
 if b->>'status'<>'password_cooldown' then raise exception 'Password cooldown bypass'; end if;
 a:=public.paw_begin_account_action(other,'password');
 if a->>'status'<>'ok' then raise exception 'Cooldown leaked to another user'; end if;
 -- A function crash leaves a durable reservation even after the short action lease expires.
 update paw_private.account_actions set lease_until=now()-interval '1 second' where player_id=other;
 b:=public.paw_begin_account_action(other,'password');
 if b->>'status'<>'password_cooldown' then raise exception 'Crash bypassed password interval'; end if;
 update public.paw_profiles set password_changed_at=now()-interval '6 minutes' where id=other;
 b:=public.paw_begin_account_action(other,'password');
 if b->>'status'<>'ok' then raise exception 'Cooldown never ends'; end if;
 perform public.paw_finish_account_action(other,(a->>'lease')::uuid,false);
 if (select lease from paw_private.account_actions where player_id=other)<>(b->>'lease')::uuid then raise exception 'Stale completion changed new lease'; end if;
 perform public.paw_finish_account_action(other,(b->>'lease')::uuid,false);
 a:=public.paw_begin_account_action(player,'delete');
 if not public.paw_mark_account_deleting(player,(a->>'lease')::uuid) then raise exception 'Delete marker failed'; end if;
 perform public.paw_finish_account_action(player,(a->>'lease')::uuid,false);
 b:=public.paw_begin_account_action(player,'avatar_remove');
 if b->>'status'<>'account_deletion_pending' then raise exception 'Upload/delete race allowed'; end if;
 b:=public.paw_begin_account_action(player,'delete');
 if b->>'status'<>'ok' then raise exception 'Deletion cannot be retried'; end if;
 if public.paw_account_session_active(player,gen_random_uuid()) then raise exception 'Invented session accepted'; end if;
 if exists(select 1 from storage.buckets where id='paw-avatars' and (public or file_size_limit<>204800 or allowed_mime_types<>array['image/jpeg'])) then raise exception 'Avatar bucket not bounded/private'; end if;
end $$;
rollback;
