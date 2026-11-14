import assert from 'node:assert/strict';
import {makeHandler} from './handler.mjs';
const url='https://trdzsdclscuwwmxnepyt.supabase.co';
const player='10000000-0000-4000-8000-000000000001',session='20000000-0000-4000-8000-000000000002',launcher='30000000-0000-4000-8000-000000000003',id='40000000-0000-4000-8000-000000000004';
const bearer='Bearer header.'+Buffer.from(JSON.stringify({session_id:session})).toString('base64url')+'.signature';
const build={id,channel:'stable',version:'0.1.0',size:123,sha256:'A'.repeat(64),executable:'KohanReborn.exe',notes:{},published_at:'2026-11-14T00:00:00Z'};
let passed=0;const check=(condition,message)=>{assert.ok(condition,message);passed++;};
async function scenario(options={}){
 const calls=[];let reads=0;
 const fetcher=async(endpoint,init)=>{
  calls.push(endpoint);check(init.redirect==='error','provider redirects forbidden');
  if(endpoint.endsWith('/auth/v1/user'))return Response.json({id:player,email_confirmed_at:options.unconfirmed?null:'2026-11-01'});
  if(endpoint.endsWith('/paw_reborn_authorize')||endpoint.endsWith('/paw_reborn_history')){
   reads++;const context=JSON.parse(init.body);check(context.player===player&&context.session===session&&context.launcher===launcher,'verified identity forwarded');
   if(options.denied||options.revoked&&reads===2)return Response.json({status:'reborn_access_denied'});
   if(options.replaced)return Response.json({status:'session_replaced'});
   if(options.rpcFailure)return new Response('private provider diagnostics',{status:500});
   return Response.json(options.action==='history'?{status:'ok',releases:options.oversized?Array(201).fill(build):options.rows||[]}:options.action==='catalog'?{status:'ok',releases:[]}:{status:'ok',release:options.wrongId?{...build,id:player}:build});
  }
  if(endpoint.includes('/storage/v1/object/sign/')){
   check(init.headers.Authorization==='Bearer private-service-key','storage access uses server credential');
   check(JSON.parse(init.body).expiresIn===120,'short-lived URL');
   return options.missing?new Response('',{status:404}):Response.json({signedURL:options.external?'https://evil.invalid/build.zip':'/object/sign/paw-reborn-builds/stable/'+id+'.zip?token=temporary'});
  }
  throw Error('Unexpected provider route');
 };
 const handler=makeHandler({url,serviceKey:'private-service-key',publicKey:'public-key',fetcher,clock:()=>Date.parse('2026-11-14T00:00:00Z')});
 const action=options.action||'download',query=['catalog','history'].includes(action)?'action='+action:`action=${action}&channel=${options.channel||'stable'}&build_id=${options.id||id}`;
 const response=await handler(new Request(url+'/functions/v1/reborn-builds?'+query,{method:options.method||'POST',headers:{authorization:options.guest?'':bearer,'x-paw-launcher':launcher}}));
 const data=await response.json();check(!JSON.stringify(data).includes('private-service-key')&&!JSON.stringify(data).includes('provider diagnostics'),'secrets not returned');
 check(response.headers.get('Cache-Control')==='no-store','authorization response cannot be cached');
 return {response,data,calls,reads};
}
let r=await scenario({action:'catalog'});check(r.response.status===200&&r.data.releases.length===0&&!r.calls.some(p=>p.includes('/storage/')),'empty catalog issues no download');
r=await scenario({action:'history'});check(r.response.status===200&&r.data.releases.length===0&&!r.calls.some(p=>p.includes('/storage/')),'empty private history issues no download');
r=await scenario({action:'history',rows:[build,{...build,id:player,version:'0.0.1'},{...build,id:session,channel:'beta'}]});check(r.response.status===200&&r.data.releases.length===3&&r.calls.some(p=>p.endsWith('/paw_reborn_history'))&&!r.calls.some(p=>p.includes('/storage/')),'history retains older releases and both branches without tickets');
for(const opts of [{denied:true},{replaced:true},{guest:true},{oversized:true}]){r=await scenario({action:'history',...opts});check(r.response.status>=400&&!r.data.releases&&!r.data.url,'private history failure cannot leak rows');}
r=await scenario();check(r.response.status===200&&r.reads===2&&r.data.url.startsWith(url+'/storage/v1/object/sign/paw-reborn-builds/stable/'+id+'.zip?token='),'authorized download rechecks membership');
check(r.data.expires_at==='2026-11-14T00:02:00.000Z','ticket lifetime correct');
for(const options of [{guest:true},{unconfirmed:true},{denied:true},{revoked:true},{replaced:true},{wrongId:true},{external:true},{missing:true},{rpcFailure:true},{channel:'../../outside'},{id:'not-a-uuid'},{method:'GET'}]){
 r=await scenario(options);check(r.response.status>=400&&!r.data.url,'denied request cannot obtain URL: '+JSON.stringify(options));
 if(options.denied||options.guest||options.unconfirmed)check(!r.calls.some(p=>p.includes('/storage/')),'denied actor never reaches storage');
}
console.log('REBORN EDGE PASS',passed,': empty channels, authentication, role revalidation, private storage and short-lived tickets; mocked requests only');
