-- Client writes go through bounded RPCs. Every reader must still own a live Auth session.
create function paw_private.social_actor() returns uuid
language sql stable security definer set search_path = '' as $$
 select p.id from public.paw_profiles p join auth.users u on u.id=p.id
 where p.id=(select auth.uid()) and not p.deletion_pending and u.deleted_at is null
 and u.email_confirmed_at is not null and exists(select 1 from auth.sessions s
 where s.user_id=p.id and s.id::text=(select auth.jwt()->>'session_id')
 and (s.not_after is null or s.not_after>now()));
$$;

create table public.paw_friendships (
 low_id uuid references public.paw_profiles(id) on delete cascade,
 high_id uuid references public.paw_profiles(id) on delete cascade,
 requester uuid not null references public.paw_profiles(id) on delete cascade,
 accepted boolean not null default false, created_at timestamptz not null default now(),
 primary key(low_id,high_id), check(low_id<high_id), check(requester in(low_id,high_id))
);
create index paw_friendships_high on public.paw_friendships(high_id);
create table public.paw_blocks (
 owner_id uuid references public.paw_profiles(id) on delete cascade,
 target_id uuid references public.paw_profiles(id) on delete cascade,
 created_at timestamptz not null default now(), primary key(owner_id,target_id), check(owner_id<>target_id)
);
create index paw_blocks_target on public.paw_blocks(target_id);
create table paw_private.social_limits (
 player_id uuid primary key references public.paw_profiles(id) on delete cascade,
 window_start timestamptz not null, requests integer not null
);
alter table paw_private.social_limits enable row level security;
revoke all on paw_private.social_limits from public,anon,authenticated;
create table public.paw_messages (
 sender_id uuid references public.paw_profiles(id) on delete cascade,
 message_id uuid not null, recipient_id uuid not null references public.paw_profiles(id) on delete cascade,
 body text not null check(length(body) between 1 and 2000 and length(btrim(body,E' \t\r\n'))>0),
 kind text not null check(kind in('text','config')), created_at timestamptz not null default clock_timestamp(),
 primary key(sender_id,message_id), check(sender_id<>recipient_id)
);
create index paw_messages_received on public.paw_messages(recipient_id,created_at desc);
create index paw_messages_sent on public.paw_messages(sender_id,created_at desc);

create function paw_private.social_allowed(a uuid,b uuid) returns boolean
language sql stable security definer set search_path = '' as $$
 select a is not null and b is not null and a<>b
 and exists(select 1 from public.paw_profiles where id=a and not deletion_pending)
 and exists(select 1 from public.paw_profiles where id=b and not deletion_pending)
 and exists(select 1 from public.paw_friendships where low_id=least(a,b) and high_id=greatest(a,b) and accepted)
 and not exists(select 1 from public.paw_blocks where (owner_id=a and target_id=b) or (owner_id=b and target_id=a));
$$;

-- Ordered profile locks serialize pair actions against blocking and account deletion.
create function paw_private.social_lock(a uuid,b uuid) returns void
language plpgsql security definer set search_path = '' as $$
begin
 perform 1 from public.paw_profiles where id in(a,b) order by id for update;
end;
$$;

alter table public.paw_friendships enable row level security;
alter table public.paw_blocks enable row level security;
alter table public.paw_messages enable row level security;
revoke all on public.paw_friendships,public.paw_blocks,public.paw_messages from public,anon,authenticated;
grant select on public.paw_friendships,public.paw_blocks,public.paw_messages to authenticated;
create policy friendship_participant on public.paw_friendships for select to authenticated
 using ((select paw_private.social_actor()) in(low_id,high_id));
create policy block_owner on public.paw_blocks for select to authenticated
 using (owner_id=(select paw_private.social_actor()));
create policy message_participant on public.paw_messages for select to authenticated
 using ((select paw_private.social_actor()) in(sender_id,recipient_id)
 and paw_private.social_allowed(sender_id,recipient_id));

create function public.paw_friend_action(action text, target uuid default null, candidate text default null) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare actor uuid := paw_private.social_actor(); peer uuid := target; f public.paw_friendships;
begin
 if actor is null then return jsonb_build_object('status','session_expired'); end if;
 if action not in('request','accept','decline','cancel','remove','block','unblock') or action is null then
  return jsonb_build_object('status','invalid_action'); end if;
 if action='request' then
  select id into peer from public.paw_profiles where nickname_key=paw_private.nickname_key(candidate) collate "C"
   and paw_private.nickname_valid(candidate) and not deletion_pending;
 end if;
 if peer is null or peer=actor then return jsonb_build_object('status','player_unavailable'); end if;
 perform paw_private.social_lock(actor,peer);
 if paw_private.social_actor() is null then return jsonb_build_object('status','session_expired'); end if;
 if not exists(select 1 from public.paw_profiles p join auth.users u on u.id=p.id
  where p.id=peer and not p.deletion_pending and u.deleted_at is null and u.email_confirmed_at is not null)
 then return jsonb_build_object('status','player_unavailable'); end if;
 if action='unblock' then
  delete from public.paw_blocks where owner_id=actor and target_id=peer;
  return jsonb_build_object('status','ok');
 end if;
 if action='block' then
  if (select count(*) from public.paw_blocks where owner_id=actor)>=200
   and not exists(select 1 from public.paw_blocks where owner_id=actor and target_id=peer)
  then return jsonb_build_object('status','friend_limit'); end if;
  insert into public.paw_blocks(owner_id,target_id) values(actor,peer) on conflict do nothing;
  delete from public.paw_friendships where low_id=least(actor,peer) and high_id=greatest(actor,peer);
  return jsonb_build_object('status','ok');
 end if;
 if exists(select 1 from public.paw_blocks where (owner_id=actor and target_id=peer) or (owner_id=peer and target_id=actor))
 then return jsonb_build_object('status','player_unavailable'); end if;
 select * into f from public.paw_friendships where low_id=least(actor,peer) and high_id=greatest(actor,peer);
 if action='request' then
  if f.low_id is not null then return jsonb_build_object('status','ok'); end if;
  if (select count(*) from public.paw_friendships where actor in(low_id,high_id))>=100
   or (select count(*) from public.paw_friendships where peer in(low_id,high_id))>=100
  then return jsonb_build_object('status','friend_limit'); end if;
  if exists(select 1 from paw_private.social_limits where player_id=actor
    and window_start>now()-interval '1 minute' and requests>=20)
  then return jsonb_build_object('status','rate_limit'); end if;
  insert into paw_private.social_limits(player_id,window_start,requests) values(actor,now(),1)
  on conflict(player_id) do update set
   requests=case when social_limits.window_start>now()-interval '1 minute' then social_limits.requests+1 else 1 end,
   window_start=case when social_limits.window_start>now()-interval '1 minute' then social_limits.window_start else now() end;
  insert into public.paw_friendships(low_id,high_id,requester) values(least(actor,peer),greatest(actor,peer),actor);
 elsif action='accept' then
  if f.low_id is null or (f.requester=actor and not f.accepted) then return jsonb_build_object('status','request_missing'); end if;
  update public.paw_friendships set accepted=true where low_id=f.low_id and high_id=f.high_id;
 elsif action in('decline','cancel','remove') then
  if f.low_id is not null and ((action='decline' and not f.accepted and f.requester<>actor)
   or (action='cancel' and not f.accepted and f.requester=actor) or (action='remove' and f.accepted)) then
   delete from public.paw_friendships where low_id=f.low_id and high_id=f.high_id;
  elsif f.low_id is not null then return jsonb_build_object('status','request_missing'); end if;
 end if;
 return jsonb_build_object('status','ok');
end;
$$;

create function public.paw_social_list() returns jsonb
language plpgsql stable security definer set search_path = '' as $$
declare actor uuid := paw_private.social_actor(); items jsonb;
begin
 if actor is null then return jsonb_build_object('status','session_expired'); end if;
 select coalesce(jsonb_agg(to_jsonb(t) order by t.nickname),'[]'::jsonb) into items from (
  select p.id,p.nickname,case when f.accepted then 'friend' when f.requester=actor then 'outgoing' else 'incoming' end relation
  from public.paw_friendships f join public.paw_profiles p on p.id=case when f.low_id=actor then f.high_id else f.low_id end
  where actor in(f.low_id,f.high_id) and not p.deletion_pending
  union all select p.id,p.nickname,'blocked' from public.paw_blocks b join public.paw_profiles p on p.id=b.target_id
  where b.owner_id=actor and not p.deletion_pending
 ) t;
 return jsonb_build_object('status','ok','players',items);
end;
$$;

create function public.paw_send_message(target uuid, message_id uuid, body text, kind text default 'text') returns jsonb
language plpgsql security definer set search_path = '' as $$
declare actor uuid:=paw_private.social_actor(); prior public.paw_messages;
begin
 if actor is null then return jsonb_build_object('status','session_expired'); end if;
 if target is null or target=actor or message_id is null or body is null or length(body) not between 1 and 2000
  or length(btrim(body,E' \t\r\n'))=0 or kind is null or kind not in('text','config')
 then return jsonb_build_object('status','invalid_message'); end if;
 perform paw_private.social_lock(actor,target);
 if paw_private.social_actor() is null or not paw_private.social_allowed(actor,target)
 then return jsonb_build_object('status','friend_required'); end if;
 select * into prior from public.paw_messages m where m.sender_id=actor and m.message_id=paw_send_message.message_id;
 if prior.message_id is not null then
  if prior.recipient_id<>target or prior.body<>body or prior.kind<>kind then return jsonb_build_object('status','message_conflict'); end if;
  return jsonb_build_object('status','ok','message',to_jsonb(prior));
 end if;
 if (select count(*) from public.paw_messages where sender_id=actor and created_at>now()-interval '1 minute')>=20
 then return jsonb_build_object('status','rate_limit'); end if;
 if (select count(*) from public.paw_messages where sender_id=actor)>=10000
 then return jsonb_build_object('status','message_limit'); end if;
 insert into public.paw_messages(sender_id,message_id,recipient_id,body,kind)
 values(actor,message_id,target,body,kind) returning * into prior;
 return jsonb_build_object('status','ok','message',to_jsonb(prior));
end;
$$;

create function public.paw_read_messages(target uuid, before_time timestamptz default null) returns jsonb
language plpgsql stable security definer set search_path = '' as $$
declare actor uuid:=paw_private.social_actor(); items jsonb;
begin
 if actor is null then return jsonb_build_object('status','session_expired'); end if;
 if not paw_private.social_allowed(actor,target) then return jsonb_build_object('status','friend_required'); end if;
 select coalesce(jsonb_agg(to_jsonb(t) order by t.created_at,t.message_id),'[]'::jsonb) into items from (
  select * from public.paw_messages where ((sender_id=actor and recipient_id=target) or (sender_id=target and recipient_id=actor))
  and (before_time is null or created_at<before_time) order by created_at desc,message_id desc limit 50
 ) t;
 return jsonb_build_object('status','ok','messages',items);
end;
$$;

revoke all on function paw_private.social_actor(),paw_private.social_allowed(uuid,uuid),paw_private.social_lock(uuid,uuid) from public,anon,authenticated;
grant execute on function paw_private.social_actor(),paw_private.social_allowed(uuid,uuid) to authenticated;
revoke all on function public.paw_friend_action(text,uuid,text),public.paw_social_list(),
 public.paw_send_message(uuid,uuid,text,text),public.paw_read_messages(uuid,timestamptz) from public,anon,authenticated;
grant execute on function public.paw_friend_action(text,uuid,text),public.paw_social_list(),
 public.paw_send_message(uuid,uuid,text,text),public.paw_read_messages(uuid,timestamptz) to authenticated;
