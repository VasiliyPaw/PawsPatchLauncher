-- Full profiles are readable by signed-in users unless either side blocks the other.
-- Chat, file transfer and friendship permissions remain unchanged.
begin;
create function paw_private.profile_view_allowed(actor uuid,target uuid) returns boolean
language sql stable security definer set search_path='' as $$
 select actor is not null and paw_private.player_live(actor)
 and exists(select 1 from public.paw_profiles p where p.id=target and not p.deletion_pending)
 and not exists(select 1 from public.paw_blocks b where (b.owner_id=actor and b.target_id=target) or (b.owner_id=target and b.target_id=actor));
$$;
revoke all on function paw_private.profile_view_allowed(uuid,uuid) from public,anon,authenticated;

-- Reuse the current validated presence/activity projections without changing
-- existing friend-only RPCs or the participant identity/ambiguity safeguards.
do $clone$ declare definition text; old_guard text;begin
 definition:=pg_get_functiondef('paw_private.friend_presence(uuid,uuid)'::regprocedure);
 old_guard:='if actor is null or not paw_private.social_allowed(actor,target) then';
 if strpos(definition,old_guard)=0 then raise exception 'Profile presence guard drift';end if;
 definition:=replace(definition,'paw_private.friend_presence(','paw_private.profile_presence(');
 definition:=replace(definition,old_guard,'if actor is null or not paw_private.profile_view_allowed(actor,target) then');
 execute definition;
 definition:=pg_get_functiondef('public.paw_game_activity(uuid)'::regprocedure);
 old_guard:='not (paw_private.social_allowed(actor,target) or paw_private.activity_profile_allowed(actor,target))';
 if strpos(definition,old_guard)=0 then raise exception 'Profile activity guard drift';end if;
 definition:=replace(definition,'public.paw_game_activity(','paw_private.profile_activity_details(');
 definition:=replace(definition,old_guard,'not paw_private.profile_view_allowed(actor,target)');
 execute definition;
end;$clone$;
revoke all on function paw_private.profile_presence(uuid,uuid),paw_private.profile_activity_details(uuid) from public,anon,authenticated;

create function public.paw_profile_card(target uuid) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare actor uuid:=paw_private.social_actor(); result jsonb; state jsonb;
begin
 if actor is null then return jsonb_build_object('status','session_expired');end if;
 if exists(select 1 from public.paw_blocks b where b.owner_id=target and b.target_id=actor) then return jsonb_build_object('status','profile_blocked');end if;
 if exists(select 1 from public.paw_blocks b where b.owner_id=actor and b.target_id=target) then return jsonb_build_object('status','profile_hidden');end if;
 if not paw_private.profile_view_allowed(actor,target) then return jsonb_build_object('status','player_unavailable');end if;
 result:=paw_private.player_summary(actor,target);
 state:=paw_private.profile_presence(actor,target);
 return jsonb_build_object('status','ok','player',result||state||jsonb_build_object('relation',coalesce((
  select case when accepted then 'friend' when requester=actor then 'outgoing' else 'incoming' end from public.paw_friendships
  where low_id=least(actor,target) and high_id=greatest(actor,target)),'friend'),'is_friend',
  exists(select 1 from public.paw_friendships where low_id=least(actor,target) and high_id=greatest(actor,target) and accepted),'unread',0));
end;$$;
revoke all on function public.paw_profile_card(uuid) from public,anon,authenticated;
grant execute on function public.paw_profile_card(uuid) to authenticated;

create function public.paw_profile_activity(target uuid) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare actor uuid:=paw_private.social_actor();
begin
 if actor is null then return jsonb_build_object('status','session_expired');end if;
 if exists(select 1 from public.paw_blocks b where b.owner_id=target and b.target_id=actor) then return jsonb_build_object('status','profile_blocked');end if;
 if exists(select 1 from public.paw_blocks b where b.owner_id=actor and b.target_id=target) then return jsonb_build_object('status','profile_hidden');end if;
 if not paw_private.profile_view_allowed(actor,target) then return jsonb_build_object('status','player_unavailable');end if;
 return paw_private.profile_activity_details(target);
end;$$;
revoke all on function public.paw_profile_activity(uuid) from public,anon,authenticated;
grant execute on function public.paw_profile_activity(uuid) to authenticated;

create or replace function public.paw_friend_avatar_allowed(player uuid,session uuid,launcher uuid,target uuid) returns boolean
language sql stable security definer set search_path='' as $$
 select public.paw_account_session_active(player,session,launcher)
 and paw_private.profile_view_allowed(player,target);
$$;
notify pgrst, 'reload schema';
commit;
