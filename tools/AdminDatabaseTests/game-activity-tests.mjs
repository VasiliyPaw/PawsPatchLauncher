import assert from 'node:assert/strict';
export async function gameActivityTests(db,login,rpc,user,peer,outsider) {
 let checks=0;const check=(ok,msg)=>{assert.ok(ok,msg);checks++;};
 const q=async(sql,args=[])=>(await db.query(sql,args)).rows;
 const ready=async id=>{await db.exec('reset role');await q("update paw_private.social_presence set seen_at=now()-interval '5 seconds' where player_id=$1",[id]);await login(id);};
 const a={phase:'match',multiplayer:true,elapsed:135,width:192,height:256,room:'A'.repeat(64),self:'p1',players:[{key:'p1',name:'Game name',bot:false,team:2,color:'#FF8000'},{key:'p2',name:'Bot',bot:true,team:1,color:'#0040FF'},{key:'p3',name:'Unknown',bot:false,team:null,color:null}]};
 const send=async(activity=a,playing=true)=>rpc('paw_presence',[playing,'unknown',{_activity:activity},null]);
 await ready(user);check((await send()).status==='ok','activity heartbeat accepted');
 await login(peer);
 let player=(await rpc('paw_social_list',[])).players.find(p=>p.id===user);
 check(player.activity.phase==='match'&&player.activity.width===192,'summary shows phase/map');
 check(!('players' in player.activity)&&!('room' in player.activity)&&!('self' in player.activity),'regular polling never downloads roster or matching metadata');
 let details=await rpc('paw_game_activity',[user]);
 check(details.status==='ok'&&details.activity.players.length===3,'authorized details');
 check(details.activity.players[0].team===2&&details.activity.players[0].color==='#FF8000'&&details.activity.players[1].team===1,'teams and colors survive heartbeat, identity enrichment and details');
 check(details.activity.players[0].profile?.id===user&&details.activity.players[1].profile===undefined&&details.activity.players[2].profile===undefined,'only matching human resolves; bots and unknown remain unlinked');
 check(!('room' in details.activity)&&!('self' in details.activity)&&details.observed_at,'detail response strips join fingerprint');
 await ready(user);await send({...a,multiplayer:false,room:null});await login(peer);
 check((await rpc('paw_game_activity',[user])).activity.players[0].profile?.id===user,'local participant links to publishing account even in single player');
 const factions={...a,players:a.players.map((p,i)=>({...p,race:i===1?'undead':'human',subrace:i===1?'shadow':'council'}))};
 await ready(user);check((await send(factions)).status==='ok','bounded native race and subrace identifiers accepted');await login(peer);
 details=await rpc('paw_game_activity',[user]);
 for(const p of factions.players){const actual=details.activity.players.find(x=>x.key===p.key);check(actual.race===p.race&&actual.subrace===p.subrace,'race and subrace preserved for linked, bot and unknown participants');}
 check(details.activity.players[0].profile?.id===user&&!details.activity.players[1].profile&&!details.activity.players[2].profile,'faction fields do not change identity matching');
 for(const choice of [{race:'random',subrace:'random'},{race:'human',subrace:'random'},{race:'random',subrace:'council'},{race:null,subrace:null},{race:'Custom_race-2',subrace:'Future_faction-3'}]){
  await ready(user);check((await send({...a,phase:'lobby',elapsed:null,players:a.players.map(p=>({...p,...choice}))})).status==='ok','lobby selections, nulls and future bounded IDs accepted');await login(peer);
  const actual=(await rpc('paw_game_activity',[user])).activity.players[0];check(actual.race===choice.race&&actual.subrace===choice.subrace,'lobby selection is returned unchanged, including independent random choices');
 }
 await ready(user);await send({...a,self:null,players:[a.players[0],a.players[1]]});await login(peer);
 check(!(await rpc('paw_game_activity',[user])).activity.players[0].profile,'one human without proven local slot is not guessed to be publisher');
 await ready(user);await send(a);
 await login(outsider);check((await rpc('paw_game_activity',[user])).status==='player_unavailable','no arbitrary player status enumeration');
 await ready(user);
 const invalid=[{...a,phase:'secret'},{...a,width:15},{...a,width:192.1},{...a,height:null},{...a,elapsed:604801},{...a,elapsed:-1},
  {...a,room:'steam://x'},{...a,self:'missing'},{...a,multiplayer:false},{...a,phase:'menu'},
  {...a,players:[...a.players,a.players[0]]},{...a,players:[{...a.players[0],name:'line\nsecret'}]},
  {...a,players:[{...a.players[0],profile:{id:peer,nickname:'impersonated'}}]},
  {...a,players:[{...a.players[0],bot:'false'}]},{...a,players:[null]}, {...a,players:42},
  {...a,players:Array.from({length:65},(_,i)=>({key:'p'+i,name:'x',bot:false}))},{...a,extra:'private'},
  {...a,players:[{...a.players[0],name:'x'.repeat(81)}]},
  ...[0,-1,65,1.5,'1',{},[]].map(team=>({...a,players:[{...a.players[0],team}]})),
  ...['red','#12345G','#FFFFFFFF','#12345',123,{},[]].map(color=>({...a,players:[{...a.players[0],color}]})),[],null];
 for(const field of ['race','subrace'])for(const value of ['', 'x'.repeat(81), 'two words', 'race/name', '../human', 'human\\name', '<human>', 'human\n', 'человек', true, 1, {}, []])
  invalid.push({...a,players:[{...a.players[0],[field]:value}]});
 for(const bad of invalid.filter(x=>x!==null))check((await send(bad)).status==='invalid_presence','invalid activity rejected');
 await login(peer);check((await rpc('paw_game_activity',[user])).activity.elapsed===135,'invalid writes leave current presence intact');
 await ready(peer);await send({...a,self:'p1'});
 details=await rpc('paw_game_activity',[user]);
 check(!details.activity.players[0].profile,'ambiguous self claims never label wrong account');
 await ready(peer);await send({...a,self:'p3'});
 details=await rpc('paw_game_activity',[user]);check(details.activity.players[2].profile?.id===peer,'same session participant resolves without nickname matching');
 await ready(peer);await send({...a,room:'B'.repeat(64),self:'p3'});
 check(!(await rpc('paw_game_activity',[user])).activity.players[2].profile,'different lobby cannot claim participant');
 // A nonfriend resolved in a visible roster may be viewed, but does not gain social privileges.
 await db.exec('reset role');await q('update public.paw_profiles set avatar_changed_at=now() where id=$1',[outsider]);
 await ready(outsider);await send({...a,self:'p3'});await login(peer);
 details=await rpc('paw_game_activity',[user]);
 check(details.activity.players[2].profile?.avatar_revision,'roster carries avatar revision for bounded image caching');
 let guest=await rpc('paw_player_profile',[outsider]);
 check(guest.status==='ok'&&guest.player.id===outsider&&!guest.player.is_friend&&guest.player.presence==='playing','recognized nonfriend profile opens');
 check(!guest.player.configuration&&!guest.player.versions&&!Object.keys(guest.player.components??{}).length,'roster identity does not expose friend configuration');
 check((await rpc('paw_game_activity',[outsider])).status==='ok','recognized participant details remain navigable');
 check((await rpc('paw_send_message',[outsider,'30000000-0000-0000-0000-000000000077','fixture','text'])).status==='friend_required','roster access never permits unsolicited chat');
 const avatarAllowed=async()=>{await db.exec('reset role');const result=(await q('select public.paw_friend_avatar_allowed($1,$1,(select launcher_id from paw_private.social_presence where player_id=$1),$2) yes',[peer,outsider]))[0].yes;await login(peer);return result;};
 check(await avatarAllowed(),'current participant avatar authorized for signed-in viewer');
 const noParticipant=async reason=>{check((await rpc('paw_player_profile',[outsider])).status==='friend_required',reason+' profile');check(!await avatarAllowed(),reason+' avatar');};
 for(const [actor,target] of [[peer,outsider],[outsider,peer]]){
  await db.exec('reset role');await q('insert into public.paw_blocks(owner_id,target_id) values($1,$2)',[actor,target]);await login(peer);
  await noParticipant('block either direction');
  await db.exec('reset role');await q('delete from public.paw_blocks where owner_id=$1 and target_id=$2',[actor,target]);await login(peer);
 }
 await ready(outsider);await send({...a,self:'p3',room:'C'.repeat(64)});await login(peer);await noParticipant('different room');
 await ready(outsider);await send({...a,self:'p3'});
 await ready(peer);await send({...a,self:'p3'});await noParticipant('ambiguous slot');
 await ready(peer);await send({...a,self:'p3',room:'B'.repeat(64)});
 await db.exec('reset role');await q("update paw_private.social_presence set seen_at=now()-interval '41 seconds' where player_id=$1",[outsider]);await login(peer);await noParticipant('stale participant');
 await ready(outsider);await send({...a,self:'p3'});
 await db.exec('reset role');await q("update paw_private.social_presence set seen_at=now()-interval '41 seconds' where player_id=$1",[user]);await login(peer);await noParticipant('stale visible host');
 await ready(user);await send({...a,players:a.players.map(p=>p.key==='p3'?{...p,bot:true}:p)});await login(peer);await noParticipant('bot cannot identify an account');
 await ready(user);await send(a);await login(peer);
 const nickname=(await rpc('paw_player_profile',[outsider])).player.nickname;
 check((await rpc('paw_friend_action',['request',user,nickname])).status==='player_unavailable','UUID and username mismatch cannot redirect request');
 check((await rpc('paw_friend_action',['request',outsider,nickname])).status==='ok','profile add friend reaches intended account');
 check((await rpc('paw_player_profile',[outsider])).player.relation==='outgoing','sent request shown in profile');
 await login(outsider);check((await rpc('paw_player_profile',[peer])).player.relation==='incoming','incoming request shown in permitted profile');
 await login(peer);await rpc('paw_friend_action',['cancel',outsider,null]);
 await ready(outsider);await send(a,false);
 await ready(user);await send({...a,phase:'lobby',elapsed:null});
 await send({...a,elapsed:900});
 await login(peer);check((await rpc('paw_game_activity',[user])).activity.phase==='lobby','existing heartbeat rate limit applies to activity too');
 await db.exec('reset role');await q('insert into public.paw_blocks(owner_id,target_id) values($1,$2)',[peer,user]);
 await login(peer);check((await rpc('paw_game_activity',[user])).status==='player_unavailable','blocked status hidden');
 await db.exec('reset role');await q('delete from public.paw_blocks where owner_id=$1 and target_id=$2',[peer,user]);
 await q("update paw_private.social_presence set seen_at=now()-interval '41 seconds' where player_id=$1",[user]);
 await login(peer);check((await rpc('paw_game_activity',[user])).activity===null,'stale activity hidden');
 check((await rpc('paw_social_list',[])).players.find(p=>p.id===user).activity===null,'stale summary hidden');
 await ready(user);await send(a,false);await login(peer);check((await rpc('paw_game_activity',[user])).activity===null,'exiting game clears activity');
 await ready(user);await send();await ready(user);await rpc('paw_presence',[true,'unknown',{},null]);
 await login(peer);check((await rpc('paw_game_activity',[user])).activity===null,'legacy client clears stale activity');
 await ready(user);await send();await ready(user);await rpc('paw_presence',[true,'unknown',{}]);
 await login(peer);check((await rpc('paw_game_activity',[user])).activity===null,'legacy three-argument client follows new wrapper');
 let denied=false;try{await q('select game_activity from paw_private.social_presence');}catch{denied=true;}check(denied,'raw activity remains private');
 denied=false;try{await q("select paw_private.presence_without_activity(true,'unknown','{}',null)");}catch{denied=true;}check(denied,'cannot bypass activity envelope directly');
 await db.exec('reset role');await db.exec('set role anon');denied=false;try{await rpc('paw_game_activity',[user]);}catch{denied=true;}check(denied,'anonymous detail access denied');
 for(const id of [user,peer]){await ready(id);await rpc('paw_presence',[false,'unknown',{},null]);}
 console.log('GAME ACTIVITY DATABASE:',checks,'PASS');return checks;
}
