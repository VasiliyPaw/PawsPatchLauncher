-- Match native UTF-16 length, Unicode whitespace and control-character rules.
create function paw_private.social_body_valid(body text) returns boolean
language sql immutable set search_path='' as $$
 select body is not null
 and length(body) between 1 and 2000
 and length(body)+length(regexp_replace(body,U&'[^\+010000-\+10FFFF]','','g'))<=2000
 and length(btrim(body,U&'\0020\0009\000A\000B\000C\000D\0085\00A0\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200A\2028\2029\202F\205F\3000'))>0
 and regexp_replace(body,E'[\t\r\n]','','g') !~ '[[:cntrl:]]';
$$;
revoke all on function paw_private.social_body_valid(text) from public,anon,authenticated;
alter table public.paw_messages add constraint paw_messages_native_text
 check(paw_private.social_body_valid(body));

create or replace function public.paw_send_message(target uuid, message_id uuid, body text, kind text default 'text') returns jsonb
language plpgsql security definer set search_path = '' as $$
declare actor uuid:=paw_private.social_actor(); prior public.paw_messages;
begin
 if actor is null then return jsonb_build_object('status','session_expired'); end if;
 if not paw_private.social_body_valid(body) or target is null or target=actor or message_id is null or body is null or length(body) not between 1 and 2000
  or length(btrim(body,E' \t\r\n'))=0 or kind is null or kind not in('text','config')
 then return jsonb_build_object('status','invalid_message'); end if;
 perform paw_private.social_lock(actor,target);
 if paw_private.social_actor() is null or not paw_private.social_allowed(actor,target)
 then return jsonb_build_object('status','friend_required'); end if;
 select * into prior from public.paw_messages m where m.sender_id=actor and m.message_id=paw_send_message.message_id;
 if prior.message_id is not null then
  if prior.recipient_id<>target or prior.body<>body or prior.kind<>kind then return jsonb_build_object('status','message_conflict'); end if;
  return jsonb_build_object('status','ok','message',to_jsonb(prior));
 end if;
 if (select count(*) from public.paw_messages where sender_id=actor and created_at>now()-interval '1 minute')>=20
 then return jsonb_build_object('status','rate_limit'); end if;
 if (select count(*) from public.paw_messages where sender_id=actor)>=10000
 then return jsonb_build_object('status','message_limit'); end if;
 insert into public.paw_messages(sender_id,message_id,recipient_id,body,kind)
 values(actor,message_id,target,body,kind) returning * into prior;
 return jsonb_build_object('status','ok','message',to_jsonb(prior));
end;
$$;
