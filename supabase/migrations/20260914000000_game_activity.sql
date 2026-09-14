-- Bounded current game activity. No activity history, raw Steam IDs or join addresses.
alter table paw_private.social_presence add column game_activity jsonb
 check(game_activity is null or (jsonb_typeof(game_activity)='object' and octet_length(game_activity::text)<=16384));
create index social_presence_game_room on paw_private.social_presence ((game_activity->>'room'),(game_activity->>'self'))
 where game_activity is not null;

create function paw_private.valid_game_activity(a jsonb) returns boolean
language plpgsql immutable set search_path='' as $$
declare p jsonb; n numeric; key text; people jsonb;
begin
 if a is null or a='null'::jsonb then return true; end if;
 if jsonb_typeof(a)<>'object' or octet_length(a::text)>16384
 or exists(select 1 from jsonb_object_keys(a) k where k not in ('phase','multiplayer','elapsed','width','height','room','self','players'))
 or jsonb_typeof(a->'phase') is distinct from 'string' or a->>'phase' not in ('menu','lobby','match','loading','editor')
 or jsonb_typeof(a->'multiplayer') is distinct from 'boolean' then return false; end if;
 foreach key in array array['elapsed','width','height'] loop
  if a->key is not null and a->key<>'null'::jsonb then
   if jsonb_typeof(a->key)<>'number' then return false; end if;
   n:=(a->>key)::numeric;
   if n<>trunc(n) or (key='elapsed' and (n<0 or n>604800)) or (key<>'elapsed' and (n<16 or n>8192)) then return false; end if;
  end if;
 end loop;
 if ((a->>'width') is null)<>((a->>'height') is null) then return false; end if;
 if a->>'room' is not null and (jsonb_typeof(a->'room')<>'string' or a->>'room' !~ '^[A-Fa-f0-9]{64}$') then return false; end if;
 if a->>'self' is not null and (jsonb_typeof(a->'self')<>'string' or a->>'self' !~ '^[A-Za-z0-9_-]{1,32}$') then return false; end if;
 people:=coalesce(nullif(a->'players','null'::jsonb),'[]'::jsonb);
 if jsonb_typeof(people)<>'array' or jsonb_array_length(people)>64 then return false; end if;
 if (select count(distinct value->>'key') from jsonb_array_elements(people))<>jsonb_array_length(people) then return false; end if;
 for p in select value from jsonb_array_elements(people) loop
  if jsonb_typeof(p)<>'object' or exists(select 1 from jsonb_object_keys(p) k where k not in ('key','name','bot','profile'))
  or jsonb_typeof(p->'key') is distinct from 'string' or p->>'key' !~ '^[A-Za-z0-9_-]{1,32}$'
  or jsonb_typeof(p->'name') is distinct from 'string' or length(btrim(p->>'name')) not between 1 and 80 or p->>'name' ~ '[[:cntrl:]]'
  or jsonb_typeof(p->'bot') is distinct from 'boolean' or (p->'profile' is not null and p->'profile'<>'null'::jsonb) then return false; end if;
 end loop;
 if a->>'self' is not null and not exists(select 1 from jsonb_array_elements(people) entry where entry->>'key'=a->>'self' and entry->>'bot'='false') then return false; end if;
 if a->>'phase' not in ('lobby','match') and (jsonb_array_length(people)>0 or a->>'room' is not null or a->>'self' is not null) then return false; end if;
 if a->>'multiplayer'='false' and a->>'room' is not null then return false; end if;
 return true;
exception when others then return false;
end; $$;
revoke all on function paw_private.valid_game_activity(jsonb) from public,anon,authenticated;

-- Retain the existing configuration/version/session checks as a private implementation.
alter function public.paw_presence(boolean,text,jsonb,text) set schema paw_private;
alter function paw_private.paw_presence(boolean,text,jsonb,text) rename to presence_without_activity;
revoke all on function paw_private.presence_without_activity(boolean,text,jsonb,text) from public,anon,authenticated;

create function public.paw_presence(playing boolean,channel text,components jsonb,configuration text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare actor uuid:=paw_private.social_actor(); activity jsonb; previous_stamp timestamptz; result jsonb;
begin
 if actor is null then return jsonb_build_object('status','session_expired'); end if;
 if components is null or jsonb_typeof(components)<>'object' or octet_length(components::text)>18432
 then return jsonb_build_object('status','invalid_presence'); end if;
 activity:=nullif(components->'_activity','null'::jsonb);
 if not paw_private.valid_game_activity(activity) then return jsonb_build_object('status','invalid_presence'); end if;
 if not coalesce(playing,false) then activity:=null; end if;
 -- The same profile lock used by the existing heartbeat prevents concurrent stale writers.
 perform 1 from public.paw_profiles where id=actor for update;
 select seen_at into previous_stamp from paw_private.social_presence where player_id=actor;
 result:=paw_private.presence_without_activity(playing,channel,components-'_activity',configuration);
 if result->>'status'='ok' then
  update paw_private.social_presence set game_activity=activity
  where player_id=actor and seen_at is distinct from previous_stamp;
 end if;
 return result;
end; $$;
revoke all on function public.paw_presence(boolean,text,jsonb,text) from public,anon,authenticated;
grant execute on function public.paw_presence(boolean,text,jsonb,text) to authenticated;

create or replace function public.paw_presence(playing boolean,channel text,components jsonb) returns jsonb
language sql security definer set search_path='' as $$ select public.paw_presence(playing,channel,components,null); $$;
revoke all on function public.paw_presence(boolean,text,jsonb) from public,anon,authenticated;
grant execute on function public.paw_presence(boolean,text,jsonb) to authenticated;

create or replace function paw_private.friend_presence(actor uuid,target uuid) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare p paw_private.social_presence; active boolean; summary jsonb;
begin
 if actor is null or not paw_private.social_allowed(actor,target) then return '{}'::jsonb; end if;
 select * into p from paw_private.social_presence where player_id=target;
 active:=p.seen_at>now()-interval '40 seconds' and public.paw_account_session_active(target,p.session_id,p.launcher_id);
 if active and p.playing_since is not null and p.game_activity is not null then
  summary:=p.game_activity-'players'-'room'-'self';
 end if;
 return jsonb_build_object('presence',case when coalesce(active,false) then case when p.playing_since is null then 'online' else 'playing' end else 'offline' end,
 'last_seen',p.seen_at,'playing_since',case when active then p.playing_since end,'channel',coalesce(p.channel,'unknown'),
 'versions',p.versions,'configuration',p.configuration,'components',coalesce(p.components,'{}'::jsonb),
 'activity',summary,'avatar_revision',(select avatar_changed_at from public.paw_profiles where id=target));
end; $$;
revoke all on function paw_private.friend_presence(uuid,uuid) from public,anon,authenticated;

create function public.paw_game_activity(target uuid) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare actor uuid:=paw_private.social_actor(); p paw_private.social_presence; participant jsonb; people jsonb:='[]'::jsonb; candidates jsonb; activity jsonb;
begin
 if actor is null then return jsonb_build_object('status','session_expired'); end if;
 if target is null or not paw_private.social_allowed(actor,target) then return jsonb_build_object('status','player_unavailable'); end if;
 select * into p from paw_private.social_presence where player_id=target;
 if p.playing_since is null or p.seen_at<=now()-interval '40 seconds' or p.game_activity is null
 or not public.paw_account_session_active(target,p.session_id,p.launcher_id)
 then return jsonb_build_object('status','ok','activity',null); end if;
 activity:=p.game_activity;
 for participant in select value from jsonb_array_elements(coalesce(nullif(activity->'players','null'::jsonb),'[]'::jsonb)) loop
  candidates:='[]'::jsonb;
  if participant->>'bot'='false' and activity->>'room' is not null then
   select coalesce(jsonb_agg(jsonb_build_object('id',r.id,'nickname',r.nickname,'display_name',r.display_name)),'[]'::jsonb) into candidates
   from (select r.id,r.nickname,r.display_name
   from paw_private.social_presence s join public.paw_profiles r on r.id=s.player_id
   where s.game_activity is not null and s.game_activity->>'room'=activity->>'room' and s.game_activity->>'self'=participant->>'key'
   and s.seen_at>now()-interval '40 seconds' and s.playing_since is not null and public.paw_account_session_active(r.id,s.session_id,s.launcher_id)
   and r.deleted_at is null and not (r.banned_at is not null and (r.ban_until is null or r.ban_until>now()))
   and not exists(select 1 from public.paw_blocks b where (b.owner_id=actor and b.target_id=r.id) or (b.owner_id=r.id and b.target_id=actor))
   limit 2) r;
  elsif participant->>'bot'='false' and participant->>'key'=activity->>'self' then
   select jsonb_build_array(jsonb_build_object('id',r.id,'nickname',r.nickname,'display_name',r.display_name)) into candidates
   from public.paw_profiles r where r.id=target;
  end if;
  -- A nickname is never an identity proof; ambiguous simultaneous claims remain unknown.
  people:=people||jsonb_build_array((participant-'profile')||case when jsonb_array_length(candidates)=1 then jsonb_build_object('profile',candidates->0) else '{}'::jsonb end);
 end loop;
 return jsonb_build_object('status','ok','activity',(activity-'room'-'self')||jsonb_build_object('players',people),'observed_at',p.seen_at);
end; $$;
revoke all on function public.paw_game_activity(uuid) from public,anon,authenticated;
grant execute on function public.paw_game_activity(uuid) to authenticated;
