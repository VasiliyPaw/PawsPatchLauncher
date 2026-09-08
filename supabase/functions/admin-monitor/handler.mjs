// Server-only reader. All destinations and methods are fixed; client input cannot select a URL,
// project, query, or recipient. Never send mail or change a provider resource during monitoring.
const project='https://trdzsdclscuwwmxnepyt.supabase.co',ref='trdzsdclscuwwmxnepyt';
const management='https://api.supabase.com',resend='https://api.resend.com';
const number=v=>Number.isSafeInteger(v)&&v>=0?v:null;
const date=v=>typeof v==='string'&&Number.isFinite(Date.parse(v))?new Date(v).toISOString():null;
const errorCode=r=>r.status===401||r.status===403?'access_denied':r.status===429?'rate_limited':r.status===0?'unreachable':r.status===404?'api_unavailable':'invalid_response';

export function emailMetric(result,key,requestedStart,periodEnd,checkedAt){
 const d=result.data,totals=d?.totals,actualStart=date(d?.start_date),actualEnd=date(d?.end_date);
 if(!result.ok||d?.object!=='metrics'||number(totals?.sent)===null||!actualStart||!actualEnd||Date.parse(actualEnd)<Date.parse(actualStart))return null;
 const partial=Date.parse(actualStart)>Date.parse(requestedStart)+1000;
 return {metric:key,used:totals.sent,quota:null,checked_at:checkedAt,period_start:actualStart,period_end:periodEnd,
  source:'resend_metrics',coverage:partial?'partial':'complete',observed_until:actualEnd,
  delivered:number(totals.delivered),failed:number(totals.failed),bounced:number(totals.bounced)};
}
export function functionTotals(results){
 let count=0,clientErrors=0,serverErrors=0;
 for(const r of results){
  if(!r.ok||!Array.isArray(r.data?.result)||r.data.result.length>1000)return null;
  for(const row of r.data.result){
   if(number(row.count)===null||number(row.client_err_count)===null||number(row.server_err_count)===null)return null;
   count+=row.count;clientErrors+=row.client_err_count;serverErrors+=row.server_err_count;
  }
 }
 return number(count)===null?null:{count,client_errors:clientErrors,server_errors:serverErrors};
}
export function makeHandler({serviceKey,resendKey,managementToken,tokenExpiresAt,fetcher=fetch,clock=()=>new Date(),pause=ms=>new Promise(resolve=>setTimeout(resolve,ms))}) {
 return async req=>{
  if(req.method!=='POST')return new Response(null,{status:405});
  const proof=req.headers.get('x-paw-monitor');
  if(!serviceKey||!proof||!/^[0-9a-f]{64}$/.test(proof))return new Response(null,{status:403});
  const deadline=AbortSignal.timeout(50000);
  async function request(url,key,body,local=false){
   if(!key)return {ok:false,status:0,data:null};
   try{
    const r=await fetcher(url,{method:body?'POST':'GET',headers:{Authorization:'Bearer '+key,...(local?{apikey:key}:{}),...(body?{'Content-Type':'application/json'}:{})},
     ...(body?{body:JSON.stringify(body)}:{}),redirect:'error',signal:AbortSignal.any([deadline,AbortSignal.timeout(12000)])});
    // Error bodies may contain provider diagnostics; never persist or return them.
    if(!r.ok){await r.body?.cancel();return {ok:false,status:r.status,data:null};}
    const reader=r.body?.getReader();let size=0,chunks=[];
    if(reader)while(true){const item=await reader.read();if(item.done)break;size+=item.value.length;if(size>1048576){await reader.cancel();return {ok:false,status:502,data:null};}chunks.push(item.value);}
    const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length;}
    return {ok:true,status:r.status,data:JSON.parse(new TextDecoder().decode(bytes))};
   }catch{return {ok:false,status:0,data:null};}
  }
  async function rpc(name,body){return request(project+'/rest/v1/rpc/'+name,serviceKey,body,true);}
  const start=await rpc('paw_monitor_begin',{proof});
  if(!start.ok)return new Response(null,{status:503});
  if(!start.data)return new Response(null,{status:403});
  const run=start.data,now=clock(),checkedAt=now.toISOString();
  const day=new Date(Date.UTC(now.getUTCFullYear(),now.getUTCMonth(),now.getUTCDate()));
  const month=new Date(Date.UTC(now.getUTCFullYear(),now.getUTCMonth(),1));
  const tomorrow=new Date(day.getTime()+86400000).toISOString(),nextMonth=new Date(Date.UTC(now.getUTCFullYear(),now.getUTCMonth()+1,1)).toISOString();
  const metricsUrl=from=>resend+'/emails/metrics?'+new URLSearchParams({start_date:from.toISOString(),end_date:checkedAt,metrics:'sent,delivered,bounced,failed'});
  // Resend's account-wide rate limit is shared with SMTP integrations and other clients.
  // Three small reads per cycle, spaced apart, never a burst or a retry storm.
  async function readEmail(){const daily=await request(metricsUrl(day),resendKey);await pause(1100);
   const monthly=await request(metricsUrl(month),resendKey);await pause(1100);
   return [daily,monthly,await request(resend+'/domains?limit=100',resendKey)];}
  const [email,health,bucket,functions]=await Promise.all([
   readEmail(),
   request(management+'/v1/projects/'+ref+'/health?services=auth&services=db&services=rest&services=storage',managementToken),
   request(project+'/storage/v1/bucket/paw-social-saves',serviceKey,undefined,true),
   request(management+'/v1/projects/'+ref+'/functions',managementToken)
  ]);
  const [daily,monthly,domains]=email;
  const snapshot={schema:1,checked_at:checkedAt,token_expires_at:date(tokenExpiresAt),metrics:[],
   errors:{egress:'billing_api_unavailable',cached_egress:'billing_api_unavailable'},services:[],email:{},storage:{},functions:{}};
  for(const [r,key,from,to] of [[daily,'emails_daily',day,tomorrow],[monthly,'emails_monthly',month,nextMonth]]){
   const m=emailMetric(r,key,from.toISOString(),to,checkedAt);
   if(m){snapshot.metrics.push(m);snapshot.email[key==='emails_daily'?'daily':'monthly']={sent:m.used,delivered:m.delivered,failed:m.failed,bounced:m.bounced,coverage:m.coverage};}
   else snapshot.errors[key]=errorCode(r);
  }
  const domain=domains.ok&&Array.isArray(domains.data?.data)?domains.data.data.find(d=>d.name==='pawspatch.xyz'):null;
  snapshot.email.domain_verified=domain?.status==='verified'&&domain?.capabilities?.sending==='enabled';
  snapshot.email.api_available=domains.ok&&domain!==null;
  snapshot.email.error=!domains.ok?errorCode(domains):!domain?'domain_missing':null;
  snapshot.storage={api_available:bucket.ok,private_bucket:bucket.data?.id==='paw-social-saves'&&bucket.data?.public===false,
   file_limit:number(bucket.data?.file_size_limit),error:bucket.ok?null:errorCode(bucket)};
  const names=['auth','db','rest','storage'];
  for(const name of names){const h=health.ok&&Array.isArray(health.data)?health.data.find(s=>s.name===name):null;
   snapshot.services.push({name,healthy:typeof h?.healthy==='boolean'?h.healthy:null,error:!health.ok?errorCode(health):!h?'invalid_response':null});}
  const deployed=functions.ok&&Array.isArray(functions.data)?functions.data:null;
  if(deployed&&deployed.length<=20&&deployed.every(f=>/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(f.id)&&typeof f.status==='string')){
   // Bounded parallelism; this project currently has five functions. Never report a partial sum as a full count.
   const batches=[];for(let i=0;i<deployed.length;i+=5)batches.push(deployed.slice(i,i+5));
   const reads=[];for(const batch of batches)reads.push(...await Promise.all(batch.map(f=>request(management+'/v0/projects/'+ref+'/analytics/endpoints/functions.req-stats?'+new URLSearchParams({interval:'1day',function_id:f.id}),managementToken))));
   const totals=functionTotals(reads);
   snapshot.functions={deployed:deployed.length,active:deployed.filter(f=>f.status==='ACTIVE').length,...(totals??{}),window_hours:24};
   if(totals)snapshot.metrics.push({metric:'functions_daily',used:totals.count,quota:null,checked_at:checkedAt,period_start:new Date(now.getTime()-86400000).toISOString(),period_end:null,source:'supabase_requests_24h',coverage:'complete',observed_until:checkedAt});
   else snapshot.errors.functions_daily=reads.some(r=>!r.ok)?errorCode(reads.find(r=>!r.ok)):'invalid_response';
  }else snapshot.errors.functions_daily=functions.ok?'invalid_response':errorCode(functions);
  const saved=await rpc('paw_monitor_store',{run,payload:snapshot});
  return saved.ok&&saved.data===true?Response.json({stored:true},{headers:{'Cache-Control':'no-store'}}):new Response(null,{status:503});
 };
}
