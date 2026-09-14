-- Only identities already resolved in a visible, current roster may expose a participant profile/avatar.
create function paw_private.activity_profile_allowed(actor uuid,target uuid) returns boolean
language sql stable security definer set search_path='' as $$
 select actor is not null and target is not null and actor<>target
 and paw_private.player_live(actor) and paw_private.player_live(target)
 and not exists(select 1 from public.paw_blocks b where (b.owner_id=actor and b.target_id=target) or (b.owner_id=target and b.target_id=actor))
 and exists(
  select 1 from paw_private.social_presence s where s.player_id=target
   and s.seen_at>now()-interval '40 seconds' and s.playing_since is not null
   and public.paw_account_session_active(target,s.session_id,s.launcher_id)
   and s.game_activity->>'room' is not null and s.game_activity->>'self' is not null
   -- Apply the same ambiguity rule as paw_game_activity; never match by nickname.
   and 1=(select count(*) from paw_private.social_presence c
    where c.game_activity is not null and c.game_activity->>'room'=s.game_activity->>'room' and c.game_activity->>'self'=s.game_activity->>'self'
    and c.seen_at>now()-interval '40 seconds' and c.playing_since is not null
    and paw_private.player_live(c.player_id) and public.paw_account_session_active(c.player_id,c.session_id,c.launcher_id)
    and not exists(select 1 from public.paw_blocks b where (b.owner_id=actor and b.target_id=c.player_id) or (b.owner_id=c.player_id and b.target_id=actor)))
   and exists(select 1 from paw_private.social_presence host
    where host.game_activity is not null and host.game_activity->>'room'=s.game_activity->>'room'
    and host.seen_at>now()-interval '40 seconds' and host.playing_since is not null
    and public.paw_account_session_active(host.player_id,host.session_id,host.launcher_id)
    and paw_private.social_allowed(actor,host.player_id)
    and exists(select 1 from jsonb_array_elements(coalesce(nullif(host.game_activity->'players','null'::jsonb),'[]'::jsonb)) p
      where p->>'key'=s.game_activity->>'self' and p->>'bot'='false')));
$$;
revoke all on function paw_private.activity_profile_allowed(uuid,uuid) from public,anon,authenticated;

create or replace function public.paw_player_profile(target uuid) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare actor uuid:=paw_private.social_actor(); result jsonb; roster_access boolean; p paw_private.social_presence;
begin
 if actor is null then return jsonb_build_object('status','session_expired');end if;
 roster_access:=paw_private.activity_profile_allowed(actor,target);
 if paw_private.admin_level(actor)<1 and not paw_private.history_allowed(actor,target) and not roster_access
 then return jsonb_build_object('status','friend_required');end if;
 result:=paw_private.player_summary(actor,target);
 if result is null then return jsonb_build_object('status','player_unavailable');end if;
 if roster_access and not paw_private.social_allowed(actor,target) then
  select * into p from paw_private.social_presence where player_id=target;
  -- A roster grants public identity/activity only, not chat, settings, files or friendship.
  result:=result||jsonb_build_object('presence','playing','playing_since',p.playing_since,'last_seen',p.seen_at,
   'activity',p.game_activity-'players'-'room'-'self');
 end if;
 return jsonb_build_object('status','ok','player',result||jsonb_build_object('relation',coalesce((
  select case when accepted then 'friend' when requester=actor then 'outgoing' else 'incoming' end from public.paw_friendships
  where low_id=least(actor,target) and high_id=greatest(actor,target)),'friend'),'is_friend',
  exists(select 1 from public.paw_friendships where low_id=least(actor,target) and high_id=greatest(actor,target) and accepted)));
end; $$;
revoke all on function public.paw_player_profile(uuid) from public,anon,authenticated;
grant execute on function public.paw_player_profile(uuid) to authenticated;

create or replace function public.paw_friend_avatar_allowed(player uuid,session uuid,launcher uuid,target uuid) returns boolean
language sql stable security definer set search_path='' as $$
 select public.paw_account_session_active(player,session,launcher) and paw_private.player_live(player)
 and exists(select 1 from public.paw_profiles where id=target and not deletion_pending)
 and (paw_private.admin_level(player)>0 or paw_private.history_allowed(player,target) or paw_private.activity_profile_allowed(player,target));
$$;
revoke all on function public.paw_friend_avatar_allowed(uuid,uuid,uuid,uuid) from public,anon,authenticated;
grant execute on function public.paw_friend_avatar_allowed(uuid,uuid,uuid,uuid) to service_role;

-- Add a revision to the existing bounded details response so images download only after a change.
do $$ declare definition text;begin
 definition:=pg_get_functiondef('public.paw_game_activity(uuid)'::regprocedure);
 if strpos(definition,'''display_name'',r.display_name))')=0 then raise exception 'Activity identity projection drift';end if;
 definition:=replace(definition,'''display_name'',r.display_name))','''display_name'',r.display_name,''avatar_revision'',r.avatar_changed_at))');
 definition:=replace(definition,'select r.id,r.nickname,r.display_name','select r.id,r.nickname,r.display_name,r.avatar_changed_at');
 if strpos(definition,'not paw_private.social_allowed(actor,target)')=0 then raise exception 'Activity visibility guard drift';end if;
 definition:=replace(definition,'not paw_private.social_allowed(actor,target)',
  'not (paw_private.social_allowed(actor,target) or paw_private.activity_profile_allowed(actor,target))');
 execute definition;
end; $$;

-- A profile action supplies its UUID as well as its displayed username. A rename cannot redirect it.
do $$ declare definition text;begin
 definition:=pg_get_functiondef('public.paw_friend_action(text,uuid,text)'::regprocedure);
 if strpos(definition,'perform paw_private.social_lock(actor,peer);')=0 then raise exception 'Friend action lock drift';end if;
 definition:=replace(definition,'perform paw_private.social_lock(actor,peer);',
  'if action=''request'' and target is not null and target is distinct from peer then return jsonb_build_object(''status'',''player_unavailable'');end if;
 perform paw_private.social_lock(actor,peer);');
 execute definition;
end; $$;
