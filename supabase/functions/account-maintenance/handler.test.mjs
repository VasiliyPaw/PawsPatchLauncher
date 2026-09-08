import test from 'node:test';
import assert from 'node:assert/strict';
import {makeHandler} from './handler.mjs';
const id='10000000-0000-0000-0000-000000000002',proof='a'.repeat(64),origin='https://trdzsdclscuwwmxnepyt.supabase.co';
function fixture(overrides={}){
 const calls=[];const handler=makeHandler({url:origin,serviceKey:'TEST-SERVER',fetcher:async(url,init)=>{
  const path=new URL(url).pathname;const body=JSON.parse(init.body);calls.push({path,body,method:init.method});
  if(overrides[path])return overrides[path](body);
  if(path.endsWith('paw_maintenance_authorize'))return Response.json(true);
  if(path.endsWith('paw_deletion_candidates'))return Response.json([{id,saves:[id+'/20000000-0000-0000-0000-000000000001.rsg']}]);
  return Response.json({});
 }});return {calls,run:headers=>handler(new Request(origin,{method:'POST',headers:headers??{'x-paw-maintenance':proof}}))};
}
test('untrusted caller without scheduler proof cannot read candidates',async()=>{const f=fixture();assert.equal((await f.run({})).status,403);assert.equal(f.calls.length,0);});
test('forged well-shaped proof rejected by database',async()=>{const f=fixture({'/rest/v1/rpc/paw_maintenance_authorize':()=>Response.json(false)});assert.equal((await f.run()).status,403);assert.equal(f.calls.length,1);});
test('cleanup deletes only due candidates; storage before Auth',async()=>{const f=fixture();const result=await f.run();assert.equal(result.status,200);const del=f.calls.filter(c=>c.method==='DELETE');assert.deepEqual(del.map(c=>c.path),['/storage/v1/object/paw-social-saves','/storage/v1/object/paw-avatars','/auth/v1/admin/users/'+id]);assert.deepEqual(del[2].body,{should_soft_delete:false});assert.equal(f.calls.at(-1).body.succeeded,true);});
test('storage failure leaves Auth and reports retry',async()=>{const f=fixture({'/storage/v1/object/paw-social-saves':()=>Response.json({}, {status:503})});assert.equal((await f.run()).status,503);assert.ok(!f.calls.some(c=>c.path.includes('/auth/')));assert.equal(f.calls.at(-1).body.succeeded,false);});
test('invalid candidate path cannot be deleted',async()=>{const f=fixture({'/rest/v1/rpc/paw_deletion_candidates':()=>Response.json([{id,saves:['../foreign']}])});assert.equal((await f.run()).status,503);assert.ok(!f.calls.some(c=>c.method==='DELETE'));assert.equal(f.calls.at(-1).body.succeeded,false);});
test('no pending deletions performs no destructive calls',async()=>{const f=fixture({'/rest/v1/rpc/paw_deletion_candidates':()=>Response.json([])});assert.equal((await f.run()).status,200);assert.ok(!f.calls.some(c=>c.method==='DELETE'));});
