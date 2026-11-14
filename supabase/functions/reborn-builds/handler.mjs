import {githubTicket} from './github.mjs';
const project="https://trdzsdclscuwwmxnepyt.supabase.co";
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const reply=(data,http=200)=>Response.json(data,{status:http,headers:{"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"}});
class Fault extends Error{constructor(code,http=403){super(code);this.code=code;this.http=http;}}
export function makeHandler({url,serviceKey,publicKey,githubToken,githubRepository,githubRepositoryId,fetcher=fetch,clock=()=>Date.now()}){
 async function call(path,init){return fetcher(url+path,{...init,redirect:"error",signal:AbortSignal.timeout(10000)});}
 async function authorize(context,rpc="paw_reborn_authorize"){
  const res=await call("/rest/v1/rpc/"+rpc,{method:"POST",headers:{apikey:serviceKey,Authorization:"Bearer "+serviceKey,"Content-Type":"application/json"},body:JSON.stringify(context)});
  if(!res.ok)throw new Fault("service_unavailable",503);
  const data=await res.json();
  if(data?.status!=="ok")throw new Fault(["reborn_access_denied","reborn_unavailable","session_replaced"].includes(data?.status)?data.status:"service_unavailable",data?.status==="session_replaced"?401:403);
  return data;
 }
 return async req=>{
  try{
   if(url!==project||!serviceKey||!publicKey)throw new Fault("service_unavailable",503);
   if(req.method!=="POST")return reply({status:"invalid_request"},405);
   const auth=req.headers.get("authorization")||"",launcher=req.headers.get("x-paw-launcher")||"";
   if(!/^Bearer [A-Za-z0-9_.-]{20,16000}$/.test(auth)||!uuid.test(launcher))throw new Fault("unauthorized",401);
   const res=await call("/auth/v1/user",{headers:{apikey:publicKey,Authorization:auth}});
   if(!res.ok)throw new Fault(res.status>=500?"service_unavailable":"unauthorized",res.status>=500?503:401);
   const user=await res.json();let session;
   try{const part=auth.slice(7).split('.')[1].replaceAll('-','+').replaceAll('_','/');session=JSON.parse(atob(part.padEnd(Math.ceil(part.length/4)*4,'='))).session_id;}catch{throw new Fault("unauthorized",401);}
   if(!uuid.test(user.id)||!uuid.test(session)||!user.email_confirmed_at)throw new Fault("unauthorized",401);
   const query=new URL(req.url).searchParams,action=query.get("action"),channel=query.get("channel"),id=query.get("build_id"),v2=query.get('protocol')==='2';
   if(query.has('protocol')&&!v2)throw new Fault('invalid_request',400);
   const compatible=rows=>rows.filter(b=>v2||!b.download_provider||b.download_provider==='supabase');
   if(action!=="catalog"&&action!=="history"&&(action!=="download"||!['stable','beta'].includes(channel)||!uuid.test(id||"")))throw new Fault("invalid_request",400);
   if(action==="history"){
    const history=await authorize({player:user.id,session,launcher},"paw_reborn_history");
    if(!Array.isArray(history.releases)||history.releases.length>200)throw new Fault("service_unavailable",503);
    return reply({status:"ok",releases:compatible(history.releases)});
   }
   const context={player:user.id,session,launcher,selected_channel:action==="download"?channel:null,build_id:action==="download"?id:null};
   const permission=await authorize(context);
   if(action==="catalog"){
    if(!Array.isArray(permission.releases)||permission.releases.length>2)throw new Fault("service_unavailable",503);
    return reply({status:"ok",releases:compatible(permission.releases)});
   }
   const build=permission.release;
   if(build?.id!==id||build?.channel!==channel||!Number.isSafeInteger(build.size)||build.size<1||build.size>17179869184||!/^[0-9A-Fa-f]{64}$/.test(build.sha256))throw new Fault("service_unavailable",503);
   let target,urlExpiry;
   if(build.download_provider==='github'){
    if(!v2)throw new Fault('reborn_unavailable');
    const ticket=await githubTicket({build,token:githubToken,repository:githubRepository,repositoryId:githubRepositoryId,fetcher,clock});
    target=ticket.url;urlExpiry=ticket.urlExpiresAt;
   }else{
   if(build.download_provider&&build.download_provider!=='supabase')throw new Fault('service_unavailable',503);
   const path="/object/sign/paw-reborn-builds/"+channel+"/"+id+".zip";
   const signed=await call("/storage/v1"+path,{method:"POST",headers:{apikey:serviceKey,Authorization:"Bearer "+serviceKey,"Content-Type":"application/json"},body:JSON.stringify({expiresIn:120})});
   if(!signed.ok)throw new Fault("reborn_unavailable");
   const data=await signed.json();
   if(typeof data.signedURL!=="string"||!data.signedURL.startsWith(path+"?token=")||data.signedURL.length>12000)throw new Fault("service_unavailable",503);
   target=url+'/storage/v1'+data.signedURL;
   }
   const fresh=await authorize(context);
   if(['id','channel','sha256','size','executable','version','download_provider','github_repository','github_repository_id','github_asset_id'].some(key=>fresh.release?.[key]!==build[key]))throw new Fault("reborn_unavailable");
   if(urlExpiry&&urlExpiry<=clock()+15000)throw new Fault('reborn_unavailable');
   return reply({status:"ok",release:build,url:target,expires_at:new Date(Math.min(clock()+120000,urlExpiry||Infinity)).toISOString(),
    ...(urlExpiry?{ticket_version:2,url_expires_at:new Date(urlExpiry).toISOString()}:{} )});
  }catch(error){return reply({status:error instanceof Fault?error.code:"service_unavailable"},error instanceof Fault?error.http:503);}
 };
}
