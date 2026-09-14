-- Recheck the displayed username after acquiring the profile lock as well.
-- A concurrent rename while waiting for that lock must not redirect the request.
do $$ declare definition text;begin
 definition:=pg_get_functiondef('public.paw_friend_action(text,uuid,text)'::regprocedure);
 if strpos(definition,'target is distinct from peer')=0 then raise exception 'Profile request identity guard missing';end if;
 definition:=replace(definition,'perform paw_private.social_lock(actor,peer);',
  'perform paw_private.social_lock(actor,peer);
 if action=''request'' and target is not null and not exists(select 1 from public.paw_profiles where id=target and nickname_key=paw_private.nickname_key(candidate) collate "C")
 then return jsonb_build_object(''status'',''player_unavailable'');end if;');
 execute definition;
end; $$;
