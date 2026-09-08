-- Narrow updates to existing guarded/idempotent RPCs. Fail closed if their source has drifted.
do $migration$
declare definition text; previous text; replacement text;
begin
 select pg_get_functiondef('public.paw_offer_create(uuid,uuid,text,text,text,bigint,text)'::regprocedure) into definition;
 previous := $old$if (select count(*) from paw_private.social_offers where sender_id=actor and created_at>now()-interval '1 minute')>=5$old$;
 replacement := $new$if (select count(*) from paw_private.social_offers s where s.sender_id=actor and s.kind=offer_kind and s.created_at>now()-interval '1 minute') >= (case when offer_kind='save' then 10 else 5 end)$new$;
 if strpos(definition,previous)=0 then raise exception 'paw_offer_create changed: review the rate-limit patch before applying'; end if;
 execute replace(definition,previous,replacement);

 select pg_get_functiondef('paw_private.change_nickname_impl(text)'::regprocedure) into definition;
 previous := $old$interval '5 minutes'$old$;
 if (length(definition)-length(replace(definition,previous,'')))/length(previous)<>2
 then raise exception 'change_nickname_impl changed: review the cooldown patch before applying'; end if;
 execute replace(definition,previous,$new$interval '1 day'$new$);
end;
$migration$;

-- Retain: active-launcher/friend guards, participant locks, duplicate IDs, save size/storage
-- quotas, ten concurrent offers, message quota, username normalization and existing grants.
