import { PGlite } from '@electric-sql/pglite';
import fs from 'node:fs/promises';
const db=new PGlite(); let checks=0;
const check=(ok,label)=>{if(!ok)throw Error(label);checks++;};
await db.exec(`
create role authenticated; create role anon;
create schema auth; create schema paw_private;
grant usage on schema public,auth to authenticated;
create function auth.uid() returns uuid language sql stable as $$select nullif(current_setting('test.actor',true),'')::uuid$$;
create table auth.users(id uuid primary key,email text);
create table public.paw_profiles(id uuid primary key,nickname text,display_name text,created_at timestamptz default now(),
 admin_level smallint not null default 0 check(admin_level between 0 and 2), protected_admin boolean default false,
 banned_at timestamptz,ban_until timestamptz,ban_reason text,deleted_at timestamptz,purge_started_at timestamptz,
 deletion_pending boolean default false,avatar_changed_at timestamptz);
alter table public.paw_profiles enable row level security;
create policy own_profile on public.paw_profiles for select to authenticated using(id=auth.uid());
grant select(id,nickname,admin_level) on public.paw_profiles to authenticated;
create table public.paw_blocks(owner_id uuid,target_id uuid);
create table paw_private.player_identities(id uuid,deleted_at timestamptz);
create table paw_private.account_actions(player_id uuid,lease_until timestamptz);
create table paw_private.moderation_audit(actor_id uuid,target_id uuid,action text,details jsonb);
create table paw_private.email_bans(id uuid,email_key text,created_at timestamptz,until_at timestamptz,reason text,actor_id uuid,revoked_at timestamptz,revoked_by uuid);
create table paw_private.social_presence(player_id uuid);
create table paw_private.social_offers(sender_id uuid,recipient_id uuid,state text);
create function paw_private.player_banned(player uuid) returns boolean language sql stable security definer set search_path='' as $$
select exists(select 1 from public.paw_profiles where id=player and banned_at is not null and (ban_until is null or ban_until>now()))$$;
create function paw_private.player_live(player uuid) returns boolean language sql stable security definer set search_path='' as $$
select exists(select 1 from public.paw_profiles where id=player and not deletion_pending and not paw_private.player_banned(player))$$;
create function paw_private.admin_level(player uuid) returns smallint language sql stable security definer set search_path='' as $$
select coalesce((select admin_level from public.paw_profiles where id=player and paw_private.player_live(player)),0)::smallint$$;
-- Auth/session transport is represented by a local actor fixture; no hosted account is contacted.
create function paw_private.social_actor() returns uuid language sql stable security definer set search_path='' as $$
select auth.uid() where paw_private.player_live(auth.uid())$$;
create function paw_private.social_lock(a uuid,b uuid) returns void language plpgsql security definer set search_path='' as $$
begin perform 1 from public.paw_profiles where id in(a,b) order by id for update; end$$;
create function paw_private.friend_presence(a uuid,b uuid) returns jsonb language sql stable security definer set search_path='' as $$select '{}'::jsonb$$;
`);
const migration=new URL('../migrations/20260910001000_paws_team.sql',import.meta.url);
await db.exec(await fs.readFile(migration,'utf8'));
const senior='10000000-0000-4000-8000-000000000001',admin='10000000-0000-4000-8000-000000000002',user='10000000-0000-4000-8000-000000000003',other='10000000-0000-4000-8000-000000000004';
for(const [id,name,level]of [[senior,'Senior',2],[admin,'Admin',1],[user,'User',0],[other,'Other',0]]){
 await db.query('insert into public.paw_profiles(id,nickname,display_name,admin_level) values($1,$2,$2,$3)',[id,name,level]);
 await db.query('insert into auth.users values($1,$2)',[id,name+'@example.invalid']);
 await db.query('insert into paw_private.player_identities values($1,null)',[id]);
}
async function actor(id){await db.exec('reset role');await db.query("select set_config('test.actor',$1,false)",[id]);await db.exec('set role authenticated');}
async function role(target,level){return (await db.query("select public.paw_admin_action('role',$1,level:=$2) result",[target,level])).rows[0].result.status;}
async function stored(id){await db.exec('reset role');return(await db.query('select * from public.paw_profiles where id=$1',[id])).rows[0];}
await actor(user); check(await role(other,-1)==='admin_required','User granted Team');
try{await db.query('update public.paw_profiles set paws_team=true where id=$1',[user]);throw Error('Direct role write succeeded');}catch(e){check(e.code==='42501','Direct write lacks privilege guard');}
await actor(admin);check(await role(user,-1)==='higher_role_required','Regular admin granted Team');
await actor(senior);check(await role(user,-1)==='ok','Senior Team grant failed');
let p=await stored(user);check(p.paws_team&&p.admin_level===0,'Team gained moderation');
await actor(user);check(await role(other,2)==='admin_required','Team elevated peer');
check((await db.query("select public.paw_admin_list('users') result")).rows[0].result.status==='admin_required','Team entered admin list');
check((await db.query('select paws_team from public.paw_profiles where id=$1',[user])).rows[0].paws_team,'Own team role not readable');
check((await db.query('select paws_team from public.paw_profiles where id=$1',[other])).rows.length===0,'Role query bypassed RLS');
await db.exec('reset role');check((await db.query('select paw_private.player_summary($1,$2) result',[senior,user])).rows[0].result.paws_team,'Social role absent');
await actor(senior);check((await db.query("select public.paw_admin_list('users') result")).rows[0].result.items.find(x=>x.id===user).paws_team,'Admin role absent');
check(await role(user,0)==='ok','Team revoke failed');p=await stored(user);check(!p.paws_team&&p.admin_level===0,'Team revoke retained access');
await actor(senior);check(await role(user,-1)==='ok','Regrant failed');check(await role(user,1)==='ok','Team to admin failed');
p=await stored(user);check(!p.paws_team&&p.admin_level===1,'Role transition not atomic');
await actor(senior);check(await role(user,3)==='invalid_action','Invalid upper role accepted');check(await role(user,-2)==='invalid_action','Invalid lower role accepted');check(await role(senior,-1)==='self_moderation','Self demotion permitted');
await db.exec('reset role');await db.query('update public.paw_profiles set protected_admin=true where id=$1',[admin]);
await actor(senior);check(await role(admin,-1)==='protected_account','Protected account changed');
await db.exec('reset role');await db.query('update public.paw_profiles set banned_at=now() where id=$1',[other]);
await actor(senior);check(await role(other,-1)==='invalid_action','Banned account given access');
await db.exec('reset role');await db.query('update public.paw_profiles set banned_at=null,deletion_pending=true,deleted_at=now(),paws_team=true where id=$1',[other]);await db.query('update paw_private.player_identities set deleted_at=now() where id=$1',[other]);
await actor(senior);check(await role(other,-1)==='invalid_action','Deleted account given access');
await db.exec('reset role');check((await db.query('select paw_private.player_summary($1,$2) result',[senior,other])).rows[0].result.paws_team===false,'Deleted badge leaked');
check((await db.query("select count(*)::int n from paw_private.moderation_audit where action='role'")).rows[0].n===4,'Role audit lost accepted grants');
await db.close();console.log('TEAM SQL PASS '+checks+': actual migration, grants, revocation, atomic roles, direct-write denial, RLS, badges and audit; local actor transport fixture');
