import test from "node:test";
import assert from "node:assert/strict";
import { makeHandler, validateSave, boundedBytes } from "./handler.mjs";
const player="00000000-0000-4000-a000-000000000001", peer="00000000-0000-4000-a000-000000000002";
const session="00000000-0000-4000-a000-000000000003",launcher="00000000-0000-4000-a000-000000000004",id="00000000-0000-4000-a000-000000000005";
const url="https://trdzsdclscuwwmxnepyt.supabase.co";
const token=Buffer.from('{"alg":"test"}').toString("base64url")+"."+Buffer.from(JSON.stringify({session_id:session,sub:peer})).toString("base64url")+".fixture";
const bytes=new Uint8Array(16);bytes.set(new TextEncoder().encode("TGCK"));
const hash=Buffer.from(await crypto.subtle.digest("SHA-256",bytes)).toString("hex");
const offer={id,sender_id:player,recipient_id:peer,kind:"save",file_name:"Тест.rsg",file_size:16,sha256:hash,state:"uploading"};
const json=x=>new Response(JSON.stringify(x),{headers:{"Content-Type":"application/json"}});
function fixture({active=true,auth=200,denyAt=0,storeFailure=false,corrupt=false,readyFail=false,cleanup=false,cleanupStatus=204}={}) {
 let checks=0,cleaned=false;const calls=[];
 const handler=makeHandler({url,serviceKey:"fixture-service",publicKey:"fixture-public",fetcher:async(address,options)=>{
  assert.equal(new URL(address).origin,url);assert.equal(options.redirect,"error");calls.push({address,options});
  if(address.endsWith("/auth/v1/user"))return auth===200?json({id:player,email_confirmed_at:"2026-09-08"}):new Response("",{status:auth});
  const payload=typeof options.body==="string"?JSON.parse(options.body):{};
  if(address.includes("/rest/")){
   assert.equal(options.headers.Authorization,"Bearer fixture-service");
   if(address.endsWith("paw_account_session_active")){assert.equal(payload.player,player);assert.equal(payload.session,session);return json(active);}
   if(address.endsWith("paw_transfer_authorize")){checks++;return json(denyAt&&checks>=denyAt?{status:"offer_unavailable"}:{status:"ok",offer,object_path:player+"/"+id+".rsg"});}
   if(address.endsWith("paw_transfer_cleanup_candidates"))return json(cleanup&&!cleaned?[peer+"/"+id+".rsg"]:[]);
   if(address.endsWith("paw_transfer_cleaned")){cleaned=cleanupStatus<300;return new Response(null,{status:cleanupStatus});}
   if(address.endsWith("paw_transfer_ready"))return json({status:readyFail?"offer_unavailable":"ok"});
   throw new Error("Unexpected RPC");
  }
  if(options.method==="DELETE")return json([]);
  if(options.method==="POST")return storeFailure?new Response(JSON.stringify({error:"duplicate"}),{status:409}):json({Key:"private"});
  return new Response(corrupt?new Uint8Array(16):bytes,{headers:{"Content-Type":"application/octet-stream"}});
 }});
 const request=(action="upload",body=bytes)=>new Request(url+"/functions/v1/social-transfers?action="+action+"&offer_id="+id,
  {method:"POST",headers:{Authorization:"Bearer "+token,"x-paw-launcher":launcher},body});
 return {handler,request,calls};
}
test("valid upload authenticates verified identity and immutable path",async()=>{
 const f=fixture();const response=await f.handler(f.request());
 assert.equal((await response.json()).status,"ok");
 assert.equal(f.calls.filter(c=>c.address.endsWith("paw_transfer_ready")).length,1);
 assert(f.calls.some(c=>c.address.endsWith("paw-social-saves/"+player+"/"+id+".rsg")));
});
test("successful void cleanup does not fail every next save attempt",async()=>{
 const f=fixture({cleanup:true});
 for(const action of ["cleanup","upload","cleanup","upload"]){
  const response=await f.handler(f.request(action));
  assert.equal(response.status,200,action+" after terminal save cleanup");
  assert.equal((await response.json()).status,"ok");
 }
 assert.equal(f.calls.filter(c=>c.address.endsWith("paw_transfer_cleaned")).length,1);
});
test("void cleanup accepts empty HTTP 200 too",async()=>{
 const f=fixture({cleanup:true,cleanupStatus:200});
 assert.equal((await f.handler(f.request("cleanup"))).status,200);
});
test("failed cleanup RPC is still a real service error",async()=>{
 const f=fixture({cleanup:true,cleanupStatus:503});
 assert.equal((await f.handler(f.request("cleanup"))).status,503);
});
for(const [label,options,status] of [["anonymous",{auth:401},"unauthorized"],["auth outage",{auth:503},"service_unavailable"],
 ["stale launcher",{active:false},"session_replaced"],["truthy forged active",{active:"true"},"session_replaced"],
 ["outsider",{denyAt:1},"offer_unavailable"],["block while uploading",{denyAt:3},"offer_unavailable"],
 ["block at ready",{readyFail:true},"offer_unavailable"]])
 test(label,async()=>{const f=fixture(options);const response=await f.handler(f.request());assert.equal((await response.json()).status,status);});
test("lost upload response reuses exact existing object",async()=>{const f=fixture({storeFailure:true});assert.equal((await (await f.handler(f.request())).json()).status,"ok");});
test("different object cannot be overwritten by retry",async()=>{const f=fixture({storeFailure:true,corrupt:true});assert.equal((await (await f.handler(f.request())).json()).status,"invalid_save");assert(!f.calls.some(c=>c.address.endsWith("paw_transfer_ready")));});
test("download rechecks access after storage read",async()=>{const f=fixture({denyAt:2});const response=await f.handler(f.request("download",null));assert.equal(response.status,403);assert.equal((await response.json()).status,"offer_unavailable");});
test("download returns only verified binary, without private URLs or keys",async()=>{const f=fixture();const response=await f.handler(f.request("download",null));assert.deepEqual(new Uint8Array(await response.arrayBuffer()),bytes);assert.equal(response.headers.get("Cache-Control"),"no-store");});
for(const bad of ["../evil.rsg","evil.exe","CON.rsg","x:evil.rsg","x\\evil.rsg","hidden\u202e.rsg"])
 test("reject name "+JSON.stringify(bad),async()=>assert.rejects(()=>validateSave({...offer,file_name:bad},bytes)));
test("bound upload before allocation",async()=>assert.rejects(()=>boundedBytes(new Response(bytes,{headers:{"Content-Length":"20971521"}}))));
test("hash and header checked",async()=>{await assert.rejects(()=>validateSave({...offer,sha256:"0".repeat(64)},bytes));await assert.rejects(()=>validateSave(offer,new Uint8Array(16)));});
test("missing launcher header stops before storage",async()=>{const f=fixture();const request=f.request();request.headers.delete("x-paw-launcher");assert.equal((await (await f.handler(request)).json()).status,"unauthorized");assert.equal(f.calls.length,0);});
