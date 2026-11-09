import assert from 'node:assert/strict';

export async function profileVisibilityTests(db,login,rpc,user,friend,outsider) {
 let checks=0; const check=(ok,why)=>{assert.ok(ok,why);checks++;};
 const q=async(sql,args=[])=>(await db.query(sql,args)).rows;
 await db.exec('reset role');
 check((await q("select relrowsecurity as protected from pg_class where oid='paw_private.profile_visibility'::regclass"))[0].protected,'privacy table has row-level security in addition to revoked client grants');
 await q("update paw_private.social_presence set seen_at=now()-interval '5 seconds' where player_id=$1",[user]);
 await login(user);
 const code='PAW-STABLE-VANILLA-PP1-CL1-OOS1';
 const activity={phase:'match',multiplayer:false,elapsed:42,width:192,height:192,players:[]};
 check((await rpc('paw_presence',[true,'stable',{core:true,colors:true,_activity:activity},code])).status==='ok','visibility fixture publishes existing validated presence');
 check((await rpc('paw_profile_visibility',[null,null])).configuration_visibility==='all','existing accounts retain full visibility by default');
 for(const settings of ['all','friends','nobody']) for(const game of ['all','friends','nobody']) {
  await login(user);
  const saved=await rpc('paw_profile_visibility',[settings,game]);
  check(saved.status==='ok'&&saved.configuration_visibility===settings&&saved.activity_visibility===game,'save independent account preferences');
  for(const actor of [user,friend,outsider]) {
   await login(actor);
   const canSettings=actor===user||settings==='all'||settings==='friends'&&actor===friend;
   const canActivity=actor===user||game==='all'||game==='friends'&&actor===friend;
   const card=(await rpc('paw_profile_card',[user])).player;
   check(card?.id===user&&card.presence==='playing','general profile survives selective privacy');
   check(canSettings?card.configuration===code&&card.components.core:card.configuration_hidden===true&&!card.configuration&&!card.versions&&!card.channel&&!card.components,'configuration privacy enforced server-side');
   check(canActivity?card.activity?.phase==='match':card.activity_hidden===true&&!card.activity,'summary privacy enforced independently');
   const details=await rpc('paw_profile_activity',[user]);
   check(details.status==='ok'&&(canActivity?details.activity?.elapsed===42:details.activity_hidden===true&&details.activity===null),'detailed public activity follows same policy');
   if(actor===friend) {
    const legacy=await rpc('paw_game_activity',[user]);
    check(legacy.status==='ok'&&(canActivity?legacy.activity?.elapsed===42:legacy.activity===null),'legacy activity cannot bypass visibility');
   }
   if(actor===friend) {
    const listed=(await rpc('paw_social_list',[])).players.find(p=>p.id===user);
    check(canSettings?listed.configuration===code:listed.configuration_hidden&&!listed.configuration,'friend list cannot leak hidden configuration');
    check(canActivity?listed.activity?.elapsed===42:listed.activity_hidden&&!listed.activity,'friend list cannot leak hidden activity');
   }
  }
 }
 await login(friend); const own=await rpc('paw_profile_visibility',[null,null]);
 check(own.configuration_visibility==='all'&&own.activity_visibility==='all','one account never changes another account preference');
 await login(user);
 for(const pair of [['invalid','all'],['all',null],[null,'all']])check((await rpc('paw_profile_visibility',pair)).status==='invalid_visibility','invalid/partial policy rejected');
 check((await rpc('paw_profile_visibility',[null,null])).configuration_visibility==='nobody','rejected writes preserve policy');
 await db.exec('reset role'); await q('insert into public.paw_blocks(owner_id,target_id) values($1,$2) on conflict do nothing',[user,outsider]);
 await login(outsider);check((await rpc('paw_profile_card',[user])).status==='profile_blocked','blocks still take priority over visibility');
 await db.exec('reset role');await q('delete from public.paw_blocks where owner_id=$1 and target_id=$2',[user,outsider]);
 await db.exec('set role anon');let denied=false;try{await rpc('paw_profile_visibility',[null,null]);}catch{denied=true;}check(denied,'guests cannot read or write account privacy');
 await login(friend);denied=false;try{await q('select * from paw_private.profile_visibility');}catch{denied=true;}check(denied,'raw preference table is private');
 denied=false;try{await q('select paw_private.friend_presence_before_visibility($1,$2)',[friend,user]);}catch{denied=true;}check(denied,'unfiltered helpers cannot be called by clients');
 await db.exec('reset role');await q('delete from paw_private.profile_visibility where player_id=$1',[user]);
 await q("update paw_private.social_presence set seen_at=now()-interval '5 seconds' where player_id=$1",[user]);await login(user);await rpc('paw_presence',[false,'unknown',{},null]);
 console.log('PROFILE VISIBILITY DATABASE:',checks,'PASS');return checks;
}
