"""Publish the authorized three-beta color fix, preserving every other catalog."""
import argparse,os,zipfile
from context import *
SOURCE=[
 'game/beta7/LobbyColorsNative.cs','game/beta7/PawLobbyColorsPayload.bin','game/beta7/PawLobbyColorsFixups.bin',
 'game/lobby-colors/build_native.py','game/lobby-colors/README.md','game/lobby-colors/build_lifetime_candidate.py',
 'game/lobby-colors/test_session_lifetime.py','game/lobby-colors/test_native_session_reset.py',
 'docs/verification-lobby-color-lifetime-20261109.md','docs/verification-lobby-color-release-20261109.md',
 'docs/release-patch-0.5.1-beta.2.json','docs/release-pure-0.5.0-beta.3.json']

def source_paths():return SOURCE+sorted(p.relative_to(REPO).as_posix()for p in (REPO/'tools/LobbyColorsRelease').iterdir()if p.suffix in ['.py','.cs'])

def bundle():
 for kind in ['arcane','pure']:
  helper=OUT/(kind+'-helpers');files={}
  for row in read(helper/'build-report.json').values():
   for path,digest in row['sources'].items():
    p=Path(path);assert sha(p)==digest
    assert p.name.lower()!='k2.exe'and p.suffix.lower()not in ['.pem','.rsg','.rwd']
    files['inputs/'+digest+'/'+p.name]=p.read_bytes()
  files['build-report.json']=(helper/'build-report.json').read_bytes()
  for p in (REPO/'game/lobby-colors').iterdir():
   if p.suffix in ['.py','.md','.json','.ini']:files['lobby-colors/'+p.name]=p.read_bytes()
  files['LobbyColorsNative.cs']=(REPO/'game/beta7/LobbyColorsNative.cs').read_bytes()
  files['README.txt']=b'Exact compiler sources/resources for the lobby-color lifetime fix. No game EXE, saves or signing keys. Rebuild managed helpers with .NET Framework x86 csc using build-report.json, remapping each input by its SHA-256 to inputs/<hash>/<filename>. The native color emitter requires the verified 1.3.72 analysis input and local assembler/emulator dependencies documented in lobby-colors/README.md. PE timestamps are not claimed deterministic. Native reset tests stub external services; complete new-lobby Internet acceptance remains unverified.\n'
  files['manifest.json']=encode({n:dict(size=len(b),sha256=hashlib.sha256(b).hexdigest().upper())for n,b in sorted(files.items())})
  path=OUT/kind/('lobby-colors-'+VERSIONS[kind]+'-build-inputs.zip')
  with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
   for n,b in sorted(files.items()):
    item=zipfile.ZipInfo(n,(2026,11,9,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED;z.writestr(item,b)
  write(OUT/kind/'bundle.json',dict(path=str(path),sha256=sha(path),size=path.stat().st_size,files=len(files)))
 print('EXACT_BUILD_INPUTS_BUNDLED',flush=True)

def gate():
 assert read(OUT/'native-checks/result.json')['passed']
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
 git('add','--',*paths);git('commit','--only','-m','Fix lobby color ownership across new sessions in all beta modes','--',*paths)
 assert subprocess.check_output(['git','diff','--cached','--binary'],cwd=REPO)==(OUT/'staged-before.patch').read_bytes()
 commit=git('rev-parse','HEAD');changed=git('diff-tree','--no-commit-id','--name-only','-r',commit).splitlines();assert set(changed)<=set(paths)
 git('push','origin','HEAD:main');write(OUT/'source-publication.json',dict(commit=commit,files=changed));print('COLOR_FIX_SOURCE_PUBLIC',commit,flush=True)

def release():
 gate();commit=read(OUT/'source-publication.json')['commit'];assert git('rev-parse','HEAD')==commit==git('ls-remote','origin','refs/heads/main').split()[0]
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
 print('COLOR_FIX_PUBLIC_ASSETS_VERIFIED',flush=True)

def promote():
 gate();proof=read(OUT/'public-assets.json');assert set(proof)=={'arcane','pure'}
 commit=read(OUT/'source-publication.json')['commit'];assert git('rev-parse','HEAD')==commit==git('ls-remote','origin','refs/heads/main').split()[0]
 for rel,digest in read(OUT/'baseline.json')['files'].items():
  assert sha(REPO/rel)==digest
  assert normalize(fetch(RAW.replace('/main/','/'+commit+'/')+rel))==normalize((REPO/rel).read_bytes()),rel
 allowed=read(OUT/'scope.json')['allowed'];assert len(allowed)==4
 for rel in allowed:(REPO/rel).write_bytes((OUT/'signed'/rel).read_bytes())
 git('add','--',*allowed);git('commit','--only','-m','Publish color ownership fix in Arcane, Vanilla and Immortals betas','--',*allowed)
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
