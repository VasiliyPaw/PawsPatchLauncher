-- Presence is bounded, server-timed and visible only across an accepted, unblocked friendship.
create table paw_private.social_presence (
 player_id uuid primary key references public.paw_profiles(id) on delete cascade,
 session_id uuid not null, launcher_id uuid not null,
 seen_at timestamptz not null, playing_since timestamptz,
 channel text not null check(channel in ('stable','beta','unknown')),
 components jsonb not null check(jsonb_typeof(components)='object')
);
alter table paw_private.social_presence enable row level security;
revoke all on paw_private.social_presence from public,anon,authenticated;

create function public.paw_presence(playing boolean, channel text, components jsonb) returns jsonb
language plpgsql security definer set search_path='' as $$
declare actor uuid:=paw_private.social_actor(); prior paw_private.social_presence; stamp timestamptz:=clock_timestamp(); sid uuid;
begin
 if actor is null then return jsonb_build_object('status','session_expired'); end if;
 if playing is null or channel is null or channel not in ('stable','beta','unknown') or components is null
 or jsonb_typeof(components)<>'object' or octet_length(components::text)>2048
 then return jsonb_build_object('status','invalid_presence'); end if;
 if exists(select 1 from jsonb_each(components) e where e.key not in
 ('core','russian','colors','desync','hostility','roaming','additional_roaming','siege','powers_shards','large_maps') or jsonb_typeof(e.value)<>'boolean')
 then return jsonb_build_object('status','invalid_presence'); end if;
 perform 1 from public.paw_profiles where id=actor for update;
 if paw_private.social_actor() is null then return jsonb_build_object('status','session_expired'); end if;
 sid := (auth.jwt()->>'session_id')::uuid;
 select * into prior from paw_private.social_presence where player_id=actor;
 -- Ignore overly frequent calls; timestamps/duration always come from the server.
 if prior.seen_at>stamp-interval '3 seconds' and prior.session_id=sid and prior.launcher_id=paw_private.launcher_header()
 then return jsonb_build_object('status','ok'); end if;
 insert into paw_private.social_presence values(actor,sid,paw_private.launcher_header(),stamp,
 case when not playing then null when prior.playing_since is not null and prior.seen_at>stamp-interval '40 seconds'
 and prior.session_id=sid and prior.launcher_id=paw_private.launcher_header() then prior.playing_since else stamp end,channel,components)
 on conflict(player_id) do update set session_id=excluded.session_id,launcher_id=excluded.launcher_id,seen_at=excluded.seen_at,
 playing_since=excluded.playing_since,channel=excluded.channel,components=excluded.components;
 return jsonb_build_object('status','ok');
end; $$;
revoke all on function public.paw_presence(boolean,text,jsonb) from public,anon,authenticated;
grant execute on function public.paw_presence(boolean,text,jsonb) to authenticated;

create function paw_private.friend_presence(actor uuid,target uuid) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare p paw_private.social_presence; active boolean;
begin
 if actor is null or not paw_private.social_allowed(actor,target) then return '{}'::jsonb; end if;
 select * into p from paw_private.social_presence where player_id=target;
 active := p.seen_at>now()-interval '40 seconds' and public.paw_account_session_active(target,p.session_id,p.launcher_id);
 return jsonb_build_object('presence',case when coalesce(active,false) then case when p.playing_since is null then 'online' else 'playing' end else 'offline' end,
 'last_seen',p.seen_at,'playing_since',case when active then p.playing_since end,'channel',coalesce(p.channel,'unknown'),
 'components',coalesce(p.components,'{}'::jsonb),'avatar_revision',(select avatar_changed_at from public.paw_profiles where id=target));
end; $$;
revoke all on function paw_private.friend_presence(uuid,uuid) from public,anon,authenticated;

-- Keep the original relationship/unread logic, with no change to its access boundaries.
alter function public.paw_social_list() set schema paw_private;
alter function paw_private.paw_social_list() rename to social_list_base;
revoke all on function paw_private.social_list_base() from public,anon,authenticated;
create function public.paw_social_list() returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare actor uuid:=paw_private.social_actor(); result jsonb;
begin
 if actor is null then return jsonb_build_object('status','session_expired'); end if;
 result:=paw_private.social_list_base();
 return jsonb_set(result,'{players}',coalesce((select jsonb_agg(item || case when item->>'relation'='friend'
 then paw_private.friend_presence(actor,(item->>'id')::uuid) else '{}'::jsonb end order by item->>'nickname')
 from jsonb_array_elements(result->'players') item),'[]'::jsonb));
end; $$;
revoke all on function public.paw_social_list() from public,anon,authenticated;
grant execute on function public.paw_social_list() to authenticated;

-- Service-only helper: Edge verifies Auth first, then both active instance and friendship.
create function public.paw_friend_avatar_allowed(player uuid,session uuid,launcher uuid,target uuid) returns boolean
language sql stable security definer set search_path='' as $$
 select public.paw_account_session_active(player,session,launcher) and paw_private.social_allowed(player,target);
$$;
revoke all on function public.paw_friend_avatar_allowed(uuid,uuid,uuid,uuid) from public,anon,authenticated;
grant execute on function public.paw_friend_avatar_allowed(uuid,uuid,uuid,uuid) to service_role;
