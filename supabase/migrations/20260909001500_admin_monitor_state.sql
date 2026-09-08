-- A separate scheduler credential, never visible to a launcher or an admin RPC.
create table paw_private.monitor_state (
 singleton boolean primary key default true check(singleton),
 proof text not null check(length(proof)=64),
 run_id uuid, started_at timestamptz, checked_at timestamptz,
 snapshot jsonb not null default '{}'::jsonb
);
insert into paw_private.monitor_state(singleton,proof)
 values(true,replace(gen_random_uuid()::text||gen_random_uuid()::text,'-',''));
alter table paw_private.monitor_state enable row level security;
revoke all on paw_private.monitor_state from public,anon,authenticated;

create function public.paw_monitor_begin(proof text) returns uuid
language plpgsql security definer set search_path='' as $$
declare run uuid;
begin
 update paw_private.monitor_state s set run_id=gen_random_uuid(),started_at=clock_timestamp()
 where s.proof=paw_monitor_begin.proof and length(paw_monitor_begin.proof)=64
 and (s.started_at is null or s.started_at<clock_timestamp()-interval '1 minute') returning s.run_id into run;
 return run;
end;$$;
create function public.paw_monitor_store(run uuid,payload jsonb) returns boolean
language plpgsql security definer set search_path='' as $$
begin
 if jsonb_typeof(payload)<>'object' or octet_length(payload::text)>65536 then return false;end if;
 update paw_private.monitor_state set snapshot=payload,checked_at=clock_timestamp()
 where run_id=run and started_at>clock_timestamp()-interval '5 minutes';
 return found;
end;$$;
revoke all on function public.paw_monitor_begin(text),public.paw_monitor_store(uuid,jsonb) from public,anon,authenticated;
grant execute on function public.paw_monitor_begin(text),public.paw_monitor_store(uuid,jsonb) to service_role;
