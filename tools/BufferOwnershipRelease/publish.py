"""Publish hash-bound beta assets, then promote four catalog files.

Use a private Git index based on current public main; never move a shared
checkout, alter its staging, or include unrelated local work in a commit.
"""
import argparse,zipfile
from context import *
SOURCE=[
 'game/graphics-guard/native_buffers.h','game/graphics-guard/build_native_buffers.py',
 'game/graphics-guard/test_buffer_ownership.c','game/graphics-guard/test_native_buffer_ownership.py',
 'game/presentation-runtime/PresentationRuntimePatch.cs',
 'tools/Arcane051Release/build_native.py','tools/Arcane051Release/build_helpers.py',
 'docs/verification-native-buffer-ownership-20261113.md',
 'docs/verification-buffer-ownership-release-20261113.md',
 'docs/release-patch-0.5.1-beta.4.json','docs/release-pure-0.5.0-beta.5.json']
def source_paths():return SOURCE+sorted(p.relative_to(REPO).as_posix()for p in(REPO/'tools/BufferOwnershipRelease').iterdir()if p.suffix in ['.py','.cs','.md'])
def bundle():
 for kind in VERSIONS:
  folder=OUT/(kind+'-helpers');files={}
  for row in read(folder/'build-report.json').values():
   for p,digest in row['sources'].items():
    p=Path(p);assert sha(p)==digest and p.suffix.lower()not in['.pem','.rsg','.rwd']and p.name.lower()!='k2.exe';files['inputs/'+digest+'/'+p.name]=p.read_bytes()
  files['build-report.json']=(folder/'build-report.json').read_bytes();files['changed-inputs.json']=(folder/'changed-inputs.json').read_bytes()
  for p in GRAPHICS.iterdir():
   if p.suffix in['.c','.h','.json']:files['graphics/'+p.name]=p.read_bytes()
  for name in ['build_native_buffers.py','prepare_guard_exports.py','test_buffer_ownership.c','test_native_buffer_ownership.py']:files['graphics/'+name]=(REPO/'game/graphics-guard'/name).read_bytes()
  for p in(REPO/'tools/BufferOwnershipRelease').iterdir():
   if p.suffix in['.py','.cs','.md']:files['release-tools/'+p.name]=p.read_bytes()
  files['tests/ownership-regressions.json']=Path('G:/PawGraphicsQA-20261113/canonical-ownership-check/ownership-regressions.json').read_bytes()
  files['README.txt']=b'Exact helper compiler inputs and native-buffer graphics sources. All other native payloads are unchanged from beta.3 Arcane / beta.4 Pure. No game EXE, player data or signing keys. Remap source/resource paths by SHA to inputs/<hash>/<filename>. Compile ordinary x86 helpers with build-report.json; use graphics/build_native_buffers.py for DLL and graphics/test_native_buffer_ownership.py for real-driver regression. Test requires an actual D3D9 HAL. Original video stripes have not been reproduced in a live match; fixed defects are independently confirmed ownership violations.\n'
  files['manifest.json']=encode({n:dict(size=len(b),sha256=hashlib.sha256(b).hexdigest().upper())for n,b in sorted(files.items())})
  path=OUT/kind/('buffer-ownership-'+VERSIONS[kind]+'-build-inputs.zip')
  with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
   for n,b in sorted(files.items()):
    item=zipfile.ZipInfo(n,(2026,11,13,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED;z.writestr(item,b)
  write(OUT/kind/'bundle.json',dict(path=str(path),sha256=sha(path),size=path.stat().st_size,files=len(files)))
 print('EXACT_BUILD_INPUTS_BUNDLED',flush=True)
def unchanged_checkout():
 assert git('rev-parse','HEAD')==read(OUT/'baseline.json')['localHead']
 assert subprocess.check_output(['git','diff','--cached','--binary'],cwd=REPO)==(OUT/'staged-before.patch').read_bytes()
def gate():
 unchanged_checkout();assert read(OUT/'compiled-checks/result.json')['passed'];assert read(OUT/'installer-result.json')['passed']
 assert 'THREE_BETA_BUFFER_FIX_ALL_SWITCHES_PASS 617474 assertions; 55296 selections'in(OUT/'catalog-checks.log').read_text()
 results=read(Path('G:/PawGraphicsQA-20261113/canonical-ownership-check/ownership-regressions.json'));assert len(results)==36 and all(r['exitCode']==r['expected']for r in results)
 assert sha(GRAPHICS/'d3d9.dll')==read(GRAPHICS/'product.json')['sha256']and read(GRAPHICS/'product.json')['nativeBufferOwnership']
 for kind in VERSIONS:
  folder=OUT/(kind+'-helpers');rows=read(folder/'build-report.json');assert len(rows)==(8 if kind=='arcane'else 4)
  for name,row in rows.items():
   assert sha(folder/name)==row['sha256']and row['features']['patchVersion']==VERSIONS[kind]and row['features']['bufferReuseRevision']==0
   for p,h in row['sources'].items():assert sha(p)==h
  b=read(OUT/kind/'bundle.json');assert sha(b['path'])==b['sha256']
 for p in read(OUT/'packages.json'):validate_package(Path(read(OUT/'package-audit.json')[p['id']]['archive']),p)
 for rel,h in read(OUT/'baseline.json')['files'].items():assert sha(OUT/'before'/rel)==h
 return True
def commit_files(parent,root,paths,message,label):
 assert head()==parent,'Public main moved: prepare against its new state before publishing'
 e=env();e['GIT_INDEX_FILE']=str(OUT/(label+'-index'));assert not Path(e['GIT_INDEX_FILE']).exists()
 def command(*a):return subprocess.check_output(['git',*a],cwd=REPO,env=e,text=True).strip()
 command('read-tree',parent);command('--work-tree='+str(root),'add','--',*paths);tree=command('write-tree')
 body=OUT/(label+'-commit.txt');body.write_text(message+'\n');commit=command('commit-tree',tree,'-p',parent,'-F',str(body))
 changed=command('diff-tree','--no-commit-id','--name-only','-r',commit).splitlines();assert set(changed)==set(paths)
 assert head()==parent;command('push','origin',commit+':refs/heads/main');unchanged_checkout();return commit,changed
def source():
 gate();base=read(OUT/'baseline.json')['publicHead'];assert head()==base
 paths=source_paths();stage=OUT/'source';stage.mkdir()
 # Never overwrite remote changes with an older local version of a tracked file.
 for rel in paths:
  before=subprocess.run(['git','show',read(OUT/'baseline.json')['localHead']+':'+rel],cwd=REPO,capture_output=True)
  current=subprocess.run(['git','show',base+':'+rel],cwd=REPO,capture_output=True)
  assert before.returncode==current.returncode and before.stdout==current.stdout,('Source path changed publicly; merge first',rel)
  p=stage/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((REPO/rel).read_bytes())
 write(OUT/'source-scope.json',dict(base=base,files={rel:sha(stage/rel)for rel in paths}))
 commit,changed=commit_files(base,stage,paths,'Fix native D3D buffer ownership in all beta modes','source');write(OUT/'source-publication.json',dict(commit=commit,files=changed));print('SOURCE_PUBLIC',commit,flush=True)
def ci(phase):
 commit=read(OUT/('source-publication.json'if phase=='source'else'publication.json'))['commit'if phase=='source'else'catalogCommit']
 rows=json.loads(fetch(API+'/actions/runs?head_sha='+commit+'&per_page=25'))['workflow_runs'];runs=[r for r in rows if r['name']=='Build and test'and r['event']=='push'and r['head_sha']==commit]
 if not runs:print('CI_PENDING',phase,commit);return
 r=max(runs,key=lambda r:r['run_number']);result={k:r[k]for k in['id','head_sha','status','conclusion','html_url']};write(OUT/(phase+'-ci.json'),result);print('CI_STATUS',json.dumps(result),flush=True)
 if r['status']=='completed'and r['conclusion']!='success':raise RuntimeError('Required CI failed: '+r['html_url'])
def release():
 gate();commit=read(OUT/'source-publication.json')['commit'];assert head()==commit
 check=read(OUT/'source-ci.json');assert check['head_sha']==commit and check['conclusion']=='success'
 for rel,h in read(OUT/'source-scope.json')['files'].items():assert sha(REPO/rel)==h,'Source changed after CI: '+rel
 proofs={}
 for kind in VERSIONS:
  tag=('patch-'if kind=='arcane'else'patch-pure-')+VERSIONS[kind];assets=[Path(v['archive'])for v in read(OUT/'package-audit.json').values()if v['kind']==kind]+[Path(read(OUT/kind/'bundle.json')['path'])]
  print(run([PYTHON,REPO/'tools/PublishLauncherRelease.py',VERSIONS[kind],commit,OUT/(kind+'-notes.md'),*assets,'--tag',tag,'--name','Paw’s Patch '+VERSIONS[kind]+' — '+('Arcane Wars'if kind=='arcane'else'Vanilla / Immortals'),'--prerelease'],OUT/(kind+'-upload.log')),flush=True)
  r=json.loads(fetch(API+'/releases/tags/'+tag));assert not r['draft']and r['prerelease'];remote={a['name']:a for a in r['assets']};checks={}
  for p in assets:
   a=remote[p.name];data=fetch(a['browser_download_url']);assert len(data)==p.stat().st_size and hashlib.sha256(data).hexdigest().upper()==sha(p)and a['digest']=='sha256:'+sha(p).lower();checks[p.name]=dict(size=len(data),sha256=sha(p))
  proofs[kind]=dict(url=r['html_url'],assets=checks,tag=tag);write(OUT/'public-assets.json',proofs)
 print('PUBLIC_ASSETS_VERIFIED',flush=True)
def promote():
 gate();assert set(read(OUT/'public-assets.json'))==set(VERSIONS);commit=read(OUT/'source-publication.json')['commit'];assert head()==commit
 for rel in FILES:assert normalize(fetch(RAW.replace('/main/','/'+commit+'/')+rel))==normalize((OUT/'before'/rel).read_bytes()),rel
 allowed=read(OUT/'scope.json')['allowed'];assert len(allowed)==4
 catalog,changed=commit_files(commit,OUT/'signed',allowed,'Publish native buffer ownership fix in all three betas','catalog')
 write(OUT/'publication.json',dict(sourceCommit=commit,catalogCommit=catalog,versions=VERSIONS,releases={k:v['url']for k,v in read(OUT/'public-assets.json').items()},installedGameModified=False));print('THREE_BETA_CATALOGS_PUBLIC',catalog,flush=True)
def readback():
 proof=read(OUT/'publication.json');commit=proof['catalogCommit'];assert head()==commit
 allowed=read(OUT/'scope.json')['allowed']
 for rel in FILES:
  data=fetch(RAW.replace('/main/','/'+commit+'/')+rel);expected=(OUT/'signed'/rel).read_bytes();assert normalize(data)==normalize(expected),rel
  if rel in FEEDS:verify(json.loads(data),key())
  if rel not in allowed:assert normalize(data)==normalize((OUT/'before'/rel).read_bytes()),rel
 for prefix in ['v2','v3']:
  f=verify(json.loads(fetch(RAW+f'feed/{prefix}/beta.json')),key());expected=verify(read(OUT/'signed'/f'feed/{prefix}/beta.json'),key());assert f==expected,'Canonical URL not propagated yet: '+prefix
  assert f['patchGuide']['version']==VERSIONS['arcane'];assert next(p for p in f['packages']if p['id']=='pure-fixes-data')['version']==VERSIONS['pure'];assert next(p for p in f['packages']if p['id']=='pure-fixes-runtime')['version']==RUNTIME
  assert f['launcher']['version']==read(OUT/'baseline.json')['launcher']
  for g in f['modGuides']:
   if g['id']in['vanilla','immortals']:assert g['patchGuide']['version']==VERSIONS['pure']
 proof['passed']=True;write(OUT/'readback.json',proof);print('PUBLIC_THREE_BETA_READBACK_PASS',json.dumps(proof),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['bundle','gate','source','source-ci','release','promote','catalog-ci','readback']);action=p.parse_args().action
 if action.endswith('-ci'):ci(action.split('-')[0])
 else:globals()[action]()
