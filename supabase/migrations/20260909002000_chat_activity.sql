-- Add only authorized conversation activity metadata to the existing list response.
-- Reuses paw_message_dialog_history; no table, grant, policy or message writes.
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
   'last_message_at',latest.created_at,'last_message_ordinal',coalesce(latest.ordinal,0),
   'is_friend',exists(select 1 from public.paw_friendships where low_id=least(actor,c.id) and high_id=greatest(actor,c.id) and accepted),
   'unread',case when c.relation='friend' and paw_private.history_allowed(actor,c.id) then (select count(*) from public.paw_messages m
    where m.recipient_id=actor and m.sender_id=c.id and m.ordinal>coalesce((select last_ordinal from paw_private.social_receipts where owner_id=actor and peer_id=c.id),0)) else 0 end) item
  from chosen c
  left join lateral (
   select m.created_at,m.ordinal from public.paw_messages m
   where c.relation='friend' and paw_private.history_allowed(actor,c.id)
    and least(m.sender_id,m.recipient_id)=least(actor,c.id)
    and greatest(m.sender_id,m.recipient_id)=greatest(actor,c.id)
   order by m.created_at desc,m.ordinal desc limit 1
  ) latest on true
  where not exists(select 1 from paw_private.hidden_chats where owner_id=actor and peer_id=c.id)
   and (c.relation='blocked' or not exists(select 1 from public.paw_blocks where owner_id=c.id and target_id=actor))
   and (c.relation='friend' or not exists(select 1 from paw_private.player_identities where id=c.id and deleted_at is not null))
 ) select coalesce(jsonb_agg(item order by item->>'display_name',item->>'id'),'[]') into items from summaries where item is not null;
 return jsonb_build_object('status','ok','players',items);
end; $$;
