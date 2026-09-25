-- Apply the observer migration only over the audited production validator.
-- Equivalent body to migrations/20260925000000_game_activity_observers.sql.
begin;
set local lock_timeout='5s';
set local statement_timeout='30s';
do $deploy$
declare definition text;
begin
 if (select md5(replace(prosrc,E'\r','')) from pg_proc where oid='paw_private.valid_game_activity(jsonb)'::regprocedure) is distinct from 'b01105abadb6bdb525395136b46be7b9' then
  raise exception 'Unexpected activity validator; inspect before deploying';
 end if;
 definition:=pg_get_functiondef('paw_private.valid_game_activity(jsonb)'::regprocedure);
 definition:=replace(definition,'''race'',''subrace''))','''race'',''subrace'',''observer''))');
 definition:=replace(definition,'  -- Native identifiers',
 $addition$  if p->'observer' is not null and p->'observer'<>'null'::jsonb and jsonb_typeof(p->'observer')<>'boolean' then return false; end if;
  if p->>'observer'='true' and (p->>'bot'='true' or p->>'team' is not null or p->>'color' is not null or p->>'race' is not null or p->>'subrace' is not null) then return false; end if;
  -- Native identifiers$addition$);
 execute definition;
 if (select md5(replace(prosrc,E'\r','')) from pg_proc where oid='paw_private.valid_game_activity(jsonb)'::regprocedure) is distinct from 'c3d0db57bc183dac69c62f6988d337ec' then
  raise exception 'Observer validator did not match tested migration';
 end if;
 if has_function_privilege('anon','paw_private.valid_game_activity(jsonb)','execute') or has_function_privilege('authenticated','paw_private.valid_game_activity(jsonb)','execute') then
  raise exception 'Unexpected direct validator access';
 end if;
end; $deploy$;
commit;
