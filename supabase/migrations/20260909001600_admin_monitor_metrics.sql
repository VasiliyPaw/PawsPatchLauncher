alter table paw_private.resource_usage drop constraint resource_usage_metric_check;
alter table paw_private.resource_usage add constraint resource_usage_metric_check
 check(metric in('egress','cached_egress','functions','functions_daily','emails_daily','emails_monthly'));
alter table paw_private.resource_usage add column period_start timestamptz,
 add column observed_until timestamptz,add column coverage text not null default 'complete' check(coverage in('complete','partial'));

create or replace function public.paw_monitor_store(run uuid,payload jsonb) returns boolean
language plpgsql security definer set search_path='' as $$
declare m jsonb;
begin
 if jsonb_typeof(payload) is distinct from 'object' or octet_length(payload::text)>65536 or payload->>'schema' is distinct from '1'
 or jsonb_typeof(payload->'metrics') is distinct from 'array' then return false;end if;
 if jsonb_array_length(payload->'metrics')>8 then return false;end if;
 update paw_private.monitor_state set snapshot=payload,checked_at=clock_timestamp(),run_id=null
 where run_id=run and started_at>clock_timestamp()-interval '5 minutes';
 if not found then return false;end if;
 for m in select value from jsonb_array_elements(payload->'metrics') loop
  if coalesce(m->>'metric','') not in('functions_daily','emails_daily','emails_monthly')
   or coalesce(m->>'source','') not in('supabase_requests_24h','resend_metrics')
   or coalesce(m->>'used','')!~'^[0-9]{1,15}$' or coalesce(m->>'coverage','') not in('complete','partial')
   or nullif(m->>'checked_at','')::timestamptz is null
   then raise invalid_parameter_value using message='invalid_monitor_metric';end if;
  insert into paw_private.resource_usage(metric,used,quota,checked_at,period_start,period_end,observed_until,source,coverage)
  values(m->>'metric',(m->>'used')::bigint,null,(m->>'checked_at')::timestamptz,(m->>'period_start')::timestamptz,
    (m->>'period_end')::timestamptz,(m->>'observed_until')::timestamptz,m->>'source',m->>'coverage')
  on conflict(metric) do update set used=excluded.used,quota=null,checked_at=excluded.checked_at,period_start=excluded.period_start,
   period_end=excluded.period_end,observed_until=excluded.observed_until,source=excluded.source,coverage=excluded.coverage;
 end loop;
 return true;
exception when invalid_parameter_value or invalid_text_representation or invalid_datetime_format or datetime_field_overflow or check_violation or not_null_violation then return false;
end;$$;

create function paw_private.monitor_snapshot() returns jsonb language sql stable set search_path='' as $$
 select jsonb_build_object('checked_at',checked_at,'token_expires_at',snapshot->'token_expires_at','services',snapshot->'services',
  'email',snapshot->'email','storage',snapshot->'storage','functions',snapshot->'functions','errors',snapshot->'errors')
 from paw_private.monitor_state where singleton;
$$;
revoke all on function paw_private.monitor_snapshot() from public,anon,authenticated;

create or replace function public.paw_admin_status() returns jsonb language plpgsql stable security definer set search_path='' as $$
declare h paw_private.service_health;
begin
 if paw_private.admin_level(paw_private.social_actor())<1 then return jsonb_build_object('status','admin_required');end if;
 select * into h from paw_private.service_health where name='deletion';
 return jsonb_build_object('status','ok','checked_at',now(),'cleanup_at',h.checked_at,'cleanup_ok',h.ok,'monitor',paw_private.monitor_snapshot());
end;$$;
create or replace function public.paw_admin_resources() returns jsonb language plpgsql stable security definer set search_path='' as $$
declare actor uuid:=paw_private.social_actor(); metrics jsonb;
begin
 if paw_private.admin_level(actor)<1 then return jsonb_build_object('status','admin_required');end if;
 select coalesce(jsonb_agg(to_jsonb(u)),'[]'::jsonb) into metrics from paw_private.resource_usage u;
 return jsonb_build_object('status','ok','checked_at',now(),'database_bytes',pg_database_size(current_database()),
  'messages_bytes',pg_total_relation_size('public.paw_messages'),'messages_count',(select count(*) from public.paw_messages),
  'offers_bytes',pg_total_relation_size('paw_private.social_offers'),
  'avatars_bytes',(select coalesce(sum(case when metadata->>'size' ~ '^[0-9]+$' then (metadata->>'size')::bigint else 0 end),0) from storage.objects where bucket_id='paw-avatars'),
  'saves_bytes',(select coalesce(sum(case when metadata->>'size' ~ '^[0-9]+$' then (metadata->>'size')::bigint else 0 end),0) from storage.objects where bucket_id='paw-social-saves'),
  'storage_bytes',(select coalesce(sum(case when metadata->>'size' ~ '^[0-9]+$' then (metadata->>'size')::bigint else 0 end),0) from storage.objects),
  'removed_messages',(select coalesce(sum(removed_count),0) from paw_private.conversation_history),
  'dialog_limit',10000,'cleanup_batch',5000,'provider_metrics',metrics,'monitor',paw_private.monitor_snapshot(),
  'quota_source','free_reference_not_verified','database_reference_limit',524288000,'storage_reference_limit',1073741824);
end;$$;
