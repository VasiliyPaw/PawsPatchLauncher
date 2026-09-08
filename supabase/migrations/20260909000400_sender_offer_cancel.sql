alter table paw_private.social_offers drop constraint social_offers_state_check;
alter table paw_private.social_offers add constraint social_offers_state_check check(state in('uploading','pending','applying','accepted','declined','failed','cancelled'));
-- Keep the existing recipient/attempt machinery; add only sender cancellation before claiming.
alter function public.paw_offer_action(uuid,text,uuid) rename to paw_offer_action_before_cancel;
revoke all on function public.paw_offer_action_before_cancel(uuid,text,uuid) from public,anon,authenticated;
create function public.paw_offer_action(offer_id uuid,action text,attempt uuid) returns jsonb
language plpgsql security definer set search_path='' as $$
declare actor uuid:=paw_private.social_actor(); o paw_private.social_offers;
begin
 if action is distinct from 'cancel' then return public.paw_offer_action_before_cancel(offer_id,action,attempt);end if;
 if actor is null then return jsonb_build_object('status','session_expired');end if;
 select * into o from paw_private.social_offers where id=offer_id;
 if not found or o.sender_id<>actor then return jsonb_build_object('status','offer_unavailable');end if;
 perform paw_private.social_lock(o.sender_id,o.recipient_id);
 select * into o from paw_private.social_offers where id=offer_id for update;
 if paw_private.social_actor() is null or not paw_private.social_allowed(o.sender_id,o.recipient_id) then return jsonb_build_object('status','friend_required');end if;
 if o.state='cancelled' then return jsonb_build_object('status','ok','offer',paw_private.offer_view(o));end if;
 if o.state not in('uploading','pending') then return jsonb_build_object('status','offer_unavailable');end if;
 if o.expires_at<=clock_timestamp() then return jsonb_build_object('status','offer_expired');end if;
 update paw_private.social_offers set state='cancelled' where id=o.id returning * into o;
 return jsonb_build_object('status','ok','offer',paw_private.offer_view(o));
end;$$;
revoke all on function public.paw_offer_action(uuid,text,uuid) from public,anon,authenticated;
grant execute on function public.paw_offer_action(uuid,text,uuid) to authenticated;

create or replace function public.paw_transfer_cleanup_candidates() returns jsonb
language sql stable security definer set search_path='' as $$
 select coalesce(jsonb_agg(path),'[]'::jsonb) from (
 select sender_id::text||'/'||id::text||'.rsg' path from paw_private.social_offers
 where kind='save' and not storage_cleaned and (state in('accepted','declined','failed','cancelled')
 or state in('uploading','pending') and expires_at<=now() or state='applying' and apply_until<=now())
 union
 select s.name from storage.objects s where s.bucket_id='paw-social-saves' and s.created_at<now()-interval '5 minutes'
 and not exists(select 1 from paw_private.social_offers o where o.sender_id::text||'/'||o.id::text||'.rsg'=s.name)
 limit 20) q;
$$;
create or replace function public.paw_transfer_cleaned(paths text[]) returns void
language sql security definer set search_path='' as $$
 update paw_private.social_offers set storage_cleaned=true where sender_id::text||'/'||id::text||'.rsg'=any(paths)
 and (state in('accepted','declined','failed','cancelled') or state in('uploading','pending') and expires_at<=now() or state='applying' and apply_until<=now());
$$;
