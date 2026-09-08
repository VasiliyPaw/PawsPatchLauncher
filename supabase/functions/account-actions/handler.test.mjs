import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {makeHandler,avatarBytes} from "./handler.mjs";
const id="11111111-1111-4111-8111-111111111111", other="22222222-2222-4222-8222-222222222222";
const launcher="44444444-4444-4444-8444-444444444444";
const lease="33333333-3333-4333-8333-333333333333";
const freshToken="signed."+btoa(JSON.stringify({session_id:other}))+".verified-by-auth";
const token="signed."+btoa(JSON.stringify({session_id:lease}))+".verified-by-auth";
function fixture(overrides={}) {
 const calls=[];
 const handler=makeHandler({url:"https://trdzsdclscuwwmxnepyt.supabase.co",serviceKey:"TEST-SERVER-ONLY",publicKey:"TEST-PUBLIC",
 fetcher:async(url,init)=>{
  const path=new URL(url).pathname, body=typeof init.body==="string"?JSON.parse(init.body):init.body;
  calls.push({path,init,body});
  const result=overrides[path]; if(result) return result({path,init,body});
  const json=x=>Response.json(x);
  if(path==="/auth/v1/user") return json({id,email:"player@example.com",email_confirmed_at:"2026-01-01"});
  if(path.endsWith("paw_account_session_active")) return json(true);
  if(path.endsWith("paw_account_action_allowed")) return json("ok");
  if(path.endsWith("paw_begin_launcher_action")) return json({status:"ok",lease});
  if(path.endsWith("paw_rotate_launcher_session")) return json(true);
  if(path.endsWith("paw_mark_account_deleting")) return json(true);
  if(path.endsWith("paw_finish_account_action")) return new Response(null,{status:204});
  if(path==="/auth/v1/token") return json({user:{id},access_token:freshToken,refresh_token:"temporary-refresh",expires_in:3600});
  if(path.startsWith("/storage/v1/object/authenticated")) return Response.json({statusCode:"404",error:"not_found"},{status:400});
  return json({});
 }});
 return {calls,run:async(input,headers={})=>{
  const response=await handler(new Request("https://ignored.invalid/",{method:"POST",headers:{"Content-Type":"application/json","x-paw-launcher":launcher,"Authorization":"Bearer "+token,...headers},body:JSON.stringify(input)}));
  return {http:response.status,...await response.json()};
 },handler};
}
test("unauthenticated does not touch server or storage",async()=>{
 const f=fixture(); assert.equal((await f.run({action:"delete"},{Authorization:""})).status,"unauthorized"); assert.equal(f.calls.length,0);
});
test("unverified JWT rejected by Auth",async()=>{
 const f=fixture({"/auth/v1/user":()=>Response.json({}, {status:401})});
 assert.equal((await f.run({action:"avatar_get"})).status,"unauthorized"); assert.equal(f.calls.length,1);
});
test("revoked live session rejected even with user JWT",async()=>{
 const f=fixture({"/rest/v1/rpc/paw_account_session_active":()=>Response.json(false)});
 assert.equal((await f.run({action:"delete",confirm:"DELETE_MY_ACCOUNT",current_password:"secret"})).status,"session_replaced");
 assert.equal(f.calls.length,2);
});
test("deletion requires explicit marker",async()=>{
 const f=fixture(); assert.equal((await f.run({action:"delete",current_password:"secret"})).status,"confirmation_required");
 assert.ok(!f.calls.some(c=>c.path.includes("begin_launcher")));
});
for(const status of ['account_banned','email_banned','protected_account'])test(status+' denies sensitive action before Auth mutation',async()=>{
 const f=fixture({'/rest/v1/rpc/paw_account_action_allowed':()=>Response.json(status)});
 assert.equal((await f.run({action:'email',email:'blocked@example.test',current_password:'secret'})).status,status);
 assert.ok(!f.calls.some(c=>c.path.includes('/storage/')||c.path==='/auth/v1/token'||c.init.method==='PUT'));
});
test("wrong current password never marks or deletes",async()=>{
 const f=fixture({"/auth/v1/token":()=>Response.json({}, {status:400})});
 assert.equal((await f.run({action:"delete",confirm:"DELETE_MY_ACCOUNT",current_password:"wrong"})).status,"invalid_credentials");
 assert.ok(!f.calls.some(c=>c.path.includes("mark_account")||c.path.includes("/admin/")));
 assert.equal(f.calls.find(c=>c.path.endsWith("finish_account_action")).body.succeeded,false);
});
test("delete targets caller and preserves Auth/avatar for seven-day restoration",async()=>{
 const f=fixture();
 assert.equal((await f.run({action:"delete",player:other,confirm:"DELETE_MY_ACCOUNT",current_password:"secret"})).status,"ok");
 assert.ok(!f.calls.some(c=>c.path.includes('/storage/')||c.path.includes('/admin/users/')));
 assert.deepEqual(f.calls.find(c=>c.path.endsWith('paw_mark_account_deleting')).body,{player:id,key:lease});
 assert.ok(!JSON.stringify(f.calls).includes(other));
 assert.ok(f.calls.some(c=>c.path==="/auth/v1/logout"&&c.init.headers.Authorization==="Bearer "+freshToken));
});
test("failed deletion reservation never purges Auth",async()=>{
 const f=fixture({"/rest/v1/rpc/paw_mark_account_deleting":()=>Response.json(false)});
 assert.notEqual((await f.run({action:"delete",confirm:"DELETE_MY_ACCOUNT",current_password:"secret"})).status,"ok");
 assert.ok(!f.calls.some(c=>c.path.includes("/admin/")));
});
test("second authenticated user cannot be substituted by reauth",async()=>{
 const f=fixture({"/auth/v1/token":()=>Response.json({user:{id:other},access_token:"wrong-user"})});
 assert.equal((await f.run({action:"delete",confirm:"DELETE_MY_ACCOUNT",current_password:"secret"})).status,"unauthorized");
 assert.ok(!f.calls.some(c=>c.path.includes("/admin/")));
});
for(const action of ["email","password"]) {
 const input={action,email:"new@example.com",password:"new-secret",current_password:"old-secret"};
 test(action+" server cooldown prevents auth mutation",async()=>{
  const f=fixture({"/rest/v1/rpc/paw_begin_launcher_action":()=>Response.json({status:action+"_cooldown"})});
  assert.equal((await f.run(input)).status,action+"_cooldown");
  assert.ok(!f.calls.some(c=>c.init.method==="PUT"||c.path==="/auth/v1/token"));
 });
 test(action+" known rejection releases reserved cooldown",async()=>{
  const f=fixture({"/auth/v1/user":({init})=>init.method==="PUT"?Response.json({error_code:"weak_password"},{status:422}):Response.json({id,email:"player@example.com",email_confirmed_at:"yes"})});
  assert.notEqual((await f.run(input)).status,"ok");
  assert.equal(f.calls.find(c=>c.path.endsWith("finish_account_action")).body.succeeded,false);
 });
 test(action+" uncertain update keeps cooldown",async()=>{
  const f=fixture({"/auth/v1/user":({init})=>{if(init.method==="PUT")throw new Error("transport");return Response.json({id,email:"player@example.com",email_confirmed_at:"yes"});}});
  assert.equal((await f.run(input)).status,"outcome_unknown");
  assert.ok(!f.calls.some(c=>c.path.endsWith("finish_account_action")), "uncertain mutation released its durable reservation");
 });
 test(action+" successful mutation commits cooldown",async()=>{
  const f=fixture(); assert.equal((await f.run(input)).status,"ok");
  assert.equal(f.calls.find(c=>c.path.endsWith("finish_account_action")).body.succeeded,true);
 });
}
test("avatar missing is a valid empty state",async()=>{
 const f=fixture(); assert.equal((await f.run({action:"avatar_get"})).avatar,null);
});
test("friend avatar requires explicit true permission, never arbitrary target paths",async()=>{
 for(const allowed of [false,null,{},"true"]) {
  const f=fixture({"/rest/v1/rpc/paw_friend_avatar_allowed":()=>Response.json(allowed)});
  assert.equal((await f.run({action:"friend_avatar_get",target:other})).status,"friend_required");
  assert.ok(!f.calls.some(c=>c.path.startsWith("/storage/")));
 }
 for(const target of [id,"../avatar.jpg",null]) {
  const f=fixture();assert.equal((await f.run({action:"friend_avatar_get",target})).status,"friend_required");
  assert.ok(!f.calls.some(c=>c.path.startsWith("/storage/")));
 }
});
test("friend avatar only reads fixed JPEG and rechecks friendship after download",async()=>{
 let checks=0;
 const f=fixture({"/rest/v1/rpc/paw_friend_avatar_allowed":()=>{checks++;return Response.json(true);},
  ["/storage/v1/object/authenticated/paw-avatars/"+other+"/avatar.jpg"]:()=>new Response(new Uint8Array([255,216,255,217]))});
 const result=await f.run({action:"friend_avatar_get",target:other});
 assert.equal(result.status,"ok");assert.equal(result.avatar,"/9j/2Q==");assert.equal(checks,2);
 assert.ok(!f.calls.some(c=>c.path.includes("begin_launcher")||c.init.method==="DELETE"));
 assert.deepEqual(f.calls.find(c=>c.path.endsWith("paw_friend_avatar_allowed")).body,{player:id,session:lease,launcher,target:other});
});
test("block or takeover during friend avatar download discards the bytes",async()=>{
 let checks=0;
 const f=fixture({"/rest/v1/rpc/paw_friend_avatar_allowed":()=>Response.json(++checks===1),
  ["/storage/v1/object/authenticated/paw-avatars/"+other+"/avatar.jpg"]:()=>new Response(new Uint8Array([1,2,3]))});
 const result=await f.run({action:"friend_avatar_get",target:other});
 assert.equal(result.status,"friend_required");assert.equal(result.avatar,undefined);
});
test("oversized request rejected without privileged write",async()=>{
 const f=fixture(); assert.equal((await f.run({action:"avatar_set",avatar:"x".repeat(285000)})).http,413);
 assert.ok(!f.calls.some(c=>c.path.includes("begin_launcher")));
});
test("avatar rejects SVG, large content and wrong dimensions",()=>{
 for(const input of [btoa("<svg/>"),"a".repeat(300000),btoa("not an image")]) assert.throws(()=>avatarBytes(input));
});
test("avatar removal targets only own known object",async()=>{
 const f=fixture(); assert.equal((await f.run({action:"avatar_remove",path:other+"/file"})).status,"ok");
 assert.deepEqual(f.calls.find(c=>c.path==="/storage/v1/object/paw-avatars").body,{prefixes:[id+"/avatar.jpg"]});
});
test("deletion pending stops avatar mutations",async()=>{
 const f=fixture({"/rest/v1/rpc/paw_begin_launcher_action":()=>Response.json({status:"account_deletion_pending"})});
 assert.equal((await f.run({action:"avatar_remove"})).status,"account_deletion_pending");
 assert.ok(!f.calls.some(c=>c.path.startsWith("/storage/")));
});
test("unsupported method rejected",async()=>{
 const f=fixture(); assert.equal((await f.handler(new Request("https://example.com"))).status,405); assert.equal(f.calls.length,0);
});

test("missing launcher header fails closed before privileged action",async()=>{
 const f=fixture(); assert.equal((await f.run({action:"avatar_remove"},{"x-paw-launcher":""})).status,"session_replaced");
 assert.ok(!f.calls.some(c=>c.path.includes("begin_launcher")||c.path.includes("/storage/")));
});
test("launcher identity comes from header, never user body",async()=>{
 const f=fixture(); await f.run({action:"avatar_remove",launcher:other});
 assert.equal(f.calls.find(c=>c.path.endsWith("paw_account_session_active")).body.launcher,launcher);
 assert.equal(f.calls.find(c=>c.path.endsWith("paw_begin_launcher_action")).body.launcher,launcher);
});
test("takeover between initial check and reserved mutation is rejected",async()=>{
 const f=fixture({"/rest/v1/rpc/paw_begin_launcher_action":()=>Response.json({status:"session_replaced"})});
 assert.equal((await f.run({action:"password",password:"new-secret",current_password:"old-secret"})).status,"session_replaced");
 assert.ok(!f.calls.some(c=>c.path==="/auth/v1/token"||c.init.method==="PUT"));
});
test("password rotation retains only current instance and reserved owner",async()=>{
 const f=fixture(); await f.run({action:"password",password:"new-secret",current_password:"old-secret"});
 assert.deepEqual(f.calls.find(c=>c.path.endsWith("paw_rotate_launcher_session")).body,
  {player:id,key:lease,session:lease,launcher,replacement:other});
});
test("failed password session transfer is not reported as success",async()=>{
 const f=fixture({"/rest/v1/rpc/paw_rotate_launcher_session":()=>Response.json(false)});
 const result=await f.run({action:"password",password:"new-secret",current_password:"old-secret"});
 assert.equal(result.status,"outcome_unknown");assert.equal(result.session,undefined);
});
test("password change hands the retained session to the same caller",async()=>{
 const f=fixture(); const result=await f.run({action:"password",password:"new-secret",current_password:"old-secret"});
 assert.equal(result.session.user.id,id);
 assert.equal(result.session.access_token,freshToken);
 assert.equal(result.session.refresh_token,"temporary-refresh");
 assert.ok(!f.calls.some(c=>c.path==="/auth/v1/logout"));
 assert.ok(!JSON.stringify(result).includes("TEST-SERVER-ONLY"));
});
test("WPF-normalized avatar is accepted and uploads to only the caller path",{skip:!process.env.PAW_AVATAR_FIXTURE},async()=>{
 const bytes=readFileSync(process.env.PAW_AVATAR_FIXTURE);
 assert.equal(avatarBytes(bytes.toString("base64")).length,bytes.length);
 const f=fixture(); assert.equal((await f.run({action:"avatar_set",avatar:bytes.toString("base64")})).status,"ok");
 const upload=f.calls.find(c=>c.path.endsWith("/paw-avatars/"+id+"/avatar.jpg"));
 assert.equal(upload.init.headers["Content-Type"],"image/jpeg");
 assert.equal(upload.init.headers["x-upsert"],"true");
 assert.equal(upload.body.length,bytes.length);
});
