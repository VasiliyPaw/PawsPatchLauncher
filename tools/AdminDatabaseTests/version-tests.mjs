import assert from 'node:assert/strict';

export async function versionTests(db, login, rpc, user, peer) {
 let checks=0; const check=(ok,msg)=>{assert.ok(ok,msg);checks++;};
 const code='PAW-BETA-IW1-SP4-RM1-SG1-LM1-RU0-CL0-OOS0';
 const versions={launcher:'0.6.4.0',mod:'arcane-wars',channel:'beta',content_id:'A'.repeat(64),patch:'0.3.0-beta.2'};
 const ready=async()=>{await db.exec('reset role');await db.query("update paw_private.social_presence set seen_at=now()-interval '5 seconds' where player_id=$1",[user]);await login(user);};
 await ready();
 check((await rpc('paw_presence',[false,'beta',{core:true,_versions:versions},code])).status==='ok','version presence accepted');
 await login(peer);
 let player=(await rpc('paw_social_list',[])).players.find(p=>p.id===user);
 check(player.versions.launcher===versions.launcher && player.versions.content_id===versions.content_id && player.versions.patch===versions.patch,'peer receives versions with configuration');
 check(player.configuration===code && !('_versions' in player.components),'version envelope separated from boolean components');
 await ready();
 for(const bad of [null,[],{...versions,launcher:1},{...versions,launcher:'../secret'}, {...versions,content_id:'path'},
  {...versions,mod:'vanilla'},{...versions,channel:'stable'},{...versions,patch:'private path'}, {...versions,extra:'private'},
  {...versions,launcher:'9'.repeat(1000)}, {...versions,content_id:42}]) {
  check((await rpc('paw_presence',[false,'beta',{core:true,_versions:bad},code])).status==='invalid_presence','malformed/bound-to-other-mode metadata rejected');
 }
 await login(peer);
 player=(await rpc('paw_social_list',[])).players.find(p=>p.id===user);
 check(player.versions.launcher===versions.launcher,'invalid metadata did not overwrite valid state');
 await ready();
 check((await rpc('paw_presence',[false,'beta',{core:true},code])).status==='ok','legacy presence still accepted');
 await login(peer);player=(await rpc('paw_social_list',[])).players.find(p=>p.id===user);
 check(player.versions===null && player.configuration===code,'legacy write clears stale versions atomically');
 await ready();
 check((await rpc('paw_presence',[false,'unknown',{_versions:{launcher:'0.6.4.0'}},null])).status==='ok','launcher-only presence supported before applying game settings');
 await login(peer);player=(await rpc('paw_social_list',[])).players.find(p=>p.id===user);
 check(player.versions.launcher==='0.6.4.0' && player.configuration===null,'launcher-only presence does not invent installed patch');
 let denied=false;try{await db.exec('select versions from paw_private.social_presence');}catch{denied=true;}
 check(denied,'version data remains private');
 await ready();await rpc('paw_presence',[false,'beta',{core:true},code]);
 console.log('SOCIAL VERSION DATABASE:',checks,'PASS');return checks;
}
