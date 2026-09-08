-- User explicitly nominated username paw; immutable identity verified read-only
-- on 2026-09-08 before preparing this grant. Fail closed on a different database.
do $$ begin
 if not exists(select 1 from public.paw_profiles where id='2facff35-56cd-45a4-b88b-b38b71384533'::uuid
  and nickname='paw' and not deletion_pending) then raise exception 'Founder identity mismatch';end if;
 update public.paw_profiles set admin_level=2,protected_admin=true where id='2facff35-56cd-45a4-b88b-b38b71384533';
 delete from public.paw_blocks where target_id='2facff35-56cd-45a4-b88b-b38b71384533';
 insert into paw_private.moderation_audit(actor_id,target_id,action) values(null,'2facff35-56cd-45a4-b88b-b38b71384533','founder_bootstrap');
end; $$;
