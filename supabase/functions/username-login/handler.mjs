const origin="https://trdzsdclscuwwmxnepyt.supabase.co";
const reply=(status,http=400,session={})=>new Response(JSON.stringify({status,...session}),{status:http,headers:{"Content-Type":"application/json","Cache-Control":"no-store"}});
export function makeHandler({url,serviceKey,publicKey,fetcher=fetch}) {
 return async req=>{
  try {
   if(req.method!=="POST")return reply("invalid_request",405);
   if(url!==origin||!serviceKey||!publicKey)return reply("service_unavailable",503);
   const reader=req.body?.getReader();if(!reader)return reply("invalid_credentials");let size=0;const chunks=[];
   try {for(;;){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>2048)return reply("invalid_credentials");chunks.push(value);}}finally{await reader.cancel();}
   const body=new Uint8Array(size);let offset=0;for(const c of chunks){body.set(c,offset);offset+=c.length;}
   let input;try{input=JSON.parse(new TextDecoder().decode(body));}catch{return reply("invalid_credentials");}
   if(typeof input.username!=="string"||!/^[A-Za-zА-Яа-яЁё0-9][A-Za-zА-Яа-яЁё0-9_.-]{2,23}$/.test(input.username)
    ||typeof input.password!=="string"||input.password.length<1||input.password.length>128)return reply("invalid_credentials");
   const ip=(req.headers.get("x-forwarded-for")||"unknown").split(",")[0].trim().slice(0,128);
   const client_bucket=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(ip))),b=>b.toString(16).padStart(2,"0")).join("");
   const common={method:"POST",redirect:"error",signal:AbortSignal.timeout(15000)};
   const target=await fetcher(origin+"/rest/v1/rpc/paw_username_login_target",{...common,headers:{apikey:serviceKey,Authorization:"Bearer "+serviceKey,"Content-Type":"application/json"},body:JSON.stringify({candidate:input.username,client_bucket})});
   if(!target.ok)return reply("service_unavailable",503);
   const result=await target.json();if(result.status==="rate_limit")return reply("rate_limit",429);
   if(result.status!=="ok"||typeof result.email!=="string")return reply("invalid_credentials",401);
   const auth=await fetcher(origin+"/auth/v1/token?grant_type=password",{...common,signal:AbortSignal.timeout(15000),headers:{apikey:publicKey,"Content-Type":"application/json"},
    body:JSON.stringify({email:result.email,password:input.password})});
   const text=await auth.text();if(text.length>65536)return reply("service_unavailable",503);
   let session;try{session=JSON.parse(text);}catch{return reply("service_unavailable",503);}
   if(!auth.ok)return reply(auth.status===429?"rate_limit":session.error_code==="email_not_confirmed"?"email_not_confirmed":auth.status>=500?"service_unavailable":"invalid_credentials",auth.status===429?429:auth.status>=500?503:401);
   if(!session.access_token||!session.refresh_token||!session.user?.id)return reply("service_unavailable",503);
   return reply("ok",200,{access_token:session.access_token,refresh_token:session.refresh_token,expires_in:session.expires_in,
    expires_at:session.expires_at,token_type:"bearer",user:{id:session.user.id,email:session.user.email}});
  }catch{return reply("service_unavailable",503);}
 };
}
