-- Reuse the same live role/session check as private build downloads.
create function public.paw_reborn_history(player uuid,session uuid,launcher uuid)
returns jsonb language plpgsql stable security definer set search_path='' as $$
declare permission jsonb;
begin
 permission := public.paw_reborn_authorize(player,session,launcher);
 if permission->>'status' <> 'ok' then return permission; end if;
 return jsonb_build_object('status','ok','releases',coalesce((select jsonb_agg(to_jsonb(r)-'enabled' order by r.published_at desc,r.id desc) from (
  select * from paw_private.reborn_builds where enabled and published_at<=now() order by published_at desc,id desc limit 200
 ) r),'[]'::jsonb));
end; $$;
revoke all on function public.paw_reborn_history(uuid,uuid,uuid) from public,anon,authenticated;
grant execute on function public.paw_reborn_history(uuid,uuid,uuid) to service_role;
