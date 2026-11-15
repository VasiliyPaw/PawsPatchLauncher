from release_context import *
from catalogs import FILES
def git(*a):return run(['git',*a]).strip()
def head():return git('ls-remote','origin','refs/heads/main').split()[0]
def unchanged():
 b=read(P/'public-baseline.json');assert git('rev-parse','HEAD')==b['localHead'];assert subprocess.check_output(['git','diff','--cached','--binary'],cwd=REPO)==(P/'staged-before.patch').read_bytes()
def gate():
 unchanged();cases=list((R/'qa-evidence/arcane060-savebuild').glob('*-savebuild.json'));assert len(cases)==12 and all(read(f)['passed']and read(f)['healthNeverEdited']for f in cases)
 assert read(O/'product-smoke.json')['passed'];assert read(O/'installer-result.json')['passed'];assert read(O/'catalog-qa/result.json')['passed'];assert read(P/'finish-controller-fix.json')['passed']
 for q in read(O/'packages.json'):
  f=O/'assets'/(q['id']+'-'+VERSION+'.zip');assert sha(f)==q['sha256']and f.stat().st_size==q['size']
 assert sha(read(O/'bundle.json')['path'])==read(O/'bundle.json')['sha256']
 print('RELEASE_GATE_PASS',flush=True)
def commit_files(parent,root,paths,message,label):
 assert head()==parent,'Remote main moved; rebase scoped release files first'
 e=env();index=O/(label+'-index');assert not index.exists();e['GIT_INDEX_FILE']=str(index)
 def g(*a):return subprocess.check_output(['git',*a],cwd=REPO,env=e,text=True).strip()
 paths_file=O/(label+'-paths');paths_file.write_bytes(('\0'.join(paths)+'\0').encode('utf-8'))
 g('read-tree',parent);g('--work-tree='+str(root),'add','--pathspec-from-file='+str(paths_file),'--pathspec-file-nul');tree=g('write-tree');body=O/(label+'-commit.txt');body.write_text(message+'\n');commit=g('commit-tree',tree,'-p',parent,'-F',str(body))
 changed=g('diff-tree','--no-commit-id','--name-only','-r',commit).splitlines();assert set(changed)==set(paths),(len(changed),len(paths));assert head()==parent;g('push','origin',commit+':refs/heads/main');unchanged();return commit
def source():
 gate();git('fetch','--no-tags','origin','main');parent=git('rev-parse','FETCH_HEAD');paths=read(O/'source-scope.json')['files']
 for p in paths:assert not git('ls-tree',parent,'--',p),'Existing remote source path requires merge: '+p
 commit=commit_files(parent,O/'source-public',paths,'Add Arcane Wars 0.6.0 roads, bridges, world features and release verification','source')
 write(O/'source-publication.json',dict(commit=commit,parent=parent,files={p:sha(O/'source-public'/p)for p in paths}));print('SOURCE_PUBLIC',commit,flush=True)
def ci(phase):
 commit=read(O/('source-publication.json'if phase=='source'else'publication.json'))['commit'if phase=='source'else'catalogCommit']
 rows=json.loads(fetch(API+'/actions/runs?head_sha='+commit+'&per_page=25'))['workflow_runs'];rows=[r for r in rows if r['name']=='Build and test'and r['head_sha']==commit]
 if not rows:print('CI_PENDING',phase);return
 r=max(rows,key=lambda r:r['run_number']);result={k:r[k]for k in ['id','head_sha','status','conclusion','html_url']};write(O/(phase+'-ci.json'),result);print('CI_STATUS',json.dumps(result),flush=True)
 if r['status']=='completed'and r['conclusion']!='success':raise RuntimeError('CI failed: '+r['html_url'])
def release():
 gate();commit=read(O/'source-publication.json')['commit'];assert read(O/'source-ci.json')['conclusion']=='success'
 for rel,h in read(O/'source-publication.json')['files'].items():assert sha(O/'source-public'/rel)==h
 assets=sorted((O/'assets').glob('*.zip'));assert len(assets)==15
 print(run([sys.executable,S/'tools/PublishLauncherRelease.py',VERSION,commit,O/'release-notes.md',*assets,'--tag',TAG,'--name','Paw’s Patch '+VERSION+' — Arcane Wars','--prerelease'],O/'release-upload.log'),flush=True)
 r=json.loads(fetch(API+'/releases/tags/'+TAG));assert not r['draft']and r['prerelease'];remote={a['name']:a for a in r['assets']};proof={}
 import urllib.request
 for p in assets:
  a=remote[p.name];assert a['size']==p.stat().st_size and a['digest']=='sha256:'+sha(p).lower()
  h=hashlib.sha256();n=0
  with urllib.request.urlopen(urllib.request.Request(a['browser_download_url'],headers={'User-Agent':'PawsRelease060'}),timeout=90)as response:
   for b in iter(lambda:response.read(1048576),b''):h.update(b);n+=len(b)
  assert n==p.stat().st_size and h.hexdigest().upper()==sha(p);proof[p.name]=dict(size=n,sha256=h.hexdigest().upper());print('PUBLIC_DOWNLOAD_VERIFIED',p.name,flush=True)
  write(O/'public-assets-progress.json',proof)
 write(O/'public-assets.json',dict(url=r['html_url'],tag=TAG,assets=proof));print('PUBLIC_ASSETS_PASS',flush=True)
def promote():
 gate();assert len(read(O/'public-assets.json')['assets'])==15
 # Always compose the four allowed files over the freshest public catalog;
 # preserve launcher, Pure releases, stable feeds and concurrent source work.
 import catalogs
 catalogs.baseline();catalogs.catalogs();parent=read(O/'catalog-baseline.json')['publicHead'];allowed=read(O/'scope.json')['allowed'];assert len(allowed)==4
 commit=commit_files(parent,O/'signed',allowed,'Publish Arcane Wars 0.6.0 beta with roads, racial bridges and 24-minute days','catalog')
 write(O/'publication.json',dict(sourceCommit=read(O/'source-publication.json')['commit'],catalogCommit=commit,version=VERSION,url=read(O/'public-assets.json')['url'],baseline=parent));print('ARCANE_BETA_PUBLIC',commit,flush=True)
def readback():
 p=read(O/'publication.json');commit=p['catalogCommit']
 for rel in FILES:
  data=fetch(RAW.replace('/main/','/'+commit+'/')+rel);assert normalize(data)==normalize((O/'signed'/rel).read_bytes()),rel
  if rel in FILES[:6]:verify(json.loads(data),key())
  if rel not in read(O/'scope.json')['allowed']:assert normalize(data)==normalize((O/'before'/rel).read_bytes()),rel
 for prefix in ['v2','v3']:
  f=verify(json.loads(fetch(RAW+f'feed/{prefix}/beta.json')),key());assert f==verify(read(O/'signed'/f'feed/{prefix}/beta.json'),key());assert f['patchGuide']['version']==VERSION
  for q in read(O/'packages.json'):assert next(x for x in f['packages']if x['id']==q['id'])==q
 p['passed']=True;write(O/'readback.json',p);unchanged();print('PUBLIC_READBACK_PASS',json.dumps(p),flush=True)
if __name__=='__main__':
 action=sys.argv[1]
 if action.endswith('-ci'):ci(action.split('-')[0])
 else:globals()[action]()
