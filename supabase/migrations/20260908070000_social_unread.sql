-- Receipt cursor points to an actually returned incoming message, never client wall time.
alter table public.paw_messages add column ordinal bigint generated always as identity;
create unique index paw_message_ordinal on public.paw_messages(ordinal);
create index paw_message_unread on public.paw_messages(recipient_id,sender_id,ordinal);
create table paw_private.social_receipts (
 owner_id uuid references public.paw_profiles(id) on delete cascade,
 peer_id uuid references public.paw_profiles(id) on delete cascade,
 last_ordinal bigint not null check(last_ordinal>0), primary key(owner_id,peer_id),check(owner_id<>peer_id)
);
create index paw_receipt_peer on paw_private.social_receipts(peer_id);
alter table paw_private.social_receipts enable row level security;
revoke all on paw_private.social_receipts from public,anon,authenticated;
revoke all on sequence public.paw_messages_ordinal_seq from public,anon,authenticated;

create or replace function public.paw_social_list() returns jsonb
language plpgsql stable security definer set search_path = '' as $$
declare actor uuid := paw_private.social_actor(); items jsonb;
begin
 if actor is null then return jsonb_build_object('status','session_expired'); end if;
 select coalesce(jsonb_agg(to_jsonb(t) order by t.nickname),'[]'::jsonb) into items from (
  select p.id,p.nickname,case when f.accepted then 'friend' when f.requester=actor then 'outgoing' else 'incoming' end relation,
   case when f.accepted and paw_private.social_allowed(actor,p.id) then
    (select count(*) from public.paw_messages m where m.recipient_id=actor and m.sender_id=p.id
     and m.ordinal>coalesce((select last_ordinal from paw_private.social_receipts where owner_id=actor and peer_id=p.id),0))
    else 0 end unread
  from public.paw_friendships f join public.paw_profiles p on p.id=case when f.low_id=actor then f.high_id else f.low_id end
  where actor in(f.low_id,f.high_id) and not p.deletion_pending
  union all select p.id,p.nickname,'blocked',0 from public.paw_blocks b join public.paw_profiles p on p.id=b.target_id
  where b.owner_id=actor and not p.deletion_pending
 ) t;
 return jsonb_build_object('status','ok','players',items);
end;
$$;

create function public.paw_mark_messages_read(target uuid,last_message uuid) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare actor uuid:=paw_private.social_actor(); marker bigint; remaining bigint;
begin
 if actor is null then return jsonb_build_object('status','session_expired'); end if;
 perform paw_private.social_lock(actor,target);
 if paw_private.social_actor() is null or not paw_private.social_allowed(actor,target)
 then return jsonb_build_object('status','friend_required'); end if;
 select ordinal into marker from public.paw_messages where sender_id=target and recipient_id=actor and message_id=last_message;
 if marker is null then return jsonb_build_object('status','invalid_message'); end if;
 insert into paw_private.social_receipts(owner_id,peer_id,last_ordinal) values(actor,target,marker)
 on conflict(owner_id,peer_id) do update set last_ordinal=greatest(social_receipts.last_ordinal,excluded.last_ordinal);
 select count(*) into remaining from public.paw_messages where sender_id=target and recipient_id=actor
  and ordinal>(select last_ordinal from paw_private.social_receipts where owner_id=actor and peer_id=target);
 return jsonb_build_object('status','ok','unread',remaining);
end;
$$;
revoke all on function public.paw_mark_messages_read(uuid,uuid) from public,anon,authenticated;
grant execute on function public.paw_mark_messages_read(uuid,uuid) to authenticated;
