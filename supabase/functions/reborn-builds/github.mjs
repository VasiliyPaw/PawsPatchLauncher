const repositoryPattern=/^[A-Za-z0-9][A-Za-z0-9-]{0,38}\/[A-Za-z0-9_.-]{1,100}$/;
const positiveId=n=>Number.isSafeInteger(n)&&n>0;
export function githubBuildValid(build,repository,repositoryId){
 return typeof repository==='string'&&repositoryPattern.test(repository)&&positiveId(repositoryId)
  &&build.download_provider==='github'&&build.github_repository===repository&&build.github_repository_id===repositoryId&&positiveId(build.github_asset_id);
}
export function signedGitHubUrl(raw,repositoryId,now){
 if(typeof raw!=='string'||raw.length>12000)throw Error('Invalid GitHub URL');
 const target=new URL(raw),expiry=target.searchParams.getAll('se');
 const expires=expiry.length===1?Date.parse(expiry[0]):NaN;
 if(target.protocol!=='https:'||target.hostname!=='release-assets.githubusercontent.com'||target.port||target.username||target.password||target.hash
  ||!new RegExp('^/github-production-release-asset/'+repositoryId+'/[A-Za-z0-9-]+$').test(target.pathname)
  ||target.searchParams.getAll('sig').length!==1||!target.searchParams.get('sig')||!Number.isFinite(expires)||expires<=now+15000)throw Error('Invalid GitHub URL');
 return {url:target.href,urlExpiresAt:expires};
}
export async function githubTicket({build,token,repository,repositoryId,fetcher,clock}){
 if(!token||!githubBuildValid(build,repository,repositoryId))throw Error('GitHub configuration unavailable');
 const api='https://api.github.com/repos/'+repository;
 async function get(path,accept='application/vnd.github+json'){
  return fetcher(api+path,{headers:{Authorization:'Bearer '+token,Accept:accept,'User-Agent':'PawsPatchLauncher-Reborn','X-GitHub-Api-Version':'2022-11-28'},
   redirect:'manual',signal:AbortSignal.timeout(10000)});
 }
 // Only api.github.com receives the repository credential. Never follow its redirect.
 const repo=await get('');
 if(repo.status!==200)throw Error('GitHub repository unavailable');
 const metadata=await repo.json();
 if(metadata.id!==repositoryId||metadata.full_name!==repository||metadata.private!==true)throw Error('GitHub repository mismatch');
 const path='/releases/assets/'+build.github_asset_id;
 const asset=await get(path);
 if(asset.status!==200)throw Error('GitHub asset unavailable');
 const item=await asset.json();
 if(item.id!==build.github_asset_id||item.state!=='uploaded'||item.size!==build.size||!/^.+\.zip$/i.test(item.name||'')
  ||typeof item.digest!=='string'||item.digest.toLowerCase()!=='sha256:'+build.sha256.toLowerCase())throw Error('GitHub asset mismatch');
 const download=await get(path+'?ticket='+clock(),'application/octet-stream');
 // GitHub may return a binary 200 instead of a redirect. Refuse to proxy a large archive.
 const location=download.headers.get('location');
 await download.body?.cancel();
 if(download.status!==302&&download.status!==307)throw Error('GitHub redirect unavailable');
 return signedGitHubUrl(location,repositoryId,clock());
}
