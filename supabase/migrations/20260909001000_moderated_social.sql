-- Separate read-only conversation history from permission to send/apply offers.
create or replace function paw_private.social_allowed(a uuid,b uuid) returns boolean
language sql stable security definer set search_path='' as $$
 select a is not null and b is not null and a<>b and paw_private.player_live(a) and paw_private.player_live(b)
 and (exists(select 1 from public.paw_friendships where low_id=least(a,b) and high_id=greatest(a,b) and accepted)
  or exists(select 1 from paw_private.official_chats where low_id=least(a,b) and high_id=greatest(a,b)))
 and not exists(select 1 from public.paw_blocks where (owner_id=a and target_id=b) or (owner_id=b and target_id=a));
$$;
create function paw_private.history_allowed(a uuid,b uuid) returns boolean language sql stable security definer set search_path='' as $$
 select a is not null and a<>b and paw_private.player_live(a)
 and not exists(select 1 from paw_private.hidden_chats where owner_id=a and peer_id=b)
 and not exists(select 1 from public.paw_blocks where (owner_id=a and target_id=b) or (owner_id=b and target_id=a))
 and (paw_private.social_allowed(a,b) or (
  (paw_private.player_banned(b) or exists(select 1 from paw_private.player_identities where id=b and deleted_at is not null))
  and (exists(select 1 from public.paw_friendships where low_id=least(a,b) and high_id=greatest(a,b) and accepted)
   or exists(select 1 from paw_private.archived_chats where owner_id=a and peer_id=b)
   or exists(select 1 from public.paw_messages where (sender_id=a and recipient_id=b) or (sender_id=b and recipient_id=a)))));
$$;
-- Authorized moderators can inspect a profile without first creating a friendship.
do $$ declare def text;begin
 def:=pg_get_functiondef('paw_private.friend_presence(uuid,uuid)'::regprocedure);
 if strpos(def,'not paw_private.social_allowed(actor,target)')=0 then raise exception 'Presence guard drift';end if;
 execute replace(def,'not paw_private.social_allowed(actor,target)',
  'not (paw_private.social_allowed(actor,target) or (paw_private.admin_level(actor)>0 and paw_private.player_live(target)))');
end; $$;
alter policy message_participant on public.paw_messages using(
 (select paw_private.social_actor()) in(sender_id,recipient_id)
 and paw_private.history_allowed((select paw_private.social_actor()),case when sender_id=(select auth.uid()) then recipient_id else sender_id end));

create function paw_private.player_summary(actor uuid,target uuid) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare p public.paw_profiles; stamp timestamptz; state jsonb;
begin
 select * into p from public.paw_profiles where id=target;
 select deleted_at into stamp from paw_private.player_identities where id=target;
 if stamp is not null then return jsonb_build_object('id',target,'nickname','deleted','display_name','Удалённый аккаунт',
  'deleted_at',stamp,'presence','offline','admin_level',0,'unread',0,'components','{}'::jsonb,'channel','unknown');end if;
 if p.id is null then return null;end if;
 state:=paw_private.friend_presence(actor,target);
 return state||jsonb_build_object('id',p.id,'nickname',p.nickname,'display_name',p.display_name,'created_at',p.created_at,
  'admin_level',p.admin_level,'avatar_revision',p.avatar_changed_at,'deleted_at',null,
  'banned_at',case when paw_private.player_banned(p.id) then p.banned_at end,
  'ban_until',case when paw_private.player_banned(p.id) then p.ban_until end,
  'ban_reason',case when paw_private.player_banned(p.id) then p.ban_reason end,
  'presence',case when paw_private.player_banned(p.id) then 'offline' else coalesce(state->>'presence','offline') end);
end; $$;

create or replace function public.paw_social_list() returns jsonb language plpgsql stable security definer set search_path='' as $$
declare actor uuid:=paw_private.social_actor(); items jsonb;
begin
 if actor is null then return jsonb_build_object('status',case when paw_private.player_banned(auth.uid()) then 'account_banned' else 'session_expired' end);end if;
 with peers as (
  select case when low_id=actor then high_id else low_id end id,
   case when accepted then 'friend' when requester=actor then 'outgoing' else 'incoming' end relation,0 priority
  from public.paw_friendships where actor in(low_id,high_id)
  union all select target_id,'blocked',-1 from public.paw_blocks where owner_id=actor
  union all select case when low_id=actor then high_id else low_id end,'friend',1 from paw_private.official_chats where actor in(low_id,high_id)
  union all select peer_id,'friend',2 from paw_private.archived_chats a where owner_id=actor
   and exists(select 1 from paw_private.player_identities i where i.id=a.peer_id and i.deleted_at is not null)
  union all select distinct case when sender_id=actor then recipient_id else sender_id end,'friend',2
   from public.paw_messages m where actor in(sender_id,recipient_id) and exists(select 1 from paw_private.player_identities i
    where i.id=case when m.sender_id=actor then m.recipient_id else m.sender_id end and i.deleted_at is not null)
 ), chosen as (select distinct on(id) id,relation from peers order by id,priority), summaries as (
  select paw_private.player_summary(actor,c.id)||jsonb_build_object('relation',c.relation,
   'is_friend',exists(select 1 from public.paw_friendships where low_id=least(actor,c.id) and high_id=greatest(actor,c.id) and accepted),
   'unread',case when c.relation='friend' and paw_private.history_allowed(actor,c.id) then (select count(*) from public.paw_messages m
    where m.recipient_id=actor and m.sender_id=c.id and m.ordinal>coalesce((select last_ordinal from paw_private.social_receipts where owner_id=actor and peer_id=c.id),0)) else 0 end) item
  from chosen c where not exists(select 1 from paw_private.hidden_chats where owner_id=actor and peer_id=c.id)
   and (c.relation='blocked' or not exists(select 1 from public.paw_blocks where owner_id=c.id and target_id=actor))
   and (c.relation='friend' or not exists(select 1 from paw_private.player_identities where id=c.id and deleted_at is not null))
 ) select coalesce(jsonb_agg(item order by item->>'display_name',item->>'id'),'[]') into items from summaries where item is not null;
 return jsonb_build_object('status','ok','players',items);
end; $$;

create function public.paw_player_profile(target uuid) returns jsonb language plpgsql stable security definer set search_path='' as $$
declare actor uuid:=paw_private.social_actor(); result jsonb;
begin
 if actor is null then return jsonb_build_object('status','session_expired');end if;
 if paw_private.admin_level(actor)<1 and not paw_private.history_allowed(actor,target) then return jsonb_build_object('status','friend_required');end if;
 result:=paw_private.player_summary(actor,target);
 if result is null then return jsonb_build_object('status','player_unavailable');end if;
 return jsonb_build_object('status','ok','player',result||jsonb_build_object('relation','friend','is_friend',
  exists(select 1 from public.paw_friendships where low_id=least(actor,target) and high_id=greatest(actor,target) and accepted)));
end; $$;
create function public.paw_admin_chat(target uuid) returns jsonb language plpgsql security definer set search_path='' as $$
declare actor uuid:=paw_private.social_actor();
begin
 perform pg_advisory_xact_lock(73190422);
 if paw_private.admin_level(actor)<1 or target is null or actor=target then return jsonb_build_object('status','admin_required');end if;
 perform paw_private.social_lock(actor,target);
 if paw_private.social_actor() is distinct from actor or paw_private.admin_level(actor)<1 then return jsonb_build_object('status','admin_required');end if;
 if not paw_private.player_live(target) then return jsonb_build_object('status','player_unavailable');end if;
 if exists(select 1 from public.paw_blocks where owner_id=actor and target_id=target) then return jsonb_build_object('status','player_unavailable');end if;
 if (select count(*) from paw_private.official_chats where opened_by=actor and created_at>now()-interval '1 minute')>=10 then return jsonb_build_object('status','rate_limit');end if;
 insert into paw_private.official_chats(low_id,high_id,opened_by) values(least(actor,target),greatest(actor,target),actor) on conflict do nothing;
 return jsonb_build_object('status','ok');
end; $$;

alter function public.paw_friend_action(text,uuid,text) rename to friend_action_before_moderation;
alter function public.friend_action_before_moderation(text,uuid,text) set schema paw_private;
revoke all on function paw_private.friend_action_before_moderation(text,uuid,text) from public,anon,authenticated;
create function public.paw_friend_action(action text,target uuid default null,candidate text default null) returns jsonb
language plpgsql security definer set search_path='' as $$
declare actor uuid:=paw_private.social_actor();peer uuid:=target;
begin
 if actor is null then return jsonb_build_object('status',case when paw_private.player_banned(auth.uid()) then 'account_banned' else 'session_expired' end);end if;
 if action='request' then select id into peer from public.paw_profiles where nickname_key=paw_private.nickname_key(candidate) collate "C";end if;
 perform paw_private.social_lock(actor,peer);
 if paw_private.social_actor() is distinct from actor then return jsonb_build_object('status','account_banned');end if;
 if action='hide_chat' then
  if not exists(select 1 from paw_private.player_identities where id=peer and deleted_at is not null)
   or not paw_private.history_allowed(actor,peer) then return jsonb_build_object('status','player_unavailable');end if;
  insert into paw_private.hidden_chats values(actor,peer) on conflict do nothing;
  return jsonb_build_object('status','ok');
 end if;
 if action='block' and (select admin_level from public.paw_profiles where id=peer)>0 then return jsonb_build_object('status','admin_cannot_block');end if;
 if exists(select 1 from paw_private.player_identities where id=peer and deleted_at is not null)
  or (paw_private.player_banned(peer) and action not in('block','remove','unblock','decline','cancel')) then return jsonb_build_object('status','player_unavailable');end if;
 return paw_private.friend_action_before_moderation(action,target,candidate);
end; $$;

create or replace function public.paw_read_messages(target uuid,before_time timestamptz default null) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare actor uuid:=paw_private.social_actor();items jsonb;
begin
 if actor is null then return jsonb_build_object('status','session_expired');end if;
 if not paw_private.history_allowed(actor,target) then return jsonb_build_object('status','friend_required');end if;
 select coalesce(jsonb_agg(to_jsonb(t) order by t.created_at,t.ordinal),'[]') into items from (
  select * from public.paw_messages where ((sender_id=actor and recipient_id=target) or(sender_id=target and recipient_id=actor))
   and (before_time is null or created_at<before_time) order by created_at desc,ordinal desc limit 50) t;
 return jsonb_build_object('status','ok','messages',items);
end; $$;
-- Read-only offer cards/receipts are available even after the peer is sanctioned.
do $$ declare def text;begin
 def:=pg_get_functiondef('public.paw_mark_messages_read(uuid,uuid)'::regprocedure);
 if strpos(def,'paw_private.social_allowed(actor,target)')=0 then raise exception 'Receipt guard drift';end if;
 execute replace(def,'paw_private.social_allowed(actor,target)','paw_private.history_allowed(actor,target)');
 def:=pg_get_functiondef('public.paw_offers(uuid)'::regprocedure);
 if strpos(def,'paw_private.social_allowed(actor,target)')=0 then raise exception 'Offer read guard drift';end if;
 execute replace(def,'paw_private.social_allowed(actor,target)','paw_private.history_allowed(actor,target)');
end; $$;
create or replace function public.paw_friend_avatar_allowed(player uuid,session uuid,launcher uuid,target uuid) returns boolean
language sql stable security definer set search_path='' as $$
 select public.paw_account_session_active(player,session,launcher) and paw_private.player_live(player)
 and exists(select 1 from public.paw_profiles where id=target and not deletion_pending)
 and (paw_private.admin_level(player)>0 or paw_private.history_allowed(player,target));
$$;
revoke all on function paw_private.history_allowed(uuid,uuid),paw_private.player_summary(uuid,uuid),public.paw_player_profile(uuid),
 public.paw_admin_chat(uuid),public.paw_friend_action(text,uuid,text) from public,anon,authenticated;
grant execute on function paw_private.history_allowed(uuid,uuid),public.paw_player_profile(uuid),public.paw_admin_chat(uuid),public.paw_friend_action(text,uuid,text) to authenticated;
