import assert from 'node:assert/strict';
export async function monitorTests(db,login,owner,peer){
 let n=0;const check=(v,m)=>{assert.ok(v,m);n++;};
 const q=async(s,p=[]) => (await db.query(s,p)).rows;
 const rpc=async(name,args=[]) => (await q(`select public.${name}(${args.map((_,i)=>'$'+(i+1)).join(',')}) v`,args))[0].v;
 const denied=async work=>{let caught=false;try{await work();}catch{caught=true;}check(caught,'monitor access denied');};
 await db.exec('reset role');const proof=(await q('select proof from paw_private.monitor_state'))[0].proof;
 for(const role of ['anon','authenticated']){
  await db.exec('set role '+role);
  await denied(()=>q('select * from paw_private.monitor_state'));
  await denied(()=>rpc('paw_monitor_begin',[proof]));
  await denied(()=>rpc('paw_monitor_store',[null,{}]));
  await denied(()=>q('select paw_private.monitor_snapshot()'));
  await db.exec('reset role');
 }
 check(await rpc('paw_monitor_begin',['0'.repeat(64)])===null,'wrong proof');
 const run=await rpc('paw_monitor_begin',[proof]);check(typeof run==='string','valid proof claims run');
 check(await rpc('paw_monitor_begin',[proof])===null,'one minute lease');
 const metric={metric:'emails_daily',used:2,source:'resend_metrics',coverage:'complete',checked_at:new Date().toISOString()};
 const payload={schema:1,metrics:[metric],email:{domain_verified:true},services:[]};
 for(const bad of [null,[],{}, {schema:1,metrics:{}},{schema:1,metrics:Array(9).fill(metric)},{...payload,metrics:[{...metric,used:-1}]},{...payload,metrics:[{...metric,source:null}]},{...payload,metrics:[{...metric,metric:'egress'}]}])
  check(await rpc('paw_monitor_store',[run,bad])===false,'invalid payload rejected');
 check(await rpc('paw_monitor_store',['00000000-0000-0000-0000-000000000000',payload])===false,'wrong run');
 check(await rpc('paw_monitor_store',[run,payload])===true,'aggregate stored');
 check(await rpc('paw_monitor_store',[run,payload])===false,'run cannot replay');
 check((await q("select used from paw_private.resource_usage where metric='emails_daily'"))[0].used===2,'actual usage stored');
 await login(peer);check((await rpc('paw_admin_resources')).status==='admin_required','normal user metrics forbidden');
 check((await rpc('paw_admin_status')).status==='admin_required','normal user status forbidden');
 await login(owner);
 for(const name of ['paw_admin_resources','paw_admin_status']){const result=await rpc(name);check(result.status==='ok'&&result.monitor.email.domain_verified,'admin snapshot visible');check(!JSON.stringify(result).includes(proof)&&!JSON.stringify(result).includes('run_id'),'scheduler proof private');}
 await db.exec('reset role');
 await q("update paw_private.monitor_state set run_id=$1,started_at=now()-interval '6 minutes'",[run]);
 check(await rpc('paw_monitor_store',[run,payload])===false,'expired run');
 console.log('MONITOR DATABASE',n,'PASS');return n;
}
