-- Extend the finite Pure beta configuration contract, without changing RPC
-- access, sessions, friendship checks or existing release configurations.
do $migration$
declare source text; updated text; actual_projection text;
 old_projection constant text := $old$components:=jsonb_build_object('core','PP1'=any(parts),'hostility',false,'roaming',false,'additional_roaming',false,
    'siege',false,'large_maps',false,'russian','RU1'=any(parts),'colors','CL1'=any(parts),'desync','OOS1'=any(parts),'powers_shards',false);$old$;
 new_projection constant text := $new$components:=jsonb_build_object('core','PP1'=any(parts),'hostility','IW1'=any(parts),
    'roaming','SP2'=any(parts) or 'SP4'=any(parts),'additional_roaming','RM1'=any(parts),
    'siege',false,'large_maps','PB1'=any(parts),'russian','RU1'=any(parts),'colors','CL1'=any(parts),'desync','OOS1'=any(parts),'powers_shards',false);
   if 'PB1'=any(parts) then components:=components||jsonb_build_object('improved_ai','AI1'=any(parts),'lair_recovery','LR1'=any(parts)); end if;$new$;
begin
 if (select md5(replace(prosrc,E'\r','')) from pg_proc where oid='paw_private.valid_social_configuration(text)'::regprocedure) is distinct from 'c7e552eb159ab343ae719f92a28286b8'
 then raise exception 'Unexpected social configuration validator'; end if;
 source:=pg_get_functiondef('paw_private.valid_social_configuration(text)'::regprocedure);
 updated:=replace(source,'(-OOS1)?(-DATA)?|IW','(-OOS1)?(-PB1-AI[01]-LR[01]-IW[01]-SP[124]-RM[01])?(-DATA)?|IW');
 if updated=source then raise exception 'Missing Pure grammar'; end if;
 source:=updated;
 updated:=replace(source,$old$if parts[3] in ('VANILLA','IMMORTALS') then$old$,$new$if parts[3] in ('VANILLA','IMMORTALS') then
  if 'PB1'=any(parts) and (parts[2]<>'BETA' or not ('PP1'=any(parts)) or 'DATA'=any(parts)) then return false; end if;$new$);
 if updated=source then raise exception 'Missing Pure option gate'; end if;
 execute updated;
 source:=replace(pg_get_functiondef('paw_private.presence_without_activity(boolean,text,jsonb,text)'::regprocedure),E'\r','');
 updated:=replace(source,$old$'large_maps','improved_ai'$old$,$new$'large_maps','improved_ai','lair_recovery'$new$);
 if updated=source then raise exception 'Missing component allowlist'; end if;
 source:=updated;
 actual_projection:=substring(source from $pattern$components:=jsonb_build_object\('core','PP1'=any\(parts\)[^;]+;$pattern$);
 if regexp_replace(actual_projection,'[[:space:]]','','g') is distinct from regexp_replace(old_projection,'[[:space:]]','','g')
 then raise exception 'Unexpected Pure component projection'; end if;
 updated:=replace(source,actual_projection,replace(new_projection,E'\r',''));
 if updated=source then raise exception 'Unexpected Pure component projection'; end if;
 execute updated;
 source:=pg_get_functiondef('public.paw_offer_create(uuid,uuid,text,text,text,bigint,text)'::regprocedure);
 updated:=replace(source,'(?=(-PP1)?(-CL1)?(-OOS1)?(-DATA)?$)',
  '(?=(-PP1)?(-CL1)?(-OOS1)?(-PB1-AI[01]-LR[01]-IW[01]-SP[124]-RM[01])?(-DATA)?$)');
 if updated=source then raise exception 'Missing Pure offer normalization'; end if;
 execute updated;
end; $migration$;
