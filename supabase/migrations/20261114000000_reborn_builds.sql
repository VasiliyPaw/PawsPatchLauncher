-- Private distribution only. Empty release/beta channels until an accepted build is published.
create table paw_private.reborn_builds (
 id uuid primary key default gen_random_uuid(),
 channel text not null check(channel in ('stable','beta')),
 version text not null check(version ~ '^[A-Za-z0-9][A-Za-z0-9.+_-]{0,63}$'),
 size bigint not null check(size between 1 and 17179869184),
 sha256 text not null check(sha256 ~ '^[0-9A-Fa-f]{64}$'),
 executable text not null check(executable ~* '^[A-Za-z0-9][A-Za-z0-9_. -]{0,100}\.exe$' and executable not like '%..%'),
 notes jsonb not null default '{}' check(jsonb_typeof(notes)='object' and octet_length(notes::text)<=70000),
 published_at timestamptz not null default now(),
 enabled boolean not null default false
);
alter table paw_private.reborn_builds enable row level security;
revoke all on paw_private.reborn_builds from public,anon,authenticated;
grant all on paw_private.reborn_builds to service_role;
create index reborn_builds_latest on paw_private.reborn_builds(channel,published_at desc) where enabled;

create function public.paw_reborn_authorize(player uuid,session uuid,launcher uuid,selected_channel text default null,build_id uuid default null)
returns jsonb language plpgsql stable security definer set search_path='' as $$
declare item paw_private.reborn_builds;
begin
 if not public.paw_account_session_active(player,session,launcher) then return jsonb_build_object('status','session_replaced');end if;
 if not paw_private.player_live(player) or not exists(select 1 from public.paw_profiles where id=player and (paws_team or admin_level>0))
 then return jsonb_build_object('status','reborn_access_denied');end if;
 if selected_channel is null and build_id is null then
  return jsonb_build_object('status','ok','releases',coalesce((select jsonb_agg(to_jsonb(r)-'enabled' order by r.channel) from (
   select distinct on (channel) * from paw_private.reborn_builds where enabled and published_at<=now() order by channel,published_at desc,id desc
  ) r),'[]'::jsonb));
 end if;
 if selected_channel not in ('stable','beta') or selected_channel is null or build_id is null
 then return jsonb_build_object('status','reborn_unavailable');end if;
 select * into item from paw_private.reborn_builds where id=build_id and channel=selected_channel and enabled and published_at<=now();
 if not found then return jsonb_build_object('status','reborn_unavailable');end if;
 return jsonb_build_object('status','ok','release',to_jsonb(item)-'enabled');
end; $$;
revoke all on function public.paw_reborn_authorize(uuid,uuid,uuid,text,uuid) from public,anon,authenticated;
grant execute on function public.paw_reborn_authorize(uuid,uuid,uuid,text,uuid) to service_role;

insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
values('paw-reborn-builds','paw-reborn-builds',false,17179869184,array['application/zip','application/octet-stream']);
-- No anon/authenticated storage policy: only the authorized edge service issues expiring URLs.
