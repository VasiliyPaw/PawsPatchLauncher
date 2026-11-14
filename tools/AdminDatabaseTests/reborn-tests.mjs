import assert from 'node:assert/strict';
export async function rebornTests(db,user,admin,launcher){
 let count=0;const check=(ok,why)=>{assert.ok(ok,why);count++;};
 const q=async(sql,values=[])=>(await db.query(sql,values)).rows;
 await db.exec('reset role');
 const history=async(actor)=>(await q('select public.paw_reborn_history($1,$1,$2) result',[actor,launcher]))[0].result;
 const call=async(actor,channel=null,id=null)=>(await q('select public.paw_reborn_authorize($1,$1,$2,$3,$4) result',[actor,launcher,channel,id]))[0].result;
 check((await q("select relrowsecurity enabled from pg_class where oid='paw_private.reborn_builds'::regclass"))[0].enabled,'build table RLS');
 for(const role of ['anon','authenticated']){
  check(!(await q("select has_table_privilege($1,'paw_private.reborn_builds','select') yes",[role]))[0].yes,'client cannot read private release rows');
  check(!(await q("select has_function_privilege($1,'public.paw_reborn_history(uuid,uuid,uuid)','execute') yes",[role]))[0].yes,'client cannot impersonate history reader');
  check(!(await q("select has_function_privilege($1,'public.paw_reborn_authorize(uuid,uuid,uuid,text,uuid)','execute') yes",[role]))[0].yes,'client cannot impersonate another actor');
 }
 check((await q("select public=false private from storage.buckets where id='paw-reborn-builds'"))[0].private,'archive bucket private');
 check((await history(admin)).releases.length===0,'admin without team can read empty private history');
 check((await history(user)).status==='reborn_access_denied','ordinary player cannot read history');
 check((await call(admin)).releases.length===0,'admin role without team can access empty channels');
 check((await call(user)).status==='reborn_access_denied','ordinary player cannot access builds');
 await q('update public.paw_profiles set paws_team=true where id=$1',[user]);
 check((await call(user)).releases.length===0,'new channels start empty');
 const releases=[];
 async function build(channel,version,enabled,offset){const id=(await q("insert into paw_private.reborn_builds(channel,version,enabled,size,sha256,executable,published_at) values($1,$2,$3,123,repeat('A',64),'KohanReborn.exe',now()+$4::interval) returning id",[channel,version,enabled,offset]))[0].id;releases.push(id);return id;}
 const disabled=await build('stable','0.0.1',false,'-3 days');
 const stable=await build('stable','0.1.0',true,'-2 days');
 const archived=await build('stable','0.0.9',true,'-4 days');
 const beta=await build('beta','0.2.0-beta.1',true,'-1 day');
 await build('stable','99.0.0',true,'1 day');
 const list=(await call(user)).releases;
 const notes=(await history(user)).releases;
 check(notes.length===3&&notes[0].id===beta&&notes[1].id===stable&&notes[2].id===archived,'history preserves older releases and both channels in publication order');
 check(notes.every(r=>!('enabled' in r)),'history does not expose internal publish switches');
 check(list.length===2&&list.some(r=>r.id===stable)&&list.some(r=>r.id===beta),'only published latest per channel');
 check((await call(user,'stable',disabled)).status==='reborn_unavailable','disabled archive unavailable');
 check((await call(user,'beta',stable)).status==='reborn_unavailable','channel substitution rejected');
 check((await call(user,'../../outside',stable)).status==='reborn_unavailable','invalid channel rejected');
 check((await call(user,'stable',stable)).release.id===stable,'authorized stable metadata');
 check((await call(admin,'beta',beta)).release.id===beta,'admin without team can request a published build');
 await q('update public.paw_profiles set admin_level=0 where id=$1',[admin]);
 check((await history(admin)).status==='reborn_access_denied','withdrawn admin role revokes history');
 check((await call(admin)).status==='reborn_access_denied','withdrawn admin role revokes build access');
 await q('update public.paw_profiles set admin_level=1 where id=$1',[admin]);
 await q('update public.paw_profiles set paws_team=false where id=$1',[user]);
 check((await history(user)).status==='reborn_access_denied','withdrawn team role revokes history');
 check((await call(user,'beta',beta)).status==='reborn_access_denied','membership withdrawal revokes download');
 await q('update public.paw_profiles set paws_team=true where id=$1',[user]);
 await q('update paw_private.launcher_sessions set released=true where player_id=$1',[user]);
 check((await history(user)).status==='session_replaced','released launcher session cannot read history');
 check((await call(user)).status==='session_replaced','released launcher session denied');
 await q('update paw_private.launcher_sessions set released=false where player_id=$1',[user]);
 await q('update public.paw_profiles set deletion_pending=true where id=$1',[user]);
 check((await history(user)).status==='reborn_access_denied','deletion-pending team account cannot read history');
 check((await call(user)).status==='reborn_access_denied','deletion-pending team account denied');
 await q('update public.paw_profiles set deletion_pending=false,paws_team=false where id=$1',[user]);
 const github=await build('stable','0.23.0',false,'-1 hour');
 check((await q('select download_provider from paw_private.reborn_builds where id=$1',[github]))[0].download_provider==='supabase','old publishers retain Storage by default');
 await q("update paw_private.reborn_builds set download_provider='github',github_repository='Owner/Private',github_repository_id=1458192487,github_asset_id=748818121 where id=$1",[github]);
 await q('update public.paw_profiles set paws_team=true where id=$1',[user]);
 check((await call(user,'stable',github)).status==='reborn_unavailable','GitHub metadata alone cannot publish disabled builds');
 await q('update paw_private.reborn_builds set enabled=true where id=$1',[github]);
 const githubMetadata=(await call(user,'stable',github)).release;
 check(githubMetadata.download_provider==='github'&&githubMetadata.github_asset_id===748818121&&githubMetadata.github_repository_id===1458192487,'service-only RPC retains GitHub identity');
 for(const mutation of ["github_repository=null","github_repository='../Private'","github_repository_id=null","github_repository_id=0","github_asset_id=null","github_asset_id=9007199254740992","download_provider='supabase'","download_provider='external'"]){
  let rejected=false;try{await q('update paw_private.reborn_builds set '+mutation+' where id=$1',[github]);}catch(error){rejected=error.code==='23514';}
  check(rejected,'provider constraint must reject '+mutation);
 }
 await q('update public.paw_profiles set paws_team=false where id=$1',[user]);
 await q('delete from paw_private.reborn_builds where id=any($1::uuid[])',[releases]);
 console.log('REBORN SQL PASS',count,': role/session gate, private storage, empty channels, latest releases and revocation');return count;
}
