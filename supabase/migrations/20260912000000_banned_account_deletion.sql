-- Banned players cannot delete their own account. Administrative deletion and
-- retention cleanup remain available; neither removes the independent email ban.
create or replace function public.paw_account_action_allowed(player uuid,action text,address text default null) returns text
language sql stable security definer set search_path='' as $$
 select case
 when action='delete' and exists(select 1 from public.paw_profiles where id=player and protected_admin) then 'protected_account'
 when action<>'delete' and exists(select 1 from public.paw_profiles where id=player and deletion_pending) then 'account_deletion_pending'
 when action<>'avatar_get' and paw_private.player_banned(player) then 'account_banned'
 when action='email' and paw_private.email_banned(address) then 'email_banned'
 else 'ok' end;
$$;

create or replace function paw_private.soft_delete(player uuid,actor uuid) returns boolean
language plpgsql security definer set search_path='' as $$
begin
 perform 1 from public.paw_profiles where id=player for update;
 if not found or exists(select 1 from public.paw_profiles where id=player and protected_admin) then return false;end if;
 if actor=player and paw_private.player_banned(player) then return false;end if;
 insert into paw_private.archived_chats(owner_id,peer_id)
 select case when low_id=player then high_id else low_id end,player from public.paw_friendships where player in(low_id,high_id) and accepted
 union select case when low_id=player then high_id else low_id end,player from paw_private.official_chats where player in(low_id,high_id)
 on conflict do nothing;
 update public.paw_profiles set deleted_at=coalesce(deleted_at,clock_timestamp()),deletion_pending=true where id=player;
 update paw_private.player_identities set deleted_at=(select deleted_at from public.paw_profiles where id=player) where id=player;
 delete from paw_private.social_presence where player_id=player;
 update paw_private.social_offers set state='failed' where player in(sender_id,recipient_id) and state in('uploading','pending','applying');
 insert into paw_private.moderation_audit(actor_id,target_id,action) values(actor,player,'delete');
 return true;
end; $$;

create or replace function public.paw_mark_account_deleting(player uuid,key uuid) returns boolean
language plpgsql security definer set search_path='' as $$
begin
 perform 1 from public.paw_profiles where id=player for update;
 if public.paw_account_action_allowed(player,'delete')<>'ok' then return false;end if;
 if not exists(select 1 from paw_private.account_actions where player_id=player and lease=key and operation='delete' and lease_until>clock_timestamp()) then return false;end if;
 return paw_private.soft_delete(player,player);
end; $$;

revoke all on function public.paw_account_action_allowed(uuid,text,text),paw_private.soft_delete(uuid,uuid),public.paw_mark_account_deleting(uuid,uuid) from public,anon,authenticated;
grant execute on function public.paw_account_action_allowed(uuid,text,text),public.paw_mark_account_deleting(uuid,uuid) to service_role;

-- email_bans has no cascading foreign key to Auth or profiles. Existing
-- paw_admin_action('ban') records the normalized address at ban time, and the
-- Auth insert trigger checks it until expiry/revocation even after final purge.
