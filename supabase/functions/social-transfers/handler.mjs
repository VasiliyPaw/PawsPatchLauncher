const project="https://trdzsdclscuwwmxnepyt.supabase.co";
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const limit=20971520;
class Fault extends Error { constructor(code,http=400){super(code);this.code=code;this.http=http;} }
const reply=(status,http=200)=>new Response(JSON.stringify({status}),{status:http,headers:{"Content-Type":"application/json","Cache-Control":"no-store","X-Content-Type-Options":"nosniff"}});
export async function boundedBytes(response,max=limit) {
 if(Number(response.headers.get("content-length"))>max)throw new Fault("invalid_save",413);
 const reader=response.body?.getReader();if(!reader)throw new Fault("invalid_save");
 const chunks=[];let length=0;
 try{for(;;){const {done,value}=await reader.read();if(done)break;length+=value.length;if(length>max)throw new Fault("invalid_save",413);chunks.push(value);}}
 finally{await reader.cancel();}
 const bytes=new Uint8Array(length);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length;}return bytes;
}
export async function validateSave(o,bytes) {
 if(!o || o.kind!=="save" || !uuid.test(o.id) || !uuid.test(o.sender_id) || !uuid.test(o.recipient_id)
 || !Number.isSafeInteger(o.file_size) || o.file_size<16 || o.file_size>limit || bytes.length!==o.file_size
 || typeof o.file_name!=="string" || o.file_name.length>128 || !/^[^./\\:*?"<>|\p{Cc}\p{Cf}][^/\\:*?"<>|\p{Cc}\p{Cf}]*\.rsg$/iu.test(o.file_name)
 || /^(con|prn|aux|nul|com[0-9¹²³]|lpt[0-9¹²³]) *\./i.test(o.file_name)
 || !/^[0-9a-f]{64}$/i.test(o.sha256) || new TextDecoder().decode(bytes.subarray(0,4))!=="TGCK")throw new Fault("invalid_save");
 const hash=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",bytes)),n=>n.toString(16).padStart(2,"0")).join("");
 if(hash!==o.sha256.toLowerCase())throw new Fault("invalid_save");
}
export function makeHandler({url,serviceKey,publicKey,fetcher=fetch}) {
 async function call(path,options={}) {
  return fetcher(project+path,{...options,redirect:"error",signal:AbortSignal.timeout(120000)});
 }
 async function rpc(name,body) {
  const res=await call("/rest/v1/rpc/"+name,{method:"POST",headers:{apikey:serviceKey,Authorization:"Bearer "+serviceKey,"Content-Type":"application/json"},body:JSON.stringify(body)});
  if(!res.ok)throw new Fault("service_unavailable",503);
  // This SQL function returns void: PostgREST legitimately responds with an empty
  // successful body. Parsing it as JSON failed AFTER cleanup committed, making
  // the next transfer attempt appear offline and its retry work.
  if(name==="paw_transfer_cleaned"){await res.body?.cancel();return null;}
  return res.json();
 }
 async function storage(path,method="GET",body) {
  return call("/storage/v1/"+path,{method,headers:{apikey:serviceKey,Authorization:"Bearer "+serviceKey,"Content-Type":method==="DELETE"?"application/json":"application/octet-stream","x-upsert":"false"},body});
 }
 async function cleanup() {
  const paths=await rpc("paw_transfer_cleanup_candidates",{});
  if(!Array.isArray(paths)||paths.length>20||paths.some(p=>!new RegExp("^[0-9a-f-]{36}/[0-9a-f-]{36}\\.rsg$","i").test(p)))throw new Fault("service_unavailable",503);
  if(paths.length){const res=await storage("object/paw-social-saves","DELETE",JSON.stringify({prefixes:paths}));if(res.ok)await rpc("paw_transfer_cleaned",{paths});}
 }
 return async req=>{
  try {
   if(url!==project || !serviceKey || !publicKey)throw new Fault("service_unavailable",503);
   if(req.method!=="POST")return reply("invalid_request",405);
   const auth=req.headers.get("authorization")||"",launcher=req.headers.get("x-paw-launcher")||"";
   if(!/^Bearer [A-Za-z0-9_.-]{20,16000}$/.test(auth)||!uuid.test(launcher))throw new Fault("unauthorized",401);
   const authRes=await call("/auth/v1/user",{headers:{apikey:publicKey,Authorization:auth}});
   if(authRes.status>=500)throw new Fault("service_unavailable",503);
   if(!authRes.ok)throw new Fault("unauthorized",401);
   const user=await authRes.json();let session;
   try{session=JSON.parse(atob(auth.slice(7).split(".")[1].replaceAll("-","+").replaceAll("_","/"))).session_id;}catch{throw new Fault("unauthorized",401);}
   if(!uuid.test(user.id)||!uuid.test(session)||!user.email_confirmed_at)throw new Fault("unauthorized",401);
   if(await rpc("paw_account_session_active",{player:user.id,session,launcher})!==true)throw new Fault("session_replaced",401);
   const input=new URL(req.url);const action=input.searchParams.get("action"),offer_id=input.searchParams.get("offer_id");
   if(action==="cleanup"){await cleanup();return reply("ok");}
   if(!["upload","download"].includes(action)||!uuid.test(offer_id||""))throw new Fault("invalid_request");
   const context={player:user.id,session,launcher,offer_id,action};
   async function authorize() {
    const result=await rpc("paw_transfer_authorize",context);
    if(result?.status!=="ok")throw new Fault(result?.status==="session_replaced"?"session_replaced":"offer_unavailable",403);
    if(result.object_path!==result.offer?.sender_id+"/"+offer_id+".rsg" || result.offer?.id!==offer_id)throw new Fault("service_unavailable",503);
    return result;
   }
   const permission=await authorize();const o=permission.offer,path="object/paw-social-saves/"+permission.object_path;
   if(action==="upload"){
    await cleanup();
    const bytes=await boundedBytes(req);await validateSave(o,bytes);await authorize();
    const sent=await storage(path,"POST",bytes);
    if(!sent.ok) {
     // A lost upload response may leave the exact immutable object already present.
     const prior=await storage(path);if(!prior.ok)throw new Fault("service_unavailable",503);
     await validateSave(o,await boundedBytes(prior));
    }
    await authorize();
    const ready=await rpc("paw_transfer_ready",{player:user.id,session,launcher,offer_id});
    if(ready?.status!=="ok")throw new Fault("offer_unavailable",403);
    return reply("ok");
   }
   const download=await storage(path);if(!download.ok)throw new Fault("service_unavailable",503);
   const bytes=await boundedBytes(download);await validateSave(o,bytes);
   await authorize(); // Revoke blocks/takeovers that happened during storage fetch.
   return new Response(bytes,{headers:{"Content-Type":"application/octet-stream","Content-Length":String(bytes.length),"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"}});
  } catch(error) {return reply(error instanceof Fault?error.code:"service_unavailable",error instanceof Fault?error.http:503);}
 };
}
