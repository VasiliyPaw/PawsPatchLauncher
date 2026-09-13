import { PGlite } from '@electric-sql/pglite';
import fs from 'node:fs/promises';
import { randomUUID } from 'node:crypto';

// Execute production SQL functions in local PostgreSQL. Only Auth/session
// transport and unrelated social tables are represented by local fixtures.
const db = new PGlite(); let checks = 0;
const check = (ok, why) => { if (!ok) throw Error(why); checks++; };
const query = async (sql, params = []) => (await db.query(sql, params)).rows;
const value = async (sql, params = []) => (await query(sql, params))[0].result;
const read = name => fs.readFile(new URL('../migrations/' + name, import.meta.url), 'utf8');
function statement(source, start) {
 const at = source.indexOf(start); if (at < 0) throw Error('Missing production statement: ' + start);
 const end = source.indexOf('$$;', at); if (end < 0) throw Error('Missing function terminator');
 return source.slice(at, end + 3);
}
await db.exec(`
create role authenticated; create role anon; create role service_role;
create schema auth; create schema paw_private;
grant usage on schema public to authenticated, anon, service_role;
create function auth.uid() returns uuid language sql stable as $$select nullif(current_setting('test.actor',true),'')::uuid$$;
create table auth.users(id uuid primary key,email text unique,email_change text,encrypted_password text);
create table public.paw_profiles(id uuid primary key references auth.users on delete cascade,nickname text,display_name text,
 created_at timestamptz default now(),admin_level smallint default 0,protected_admin boolean default false,paws_team boolean default false,
 banned_at timestamptz,ban_until timestamptz,ban_reason text,deleted_at timestamptz,purge_started_at timestamptz,
 deletion_pending boolean default false,email_changed_at timestamptz,password_changed_at timestamptz);
create table paw_private.player_identities(id uuid primary key,deleted_at timestamptz);
create table paw_private.account_actions(player_id uuid primary key references public.paw_profiles on delete cascade,
 lease uuid,lease_until timestamptz,operation text,previous_changed_at timestamptz);
create table paw_private.archived_chats(owner_id uuid,peer_id uuid,primary key(owner_id,peer_id));
create table paw_private.official_chats(low_id uuid,high_id uuid);
create table public.paw_friendships(low_id uuid,high_id uuid,accepted boolean);
create table public.paw_blocks(owner_id uuid,target_id uuid);
create table paw_private.social_presence(player_id uuid);
create table paw_private.social_offers(sender_id uuid,recipient_id uuid,state text);
create table paw_private.moderation_audit(actor_id uuid,target_id uuid,action text,details jsonb);
create function public.paw_account_session_active(player uuid,session uuid,launcher uuid) returns boolean language sql as $$select player=auth.uid()$$;
create function paw_private.launcher_actor() returns uuid language sql stable as $$select auth.uid()$$;
create function paw_private.social_lock(a uuid,b uuid) returns void language plpgsql as $$begin perform 1 from public.paw_profiles where id in(a,b) order by id for update;end$$;
`);
const foundation = await read('20260909000900_moderation_foundation.sql');
const actions = await read('20260908020000_account_actions_avatars.sql');
const team = await read('20260910001000_paws_team.sql');
const emailTable = foundation.match(/create table paw_private\.email_bans\([\s\S]*?\);/)[0];
await db.exec(emailTable + '\n' + foundation.match(/create unique index paw_current_email_ban[^;]+;/)[0]);
for (const start of [
 'create or replace function paw_private.nickname_valid(',
 'create function paw_private.email_key(', 'create function paw_private.email_banned(',
 'create function paw_private.player_banned(', 'create function paw_private.player_live(',
 'create or replace function paw_private.social_actor(', 'create function paw_private.admin_level(',
 'create function paw_private.auth_moderation_guard(', 'create function public.paw_registration_check(',
 'create function public.paw_account_action_allowed(', 'create function paw_private.soft_delete(',
 'create or replace function public.paw_mark_account_deleting(', 'create function paw_private.protect_founder('
]) await db.exec(statement(foundation, start));
await db.exec(statement(actions, 'create function public.paw_begin_account_action('));
await db.exec(statement(actions, 'create function public.paw_finish_account_action('));
await db.exec(statement(foundation, 'create or replace function public.paw_begin_launcher_action('));
await db.exec(statement(team, 'create or replace function public.paw_admin_action('));
await db.exec(foundation.match(/create trigger paw_auth_moderation[\s\S]*?;/)[0]);
await db.exec(foundation.match(/create trigger paw_protect_founder[^;]+;/)[0]);
await db.exec(await read('20260912000000_banned_account_deletion.sql'));
async function seed(name, level = 0) {
 const id = randomUUID(), email = name + '@example.invalid';
 await query('insert into auth.users(id,email) values($1,$2)', [id,email]);
 await query('insert into public.paw_profiles(id,nickname,display_name,admin_level) values($1,$2,$2,$3)', [id,name,level]);
 await query('insert into paw_private.player_identities(id) values($1)', [id]);
 return {id,email};
}
const senior = await seed('Senior',2);
async function actor(id) { await query("select set_config('test.actor',$1,false)", [id]); }
async function moderate(action, id, until = null) {
 await actor(senior.id);
 return value("select public.paw_admin_action($1,$2,'Fixture ban',$3::timestamptz) result", [action,id,until]);
}
async function allowed(player) { return value("select public.paw_account_action_allowed($1,'delete') result",[player.id]); }
async function registration(email) { return value("select public.paw_registration_check($1,'NewPlayer') result",[email]); }
async function denyDirectSignup(email) {
 let denied=false;
 try { await query('insert into auth.users(id,email) values($1,$2)',[randomUUID(),email]); }
 catch(error) { denied=error.message.includes('email_banned'); }
 check(denied,'Direct Auth signup bypasses email ban');
}
for (const permanent of [false,true]) {
 const player = await seed(permanent?'Permanent':'Temporary');
 const until = permanent ? null : new Date(Date.now()+3600000).toISOString();
 check((await moderate('ban',player.id,until)).status==='ok','Production admin ban failed');
 check(await allowed(player)==='account_banned','Banned delete preflight allowed');
 check(await value('select paw_private.soft_delete($1,$1) result',[player.id])===false,'Private self-delete bypass');
 await actor(player.id);
 check((await value("select public.paw_begin_launcher_action($1,$2,$3,'delete') result",[player.id,randomUUID(),randomUUID()])).status==='account_banned','Banned deletion acquired a lease');
 const lease=randomUUID();
 await query("insert into paw_private.account_actions(player_id,lease,lease_until,operation) values($1,$2,now()+interval '1 minute','delete')",[player.id,lease]);
 check(await value('select public.paw_mark_account_deleting($1,$2) result',[player.id,lease])===false,'Previously acquired lease bypasses new ban');
 check(!(await value('select deletion_pending result from public.paw_profiles where id=$1',[player.id])),'Rejected deletion changed profile');
 await query('delete from paw_private.account_actions where player_id=$1',[player.id]);
 check((await moderate('delete',player.id)).status==='ok','Administrator cannot remove banned account');
 const record=(await query('select * from paw_private.email_bans where email_key=lower($1) and revoked_at is null',[player.email]))[0];
 check(record && (permanent ? record.until_at===null : new Date(record.until_at).toISOString()===until),'Ban term changed at deletion');
 await query('delete from auth.users where id=$1',[player.id]);
 check(!(await query('select id from public.paw_profiles where id=$1',[player.id])).length,'Auth purge did not remove profile fixture');
 check((await registration('  '+player.email.toUpperCase()+'  ')).status==='email_banned','Purged email can be registered through preflight');
 await denyDirectSignup(player.email.toUpperCase());
 if (permanent) {
  await query("update paw_private.email_bans set created_at=now()-interval '100 years' where id=$1",[record.id]);
  check((await registration(player.email)).status==='email_banned','Permanent ban expired with age');
  check((await moderate('unban',record.id)).status==='ok','Cannot unban deleted identity email');
 } else {
  await query("update paw_private.email_bans set created_at=now()-interval '2 hours',until_at=now()-interval '1 second' where id=$1",[record.id]);
 }
 check((await registration(player.email)).status==='ok','Expired/revoked ban still blocks registration');
 await query('insert into auth.users(id,email) values($1,$2)',[randomUUID(),player.email]);
 check(true,'Signup after expiry/revocation');
}
const normal=await seed('Normal');
await actor(normal.id);
check(await allowed(normal)==='ok','Unbanned account cannot delete');
let lease=await value("select public.paw_begin_launcher_action($1,$2,$3,'delete') result",[normal.id,randomUUID(),randomUUID()]);
check(lease.status==='ok','Normal lease rejected');
check((await moderate('ban',normal.id)).status==='account_busy','Ban/deletion lease race not serialized');
await query('update public.paw_profiles set banned_at=now() where id=$1',[normal.id]);
check(await value('select public.paw_mark_account_deleting($1,$2) result',[normal.id,lease.lease])===false,'Late ban ignored at commit');
await query("update public.paw_profiles set ban_until=now()-interval '1 second' where id=$1",[normal.id]);
check(await allowed(normal)==='ok','Expired profile ban blocks deletion');
check(await value('select public.paw_mark_account_deleting($1,$2) result',[normal.id,lease.lease])===true,'Deletion after ban expiry failed');
check(await value('select public.paw_mark_account_deleting($1,$2) result',[normal.id,lease.lease])===true,'Unbanned retry failed');
await query('update public.paw_profiles set protected_admin=true where id=$1',[senior.id]);
check(await allowed(senior)==='protected_account','Founder deletion protection lost');
check(await value('select paw_private.soft_delete($1,$2) result',[senior.id,normal.id])===false,'Admin can delete protected founder');
for(const role of ['anon','authenticated']) for(const signature of ['public.paw_account_action_allowed(uuid,text,text)','public.paw_mark_account_deleting(uuid,uuid)','paw_private.soft_delete(uuid,uuid)'])
 check(await value('select has_function_privilege($1,$2,\'execute\') result',[role,signature])===false,'Privileged deletion RPC exposed: '+role);
check(await value("select has_function_privilege('service_role','public.paw_mark_account_deleting(uuid,uuid)','execute') result")===true,'Service deletion grant lost');
await db.close();
console.log('BANNED DELETION SQL PASS '+checks+': production migration, ban/delete serialization, late ban, expiry, permanent ban, Auth purge, direct signup, unban, retry and grants; isolated PostgreSQL fixtures');
