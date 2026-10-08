-- Public chat author avatars and aggregate launcher presence only.
begin;
create function public.paw_community_avatar_allowed(object_name text) returns boolean
language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.paw_profiles p
  where $1=p.id::text||'/avatar.jpg' and not p.deletion_pending
  and exists(select 1 from paw_private.community_messages m where m.sender_id=p.id and m.removed_at is null));
$$;
revoke all on function public.paw_community_avatar_allowed(text) from public;
grant execute on function public.paw_community_avatar_allowed(text) to anon,authenticated;
create policy community_author_avatar_read on storage.objects for select to anon,authenticated
 using(bucket_id='paw-avatars' and public.paw_community_avatar_allowed(name));

create or replace function paw_private.community_json(m paw_private.community_messages) returns jsonb
language sql stable security definer set search_path='' as $$
 select jsonb_build_object('ordinal',m.ordinal,'message_id',m.message_id,'sender_id',m.sender_id,
  'body',case when m.removed_at is not null then '' else m.body end,'removed',m.removed_at is not null,
  'created_at',m.created_at,'nickname',p.nickname,'display_name',p.display_name,'admin_level',p.admin_level,
  'avatar_revision',p.avatar_changed_at)
 from public.paw_profiles p where p.id=m.sender_id and not p.deletion_pending;
$$;
create or replace function paw_private.community_profile_changed() returns trigger
language plpgsql security definer set search_path='' as $$
begin
 if tg_op='UPDATE' and (old.nickname,old.display_name,old.admin_level,old.deletion_pending,old.avatar_changed_at)
  is not distinct from (new.nickname,new.display_name,new.admin_level,new.deletion_pending,new.avatar_changed_at) then return new;end if;
 update paw_private.community_history h set revision=revision+1
 where exists(select 1 from paw_private.community_messages m where m.channel=h.channel and m.sender_id=old.id);
 return new;
end;$$;
drop trigger community_profile_changed on public.paw_profiles;
create trigger community_profile_changed after update of nickname,display_name,admin_level,deletion_pending,avatar_changed_at or delete
 on public.paw_profiles for each row execute function paw_private.community_profile_changed();

create function public.paw_community_online() returns jsonb
language sql stable security definer set search_path='' as $$
 select jsonb_build_object('status','ok','online',count(*))
 from paw_private.social_presence s join public.paw_profiles p on p.id=s.player_id
 where s.seen_at>now()-interval '40 seconds' and not p.deletion_pending
 and public.paw_account_session_active(s.player_id,s.session_id,s.launcher_id);
$$;
revoke all on function public.paw_community_online() from public;
grant execute on function public.paw_community_online() to anon,authenticated;
notify pgrst, 'reload schema';
commit;
