-- Installed only after account-maintenance deployment. No secret is embedded in
-- cron job text, source control, responses or client configuration.
create extension if not exists pg_cron;
create extension if not exists pg_net with schema extensions;
create function paw_private.schedule_account_cleanup() returns bigint language sql security definer set search_path='' as $$
 select net.http_post(
  url:='https://trdzsdclscuwwmxnepyt.supabase.co/functions/v1/account-maintenance',
  headers:=jsonb_build_object('Content-Type','application/json','x-paw-maintenance',(select token from paw_private.maintenance_secret)),
  body:='{}'::jsonb,timeout_milliseconds:=150000);
$$;
revoke all on function paw_private.schedule_account_cleanup() from public,anon,authenticated;
select cron.schedule('paw-account-retention','*/5 * * * *','select paw_private.schedule_account_cleanup()');
