from context import *
import urllib.request,urllib.error,urllib.parse,http.client,ssl

def unchanged():
 b=read(P/'baseline.json');assert git('rev-parse','HEAD')==b['localHead'];assert subprocess.check_output(['git','diff','--cached','--binary'],cwd=REPO)==(P/'staged-before.patch').read_bytes()
def head():return git('ls-remote','origin','refs/heads/main').split()[0]
def gate():
 unchanged();assert read(O/'verification.json')['passed'];assert read(O/'catalog-qa/result.json')['passed']
 for mod in['arcane','vanilla','immortals']:assert read(O/(mod+'-installer-result.json'))['passed']
 for p in read(O/'packages.json'):
  f=Path(read(O/'package-audit.json')[p['id']]['path']);assert sha(f)==p['sha256']and f.stat().st_size==p['size']
 for group in['arcane','pure']:
  b=read(O/group/'bundle.json');assert sha(b['path'])==b['sha256']
 assert read(HD/'verification.json')['allSourcePixelsPreserved'];print('ALL_BETA_RELEASE_GATE_PASS',flush=True)
def commit_files(parent,root,paths,message,label):
 assert head()==parent,'Remote moved; refresh scoped files first';e=env();index=O/(label+'-index');assert not index.exists();e['GIT_INDEX_FILE']=str(index)
 def g(*a):return subprocess.check_output(['git',*a],cwd=REPO,env=e,text=True).strip()
 pathsfile=O/(label+'-paths');pathsfile.write_bytes(('\0'.join(paths)+'\0').encode());g('read-tree',parent);g('--work-tree='+str(root),'add','--pathspec-from-file='+str(pathsfile),'--pathspec-file-nul');tree=g('write-tree');body=O/(label+'-commit.txt');body.write_text(message+'\n');commit=g('commit-tree',tree,'-p',parent,'-F',str(body));changed=g('diff-tree','--no-commit-id','--name-only','-r',commit).splitlines();assert set(changed)==set(paths);assert head()==parent;g('push','origin',commit+':refs/heads/main');unchanged();return commit
def source():
 gate();git('fetch','--no-tags','origin','main');parent=git('rev-parse','FETCH_HEAD');paths=read(O/'source-scope.json')['files']
 for rel in paths:
  current=subprocess.run(['git','show',parent+':'+rel],cwd=REPO,capture_output=True)
  if(S/rel).exists():assert current.returncode==0 and normalize(current.stdout)==normalize((S/rel).read_bytes()),'Concurrent source change: '+rel
  else:assert current.returncode!=0,'Concurrent new path: '+rel
 commit=commit_files(parent,O/'source-public',paths,'Preserve full-resolution HD icons and faction HUD frames across all patch betas','source');write(O/'source-publication.json',dict(commit=commit,parent=parent,files={p:sha(O/'source-public'/p)for p in paths}));print('SOURCE_PUBLIC',commit,flush=True)
_token=None
def credential():
 global _token
 if _token is None:
  _token=os.environ.get('GH_TOKEN')
  if not _token:
   q=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',cwd=REPO,capture_output=True,text=True,check=True);_token=dict(line.split('=',1)for line in q.stdout.splitlines()if'='in line).get('password')
  assert _token,'Missing configured GitHub credential'
 return _token
def request(url,method='GET',data=None):
 if isinstance(data,dict):data=json.dumps(data).encode()
 headers={'Authorization':'Bearer '+credential(),'User-Agent':'PawsFullResolutionRelease','Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','Content-Type':'application/json'}
 with urllib.request.urlopen(urllib.request.Request(url,headers=headers,data=data,method=method),timeout=120)as r:return json.load(r)
def ci(phase):
 commit=read(O/('source-publication.json'if phase=='source'else'publication.json'))['commit'if phase=='source'else'catalogCommit'];rows=request(API+'/actions/runs?head_sha='+commit+'&per_page=25')['workflow_runs'];rows=[r for r in rows if r['name']=='Build and test'and r['head_sha']==commit]
 if not rows:print('CI_PENDING',phase);return
 r=max(rows,key=lambda r:r['run_number']);result={k:r[k]for k in['id','head_sha','status','conclusion','html_url']};write(O/(phase+'-ci.json'),result);print('CI_STATUS',json.dumps(result),flush=True)
 if r['status']=='completed'and r['conclusion']!='success':raise RuntimeError('CI failed: '+r['html_url'])
def upload(release,path):
 digest='sha256:'+sha(path).lower();existing=next((a for a in release['assets']if a['name']==path.name),None)
 if existing:assert existing['digest']==digest and existing['size']==path.stat().st_size;return
 url=urllib.parse.urlsplit(release['upload_url'].split('{',1)[0]+'?name='+urllib.parse.quote(path.name));assert url.hostname=='uploads.github.com'and url.scheme=='https'
 conn=http.client.HTTPSConnection(url.hostname,timeout=120,context=ssl.create_default_context());conn.putrequest('POST',url.path+'?'+url.query)
 for k,v in{'Authorization':'Bearer '+credential(),'User-Agent':'PawsFullResolutionRelease','Accept':'application/vnd.github+json','Content-Type':'application/octet-stream','Content-Length':str(path.stat().st_size)}.items():conn.putheader(k,v)
 conn.endheaders();sent=0;milestone=0
 with path.open('rb')as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):
   conn.send(b);sent+=len(b)
   if sent//(128*1024*1024)>milestone:
    milestone=sent//(128*1024*1024);write(O/'upload-progress.json',dict(file=path.name,sent=sent,total=path.stat().st_size));print('UPLOAD_PROGRESS',path.name,sent,flush=True)
 response=conn.getresponse();raw=response.read();assert response.status==201,(response.status,raw[:1000]);asset=json.loads(raw);conn.close();assert asset['size']==path.stat().st_size and asset['digest']==digest;print('ASSET_VERIFIED',path.name,asset['size'],flush=True)
def stage():
 gate();assert read(O/'source-ci.json')['conclusion']=='success';commit=read(O/'source-publication.json')['commit']
 for group,v,tag,name in[('arcane',ARC,'patch-'+ARC,'Arcane Wars'),('pure',PURE,'patch-pure-'+PURE,'Vanilla / Immortals')]:
  try:r=request(API+'/releases/tags/'+tag)
  except urllib.error.HTTPError as error:
   if error.code!=404:raise
   r=next((r for r in request(API+'/releases?per_page=100')if r['tag_name']==tag),None)
   if r is None:r=request(API+'/releases','POST',dict(tag_name=tag,target_commitish=commit,name='Paw’s Patch '+v+' — '+name,body=(O/group/'release-notes.md').read_text('utf-8'),draft=True,prerelease=True,make_latest='false'))
  assert r['target_commitish']==commit and r['prerelease']
  assert r['draft'],'Unexpected already-public release; use readback'
  assets=sorted((O/group/'assets').glob('*.zip'));assert len(assets)==(5 if group=='arcane'else 4)
  for path in assets:upload(r,path)
  r=request(API+'/releases/'+str(r['id']));assert len(r['assets'])==len(assets);write(O/group/'draft.json',r);print('DRAFT_READY',group,flush=True)
def release():
 gate();assert read(O/'source-ci.json')['conclusion']=='success'
 for group,v,tag in[('arcane',ARC,'patch-'+ARC),('pure',PURE,'patch-pure-'+PURE)]:
  r=request(API+'/releases/'+str(read(O/group/'draft.json')['id']));assert r['target_commitish']==read(O/'source-publication.json')['commit']and r['prerelease']
  if r['draft']:r=request(API+'/releases/'+str(r['id']),'PATCH',dict(draft=False,make_latest='false'))
  remote={a['name']:a for a in r['assets']};proof={}
  for p in sorted((O/group/'assets').glob('*.zip')):
   a=remote[p.name];assert a['size']==p.stat().st_size and a['digest']=='sha256:'+sha(p).lower();h=hashlib.sha256();n=0;milestone=0
   with urllib.request.urlopen(urllib.request.Request(a['browser_download_url'],headers={'User-Agent':'PawsFullResolutionRelease'}),timeout=120)as response:
    for b in iter(lambda:response.read(4*1024*1024),b''):
     h.update(b);n+=len(b)
     if n//(128*1024*1024)>milestone:
      milestone=n//(128*1024*1024);write(O/'download-progress.json',dict(file=p.name,bytes=n,total=p.stat().st_size));print('DOWNLOAD_PROGRESS',p.name,n,flush=True)
   assert n==p.stat().st_size and h.hexdigest().upper()==sha(p);proof[p.name]=dict(size=n,sha256=h.hexdigest().upper());write(O/group/'public-assets-progress.json',proof);print('PUBLIC_DOWNLOAD_VERIFIED',p.name,flush=True)
  write(O/group/'public-assets.json',dict(url=r['html_url'],tag=tag,assets=proof));print('PUBLIC_ASSETS_PASS',group,flush=True)
def promote():
 gate()
 for group,count in[('arcane',5),('pure',4)]:assert len(read(O/group/'public-assets.json')['assets'])==count
 import catalogs
 parent=snapshot();catalogs.catalogs()
 # Revalidate selection over the latest public parent before the scoped push.
 print(run([sys.executable,P/'catalog_check.py'],O/'catalog-recheck.log'),flush=True)
 allowed=read(O/'scope.json')['allowed'];assert len(allowed)==4
 commit=commit_files(parent,O/'signed',allowed,'Publish full-resolution HD UI in Arcane beta.4 and Vanilla/Immortals beta.8','catalog');write(O/'publication.json',dict(sourceCommit=read(O/'source-publication.json')['commit'],catalogCommit=commit,baseline=parent,versions=dict(arcane=ARC,pure=PURE)));print('ALL_BETA_CATALOGS_PUBLIC',commit,flush=True)
def readback():
 publication=read(O/'publication.json');commit=publication['catalogCommit']
 for rel in FILES:
  data=fetch(RAW.replace('/main/','/'+commit+'/')+rel);assert normalize(data)==normalize((O/'signed'/rel).read_bytes()),rel
  if rel in FILES[:6]:verify(json.loads(data),key())
  if rel not in read(O/'scope.json')['allowed']:assert normalize(data)==normalize((O/'before'/rel).read_bytes()),rel
 for prefix in['v2','v3']:
  f=verify(json.loads(fetch(RAW+f'feed/{prefix}/beta.json')),key());assert f==verify(read(O/'signed'/f'feed/{prefix}/beta.json'),key())
  for p in read(O/'packages.json'):assert next(q for q in f['packages']if q['id']==p['id'])==p
 publication['passed']=True;write(O/'readback.json',publication);unchanged();print('PUBLIC_READBACK_PASS',flush=True)
if __name__=='__main__':
 action=sys.argv[1]
 if action.endswith('-ci'):ci(action.split('-')[0])
 else:globals()[action]()
