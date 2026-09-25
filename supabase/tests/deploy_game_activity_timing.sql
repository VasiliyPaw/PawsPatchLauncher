-- Add explicit match timing over the audited observer validator, atomically.
begin;
set local lock_timeout='5s';
set local statement_timeout='30s';
do $deploy$
declare definition text;
begin
 if (select md5(replace(prosrc,E'\r','')) from pg_proc where oid='paw_private.valid_game_activity(jsonb)'::regprocedure) is distinct from 'c3d0db57bc183dac69c62f6988d337ec' then
  raise exception 'Unexpected activity validator; inspect before deploying';
 end if;
 definition:=pg_get_functiondef('paw_private.valid_game_activity(jsonb)'::regprocedure);
 definition:=replace(definition,'''room'',''self'',''players''))','''room'',''self'',''players'',''paused'',''speed''))');
 definition:=replace(definition,' foreach key in array array[''elapsed'',''width'',''height''] loop',
 $addition$ if a->'paused' is not null and a->'paused'<>'null'::jsonb and jsonb_typeof(a->'paused')<>'boolean' then return false; end if;
 if a->'speed' is not null and a->'speed'<>'null'::jsonb then
  if jsonb_typeof(a->'speed')<>'number' then return false; end if;
  n:=(a->>'speed')::numeric;
  if n<0.001 or n>1024 then return false; end if;
 end if;
 if a->>'phase'<>'match' and (a->>'paused' is not null or a->>'speed' is not null) then return false; end if;
 foreach key in array array['elapsed','width','height'] loop$addition$);
 execute definition;
 if (select md5(replace(prosrc,E'\r','')) from pg_proc where oid='paw_private.valid_game_activity(jsonb)'::regprocedure) is distinct from '220fd9aadd8dffa754d1067161050b78' then
  raise exception 'Timing validator does not match tested migration';
 end if;
 if has_function_privilege('anon','paw_private.valid_game_activity(jsonb)','execute') or has_function_privilege('authenticated','paw_private.valid_game_activity(jsonb)','execute') then
  raise exception 'Unexpected direct validator access';
 end if;
end; $deploy$;
commit;
