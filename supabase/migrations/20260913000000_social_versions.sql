-- Prepared for local review. No production deployment is part of this change.
-- Optional bounded metadata uses the existing presence RPC envelope. Legacy writes clear
-- versions atomically with configuration; client version claims are not authorization.
alter table paw_private.social_presence add column versions jsonb
 check(versions is null or (jsonb_typeof(versions)='object' and octet_length(versions::text)<=512));

create or replace function public.paw_presence(playing boolean, channel text, components jsonb, configuration text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare actor uuid:=paw_private.social_actor(); prior paw_private.social_presence; stamp timestamptz:=clock_timestamp(); sid uuid; parts text[]; version_info jsonb;
begin
 if actor is null then return jsonb_build_object('status','session_expired'); end if;
 if playing is null or channel is null or channel not in ('stable','beta','unknown') or components is null
 or jsonb_typeof(components)<>'object' or octet_length(components::text)>2048
 then return jsonb_build_object('status','invalid_presence'); end if;
 version_info:=components->'_versions';
 components:=components-'_versions';
 if version_info is not null then
  if jsonb_typeof(version_info)<>'object' or octet_length(version_info::text)>512
   or exists(select 1 from jsonb_each(version_info) e where e.key not in ('launcher','mod','channel','content_id','patch'))
   or jsonb_typeof(version_info->'launcher') is distinct from 'string'
   or length(version_info->>'launcher')>32 or (version_info->>'launcher') !~ '^[0-9]+[.][0-9]+([.][0-9]+){0,2}$'
   or (version_info->'mod' is not null and version_info->'mod'<>'null'::jsonb and
      (jsonb_typeof(version_info->'mod')<>'string' or version_info->>'mod' not in ('vanilla','immortals','arcane-wars')))
   or (version_info->'channel' is not null and version_info->'channel'<>'null'::jsonb and
      (jsonb_typeof(version_info->'channel')<>'string' or version_info->>'channel' not in ('stable','beta')))
   or (version_info->'content_id' is not null and version_info->'content_id'<>'null'::jsonb and
      (jsonb_typeof(version_info->'content_id')<>'string' or (version_info->>'content_id') !~ '^[0-9A-Fa-f]{64}$'))
   or (version_info->'patch' is not null and version_info->'patch'<>'null'::jsonb and
      (jsonb_typeof(version_info->'patch')<>'string' or (version_info->>'patch') !~ '^[A-Za-z0-9.+-]{1,64}$'))
  then return jsonb_build_object('status','invalid_presence'); end if;
  if version_info->>'mod' is not null and (configuration is null or version_info->>'channel' is distinct from channel
   or version_info->>'mod' is distinct from case when configuration like 'PAW-%-VANILLA%' then 'vanilla'
      when configuration like 'PAW-%-IMMORTALS%' then 'immortals' else 'arcane-wars' end)
  then return jsonb_build_object('status','invalid_presence'); end if;
 end if;
 if exists(select 1 from jsonb_each(components) e where e.key not in
 ('core','russian','colors','desync','hostility','roaming','additional_roaming','siege','powers_shards','large_maps') or jsonb_typeof(e.value)<>'boolean')
 then return jsonb_build_object('status','invalid_presence'); end if;
 if configuration is not null then
  if octet_length(configuration)>128 or configuration !~ '^PAW-(STABLE|BETA)-((VANILLA|IMMORTALS)(-RU[01])?(-PP1(-DATA)?)?|IW[01]-SP[124]-RM[01]-SG[01]-LM1-RU[01]-CL[01]-OOS[01](-PS[01])?|IW[01]-SP[124]-RM[01]-SG[01]-LM0-RU[01]-CL[01]-OOS[01](-PS[01])?-PP0|IW0-SP[124]-RM[01]-SG[01]-LM1-RU[01]-CL0-OOS0(-PS[01])?-DATA|IW0-SP[124]-RM[01]-SG[01]-LM0-RU[01]-CL0-OOS0(-PS[01])?-PP0-DATA)$'
  then return jsonb_build_object('status','invalid_presence'); end if;
  parts:=string_to_array(configuration,'-');
  if lower(parts[2])<>channel then return jsonb_build_object('status','invalid_presence'); end if;
  if parts[3] in ('VANILLA','IMMORTALS') then
   components:=jsonb_build_object('core','PP1'=any(parts),'hostility',false,'roaming',false,'additional_roaming',false,
    'siege',false,'large_maps',false,'russian','RU1'=any(parts),'colors',false,'desync',false,'powers_shards',false);
  else
   components:=jsonb_build_object('core',not ('PP0'=any(parts)),'hostility',parts[3]='IW1','roaming',parts[4]<>'SP1',
    'additional_roaming',parts[5]='RM1','siege',parts[6]='SG1','large_maps',parts[7]='LM1',
    'russian',parts[8]='RU1','colors',parts[9]='CL1','desync',parts[10]='OOS1','powers_shards',not ('PS0'=any(parts)));
  end if;
 end if;
 perform 1 from public.paw_profiles where id=actor for update;
 if paw_private.social_actor() is null then return jsonb_build_object('status','session_expired'); end if;
 sid := (auth.jwt()->>'session_id')::uuid;
 select * into prior from paw_private.social_presence where player_id=actor;
 -- Ignore overly frequent calls; timestamps/duration always come from the server.
 if prior.seen_at>stamp-interval '3 seconds' and prior.session_id=sid and prior.launcher_id=paw_private.launcher_header()
 then return jsonb_build_object('status','ok'); end if;
 insert into paw_private.social_presence(player_id,session_id,launcher_id,seen_at,playing_since,channel,components,configuration,versions) values(actor,sid,paw_private.launcher_header(),stamp,
 case when not playing then null when prior.playing_since is not null and prior.seen_at>stamp-interval '40 seconds'
 and prior.session_id=sid and prior.launcher_id=paw_private.launcher_header() then prior.playing_since else stamp end,channel,components,configuration,version_info)
 on conflict(player_id) do update set session_id=excluded.session_id,launcher_id=excluded.launcher_id,seen_at=excluded.seen_at,
 playing_since=excluded.playing_since,channel=excluded.channel,components=excluded.components,configuration=excluded.configuration,versions=excluded.versions;
 return jsonb_build_object('status','ok');
end; $$;
revoke all on function public.paw_presence(boolean,text,jsonb,text) from public,anon,authenticated;
grant execute on function public.paw_presence(boolean,text,jsonb,text) to authenticated;

create or replace function paw_private.friend_presence(actor uuid,target uuid) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare p paw_private.social_presence; active boolean;
begin
 if actor is null or not paw_private.social_allowed(actor,target) then return '{}'::jsonb; end if;
 select * into p from paw_private.social_presence where player_id=target;
 active := p.seen_at>now()-interval '40 seconds' and public.paw_account_session_active(target,p.session_id,p.launcher_id);
 return jsonb_build_object('presence',case when coalesce(active,false) then case when p.playing_since is null then 'online' else 'playing' end else 'offline' end,
 'last_seen',p.seen_at,'playing_since',case when active then p.playing_since end,'channel',coalesce(p.channel,'unknown'),
 'versions',p.versions,'configuration',p.configuration,'components',coalesce(p.components,'{}'::jsonb),'avatar_revision',(select avatar_changed_at from public.paw_profiles where id=target));
end; $$;
revoke all on function paw_private.friend_presence(uuid,uuid) from public,anon,authenticated;

