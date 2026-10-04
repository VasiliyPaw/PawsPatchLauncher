-- Promote the existing Arcane AI option to stable. Pure beta rules and RPC
-- permissions are intentionally unchanged.
do $migration$
declare source text; updated text;
 old_gate constant text := $old$if 'AI1'=any(parts) and (parts[2]<>'BETA' or 'PP0'=any(parts) or 'DATA'=any(parts)) then return false; end if;$old$;
 new_gate constant text := $new$if 'AI1'=any(parts) and ('PP0'=any(parts) or 'DATA'=any(parts)) then return false; end if;$new$;
begin
 source:=pg_get_functiondef('paw_private.valid_social_configuration(text)'::regprocedure);
 if (length(source)-length(replace(source,old_gate,'')))<>length(old_gate)
 then raise exception 'Unexpected Arcane AI configuration gate'; end if;
 updated:=replace(source,old_gate,new_gate);
 execute updated;
 if not paw_private.valid_social_configuration('PAW-STABLE-IW1-SP4-RM1-SG1-LM1-RU0-CL1-OOS1-AI1')
 or paw_private.valid_social_configuration('PAW-STABLE-VANILLA-PP1-PB1-AI1-LR1-IW1-SP4-RM1')
 or paw_private.valid_social_configuration('PAW-STABLE-IW1-SP4-RM1-SG1-LM0-RU0-CL1-OOS1-AI1-PP0')
 or paw_private.valid_social_configuration('PAW-STABLE-IW0-SP1-RM0-SG0-LM1-RU0-CL0-OOS0-AI1-DATA')
 then raise exception 'Invalid stable AI configuration contract'; end if;
end; $migration$;
