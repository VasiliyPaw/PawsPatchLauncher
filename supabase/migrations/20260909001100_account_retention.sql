create table paw_private.maintenance_secret(token text not null check(length(token)=64));
insert into paw_private.maintenance_secret values(replace(gen_random_uuid()::text||gen_random_uuid()::text,'-',''));
create table paw_private.service_health(name text primary key,checked_at timestamptz not null,ok boolean not null);
alter table paw_private.maintenance_secret enable row level security;
alter table paw_private.service_health enable row level security;
revoke all on paw_private.maintenance_secret,paw_private.service_health from public,anon,authenticated;
create function public.paw_maintenance_authorize(proof text) returns boolean language sql stable security definer set search_path='' as $$
 select proof is not null and length(proof)=64 and exists(select 1 from paw_private.maintenance_secret where token=proof);
$$;
create function public.paw_deletion_candidates() returns jsonb language plpgsql security definer set search_path='' as $$
declare ids uuid[];
begin
 select array_agg(id) into ids from (select id from public.paw_profiles
  where not protected_admin and deleted_at+interval '7 days'<=clock_timestamp()
  order by deleted_at,id limit 5 for update skip locked) q;
 update public.paw_profiles set purge_started_at=coalesce(purge_started_at,clock_timestamp()) where id=any(ids);
 return coalesce((select jsonb_agg(jsonb_build_object('id',p.id,'saves',coalesce((select jsonb_agg(o.sender_id::text||'/'||o.id::text||'.rsg')
  from paw_private.social_offers o where p.id in(o.sender_id,o.recipient_id) and o.kind='save'),'[]'))) from public.paw_profiles p where p.id=any(ids)),'[]');
end; $$;
create function paw_private.finalize_identity() returns trigger language plpgsql security definer set search_path='' as $$
begin
 update paw_private.player_identities set deleted_at=coalesce(deleted_at,clock_timestamp()),finalized_at=clock_timestamp() where id=old.id;
 return old;
end; $$;
create trigger paw_finalize_identity before delete on public.paw_profiles for each row execute function paw_private.finalize_identity();
create function public.paw_maintenance_finished(succeeded boolean) returns void language sql security definer set search_path='' as $$
 insert into paw_private.service_health values('deletion',clock_timestamp(),succeeded) on conflict(name) do update set checked_at=excluded.checked_at,ok=excluded.ok;
$$;
create function public.paw_admin_status() returns jsonb language plpgsql stable security definer set search_path='' as $$
declare h paw_private.service_health;
begin
 if paw_private.admin_level(paw_private.social_actor())<1 then return jsonb_build_object('status','admin_required');end if;
 select * into h from paw_private.service_health where name='deletion';
 return jsonb_build_object('status','ok','checked_at',now(),'cleanup_at',h.checked_at,'cleanup_ok',h.ok);
end; $$;
revoke all on function public.paw_maintenance_authorize(text),public.paw_deletion_candidates(),paw_private.finalize_identity(),public.paw_maintenance_finished(boolean),public.paw_admin_status() from public,anon,authenticated;
grant execute on function public.paw_maintenance_authorize(text),public.paw_deletion_candidates(),public.paw_maintenance_finished(boolean) to service_role;
grant execute on function public.paw_admin_status() to authenticated;
