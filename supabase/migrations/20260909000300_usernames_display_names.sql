-- Existing nickname is the unique username. Stable UUIDs and all relationships remain unchanged.
alter table public.paw_profiles add column display_name text, add column display_name_changed_at timestamptz;
update public.paw_profiles set display_name=nickname;
alter table public.paw_profiles alter column display_name set not null;
create function paw_private.valid_display_name(value text) returns boolean
language sql immutable set search_path='' as $$
 select value is not null and length(value) between 1 and 32 and value=btrim(value)
 and value !~ '[[:cntrl:]]' and value !~ '[​‌‍‎‏‪-‮⁦-⁩]' and value !~ '^[[:space:]]*$';
$$;
revoke all on function paw_private.valid_display_name(text) from public,anon,authenticated;
alter table public.paw_profiles add constraint display_name_valid check(paw_private.valid_display_name(display_name));
create function paw_private.profile_display_name() returns trigger language plpgsql security definer set search_path='' as $$
begin
 if new.display_name is null then
  select coalesce(raw_user_meta_data->>'display_name',new.nickname) into new.display_name from auth.users where id=new.id;
 end if;
 if not paw_private.valid_display_name(new.display_name) then raise exception 'invalid_display_name';end if;
 return new;
end;$$;
revoke all on function paw_private.profile_display_name() from public,anon,authenticated;
create trigger paw_profile_display_name before insert on public.paw_profiles for each row execute function paw_private.profile_display_name();
grant select(display_name,display_name_changed_at) on public.paw_profiles to authenticated;

create function public.paw_change_display_name(candidate text) returns jsonb language plpgsql security definer set search_path='' as $$
declare actor uuid:=paw_private.social_actor(); changed timestamptz; current_name text;
begin
 if actor is null then return jsonb_build_object('status','session_expired');end if;
 if not paw_private.valid_display_name(candidate) then return jsonb_build_object('status','invalid_display_name');end if;
 select display_name,display_name_changed_at into current_name,changed from public.paw_profiles where id=actor for update;
 if paw_private.social_actor() is null then return jsonb_build_object('status','session_expired');end if;
 if current_name=candidate then return jsonb_build_object('status','unchanged');end if;
 if changed>clock_timestamp()-interval '5 minutes' then return jsonb_build_object('status','display_name_cooldown');end if;
 update public.paw_profiles set display_name=candidate,display_name_changed_at=clock_timestamp() where id=actor;
 return jsonb_build_object('status','ok');
end;$$;
revoke all on function public.paw_change_display_name(text) from public,anon,authenticated;
grant execute on function public.paw_change_display_name(text) to authenticated;

alter function public.paw_social_list() rename to paw_social_list_before_names;
revoke all on function public.paw_social_list_before_names() from public,anon,authenticated;
create function public.paw_social_list() returns jsonb language plpgsql security definer set search_path='' as $$
declare result jsonb;
begin
 result:=public.paw_social_list_before_names();
 if result->>'status'<>'ok' then return result;end if;
 return jsonb_set(result,'{players}',coalesce((select jsonb_agg(entry||jsonb_build_object('display_name',p.display_name) order by ord)
 from jsonb_array_elements(result->'players') with ordinality x(entry,ord)
 join public.paw_profiles p on p.id=(entry->>'id')::uuid),'[]'::jsonb));
end;$$;
revoke all on function public.paw_social_list() from public,anon,authenticated;
grant execute on function public.paw_social_list() to authenticated;

create table paw_private.username_login_limits(key text primary key, started_at timestamptz not null, attempts integer not null);
alter table paw_private.username_login_limits enable row level security;
revoke all on paw_private.username_login_limits from public,anon,authenticated;
create function public.paw_username_login_target(candidate text,client_bucket text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare bucket_key text; count integer; address text;
begin
 if candidate is null or candidate !~ '^[A-Za-zА-Яа-яЁё0-9][A-Za-zА-Яа-яЁё0-9_.-]{2,23}$'
 or client_bucket is null or client_bucket !~ '^[0-9a-f]{64}$' then return jsonb_build_object('status','invalid_credentials');end if;
 -- Fixed lock order. Global bound also bounds the number of per-name/IP rows.
 foreach bucket_key in array array['0global','1ip:'||client_bucket,'2name:'||paw_private.nickname_key(candidate)] loop
  insert into paw_private.username_login_limits as l(key,started_at,attempts) values(bucket_key,clock_timestamp(),1)
  on conflict(key) do update set attempts=case when l.started_at<clock_timestamp()-interval '1 minute' then 1 else l.attempts+1 end,
   started_at=case when l.started_at<clock_timestamp()-interval '1 minute' then clock_timestamp() else l.started_at end returning attempts into count;
  if count>(case when bucket_key='0global' then 60 when left(bucket_key,3)='1ip' then 20 else 8 end) then return jsonb_build_object('status','rate_limit');end if;
 end loop;
 delete from paw_private.username_login_limits where started_at<clock_timestamp()-interval '1 day';
 select u.email into address from public.paw_profiles p join auth.users u on u.id=p.id
 where p.nickname_key=paw_private.nickname_key(candidate) collate "C" and not p.deletion_pending;
 return jsonb_build_object('status','ok','email',coalesce(address,'missing-'||client_bucket||'@example.invalid'));
end;$$;
revoke all on function public.paw_username_login_target(text,text) from public,anon,authenticated;
grant execute on function public.paw_username_login_target(text,text) to service_role;
