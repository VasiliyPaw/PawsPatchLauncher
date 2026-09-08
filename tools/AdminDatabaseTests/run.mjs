import { PGlite } from '@electric-sql/pglite';
import { readFile, readdir } from 'node:fs/promises';
import assert from 'node:assert/strict';
import { historyTests } from './history-tests.mjs';
import { monitorTests } from './monitor-tests.mjs';
const db=new PGlite();
await db.exec(`create role anon;create role authenticated;create role service_role bypassrls;create role supabase_auth_admin;
create schema auth;create schema storage;
create table auth.users(id uuid primary key,email text,email_change text,encrypted_password text,email_confirmed_at timestamptz,deleted_at timestamptz,raw_user_meta_data jsonb,created_at timestamptz default now());
create table auth.sessions(id uuid primary key,user_id uuid references auth.users on delete cascade,created_at timestamptz default now(),not_after timestamptz);
create function auth.uid() returns uuid language sql stable as $$select nullif(current_setting('request.jwt.claims',true),'')::jsonb->>'sub'$$;
` .replace("select nullif(current_setting('request.jwt.claims',true),'')::jsonb->>'sub'","select (nullif(current_setting('request.jwt.claims',true),'')::jsonb->>'sub')::uuid"));
await db.exec(`create function auth.jwt() returns jsonb language sql stable as $$select coalesce(nullif(current_setting('request.jwt.claims',true),''),'{}')::jsonb$$;
grant usage on schema auth to authenticated,anon;grant execute on all functions in schema auth to authenticated,anon;
create table storage.buckets(id text primary key,name text,public boolean,file_size_limit bigint,allowed_mime_types text[]);
create table storage.objects(id uuid primary key default gen_random_uuid(),bucket_id text,name text,metadata jsonb,created_at timestamptz default now());`);
const base=new URL('../../supabase/migrations/',import.meta.url);
for(const file of (await readdir(base)).filter(n=>n.endsWith('.sql')&&!n.includes('scheduler')&&!n.includes('founder_grant')).sort()){
 try{await db.exec(await readFile(new URL(file,base),'utf8'));console.log('MIGRATION',file);}
 catch(e){console.error('FAILED',file,e.message,e.cause?.message);process.exit(1);}
}
let checks=0;
const check=(v,msg)=>{assert.ok(v,msg);checks++;};
const denied=async(work,msg)=>{let caught=false;try{await work();}catch{caught=true;}check(caught,msg);};
const query=async(sql,params=[])=> (await db.query(sql,params)).rows;
const owner='2facff35-56cd-45a4-b88b-b38b71384533',admin='10000000-0000-0000-0000-000000000001',user='10000000-0000-0000-0000-000000000002',peer='10000000-0000-0000-0000-000000000003';
const instance='20000000-0000-0000-0000-000000000001';
for(const [id,name] of [[owner,'paw'],[admin,'admin'],[user,'user'],[peer,'peer']]){
 await query(`insert into auth.users(id,email,email_confirmed_at,raw_user_meta_data) values($1,$2,now(),$3::jsonb)`,[id,name+'@example.test',JSON.stringify({nickname:name,display_name:name})]);
 await query(`insert into auth.sessions(id,user_id) values($1,$1)`,[id]);
 await query(`insert into paw_private.launcher_sessions values($1,$1,now(),$2,false)`,[id,instance]);
}
await db.exec(await readFile(new URL('20260909001300_founder_grant.sql',base),'utf8'));
await db.exec(`update public.paw_profiles set admin_level=1 where nickname='admin';`);
await query('insert into public.paw_friendships(low_id,high_id,requester,accepted) values(least($1::uuid,$2::uuid),greatest($1::uuid,$2::uuid),$1,true)',[user,peer]);
const login=async id=>{await db.exec('reset role');await query("select set_config('request.jwt.claims',$1,false),set_config('request.headers',$2,false)",[JSON.stringify({sub:id,session_id:id}),JSON.stringify({'x-paw-launcher':instance})]);await db.exec('set role authenticated');};
const rpc=async(name,args)=> (await query(`select public.${name}(${args.map((_,i)=>'$'+(i+1)).join(',')}) result`,args))[0].result;
await login(user);
check((await rpc('paw_admin_list',['users','',0])).status==='admin_required','ordinary user cannot enumerate users');
check((await rpc('paw_admin_action',['role',user,'',null,2])).status==='admin_required','ordinary cannot grant role');
check((await rpc('paw_admin_chat',[peer])).status==='admin_required','ordinary cannot open official chat');
check((await rpc('paw_friend_action',['block',owner,null])).status==='admin_cannot_block','cannot block owner');
check((await rpc('paw_read_messages',[owner,null])).status==='friend_required','no arbitrary history');
await login(admin);
check((await rpc('paw_admin_action',['role',user,'',null,1])).status==='higher_role_required','normal admin cannot grant roles');
for(const action of ['role','ban','delete'])check((await rpc('paw_admin_action',[action,owner,'test',null,0])).status==='protected_account','protected founder '+action);
check((await rpc('paw_admin_chat',[user])).status==='ok','admin opens official dialog');
check((await rpc('paw_send_message',[user,'30000000-0000-0000-0000-000000000001','Official test','text'])).status==='ok','admin sends without friendship');
await login(user);
check((await rpc('paw_social_list',[])).players.some(p=>p.id===admin&&p.admin_level===1),'recipient sees official verified admin');
check((await rpc('paw_send_message',[admin,'30000000-0000-0000-0000-000000000002','Reply test','text'])).status==='ok','recipient can reply');
await login(owner);
check((await rpc('paw_admin_action',['ban',user,'Test reason',new Date(Date.now()+60000).toISOString(),null])).status==='ok','one minute email ban');
await login(user);
check((await rpc('paw_social_list',[])).status==='account_banned','banned cannot use friends');
check((await rpc('paw_launcher_session',['check',null])).status==='ok','banned can keep launcher session for local game');
check((await rpc('paw_change_nickname',['renamed'])).status!=='ok','banned cannot rename');
await login(admin);
const banned=(await rpc('paw_social_list',[])).players.find(p=>p.id===user);
check(banned?.banned_at&&banned.presence==='offline','peer sees ban and offline');
check((await rpc('paw_send_message',[user,'30000000-0000-0000-0000-000000000003','Blocked send','text'])).status!=='ok','cannot send to banned');
check((await rpc('paw_read_messages',[user,null])).messages.length===2,'history retained while banned');
await db.exec('reset role');
check((await rpc('paw_registration_check',['USER@example.test','newuser'])).status==='email_banned','banned email registration preflight');
try{await query(`insert into auth.users(id,email,raw_user_meta_data) values(gen_random_uuid(),'USER@example.test','{"nickname":"other"}')`);check(false,'direct Auth signup accepted banned email');}catch(e){check(e.message.includes('email_banned'),'Auth signup guard');}
try{await query(`update auth.users set encrypted_password='x' where id=$1`,[user]);check(false,'direct banned password mutation');}catch(e){check(e.message.includes('account_restricted'),'Auth password guard');}
const banId=(await query('select id from paw_private.email_bans where revoked_at is null'))[0].id;
await login(owner);check((await rpc('paw_admin_action',['unban',banId,'',null,null])).status==='ok','unban');
check((await rpc('paw_admin_action',['delete',user,'',null,null])).status==='ok','soft delete');
await login(admin);
check((await rpc('paw_social_list',[])).players.find(p=>p.id===user)?.display_name==='Удалённый аккаунт','deleted tombstone');
check((await rpc('paw_read_messages',[user,null])).messages.length===2,'deleted history retained');
check((await rpc('paw_friend_action',['block',user,null])).status==='player_unavailable','cannot block deleted');
await login(owner);
check((await rpc('paw_admin_action',['restore',user,'',null,null])).status==='ok','restore within seven days');
check((await rpc('paw_admin_action',['role',user,'',null,2])).status==='ok','owner grants senior role');
check((await rpc('paw_admin_action',['role',user,'',null,0])).status==='ok','owner revokes role');
check((await rpc('paw_admin_action',['delete',user,'',null,null])).status==='ok','delete again');
await db.exec('reset role');
check((await rpc('paw_nickname_available',['user']))===false,'username reserved');
await query(`update public.paw_profiles set deleted_at=now()-interval '8 days' where id=$1`,[user]);
await login(owner);check((await rpc('paw_admin_action',['restore',user,'',null,null])).status==='restore_expired','restore expires after seven days');
await login(admin);check((await rpc('paw_friend_action',['hide_chat',user,null])).status==='ok','hide deleted chat');
check(!(await rpc('paw_social_list',[])).players.some(p=>p.id===user),'hidden tombstone absent');
await db.exec('reset role');
const due=await rpc('paw_deletion_candidates',[]);check(due.length===1&&due[0].id===user,'only due accounts selected for final deletion');
await login(owner);check((await rpc('paw_admin_action',['restore',user,'',null,null])).status==='restore_expired','claimed purge cannot be restored');
await db.exec('reset role');
await query('delete from auth.users where id=$1',[user]);
check((await query('select count(*)::int n from public.paw_messages where sender_id=$1 or recipient_id=$1',[user]))[0].n===2,'messages survive final Auth cascade');
check(await rpc('paw_nickname_available',['user']),'username free after final deletion');
check((await query('select finalized_at is not null yes from paw_private.player_identities where id=$1',[user]))[0].yes,'anonymized tombstone finalized');
await login(peer);
check((await rpc('paw_social_list',[])).players.some(p=>p.id===user&&p.deleted_at),'empty friendship chat survives final purge');
check((await rpc('paw_read_messages',[user,null])).messages.length===0,'empty archived chat readable without arbitrary history');
await db.exec('reset role');
try{await query('delete from auth.users where id=$1',[owner]);check(false,'founder deleted');}catch(e){check(e.message.includes('protected_account'),'founder Auth delete guarded');}
await query('update public.paw_profiles set banned_at=now(),ban_until=now()-interval \'1 second\' where id=$1',[peer]);
check(!(await query('select paw_private.player_banned($1) banned',[peer]))[0].banned,'temporary ban expires without job');
await denied(()=>query(`insert into auth.users(id,email,raw_user_meta_data) values(gen_random_uuid(),'new@example.test','{"nickname":"русский"}')`),'server Cyrillic signup denied');
await login(peer);check((await rpc('paw_change_nickname',['русский'])).status==='invalid_nickname','server Cyrillic rename denied');
await db.exec('reset role');
await query(`update auth.users set raw_user_meta_data=raw_user_meta_data||'{"admin_level":2,"protected_admin":true}' where id=$1`,[peer]);
check((await query('select admin_level=0 and not protected_admin safe from public.paw_profiles where id=$1',[peer]))[0].safe,'mutable user metadata cannot grant admin');
await login(peer);
for(const [name,args] of [['paw_deletion_candidates',[]],['paw_maintenance_authorize',['0'.repeat(64)]],['paw_maintenance_finished',[true]]]){
 await denied(()=>rpc(name,args),'maintenance denied '+name);
}
await db.exec('reset role');
for(const name of ['Привет','héllo','ｐａｗ','a b','ab','_abc'])check(!(await query('select paw_private.nickname_valid($1) valid',[name]))[0].valid,'reject username '+name);
for(const name of ['Paw','abc_123','user-name','user.name','123'])check((await query('select paw_private.nickname_valid($1) valid',[name]))[0].valid,'allow username '+name);
await login(user);
for(const table of ['email_bans','moderation_audit','player_identities','maintenance_secret'])await denied(()=>query('select * from paw_private.'+table),'private read denied '+table);
await denied(()=>query('update public.paw_profiles set admin_level=2 where id=$1',[peer]),'direct role write denied');
checks+=await historyTests(db);
checks+=await monitorTests(db,login,owner,peer);
console.log('ADMIN DATABASE CHECKS:',checks,'PASS (isolated PostgreSQL/WASM, no production mutations)');
await db.close();
