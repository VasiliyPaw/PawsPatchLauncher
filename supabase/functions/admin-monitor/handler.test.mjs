import assert from 'node:assert/strict';
import {makeHandler,emailMetric,functionTotals} from './handler.mjs';
let checks=0;const check=(v,m)=>{assert.ok(v,m);checks++;};
const now=new Date('2026-09-08T15:40:00Z'),proof='a'.repeat(64),id='11111111-1111-1111-1111-111111111111';
const row={count:7,client_err_count:1,server_err_count:2};
const ok=data=>({ok:true,data});
const metric={object:'metrics',start_date:'2026-09-01T00:00:00Z',end_date:now.toISOString(),totals:{sent:2,delivered:2,failed:0,bounced:0}};
check(emailMetric(ok(metric),'emails_monthly','2026-09-01T00:00:00Z',null,now.toISOString()).coverage==='complete','complete month');
check(emailMetric(ok({...metric,start_date:'2026-09-07T00:00:00Z'}),'emails_monthly','2026-09-01T00:00:00Z',null,now.toISOString()).coverage==='partial','retention is not full month');
for(const sent of [-1,1.5,'2',null,Number.MAX_SAFE_INTEGER+1])check(emailMetric(ok({...metric,totals:{sent}}),'x',metric.start_date,null,now.toISOString())===null,'reject invalid count');
check(emailMetric(ok({...metric,totals:{sent:0}}),'x',metric.start_date,null,now.toISOString()).used===0,'real zero retained');
check(functionTotals([ok({result:[row,row]})]).count===14,'counts requests, not logs');
check(functionTotals([ok({result:[row]}),{ok:false}])===null,'partial function count rejected');
check(functionTotals([ok({result:[{...row,count:-1}]})])===null,'negative count rejected');
check(functionTotals([ok({result:[]})]).count===0,'empty request bucket zero');
async function scenario({method='POST',header=proof,authorize=true,fault,store=true,clock=()=>now}={}){
 const calls=[],pauses=[];let snapshot;
 const fetcher=async(url,init)=>{
  calls.push({url,init});check(init.redirect==='error','redirect forbidden');
  if(fault){const f=fault(url);if(f)return new Response(JSON.stringify(f.data??{secret:'never persist provider diagnostic'}),{status:f.status??200});}
  if(url.endsWith('/paw_monitor_begin'))return Response.json(authorize?id:null);
  if(url.endsWith('/paw_monitor_store')){snapshot=JSON.parse(init.body).payload;return Response.json(store);}
  if(url.includes('/emails/metrics'))return Response.json({...metric,start_date:new URL(url).searchParams.get('start_date'),end_date:new URL(url).searchParams.get('end_date')});
  if(url.includes('/domains?'))return Response.json({data:[{name:'pawspatch.xyz',status:'verified',capabilities:{sending:'enabled'}}]});
  if(url.includes('/health?'))return Response.json(['auth','db','rest','storage'].map(name=>({name,healthy:true})));
  if(url.includes('/bucket/'))return Response.json({id:'paw-social-saves',public:false,file_size_limit:20971520});
  if(url.endsWith('/functions'))return Response.json([{id,status:'ACTIVE'}]);
  if(url.includes('/functions.req-stats?'))return Response.json({result:[row]});
  throw new Error('Unexpected endpoint');
 };
 const handler=makeHandler({serviceKey:'test_service',resendKey:'test_resend',managementToken:'test_pat',tokenExpiresAt:'2026-10-08T00:00:00Z',fetcher,clock,pause:async ms=>pauses.push(ms)});
 const result=await handler(new Request('https://example.test/monitor',{method,headers:header?{'x-paw-monitor':header}:{}}));
 return {result,calls,snapshot,pauses};
}
for(const args of [{method:'GET'},{header:null},{header:'bad'}]){const r=await scenario(args);check(r.result.status>=400&&r.calls.length===0,'unauthorized no provider calls');}
const forged=await scenario({authorize:false});check(forged.result.status===403&&forged.calls.length===1,'proof checked before provider access');
const good=await scenario();check(good.result.status===200,'success');check(good.snapshot.metrics.length===3,'three actual usage metrics');
check(good.snapshot.email.domain_verified&&good.snapshot.storage.private_bucket,'domain and private storage verified');
check(good.snapshot.services.every(s=>s.healthy),'health snapshot');
check(good.snapshot.functions.count===7&&good.snapshot.functions.server_errors===2,'function error statistics');
check(good.pauses.length===2&&good.pauses.every(ms=>ms>=1000),'Resend paced');
check(good.calls.filter(c=>!c.url.includes('/rpc/')).every(c=>c.init.method==='GET'),'no provider mutation');
check(!/test_service|test_pat|test_resend/.test(JSON.stringify(good.snapshot)),'no secrets in stored snapshot');
check(!good.calls.some(c=>c.url.includes('/platform/')||c.url.includes('/emails?')),'no private billing or personal email bodies');
check(good.snapshot.errors.egress==='billing_api_unavailable','unavailable traffic explicit');
const year=await scenario({clock:()=>new Date('2026-12-31T23:59:59Z')});
check(year.snapshot.metrics.find(m=>m.metric==='emails_monthly').period_end==='2027-01-01T00:00:00.000Z','year boundary');
for(const status of [401,403,429,404,500]){
 const bad=await scenario({fault:url=>url.includes('/emails/metrics')?{status}:null});
 check(!bad.snapshot.metrics.some(m=>m.metric.startsWith('emails')),'missing not zero');
 check(!JSON.stringify(bad.snapshot).includes('never persist'),'error body discarded');
}
const malformed=await scenario({fault:url=>url.endsWith('/functions')?{data:[{id:'../../secrets',status:'ACTIVE'}]}:null});
check(!malformed.calls.some(c=>c.url.includes('/functions.req-stats')),'untrusted function ID cannot change URL');
check(!malformed.snapshot.metrics.some(m=>m.metric==='functions_daily'),'malformed functions not zero');
const badStore=await scenario({store:false});check(badStore.result.status===503,'storage failure is not success');
console.log('MONITOR HANDLER',checks,'PASS');
