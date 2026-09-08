create or replace function public.paw_offer_action_before_cancel(offer_id uuid,action text,attempt uuid) returns jsonb
language plpgsql security definer set search_path='' as $$
declare actor uuid:=paw_private.social_actor(); o paw_private.social_offers;
begin
 if actor is null then return jsonb_build_object('status','session_expired');end if;
 select * into o from paw_private.social_offers where id=offer_id;
 if not found or actor<>o.recipient_id then return jsonb_build_object('status','offer_unavailable');end if;
 perform paw_private.social_lock(o.sender_id,o.recipient_id);
 select * into o from paw_private.social_offers where id=offer_id for update;
 if paw_private.social_actor() is null or not paw_private.social_allowed(o.sender_id,o.recipient_id) then return jsonb_build_object('status','friend_required');end if;
 if action is null or action not in('begin','decline','touch','complete','fail') then return jsonb_build_object('status','invalid_offer');end if;
 if action<>'decline' and (attempt is null or attempt='00000000-0000-0000-0000-000000000000'::uuid) then return jsonb_build_object('status','invalid_offer');end if;
 if o.state='applying' and o.apply_until<=clock_timestamp() then
  update paw_private.social_offers set state='failed' where id=o.id returning * into o;
 end if;
 if o.state='pending' and o.expires_at<=clock_timestamp() then return jsonb_build_object('status','offer_expired','offer',paw_private.offer_view(o));end if;
 if action='decline' and o.state='pending' then
  update paw_private.social_offers set state='declined' where id=o.id returning * into o;
 elsif action='begin' and o.state='pending' then
  update paw_private.social_offers set state='applying',attempt=paw_offer_action_before_cancel.attempt,started_at=clock_timestamp(),apply_until=clock_timestamp()+interval '2 minutes' where id=o.id returning * into o;
 elsif action='touch' and o.state='applying' and o.attempt=attempt then
  update paw_private.social_offers set apply_until=least(clock_timestamp()+interval '2 minutes',started_at+interval '30 minutes') where id=o.id returning * into o;
 elsif action in('complete','fail') and o.state='applying' and o.attempt=attempt then
  update paw_private.social_offers set state=case when action='complete' then 'accepted' else 'failed' end,apply_until=case when action='fail' then null else apply_until end where id=o.id returning * into o;
 elsif action='complete' and o.state='failed' and o.attempt=attempt and o.apply_until is not null then
  -- A durable receipt can acknowledge a completed local install after reconnecting.
  -- Explicit failures clear apply_until and cannot be promoted to success.
  update paw_private.social_offers set state='accepted' where id=o.id returning * into o;
 elsif not (action='begin' and o.state='applying' and o.attempt=attempt
  or action='complete' and o.state='accepted' and o.attempt=attempt
  or action='fail' and o.state='failed' and o.attempt=attempt
  or action='decline' and o.state='declined') then return jsonb_build_object('status','offer_unavailable','offer',paw_private.offer_view(o));end if;
 return jsonb_build_object('status','ok','offer',paw_private.offer_view(o));
end;$$;
revoke all on function public.paw_offer_action_before_cancel(uuid,text,uuid) from public,anon,authenticated;
