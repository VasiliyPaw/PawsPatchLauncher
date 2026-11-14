import assert from 'node:assert/strict';
import {makeHandler} from './handler.mjs';
const project='https://trdzsdclscuwwmxnepyt.supabase.co',repository='Owner/Private',repositoryId=1458192487;
const player='10000000-0000-4000-8000-000000000001',session='20000000-0000-4000-8000-000000000002',launcher='30000000-0000-4000-8000-000000000003',id='40000000-0000-4000-8000-000000000004';
const bearer='Bearer header.'+Buffer.from(JSON.stringify({session_id:session})).toString('base64url')+'.signature';
const now=Date.parse('2026-11-14T00:00:00Z');
const build={id,channel:'stable',version:'0.23.0',size:140733219,sha256:'A'.repeat(64),executable:'KohanReborn-Menu.exe',notes:{},published_at:'2026-11-14T00:00:00Z',download_provider:'github',github_repository:repository,github_repository_id:repositoryId,github_asset_id:748818121};
let count=0;const check=(ok,why)=>{assert.ok(ok,why);count++;};
const cdn=(expiry=now+3600000)=>`https://release-assets.githubusercontent.com/github-production-release-asset/${repositoryId}/abcd-1234?se=${encodeURIComponent(new Date(expiry).toISOString())}&sig=fixture`;
async function scenario(options={}){
 let reads=0;const calls=[];const selected={...build,...options.build};
 const fetcher=async(endpoint,init)=>{
  calls.push(endpoint);const target=new URL(endpoint);
  if(target.origin===project){
   check(init.redirect==='error','Supabase redirects disabled');
   if(target.pathname.endsWith('/user'))return Response.json({id:player,email_confirmed_at:'2026-11-01'});
   reads++;check(init.headers.Authorization==='Bearer server-service','only server credential calls authorization RPC');
   if(options.denied||options.revoked&&reads===2)return Response.json({status:'reborn_access_denied'});
   const fresh=reads===2&&options.changed?{...selected,...options.changed}:selected;
   return Response.json({status:'ok',release:fresh,releases:[selected]});
  }
  check(target.origin==='https://api.github.com','CDN is never fetched by server');
  check(init.redirect==='manual'&&init.headers.Authorization==='Bearer repository-read-secret','GitHub credential only reaches API with manual redirects');
  if(target.pathname==='/repos/'+repository)return Response.json({id:options.repoId||repositoryId,full_name:repository,private:!options.public});
  check(target.pathname==='/repos/'+repository+'/releases/assets/'+build.github_asset_id,'pinned repository and exact asset');
  if(init.headers.Accept==='application/vnd.github+json')return Response.json({id:build.github_asset_id,size:build.size,digest:'sha256:'+build.sha256,name:'archive.zip',state:'uploaded',...options.asset});
  if(options.binary)return new Response('binary bytes must never be proxied');
  if(options.failed)return new Response('private provider diagnostic',{status:403});
  return new Response(null,{status:options.redirectStatus||302,headers:{location:options.location||cdn(options.expiry)}});
 };
 const handler=makeHandler({url:project,serviceKey:'server-service',publicKey:'public-key',githubToken:options.noToken?undefined:'repository-read-secret',githubRepository:repository,githubRepositoryId:repositoryId,fetcher,clock:()=>now});
 const action=options.action||'download';
 const response=await handler(new Request(`${project}/functions/v1/reborn-builds?action=${action}${options.legacy?'':'&protocol=2'}&channel=stable&build_id=${id}`,{method:'POST',headers:{authorization:bearer,'x-paw-launcher':launcher}}));
 const data=await response.json();
 check(!JSON.stringify(data).includes('repository-read-secret')&&!JSON.stringify(data).includes('server-service')&&!JSON.stringify(data).includes('provider diagnostic'),'no provider secrets returned');
 check(response.headers.get('cache-control')==='no-store','no ticket caching');
 return {response,data,calls,reads};
}
let r=await scenario();check(r.response.status===200&&r.data.ticket_version===2&&r.reads===2,'authorized v2 download rechecks live role');
check(r.data.expires_at==='2026-11-14T00:02:00.000Z'&&r.data.url_expires_at==='2026-11-14T01:00:00.000Z','CDN expiry is not the short start window');
r=await scenario({expiry:now+45000});check(r.response.status===200&&r.data.expires_at===r.data.url_expires_at,'start window bounded by upstream expiry');
for(const action of ['catalog','history']){
 r=await scenario({action});check(r.data.releases.length===1&&!r.calls.some(p=>p.startsWith('https://api.github.com')),'v2 metadata read does not issue a ticket');
 r=await scenario({action,legacy:true});check(r.data.releases.length===0,'legacy clients do not see unsupported provider');
}
for(const options of [{legacy:true},{denied:true},{revoked:true},{noToken:true},{public:true},{repoId:1},{binary:true},{failed:true},{redirectStatus:301},
 {asset:{id:1}},{asset:{size:1}},{asset:{digest:'sha256:'+'B'.repeat(64)}},{asset:{state:'new'}},{asset:{name:'archive.exe'}},
 {build:{github_repository:'Other/Private'}},{build:{github_repository_id:1}},{build:{github_asset_id:null}},{build:{download_provider:'arbitrary'}},
 {changed:{github_asset_id:1}},{changed:{github_repository_id:1}},{changed:{download_provider:'supabase'}},{changed:{sha256:'B'.repeat(64)}},
 {expiry:now-1},{expiry:now+5000},...[
  cdn().replace('https:','http:'),cdn().replace('.com/','.com:444/'),cdn().replace('release-assets.githubusercontent.com','evil.invalid'),
  cdn().replace('https://','https://user@'),cdn()+'#fragment',cdn().replace(String(repositoryId),'2'),cdn()+'&se=2026-11-15',cdn().replace('&sig=fixture',''),cdn()+'&sig=second'
 ].map(location=>({location}))]){
 r=await scenario(options);check(r.response.status>=400&&!r.data.url,'invalid ticket withheld: '+JSON.stringify(options));
 if(options.denied||options.legacy||options.noToken)check(!r.calls.some(p=>p.startsWith('https://api.github.com')),'unauthorized/unsupported/unconfigured request never reaches GitHub');
}
console.log('REBORN GITHUB EDGE PASS',count,': private repository, exact digest/size/asset, live role, legacy isolation, manual redirects and independent URL expiry');
