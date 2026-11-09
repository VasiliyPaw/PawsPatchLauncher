"""Publish the authorized three-beta minimap fix, preserving every other catalog."""
import argparse,os,zipfile
from context import *
SOURCE=[
 'game/ui-scout-test/runtime.c','game/ui-scout-test/test_inverse_return.py',
 'docs/verification-minimap-crash-release-20261109.md',
 'docs/release-patch-0.5.1-beta.3.json','docs/release-pure-0.5.0-beta.4.json']

def source_paths():return SOURCE+sorted(p.relative_to(REPO).as_posix()for p in (REPO/'tools/MinimapCrashRelease').iterdir()if p.suffix in ['.py','.cs','.md'])

def bundle():
 for kind in ['arcane','pure']:
  helper=OUT/(kind+'-helpers');files={}
  for row in read(helper/'build-report.json').values():
   for path,digest in row['sources'].items():
    p=Path(path);assert sha(p)==digest
    assert p.name.lower()!='k2.exe'and p.suffix.lower()not in ['.pem','.rsg','.rwd']
    files['inputs/'+digest+'/'+p.name]=p.read_bytes()
  files['build-report.json']=(helper/'build-report.json').read_bytes()
  native=OUT/(kind+'-native')
  for p in native.iterdir():
   if p.suffix in ['.c','.h','.json']:files['native/'+p.name]=p.read_bytes()
  for p in (native/'qa').iterdir():
   if p.suffix in ['.c','.h','.py','.json']:files['native/qa/'+p.name]=p.read_bytes()
  for p in (REPO/'tools/MinimapCrashRelease').iterdir():
   if p.suffix in ['.py','.cs','.md']:files['release-tools/'+p.name]=p.read_bytes()
  files['tests/test_inverse_return.py']=(REPO/'game/ui-scout-test/test_inverse_return.py').read_bytes()
  files['tests/test_native.py']=(REPO/'game/ui-scout-test/test_native.py').read_bytes()
  files['README.txt']=b'Exact sources/resources for the minimap return-contract crash fix. No game EXE, saves, signing keys or unrelated experiments. Native TCC compiler command and SHA-bound baseline are in native/build.json. Rebuild managed x86 helpers from build-report.json, remapping inputs by SHA-256 to inputs/<hash>/<filename>. Run compiled x86 callback tests with the documented local Unicorn/Keystone fixtures. No live match after this fix is claimed. PE timestamps are not claimed deterministic.\n'
  files['manifest.json']=encode({n:dict(size=len(b),sha256=hashlib.sha256(b).hexdigest().upper())for n,b in sorted(files.items())})
  path=OUT/kind/('minimap-crash-'+VERSIONS[kind]+'-build-inputs.zip')
  with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
   for n,b in sorted(files.items()):
    item=zipfile.ZipInfo(n,(2026,11,9,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED;z.writestr(item,b)
  write(OUT/kind/'bundle.json',dict(path=str(path),sha256=sha(path),size=path.stat().st_size,files=len(files)))
 print('EXACT_BUILD_INPUTS_BUNDLED',flush=True)

def gate():
 assert read(OUT/'native-checks/result.json')['passed']
 from build import NATIVES,DLLS,correct
 for kind,base in NATIVES.items():
  native=OUT/(kind+'-native');meta=read(native/'build.json')
  assert sha(native/DLLS[kind])==meta['sha256']
  assert (native/'ui.c').read_text()==correct((base/'ui.c').read_text())
  for name,digest in meta['sources'].items():
   assert sha(native/name)==digest
   if name!='ui.c':assert sha(base/name)==digest
  assert read(native/'return-contract.json')['passed']
  assert read(native/'qa/native-test.json')['passed']
  changed={Path(p).name for p in read(OUT/(kind+'-helpers')/'changed-inputs.json')}
  expected={DLLS[kind],'PresentationRuntimePayload.cs','25-LargeMapsIdentity.cs'}if kind=='arcane'else{DLLS[kind],'PurePresentationRuntimePayload.cs','4-PureChannel.cs'}
  assert changed==expected,changed
 assert read(OUT/'installer-result.json')==dict(passed=True,pureCases=20,arcaneCases=12,gamesLaunched=False)
 assert 'THREE_BETAS_ALL_SWITCHES_PASS 635906 assertions; 55296 selections'in (OUT/'catalog-checks.log').read_text()
 for kind in ['arcane','pure']:
  helper=OUT/(kind+'-helpers');rows=read(helper/'build-report.json');assert len(rows)==(8 if kind=='arcane'else 4)
  for name,row in rows.items():
   assert sha(helper/name)==row['sha256']and row['features']['patchVersion']==VERSIONS[kind]
   for path,digest in row['sources'].items():assert sha(path)==digest,path
  b=read(OUT/kind/'bundle.json');assert sha(b['path'])==b['sha256']
 for p in read(OUT/'packages.json'):
  validate_package(Path(read(OUT/'package-audit.json')[p['id']]['archive']),p)
 baseline=read(OUT/'baseline.json')
 for rel,digest in baseline['files'].items():assert sha(REPO/rel)==digest,rel
 preserved=read(REPO/'outputs/arcane-051-release-20261109/preserved-work/manifest.json')
 for label in ['installed-exe','save-one','save-two']:
  item=preserved[label];assert sha(item['path']).lower()==item['sha256'].lower(),label
 assert subprocess.check_output(['git','diff','--cached','--binary'],cwd=REPO)==(OUT/'staged-before.patch').read_bytes()
 return True

def source():
 gate();head=read(OUT/'baseline.json')['publicHead'];assert git('rev-parse','HEAD')==head==git('ls-remote','origin','refs/heads/main').split()[0]
 paths=source_paths();assert not set(git('diff','--cached','--name-only').splitlines()).intersection(paths)
 write(OUT/'source-scope.json',dict(base=head,files={p:sha(REPO/p)for p in paths}))
 git('add','--',*paths);git('commit','--only','-m','Fix minimap inverse return pointer in all beta modes','--',*paths)
 assert subprocess.check_output(['git','diff','--cached','--binary'],cwd=REPO)==(OUT/'staged-before.patch').read_bytes()
 commit=git('rev-parse','HEAD');changed=git('diff-tree','--no-commit-id','--name-only','-r',commit).splitlines();assert set(changed)<=set(paths)
 git('push','origin','HEAD:main');write(OUT/'source-publication.json',dict(commit=commit,files=changed));print('MINIMAP_FIX_SOURCE_PUBLIC',commit,flush=True)

def release():
 gate();commit=read(OUT/'source-publication.json')['commit'];assert git('rev-parse','HEAD')==commit==git('ls-remote','origin','refs/heads/main').split()[0]
 ci=read(OUT/'source-ci.json');assert ci['head_sha']==commit and ci['conclusion']=='success'
 for path,digest in read(OUT/'source-scope.json')['files'].items():assert sha(REPO/path)==digest,path
 proofs={}
 for kind in ['arcane','pure']:
  tag=('patch-'if kind=='arcane'else'patch-pure-')+VERSIONS[kind]
  assets=[Path(v['archive'])for v in read(OUT/'package-audit.json').values()if v['kind']==kind]+[Path(read(OUT/kind/'bundle.json')['path'])]
  args=[PYTHON,REPO/'tools/PublishLauncherRelease.py',VERSIONS[kind],commit,OUT/(kind+'-notes.md'),*assets,'--tag',tag,'--name','Paw’s Patch '+VERSIONS[kind]+' — '+('Arcane Wars'if kind=='arcane'else'Vanilla / Immortals'),'--prerelease']
  print(run(args,OUT/(kind+'-upload.log')),flush=True)
  result=json.loads(fetch(API+'/releases/tags/'+tag));assert not result['draft']and result['prerelease'];remote={x['name']:x for x in result['assets']}
  checks={}
  for p in assets:
   r=remote[p.name];data=fetch(r['browser_download_url']);assert len(data)==p.stat().st_size and hashlib.sha256(data).hexdigest().upper()==sha(p)and r['digest']=='sha256:'+sha(p).lower()
   checks[p.name]=dict(size=len(data),sha256=sha(p))
  proofs[kind]=dict(url=result['html_url'],assets=checks,tag=tag)
  write(OUT/'public-assets.json',proofs)
 print('MINIMAP_FIX_PUBLIC_ASSETS_VERIFIED',flush=True)

def promote():
 gate();proof=read(OUT/'public-assets.json');assert set(proof)=={'arcane','pure'}
 commit=read(OUT/'source-publication.json')['commit'];assert git('rev-parse','HEAD')==commit==git('ls-remote','origin','refs/heads/main').split()[0]
 for rel,digest in read(OUT/'baseline.json')['files'].items():
  assert sha(REPO/rel)==digest
  assert normalize(fetch(RAW.replace('/main/','/'+commit+'/')+rel))==normalize((REPO/rel).read_bytes()),rel
 allowed=read(OUT/'scope.json')['allowed'];assert len(allowed)==4
 for rel in allowed:(REPO/rel).write_bytes((OUT/'signed'/rel).read_bytes())
 git('add','--',*allowed);git('commit','--only','-m','Publish minimap crash fix in Arcane, Vanilla and Immortals betas','--',*allowed)
 assert subprocess.check_output(['git','diff','--cached','--binary'],cwd=REPO)==(OUT/'staged-before.patch').read_bytes()
 catalog=git('rev-parse','HEAD');git('push','origin','HEAD:main')
 write(OUT/'publication.json',dict(sourceCommit=commit,catalogCommit=catalog,versions=VERSIONS,releases={k:v['url']for k,v in proof.items()},installedGameModified=False))
 print('THREE_BETA_CATALOGS_PUBLIC',catalog,flush=True)

def readback():
 proof=read(OUT/'publication.json');commit=proof['catalogCommit'];assert git('rev-parse','HEAD')==commit==git('ls-remote','origin','refs/heads/main').split()[0]
 allowed=read(OUT/'scope.json')['allowed']
 for rel in FEEDS+['feed/changelog.history.json','feed/patch-guide-beta.json']:
  data=fetch(RAW.replace('/main/','/'+commit+'/')+rel);assert normalize(data)==normalize((REPO/rel).read_bytes()),rel
  if rel in FEEDS:verify(json.loads(data),key())
  if rel not in allowed:assert normalize(data)==normalize((OUT/'before'/rel).read_bytes()),rel
 for prefix in ['v2','v3']:
  f=verify(json.loads(fetch(RAW+f'feed/{prefix}/beta.json')),key());assert f['patchGuide']['version']==VERSIONS['arcane']
  assert next(p for p in f['packages']if p['id']=='pure-fixes-data')['version']==VERSIONS['pure']
  assert next(p for p in f['packages']if p['id']=='pure-fixes-runtime')['version']==RUNTIME
  assert f['launcher']['version']=='1.0.13'
  for g in f['modGuides']:
   if g['id']in ['vanilla','immortals']:assert g['patchGuide']['version']==VERSIONS['pure']
 proof['passed']=True;write(OUT/'readback.json',proof);print('PUBLIC_THREE_BETA_READBACK_PASS',json.dumps(proof),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['bundle','gate','source','release','promote','readback']);a=p.parse_args();globals()[a.action]()
