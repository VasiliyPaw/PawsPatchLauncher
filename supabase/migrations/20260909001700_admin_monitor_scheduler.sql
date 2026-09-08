-- The request authenticates with a dedicated, private database-generated proof.
-- Neither provider key appears in cron text or a launcher response.
create function paw_private.schedule_admin_monitor() returns bigint
language sql security definer set search_path='' as $$
 select net.http_post(
  url:='https://trdzsdclscuwwmxnepyt.supabase.co/functions/v1/admin-monitor',
  headers:=jsonb_build_object('Content-Type','application/json','x-paw-monitor',(select proof from paw_private.monitor_state)),
  body:='{}'::jsonb,timeout_milliseconds:=60000);
$$;
revoke all on function paw_private.schedule_admin_monitor() from public,anon,authenticated;
select cron.schedule('paw-admin-monitor','*/15 * * * *','select paw_private.schedule_admin_monitor()');
