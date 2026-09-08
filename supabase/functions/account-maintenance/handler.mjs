// Scheduled cleanup only. Credentials stay in the function runtime; the scheduler
// proof is generated and stored in a private database table, never in a launcher.
export function makeHandler({url,serviceKey,fetcher=fetch}) {
 const project='https://trdzsdclscuwwmxnepyt.supabase.co';
 const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
 return async req=>{
  if(req.method!=='POST')return new Response(null,{status:405});
  const proof=req.headers.get('x-paw-maintenance');
  if(url!==project||!serviceKey||!proof||!/^[0-9a-f]{64}$/.test(proof))return new Response(null,{status:403});
  async function call(path,body,method='POST'){
   const result=await fetcher(project+path,{method,headers:{apikey:serviceKey,Authorization:'Bearer '+serviceKey,'Content-Type':'application/json'},
    body:JSON.stringify(body),redirect:'error',signal:AbortSignal.timeout(15000)});
   if(!result.ok)throw new Error('maintenance_failed');return result.status===204?null:await result.json();
  }
  const rpc=(name,body={})=>call('/rest/v1/rpc/'+name,body);
  let authorized=false,ok=true,removed=0;
  try{
   if(await rpc('paw_maintenance_authorize',{proof})!==true)return new Response(null,{status:403});authorized=true;
   const users=await rpc('paw_deletion_candidates');
   if(!Array.isArray(users)||users.length>5)throw new Error('invalid_candidates');
   for(const user of users){
    if(!uuid.test(user.id)||!Array.isArray(user.saves)||user.saves.some(p=>!new RegExp('^[0-9a-f-]{36}/[0-9a-f-]{36}\\.rsg$','i').test(p)))throw new Error('invalid_candidate');
    try{
     // Storage cleanup first. On failure retain the Auth account and retry safely.
     for(let i=0;i<user.saves.length;i+=100)await call('/storage/v1/object/paw-social-saves',{prefixes:user.saves.slice(i,i+100)},'DELETE');
     await call('/storage/v1/object/paw-avatars',{prefixes:[user.id+'/avatar.jpg']},'DELETE');
     await call('/auth/v1/admin/users/'+user.id,{should_soft_delete:false},'DELETE');removed++;
    }catch{ok=false;}
   }
   return Response.json({status:ok?'ok':'retry_pending',removed},{status:ok?200:503,headers:{'Cache-Control':'no-store'}});
  }catch{ok=false;return Response.json({status:'retry_pending'},{status:503});}
  finally{if(authorized)await rpc('paw_maintenance_finished',{succeeded:ok}).catch(()=>{});}
 };
}
