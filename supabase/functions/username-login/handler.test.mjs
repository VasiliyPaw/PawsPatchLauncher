import test from "node:test";
import assert from "node:assert/strict";
import { makeHandler } from "./handler.mjs";
const url="https://trdzsdclscuwwmxnepyt.supabase.co";
const request=(body={username:"Player_1",password:"secret6"})=>new Request(url+"/functions/v1/username-login",{method:"POST",body:JSON.stringify(body),headers:{"x-forwarded-for":"203.0.113.4"}});
function fixture(status=200,auth={access_token:"access",refresh_token:"refresh",expires_in:3600,user:{id:"uid",email:"private@example.invalid",user_metadata:{secret:"hidden"}}},target={status:"ok",email:"private@example.invalid"}){
 const calls=[]; const handler=makeHandler({url,serviceKey:"server-only",publicKey:"public",fetcher:async(u,o)=>{
  calls.push({u,o});return new Response(JSON.stringify(calls.length===1?target:auth),{status:calls.length===1?200:status});
 }});return {calls,handler};
}
test("username resolved privately and password checked by Auth, sanitized response",async()=>{
 const {calls,handler}=fixture();const response=await handler(request());assert.equal(response.status,200);
 const result=await response.json();assert.equal(result.access_token,"access");assert.equal(result.user.email,"private@example.invalid");
 assert.equal(result.user.user_metadata,undefined);assert.ok(!JSON.stringify(result).includes("server-only"));
 assert.equal(calls[0].o.headers.Authorization,"Bearer server-only");assert.equal(calls[1].o.headers.apikey,"public");
 assert.deepEqual(JSON.parse(calls[1].o.body),{email:"private@example.invalid",password:"secret6"});
 assert.match(JSON.parse(calls[0].o.body).client_bucket,/^[0-9a-f]{64}$/);
 assert.equal(calls[0].o.redirect,"error");assert.equal(response.headers.get("Cache-Control"),"no-store");
});
test("unknown user still runs password Auth and never returns resolved email",async()=>{
 const {calls,handler}=fixture(400,{error_code:"invalid_credentials",message:"private server detail"},{status:"ok",email:"missing-foo@example.invalid"});
 const result=await handler(request());assert.equal(result.status,401);assert.equal(calls.length,2);
 assert.deepEqual(await result.json(),{status:"invalid_credentials"});
});
test("rate limit stops before Auth",async()=>{
 const {calls,handler}=fixture(200,{}, {status:"rate_limit"});const response=await handler(request());
 assert.equal(response.status,429);assert.equal(calls.length,1);
});
test("correct password unconfirmed email gets actionable safe code",async()=>{
 const {handler}=fixture(400,{error_code:"email_not_confirmed",message:"hidden"});
 assert.deepEqual(await (await handler(request())).json(),{status:"email_not_confirmed"});
});
test("bad, oversized, injected usernames and passwords never hit backend",async()=>{
 for(const body of [{username:"",password:"x"},{username:"a@x.com",password:"x"},{username:"../player",password:"x"},{username:"a".repeat(25),password:"x"},{username:"valid",password:"a".repeat(129)},{username:"valid",password:""}]){
  const {handler,calls}=fixture();assert.equal((await handler(request(body))).status,400);assert.equal(calls.length,0);
 }
 const {handler,calls}=fixture();assert.equal((await handler(request({username:"x".repeat(3000),password:"x"}))).status,400);assert.equal(calls.length,0);
});
test("non POST and wrong configured origin rejected without network",async()=>{
 const {handler,calls}=fixture();assert.equal((await handler(new Request(url))).status,405);assert.equal(calls.length,0);
 const bad=makeHandler({url:"https://evil.invalid",serviceKey:"s",publicKey:"p"});assert.equal((await bad(request())).status,503);
});
test("upstream errors are not disclosed",async()=>{
 const {handler}=fixture(500,{message:"secret"});assert.deepEqual(await (await handler(request())).json(),{status:"service_unavailable"});
 const broken=makeHandler({url,serviceKey:"s",publicKey:"p",fetcher:async()=>{throw Error("secret");}});
 assert.deepEqual(await (await broken(request())).json(),{status:"service_unavailable"});
});
