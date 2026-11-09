begin;
create table paw_private.profile_visibility (
 player_id uuid primary key references public.paw_profiles(id) on delete cascade,
 configuration_visibility text not null default 'all' check(configuration_visibility in ('all','friends','nobody')),
 activity_visibility text not null default 'all' check(activity_visibility in ('all','friends','nobody'))
);
alter table paw_private.profile_visibility enable row level security;
revoke all on paw_private.profile_visibility from public,anon,authenticated;

create function paw_private.profile_field_visible(actor uuid,target uuid,field text) returns boolean
language sql stable security definer set search_path='' as $$
 select actor is not null and field in ('configuration','activity') and (actor=target or coalesce((
  select case when field='configuration' then configuration_visibility when field='activity' then activity_visibility else 'nobody' end
  from paw_private.profile_visibility where player_id=target),'all')='all'
  or (coalesce((select case when field='configuration' then configuration_visibility when field='activity' then activity_visibility else 'nobody' end
   from paw_private.profile_visibility where player_id=target),'all')='friends'
   and exists(select 1 from public.paw_friendships where low_id=least(actor,target) and high_id=greatest(actor,target) and accepted)));
$$;
revoke all on function paw_private.profile_field_visible(uuid,uuid,text) from public,anon,authenticated;

create function public.paw_profile_visibility(configuration_visibility text default null,activity_visibility text default null) returns jsonb
language plpgsql security definer set search_path='' as $$
declare actor uuid:=paw_private.social_actor(); saved paw_private.profile_visibility;
begin
 if actor is null then return jsonb_build_object('status','session_expired');end if;
 if configuration_visibility is not null or activity_visibility is not null then
  if configuration_visibility is null or activity_visibility is null or configuration_visibility not in ('all','friends','nobody') or activity_visibility not in ('all','friends','nobody') then
   return jsonb_build_object('status','invalid_visibility');end if;
  perform 1 from public.paw_profiles where id=actor for update;
  insert into paw_private.profile_visibility as p(player_id,configuration_visibility,activity_visibility)
   values(actor,configuration_visibility,activity_visibility)
   on conflict(player_id) do update set configuration_visibility=excluded.configuration_visibility,activity_visibility=excluded.activity_visibility;
 end if;
 select * into saved from paw_private.profile_visibility where player_id=actor;
 return jsonb_build_object('status','ok','configuration_visibility',coalesce(saved.configuration_visibility,'all'),'activity_visibility',coalesce(saved.activity_visibility,'all'));
end;$$;
revoke all on function public.paw_profile_visibility(text,text) from public,anon,authenticated;
grant execute on function public.paw_profile_visibility(text,text) to authenticated;

create function paw_private.visible_profile_fields(actor uuid,target uuid,fields jsonb) returns jsonb
language plpgsql stable security definer set search_path='' as $$
begin
 if fields is null or fields='{}'::jsonb then return fields;end if;
 if not paw_private.profile_field_visible(actor,target,'configuration') then
  fields:=(fields-'channel'-'components'-'configuration'-'versions')||jsonb_build_object('configuration_hidden',true);
 end if;
 if not paw_private.profile_field_visible(actor,target,'activity') then fields:=(fields-'activity')||jsonb_build_object('activity_hidden',true);end if;
 return fields;
end;$$;
revoke all on function paw_private.visible_profile_fields(uuid,uuid,jsonb) from public,anon,authenticated;

do $clone$ declare definition text;begin
 definition:=pg_get_functiondef('paw_private.friend_presence(uuid,uuid)'::regprocedure);
 execute replace(definition,'paw_private.friend_presence(','paw_private.friend_presence_before_visibility(');
 definition:=pg_get_functiondef('paw_private.profile_presence(uuid,uuid)'::regprocedure);
 execute replace(definition,'paw_private.profile_presence(','paw_private.profile_presence_before_visibility(');
 definition:=pg_get_functiondef('public.paw_game_activity(uuid)'::regprocedure);
 execute replace(definition,'public.paw_game_activity(','paw_private.game_activity_before_visibility(');
 definition:=pg_get_functiondef('public.paw_profile_activity(uuid)'::regprocedure);
 execute replace(definition,'public.paw_profile_activity(','paw_private.profile_activity_before_visibility(');
end;$clone$;
revoke all on function paw_private.friend_presence_before_visibility(uuid,uuid),paw_private.profile_presence_before_visibility(uuid,uuid),
 paw_private.game_activity_before_visibility(uuid),paw_private.profile_activity_before_visibility(uuid) from public,anon,authenticated;

create or replace function paw_private.friend_presence(actor uuid,target uuid) returns jsonb
language sql stable security definer set search_path='' as $$
 select paw_private.visible_profile_fields(actor,target,paw_private.friend_presence_before_visibility(actor,target));
$$;
create or replace function paw_private.profile_presence(actor uuid,target uuid) returns jsonb
language sql stable security definer set search_path='' as $$
 select paw_private.visible_profile_fields(actor,target,paw_private.profile_presence_before_visibility(actor,target));
$$;

create function paw_private.visible_activity(actor uuid,target uuid,details jsonb) returns jsonb
language sql stable security definer set search_path='' as $$
 select case when details->>'status'='ok' and not paw_private.profile_field_visible(actor,target,'activity')
  then jsonb_build_object('status','ok','activity',null,'activity_hidden',true) else details end;
$$;
revoke all on function paw_private.visible_activity(uuid,uuid,jsonb) from public,anon,authenticated;

create or replace function public.paw_game_activity(target uuid) returns jsonb
language sql stable security definer set search_path='' as $$
 select paw_private.visible_activity(paw_private.social_actor(),target,paw_private.game_activity_before_visibility(target));
$$;
create or replace function public.paw_profile_activity(target uuid) returns jsonb
language sql stable security definer set search_path='' as $$
 select paw_private.visible_activity(paw_private.social_actor(),target,paw_private.profile_activity_before_visibility(target));
$$;
notify pgrst,'reload schema';
commit;
