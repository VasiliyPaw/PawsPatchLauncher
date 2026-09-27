-- Promote only the Vanilla/Immortals option contract to the stable channel.
-- Existing RPCs, auth, friendships, privileges and Arcane AI restrictions remain intact.
do $migration$
declare source text; updated text;
begin
 if (select md5(replace(prosrc,E'\r','')) from pg_proc where oid='paw_private.valid_social_configuration(text)'::regprocedure) is distinct from '8ed7bc2f5e9d4183aaadc8ac7aee9949'
 then raise exception 'Unexpected social configuration validator'; end if;
 source:=pg_get_functiondef('paw_private.valid_social_configuration(text)'::regprocedure);
 updated:=replace(source,$old$(parts[2]<>'BETA' or not ('PP1'=any(parts)) or 'DATA'=any(parts))$old$,$new$(not ('PP1'=any(parts)) or 'DATA'=any(parts))$new$);
 if updated=source then raise exception 'Missing pure beta restriction'; end if;
 execute updated;
 if (select md5(replace(prosrc,E'\r','')) from pg_proc where oid='paw_private.valid_social_configuration(text)'::regprocedure) is distinct from 'c7e552eb159ab343ae719f92a28286b8'
 then raise exception 'Unexpected updated validator'; end if;
end; $migration$;
