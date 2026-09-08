// Runs in Deno Edge and in Node's isolated, mocked tests. Never log bodies or tokens.
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const project = "https://trdzsdclscuwwmxnepyt.supabase.co";
const redirect = "https://paws-patch-email-confirmation.vasiliypaw.chatgpt.site/";
const maxAvatar = 204800;
class Fault extends Error { constructor(code, http = 400) { super(code); this.code = code; this.http = http; } }
const reply = (status, http = 200, data = {}) => new Response(JSON.stringify({status, ...data}), {
 status: http, headers: {"Content-Type":"application/json", "Cache-Control":"no-store", "X-Content-Type-Options":"nosniff"} });

async function boundedBody(req) {
 if (Number(req.headers.get("content-length")) > 285000) throw new Fault("avatar_too_large",413);
 const reader=req.body?.getReader(); if (!reader) throw new Fault("invalid_request");
 let size=0; const parts=[];
 try { for (;;) { const {done,value}=await reader.read(); if(done) break; size+=value.length;
  if(size>285000) throw new Fault("avatar_too_large",413); parts.push(value); }
 } finally { await reader.cancel(); }
 const all=new Uint8Array(size); let offset=0;
 for(const part of parts) { all.set(part,offset); offset+=part.length; }
 try { return JSON.parse(new TextDecoder().decode(all)); } catch { throw new Fault("invalid_request"); }
}
export function avatarBytes(value) {
 if(typeof value!=="string" || value.length>Math.ceil(maxAvatar/3)*4 ||
  !/^[A-Za-z0-9+/]+={0,2}$/.test(value)) throw new Fault("invalid_avatar");
 let raw; try { raw=atob(value); } catch { throw new Fault("invalid_avatar"); }
 const bytes=Uint8Array.from(raw,c=>c.charCodeAt(0));
 if(bytes.length<32 || bytes.length>maxAvatar || bytes[0]!==255 || bytes[1]!==216 ||
  bytes.at(-2)!==255 || bytes.at(-1)!==217) throw new Fault("invalid_avatar");
 // Accept only 8-bit baseline/progressive JPEG, exactly the launcher's normalized size.
 let position=2, valid=false;
 while(position+4<bytes.length) {
  if(bytes[position++]!==255) throw new Fault("invalid_avatar");
  while(bytes[position]===255) position++;
  const marker=bytes[position++];
  if(marker===0xda) break;
  const length=(bytes[position]<<8)|bytes[position+1];
  if(length<2 || position+length>bytes.length) throw new Fault("invalid_avatar");
  if(marker===0xc0 || marker===0xc2) {
   const height=(bytes[position+3]<<8)|bytes[position+4], width=(bytes[position+5]<<8)|bytes[position+6];
   if(length<8 || bytes[position+2]!==8 || width!==256 || height!==256) throw new Fault("invalid_avatar");
   valid=true;
  }
  position+=length;
 }
 if(!valid) throw new Fault("invalid_avatar");
 return bytes;
}
function sessionId(token) {
 try { const part=token.split(".")[1].replace(/-/g,"+").replace(/_/g,"/");
  const data=JSON.parse(atob(part.padEnd(Math.ceil(part.length/4)*4,"=")));
  return UUID.test(data.session_id) ? data.session_id : null;
 } catch { return null; }
}
// All privileged credentials come from the function runtime, never the desktop.
export function makeHandler({url, serviceKey, publicKey, fetcher=fetch}) {
 return async function handle(req) {
  if(req.method!=="POST") return reply("method_not_allowed",405);
  if(url!==project || !serviceKey || !publicKey) return reply("service_unavailable",503);
  let lease=null, player=null, freshToken=null, freshSession=null, commit=false, mutationStarted=false, uncertain=false;
  let resultData={};
  async function call(path, {method="GET", body, token, admin=false, raw=false}={}) {
   const headers={apikey:admin?serviceKey:publicKey, Authorization:"Bearer "+(admin?serviceKey:token)};
   if(body!==undefined) headers["Content-Type"]=raw?"image/jpeg":"application/json";
   if(raw) headers["x-upsert"]="true";
   return await fetcher(url+path, {method,headers,body:body===undefined?undefined:raw?body:JSON.stringify(body),
    redirect:"error",signal:AbortSignal.timeout(12000)});
  }
  async function rpc(name,body) {
   const response=await call("/rest/v1/rpc/"+name,{method:"POST",body,admin:true});
   if(!response.ok) throw new Fault("service_unavailable",503);
   return response.status===204 ? null : await response.json();
  }
  try {
   if(!req.headers.get("content-type")?.startsWith("application/json")) throw new Fault("invalid_request");
   const auth=req.headers.get("authorization")??"";
   if(!auth.startsWith("Bearer ") || auth.length>16400) throw new Fault("unauthorized",401);
   const token=auth.slice(7);
   // Do NOT trust decoded JWT claims alone. Auth verifies signature, expiry and live user first.
   const who=await call("/auth/v1/user",{token});
   if(!who.ok) throw new Fault(who.status>=500?"service_unavailable":"unauthorized",who.status>=500?503:401);
   const user=await who.json(); player=user.id;
   const session=sessionId(token);
   const launcher=req.headers.get("x-paw-launcher");
   if(!UUID.test(player) || !user.email_confirmed_at || !session) throw new Fault("unauthorized",401);
   if(!UUID.test(launcher??"") || !await rpc("paw_account_session_active",{player,session,launcher}))
    throw new Fault("session_replaced",401);
   const input=await boundedBody(req);
   const action=input?.action;
   if(!["email","password","avatar_get","friend_avatar_get","avatar_set","avatar_remove","delete"].includes(action)) throw new Fault("invalid_action");
   const allowed=await rpc("paw_account_action_allowed",{player,action,address:action==="email"?input.email:null});
   if(allowed!=="ok") throw new Fault(typeof allowed==="string"?allowed:"service_unavailable",403);
   const friendAvatar=action==="friend_avatar_get";
   const target=friendAvatar?input.target:player;
   async function canReadFriend() {
    return UUID.test(target??"") && target!==player && (await rpc("paw_friend_avatar_allowed",{player,session,launcher,target}))===true;
   }
   if(friendAvatar && !await canReadFriend()) throw new Fault("friend_required",403);
   const path=target+"/avatar.jpg";
   if(action==="avatar_get" || friendAvatar) {
    const response=await call("/storage/v1/object/authenticated/paw-avatars/"+path,{admin:true});
    // Storage uses either 400 + statusCode or 404 for a missing key.
    if(!response.ok) {
     const info=await response.json().catch(()=>({}));
     if(response.status===404 || info.statusCode==="404" || info.error==="not_found")
      return reply("ok",200,{avatar:null});
     throw new Fault("service_unavailable",503);
    }
    const declared=Number(response.headers.get("content-length"));
    if(declared>maxAvatar) throw new Fault("invalid_avatar");
    const bytes=new Uint8Array(await response.arrayBuffer());
    if(bytes.length>maxAvatar) throw new Fault("invalid_avatar");
    // A block/takeover while storage was loading must revoke the response too.
    if(friendAvatar && !await canReadFriend()) throw new Fault("friend_required",403);
    let binary=""; for(const byte of bytes) binary+=String.fromCharCode(byte);
    return reply("ok",200,{avatar:btoa(binary)});
   }
   let bytes;
   if(action==="avatar_set") bytes=avatarBytes(input.avatar);
   if(["email","password","delete"].includes(action)) {
    if(typeof input.current_password!=="string" || input.current_password.length<1 || input.current_password.length>128)
     throw new Fault("current_password_required");
   }
   if(action==="delete" && input.confirm!=="DELETE_MY_ACCOUNT") throw new Fault("confirmation_required");
   if(action==="email") {
    if(typeof input.email!=="string" || input.email.length>254 ||
     !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(input.email)) throw new Fault("invalid_email");
    if(user.email?.toLowerCase()===input.email.toLowerCase()) throw new Fault("same_email");
   }
   if(action==="password") {
    if(typeof input.password!=="string" || input.password.length<6 || input.password.length>128) throw new Fault("weak_password");
    if(input.password===input.current_password) throw new Fault("same_password");
   }
   const begin=await rpc("paw_begin_launcher_action",{player,session,launcher,action});
   if(begin.status!=="ok") throw new Fault(begin.status,409);
   lease=begin.lease;
   if(!UUID.test(lease)) throw new Fault("service_unavailable",503);
   if(["email","password","delete"].includes(action)) {
    const response=await call("/auth/v1/token?grant_type=password",{method:"POST",
     body:{email:user.email,password:input.current_password}});
    if(!response.ok) {
     if(response.status===429) throw new Fault("rate_limit",429);
     throw new Fault(response.status>=500?"service_unavailable":"invalid_credentials",response.status>=500?503:400);
    }
    const fresh=await response.json(); freshToken=fresh.access_token; freshSession=fresh;
    if(fresh.user?.id!==player || typeof freshToken!=="string") throw new Fault("unauthorized",401);
    if(action==="password" && (typeof fresh.refresh_token!=="string" || !Number.isFinite(fresh.expires_in) || fresh.expires_in<=0)) throw new Fault("service_unavailable",503);
   }
   if(action==="email" || action==="password") {
    const body=action==="email"?{email:input.email}:{password:input.password,current_password:input.current_password};
    mutationStarted=true; commit=true; // Uncertain transport outcome must not immediately permit another change.
    const response=await call("/auth/v1/user"+(action==="email"?"?redirect_to="+encodeURIComponent(redirect):""),
     {method:"PUT",token:freshToken,body});
    if(!response.ok) {
     // 5xx might follow a committed change; keep the reservation in that case.
     if(response.status>=500) throw new Fault("outcome_unknown",503);
     commit=false;
     const error=await response.json().catch(()=>({}));
     const known={email_exists:"email_unavailable",user_already_exists:"email_unavailable",weak_password:"weak_password",
      same_password:"same_password",reauthentication_needed:"reauthentication_needed",
      email_address_invalid:"invalid_email",over_email_send_rate_limit:"rate_limit"};
     throw new Fault(response.status===429?"rate_limit":known[error.error_code]??"service_error",400);
    }
    if(action==="password") {
     const updated=await response.json();
     if(updated.id!==player) throw new Fault("outcome_unknown",503);
     const replacement=sessionId(freshToken);
     if(!replacement || !await rpc("paw_rotate_launcher_session",{player,key:lease,session,launcher,replacement}))
      throw new Fault("outcome_unknown",503);
     // Auth revokes every session except the one changing the password. Return this new
     // user session to the same authenticated caller so Remember me keeps working.
     resultData={session:{access_token:freshSession.access_token,refresh_token:freshSession.refresh_token,
      expires_in:freshSession.expires_in,user:updated}};
    }
   } else if(action==="avatar_set") {
    mutationStarted=true;
    const response=await call("/storage/v1/object/paw-avatars/"+path,{method:"POST",body:bytes,admin:true,raw:true});
    if(!response.ok) throw new Fault("service_unavailable",503);
    commit=true;
   } else if(action==="delete") {
    // Reversible application deletion, not Auth's irreversible user removal.
    // Retain avatar privately for restoration; no peer can read a deleted profile.
    mutationStarted=true;
    if(!await rpc("paw_mark_account_deleting",{player,key:lease})) throw new Fault("account_busy",409);
    commit=true;
   } else {
    mutationStarted=true;
    const response=await call("/storage/v1/object/paw-avatars",{method:"DELETE",body:{prefixes:[path]},admin:true});
    if(!response.ok) throw new Fault("service_unavailable",503);
    commit=true;
   }
   await rpc("paw_finish_account_action",{player,key:lease,succeeded:commit}); lease=null;
   if(action==="password") freshToken=null; // This session now belongs to the launcher, not a disposable check.
   return reply("ok",200,resultData);
  } catch(error) {
   if(error instanceof Fault) { uncertain=error.code==="outcome_unknown"; return reply(error.code,error.http); }
   uncertain=mutationStarted;
   return reply(mutationStarted?"outcome_unknown":"service_unavailable",503);
  } finally {
   // Delete failure leaves deletion_pending set, denying subsequent avatar writes; retry is safe.
   if(lease && player && !uncertain) await rpc("paw_finish_account_action",{player,key:lease,succeeded:commit}).catch(()=>{});
   if(freshToken) await call("/auth/v1/logout?scope=local",{method:"POST",token:freshToken}).catch(()=>{});
  }
 };
}
