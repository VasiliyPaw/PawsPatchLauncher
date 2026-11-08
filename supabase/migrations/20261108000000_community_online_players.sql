-- Public online directory: the same live sessions counted by paw_community_online.
-- Only public identity fields leave the server, ten players per request.
begin;
create function public.paw_community_players(page_index integer default 0) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare result jsonb;
begin
 if page_index is null or page_index<0 then return jsonb_build_object('status','invalid_page');end if;
 with active as materialized (
  select p.id,p.nickname,p.display_name,p.avatar_changed_at
  from paw_private.social_presence s join public.paw_profiles p on p.id=s.player_id
  where s.seen_at>now()-interval '40 seconds' and not p.deletion_pending
   and public.paw_account_session_active(s.player_id,s.session_id,s.launcher_id)
 ), totals as (select count(*)::integer n from active),
 paging as (select n,least(page_index,greatest(0,(n-1)/10)) page from totals),
 players as (
  select a.* from active a order by lower(a.nickname) collate "C",a.id
  limit 10 offset (select page::bigint*10 from paging)
 )
 select jsonb_build_object('status','ok','total',paging.n,'page',paging.page,
  'players',coalesce((select jsonb_agg(jsonb_build_object('id',p.id,'nickname',p.nickname,
   'display_name',p.display_name,'avatar_revision',p.avatar_changed_at)
   order by lower(p.nickname) collate "C",p.id) from players p),'[]'::jsonb)) into result from paging;
 return result;
end;$$;
revoke all on function public.paw_community_players(integer) from public;
grant execute on function public.paw_community_players(integer) to anon,authenticated;

-- Directory avatars also work for players who have never posted in chat.
create or replace function public.paw_community_avatar_allowed(object_name text) returns boolean
language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.paw_profiles p
  where $1=p.id::text||'/avatar.jpg' and not p.deletion_pending
  and (exists(select 1 from paw_private.community_messages m where m.sender_id=p.id and m.removed_at is null)
   or exists(select 1 from paw_private.social_presence s where s.player_id=p.id
    and s.seen_at>now()-interval '40 seconds'
    and public.paw_account_session_active(s.player_id,s.session_id,s.launcher_id))));
$$;
notify pgrst, 'reload schema';
commit;
