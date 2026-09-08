-- Do not send redundant configurations; preserve friendship, single-launcher and retry guards.
create or replace function public.paw_offer_create(target uuid,offer_id uuid,offer_kind text,configuration text,file_name text,file_size bigint,sha256 text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare actor uuid:=paw_private.social_actor(); o paw_private.social_offers;
begin
 if actor is null then return jsonb_build_object('status','session_expired');end if;
 if target is null or offer_id is null or offer_id='00000000-0000-0000-0000-000000000000'::uuid or target=actor
 or offer_kind is null or offer_kind not in('config','save') then return jsonb_build_object('status','invalid_offer');end if;
 perform paw_private.social_lock(actor,target);
 if paw_private.social_actor() is null or not paw_private.social_allowed(actor,target) then return jsonb_build_object('status','friend_required');end if;
 if offer_kind='config' then
  if configuration is null or octet_length(configuration)>128 or configuration !~ '^PAW-(STABLE|BETA)-IW[01]-SP[124]-RM[01]-SG[01]-LM1-RU[01]-CL[01]-OOS[01](-PS[01])?$'
  or file_name is not null or file_size is not null or sha256 is not null then return jsonb_build_object('status','invalid_offer');end if;
 else
  if configuration is not null or file_name is null or length(file_name) not between 5 and 128
  or lower(right(file_name,4))<>'.rsg' or file_name ~ '[[:cntrl:]/\\:*?"<>|]' or left(file_name,1)='.'
  or file_size is null or file_size not between 16 and 20971520 or sha256 is null or sha256 !~ '^[0-9a-fA-F]{64}$'
  then return jsonb_build_object('status','invalid_save');end if;
 end if;
 select * into o from paw_private.social_offers where id=offer_id;
 if found then
  if o.sender_id<>actor or o.recipient_id<>target or o.kind<>offer_kind or o.configuration is distinct from configuration
  or o.file_name is distinct from file_name or o.file_size is distinct from file_size or lower(o.sha256) is distinct from lower(sha256)
  then return jsonb_build_object('status','message_conflict');end if;
  return jsonb_build_object('status','ok','offer',paw_private.offer_view(o));
 end if;
 -- Compare under the existing participant/session locks, after idempotent retries.
 -- PS1 is the explicit spelling of the legacy default (an omitted PS suffix).
 if offer_kind='config' and exists(select 1 from paw_private.social_presence p where p.player_id=target
 and regexp_replace(p.configuration,'-PS1$','')=regexp_replace(paw_offer_create.configuration,'-PS1$','')) then
  return jsonb_build_object('status','configuration_matches');
 end if;
 if (select count(*) from paw_private.social_offers where sender_id=actor and created_at>now()-interval '1 minute')>=5
 or (select count(*) from paw_private.social_offers where sender_id=actor and state in('uploading','pending','applying') and expires_at>now())>=10
 then return jsonb_build_object('status','rate_limit');end if;
 if (select count(*) from public.paw_messages where sender_id=actor)>=10000 then return jsonb_build_object('status','message_limit');end if;
 if offer_kind='save' and coalesce((select sum(s.file_size) from paw_private.social_offers s where s.sender_id=actor and s.kind='save' and not storage_cleaned),0)+file_size>52428800
 then return jsonb_build_object('status','storage_limit');end if;
 insert into paw_private.social_offers(id,sender_id,recipient_id,kind,configuration,file_name,file_size,sha256,state,storage_cleaned)
 values(offer_id,actor,target,offer_kind,configuration,file_name,file_size,lower(sha256),case when offer_kind='config' then 'pending' else 'uploading' end,offer_kind='config') returning * into o;
 if offer_kind='config' then
  insert into public.paw_messages(sender_id,message_id,recipient_id,kind,body)
  values(actor,offer_id,target,'config','Предложение конфигурации · Configuration offer');
 end if;
 return jsonb_build_object('status','ok','offer',paw_private.offer_view(o));
end;$$;
revoke all on function public.paw_offer_create(uuid,uuid,text,text,text,bigint,text) from public,anon,authenticated;
grant execute on function public.paw_offer_create(uuid,uuid,text,text,text,bigint,text) to authenticated;
