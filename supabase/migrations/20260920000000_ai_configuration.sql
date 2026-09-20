-- Keep presence, copying and offers on the same bounded configuration contract.
-- Session, friendship, moderation and rate-limit checks remain unchanged.
create or replace function paw_private.valid_social_configuration(code text) returns boolean
language plpgsql immutable set search_path='' as $$
declare parts text[];
begin
 if code is null or octet_length(code)>128 or code ~ '[[:cntrl:]]'
 or code !~ '^PAW-(STABLE|BETA)-((VANILLA|IMMORTALS)(-RU[01])?(-PP1)?(-CL1)?(-OOS1)?(-DATA)?|IW[01]-SP[124]-RM[01]-SG[01]-LM[01]-RU[01]-CL[01]-OOS[01](-PS[01])?(-AI1)?(-PP0)?(-DATA)?)(-TX(DE|FR|CS|UK))?(-VO(EN|RU|DE|FR))?$'
 then return false; end if;
 parts:=string_to_array(code,'-');
 if parts[3] in ('VANILLA','IMMORTALS') then
  if 'DATA'=any(parts) and not ('PP1'=any(parts) or parts[3]='IMMORTALS') then return false; end if;
  if ('CL1'=any(parts) or 'OOS1'=any(parts)) and
   (parts[2]<>'BETA' or not ('PP1'=any(parts)) or 'DATA'=any(parts)) then return false; end if;
 else
  if 'AI1'=any(parts) and (parts[2]<>'BETA' or 'PP0'=any(parts) or 'DATA'=any(parts)) then return false; end if;
  if (parts[7]='LM1')=('PP0'=any(parts)) then return false; end if;
  if 'DATA'=any(parts) and (parts[3]='IW1' or parts[9]='CL1' or parts[10]='OOS1') then return false; end if;
 end if;
 return true;
end; $$;
revoke all on function paw_private.valid_social_configuration(text) from public,anon,authenticated;

-- Preserve session/friendship/rate checks; extend only the finite gameplay contract.
do $migration$
declare source text; updated text;
begin
 source:=pg_get_functiondef('paw_private.presence_without_activity(boolean,text,jsonb,text)'::regprocedure);
 if md5(replace((select prosrc from pg_proc where oid='paw_private.presence_without_activity(boolean,text,jsonb,text)'::regprocedure),E'\r',''))<>'5026a243237436fb55d648c914bdb005'
 then raise exception 'Unexpected presence implementation'; end if;
 updated:=replace(source,$old$'powers_shards','large_maps'$old$,$new$'powers_shards','large_maps','improved_ai'$new$);
 if updated=source then raise exception 'Missing component validation'; end if;
 source:=updated;
 updated:=replace(source,$old$'powers_shards',not ('PS0'=any(parts))$old$,$new$'powers_shards',not ('PS0'=any(parts)),'improved_ai','AI1'=any(parts)$new$);
 if updated=source then raise exception 'Missing component projection'; end if;
 execute updated;
end; $migration$;
