from context import *
import urllib.error,urllib.parse,http.client,ssl,time
def credential():
 q=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',cwd=REPO,capture_output=True,text=True,env=env(),check=True);v=dict(s.split('=',1)for s in q.stdout.splitlines()if '='in s);assert v.get('password');return v['password']
def request(url,method='GET',data=None):
 if isinstance(data,dict):data=encode(data)
 h={'Authorization':'Bearer '+credential(),'User-Agent':'PawsArcaneBeta7Release','Accept':'application/vnd.github+json','Content-Type':'application/json','X-GitHub-Api-Version':'2022-11-28'}
 with urllib.request.urlopen(urllib.request.Request(url,headers=h,data=data,method=method),timeout=90)as r:return json.load(r)
def head():return git('ls-remote','origin','refs/heads/main').split()[0]
def gate():
 unchanged();v=read(O/'verification.json');assert v['passed'];assert read(O/'qa/result.json')['passed'];assert read(O/'helpers/build-report.json')['passed'];assert read(O/'native-all-closure.json')['allOwnedClosed']
 from packages import validate
 for p in read(O/'packages.json'):validate(Path(read(O/'package-audit.json')[p['id']]['path']),p)
 b=read(O/'bundle.json');assert sha(b['path'])==b['sha256'];assert len(list((O/'assets').glob('*.zip')))==5
def commit_files(parent,root,paths,msg,label):
 unchanged();assert head()==parent,'Remote moved; refresh scoped parent before retry';e=env();index=O/(label+'-index');assert not index.exists();e['GIT_INDEX_FILE']=str(index)
 def g(*a):
  r=subprocess.run(['git',*map(str,a)],cwd=REPO,env=e,capture_output=True,text=True,encoding='utf-8');assert r.returncode==0,r.stderr[-2000:];return r.stdout.strip()
 pathfile=O/(label+'-paths');pathfile.write_bytes(('\0'.join(paths)+'\0').encode());g('read-tree',parent);g('--work-tree='+str(root),'add','--pathspec-from-file='+str(pathfile),'--pathspec-file-nul');tree=g('write-tree');body=O/(label+'-message.txt');body.write_text(msg+'\n',encoding='utf-8');c=g('commit-tree',tree,'-p',parent,'-F',body);changed=g('diff-tree','--no-commit-id','--name-only','-r',c).splitlines();assert changed and set(changed)<=set(paths);assert head()==parent;g('push','origin',c+':refs/heads/main');unchanged();return c
def source():
 gate();git('fetch','--no-tags','origin','main');parent=git('rev-parse','FETCH_HEAD');base=read(P/'baseline.json')['publicHead'];paths=read(O/'source-scope.json')['files']
 for rel in paths:
  a=subprocess.run(['git','show',parent+':'+rel],cwd=REPO,capture_output=True);b=subprocess.run(['git','show',base+':'+rel],cwd=REPO,capture_output=True);assert a.returncode==b.returncode and a.stdout.replace(b'\r\n',b'\n')==b.stdout.replace(b'\r\n',b'\n'),'Concurrent source change: '+rel
 c=commit_files(parent,S,paths,'Prepare Arcane Wars beta.7 bridge, AI and water fixes','source');write(O/'source-publication.json',dict(commit=c,parent=parent,files={p:sha(S/p)for p in paths}));print('SOURCE_PUBLIC',c,flush=True)
def ci(phase):
 c=read(O/('source-publication.json'if phase=='source'else'publication.json'))['commit'if phase=='source'else'catalogCommit'];rows=request(API+'/actions/runs?head_sha='+c+'&per_page=25')['workflow_runs'];rows=[r for r in rows if r['name']=='Build and test'and r['head_sha']==c]
 if not rows:print('CI_PENDING',phase);return
 r=max(rows,key=lambda r:r['run_number']);result={k:r[k]for k in['id','head_sha','status','conclusion','html_url']};write(O/(phase+'-ci.json'),result);print('CI_STATUS',json.dumps(result),flush=True)
 if r['status']=='completed'and r['conclusion']!='success':raise RuntimeError('CI failed: '+r['html_url'])
def upload(release,path):
 digest='sha256:'+sha(path).lower();old=next((a for a in release['assets']if a['name']==path.name),None)
 if old:assert old['digest']==digest and old['size']==path.stat().st_size;return
 u=urllib.parse.urlsplit(release['upload_url'].split('{')[0]+'?name='+urllib.parse.quote(path.name));assert u.scheme=='https'and u.hostname=='uploads.github.com';conn=http.client.HTTPSConnection(u.hostname,timeout=120,context=ssl.create_default_context());conn.putrequest('POST',u.path+'?'+u.query)
 for k,v in{'Authorization':'Bearer '+credential(),'User-Agent':'PawsArcaneBeta7Release','Content-Type':'application/octet-stream','Content-Length':str(path.stat().st_size)}.items():conn.putheader(k,v)
 conn.endheaders()
 with path.open('rb')as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):conn.send(b)
 response=conn.getresponse();raw=response.read();assert response.status==201,(response.status,raw[:500]);a=json.loads(raw);conn.close();assert a['size']==path.stat().st_size and a['digest']==digest;print('ASSET_VERIFIED',path.name,a['size'],flush=True)
def stage():
 gate();assert read(O/'source-ci.json')['conclusion']=='success';c=read(O/'source-publication.json')['commit']
 try:r=request(API+'/releases/tags/'+TAG)
 except urllib.error.HTTPError as e:
  if e.code!=404:raise
  r=next((r for r in request(API+'/releases?per_page=100')if r['tag_name']==TAG),None)
  if r is None:r=request(API+'/releases','POST',dict(tag_name=TAG,target_commitish=c,name='Paw’s Patch '+V+' — Arcane Wars',body=(O/'release-notes.md').read_text('utf-8'),draft=True,prerelease=True,make_latest='false'))
 assert r['target_commitish']==c and r['prerelease']and r['draft'],'Unexpected existing public release'
 for f in sorted((O/'assets').glob('*.zip')):upload(r,f)
 r=request(API+'/releases/'+str(r['id']));assert len(r['assets'])==5;write(O/'draft.json',r);print('DRAFT_READY',r['id'],flush=True)
def release():
 gate();assert read(O/'source-ci.json')['conclusion']=='success';r=request(API+'/releases/'+str(read(O/'draft.json')['id']));assert r['target_commitish']==read(O/'source-publication.json')['commit']and r['prerelease']
 if r['draft']:r=request(API+'/releases/'+str(r['id']),'PATCH',dict(draft=False,make_latest='false'))
 proof={};remote={a['name']:a for a in r['assets']}
 for p in sorted((O/'assets').glob('*.zip')):
  a=remote[p.name];assert a['size']==p.stat().st_size and a['digest']=='sha256:'+sha(p).lower();h=hashlib.sha256();n=0
  with urllib.request.urlopen(urllib.request.Request(a['browser_download_url'],headers={'User-Agent':'PawsArcaneBeta7Release','Cache-Control':'no-cache'}),timeout=120)as response:
   for b in iter(lambda:response.read(4*1024*1024),b''):h.update(b);n+=len(b)
  assert n==p.stat().st_size and h.hexdigest().upper()==sha(p);proof[p.name]=dict(size=n,sha256=h.hexdigest().upper());write(O/'public-assets-progress.json',proof);print('PUBLIC_DOWNLOAD_VERIFIED',p.name,flush=True)
 write(O/'public-assets.json',dict(url=r['html_url'],tag=TAG,assets=proof))
def promote():
 gate();assert len(read(O/'public-assets.json')['assets'])==5
 import catalogs
 parent=snapshot()
 for name in ['ModuleInstaller.cs','GamePackageSelector.cs','EffectiveSettings.cs','GameExecutableSelector.cs','UpdateDetector.cs','Models.cs']:
  rel='src/PawsPatchLauncher/'+name;current=subprocess.check_output(['git','show',parent+':'+rel],cwd=REPO);assert current.replace(b'\r\n',b'\n')==(S/rel).read_bytes().replace(b'\r\n',b'\n'),'Launcher selection/installer changed since QA: '+rel
 catalogs.main();allowed=read(O/'scope.json')['allowed'];assert set(allowed)=={'feed/v2/beta.json','feed/v3/beta.json','feed/changelog.history.json','feed/patch-guide-beta.json'}
 c=commit_files(parent,O/'signed',allowed,'Publish Arcane Wars 0.6.0-beta.7','catalog');write(O/'publication.json',dict(sourceCommit=read(O/'source-publication.json')['commit'],catalogCommit=c,parent=parent,version=V));print('BETA_CATALOG_PUBLIC',c,flush=True)
def readback():
 publication=read(O/'publication.json');c=publication['catalogCommit'];proof={}
 for rel in FILES:
  with urllib.request.urlopen(urllib.request.Request(RAW+c+'/'+rel,headers={'User-Agent':'PawsArcaneBeta7Release'}),timeout=60)as r:b=r.read()
  assert b.replace(b'\r\n',b'\n')==(O/'signed'/rel).read_bytes().replace(b'\r\n',b'\n'),rel
  if rel in FILES[:6]:verify(json.loads(b))
  proof[rel]=hashlib.sha256(b).hexdigest()
 for prefix in['v2','v3']:
  rel=f'feed/{prefix}/beta.json'
  with urllib.request.urlopen(urllib.request.Request(RAW+'main/'+rel,headers={'User-Agent':'PawsArcaneBeta7Release','Cache-Control':'no-cache'}),timeout=60)as r:f=verify(json.load(r))
  assert f==verify(read(O/'signed'/rel));assert f['launcher']==verify(read(O/'before'/rel))['launcher']
  for p in read(O/'packages.json'):assert next(q for q in f['packages']if q['id']==p['id'])==p
 assert read(O/'catalog-ci.json')['conclusion']=='success';unchanged();write(O/'readback.json',dict(passed=True,**publication,files=proof,publicAssetsVerified=5));print('PUBLIC_BETA7_READBACK_PASS',flush=True)
if __name__=='__main__':
 action=sys.argv[1]
 if action.endswith('-ci'):ci(action.split('-')[0])
 else:globals()[action]()
