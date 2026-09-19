-- Keep presence, copying and offers on the same bounded configuration contract.
-- Session, friendship, moderation and rate-limit checks remain unchanged.
create function paw_private.valid_social_configuration(code text) returns boolean
language plpgsql immutable set search_path='' as $$
declare parts text[];
begin
 if code is null or octet_length(code)>128 or code ~ '[[:cntrl:]]'
 or code !~ '^PAW-(STABLE|BETA)-((VANILLA|IMMORTALS)(-RU[01])?(-PP1)?(-CL1)?(-OOS1)?(-DATA)?|IW[01]-SP[124]-RM[01]-SG[01]-LM[01]-RU[01]-CL[01]-OOS[01](-PS[01])?(-PP0)?(-DATA)?)(-TX(DE|FR|CS|UK))?(-VO(EN|RU|DE|FR))?$'
 then return false; end if;
 parts:=string_to_array(code,'-');
 if parts[3] in ('VANILLA','IMMORTALS') then
  if 'DATA'=any(parts) and not ('PP1'=any(parts) or parts[3]='IMMORTALS') then return false; end if;
  if ('CL1'=any(parts) or 'OOS1'=any(parts)) and
   (parts[2]<>'BETA' or not ('PP1'=any(parts)) or 'DATA'=any(parts)) then return false; end if;
 else
  if (parts[7]='LM1')=('PP0'=any(parts)) then return false; end if;
  if 'DATA'=any(parts) and (parts[3]='IW1' or parts[9]='CL1' or parts[10]='OOS1') then return false; end if;
 end if;
 return true;
end; $$;
revoke all on function paw_private.valid_social_configuration(text) from public,anon,authenticated;

alter table paw_private.social_presence drop constraint social_presence_configuration_check;
alter table paw_private.social_presence add constraint social_presence_configuration_check
 check(configuration is null or paw_private.valid_social_configuration(configuration));

-- Change only the known validation/projection fragments of existing functions.
-- Abort rather than overwrite a function that has diverged from this baseline.
do $migration$
declare source text; updated text; signature text;
 old_validation constant text := $old$octet_length(configuration)>128 or configuration !~ '^PAW-(STABLE|BETA)-((VANILLA|IMMORTALS)(-RU[01])?(-PP1(-DATA)?)?|IW[01]-SP[124]-RM[01]-SG[01]-LM1-RU[01]-CL[01]-OOS[01](-PS[01])?|IW[01]-SP[124]-RM[01]-SG[01]-LM0-RU[01]-CL[01]-OOS[01](-PS[01])?-PP0|IW0-SP[124]-RM[01]-SG[01]-LM1-RU[01]-CL0-OOS0(-PS[01])?-DATA|IW0-SP[124]-RM[01]-SG[01]-LM0-RU[01]-CL0-OOS0(-PS[01])?-PP0-DATA)$'$old$;
 old_flags constant text := $old$'russian','RU1'=any(parts),'colors',false,'desync',false$old$;
begin
 foreach signature in array array['paw_private.presence_without_activity(boolean,text,jsonb,text)',
  'public.paw_offer_create(uuid,uuid,text,text,text,bigint,text)'] loop
  source:=pg_get_functiondef(signature::regprocedure);
  if length(source)-length(replace(source,old_validation,''))<>length(old_validation)
  then raise exception 'Unexpected configuration validation in %',signature; end if;
  updated:=replace(source,old_validation,'not paw_private.valid_social_configuration(configuration)');
  if signature like 'paw_private.presence_%' then
   if length(updated)-length(replace(updated,old_flags,''))<>length(old_flags)
   then raise exception 'Unexpected component projection'; end if;
   updated:=replace(updated,old_flags,$new$'russian','RU1'=any(parts),'colors','CL1'=any(parts),'desync','OOS1'=any(parts)$new$);
  else
   updated:=replace(updated,'(?=(-PP1)?(-DATA)?$)','(?=(-PP1)?(-CL1)?(-OOS1)?(-DATA)?$)');
  end if;
  execute updated;
 end loop;
end;
$migration$;
