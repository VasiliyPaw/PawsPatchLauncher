-- Add optional native race/faction IDs to current game activity.
-- Legacy clients may omit both fields. Identity matching and social visibility
-- remain unchanged; faction choices never grant profile or avatar access.

create or replace function paw_private.valid_game_activity(a jsonb) returns boolean
language plpgsql immutable set search_path='' as $$
declare p jsonb; n numeric; key text; people jsonb;
begin
 if a is null or a='null'::jsonb then return true; end if;
 if jsonb_typeof(a)<>'object' or octet_length(a::text)>16384
 or exists(select 1 from jsonb_object_keys(a) k where k not in ('phase','multiplayer','elapsed','width','height','room','self','players'))
 or jsonb_typeof(a->'phase') is distinct from 'string' or a->>'phase' not in ('menu','lobby','match','loading','editor')
 or jsonb_typeof(a->'multiplayer') is distinct from 'boolean' then return false; end if;
 foreach key in array array['elapsed','width','height'] loop
  if a->key is not null and a->key<>'null'::jsonb then
   if jsonb_typeof(a->key)<>'number' then return false; end if;
   n:=(a->>key)::numeric;
   if n<>trunc(n) or (key='elapsed' and (n<0 or n>604800)) or (key<>'elapsed' and (n<16 or n>8192)) then return false; end if;
  end if;
 end loop;
 if ((a->>'width') is null)<>((a->>'height') is null) then return false; end if;
 if a->>'room' is not null and (jsonb_typeof(a->'room')<>'string' or a->>'room' !~ '^[A-Fa-f0-9]{64}$') then return false; end if;
 if a->>'self' is not null and (jsonb_typeof(a->'self')<>'string' or a->>'self' !~ '^[A-Za-z0-9_-]{1,32}$') then return false; end if;
 people:=coalesce(nullif(a->'players','null'::jsonb),'[]'::jsonb);
 if jsonb_typeof(people)<>'array' or jsonb_array_length(people)>64 then return false; end if;
 if (select count(distinct value->>'key') from jsonb_array_elements(people))<>jsonb_array_length(people) then return false; end if;
 for p in select value from jsonb_array_elements(people) loop
  if jsonb_typeof(p)<>'object' or exists(select 1 from jsonb_object_keys(p) k where k not in ('key','name','bot','profile','team','color','race','subrace'))
  or jsonb_typeof(p->'key') is distinct from 'string' or p->>'key' !~ '^[A-Za-z0-9_-]{1,32}$'
  or jsonb_typeof(p->'name') is distinct from 'string' or length(btrim(p->>'name')) not between 1 and 80 or p->>'name' ~ '[[:cntrl:]]'
  or jsonb_typeof(p->'bot') is distinct from 'boolean' or (p->'profile' is not null and p->'profile'<>'null'::jsonb) then return false; end if;
  -- Native identifiers are bounded labels, never paths, markup or identity claims.
  -- Missing values stay unknown; the native lobby choice uses the exact ID 'random'.
  foreach key in array array['race','subrace'] loop
   if p->>key is not null and (jsonb_typeof(p->key)<>'string' or p->>key !~ '^[A-Za-z0-9_-]{1,80}$') then return false; end if;
  end loop;
  if p->>'team' is not null then
   if jsonb_typeof(p->'team')<>'number' then return false; end if;
   n:=(p->>'team')::numeric;
   if n<>trunc(n) or n<1 or n>64 then return false; end if;
  end if;
  if p->>'color' is not null and (jsonb_typeof(p->'color')<>'string' or p->>'color' !~ '^#[A-Fa-f0-9]{6}$') then return false; end if;
 end loop;
 if a->>'self' is not null and not exists(select 1 from jsonb_array_elements(people) entry where entry->>'key'=a->>'self' and entry->>'bot'='false') then return false; end if;
 if a->>'phase' not in ('lobby','match') and (jsonb_array_length(people)>0 or a->>'room' is not null or a->>'self' is not null) then return false; end if;
 if a->>'multiplayer'='false' and a->>'room' is not null then return false; end if;
 return true;
exception when others then return false;
end; $$;
revoke all on function paw_private.valid_game_activity(jsonb) from public,anon,authenticated;

