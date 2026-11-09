"""Publish the authorized Arcane beta only after explicit native acceptance."""
import argparse,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
REPO=Path(__file__).resolve().parents[2];sys.path.insert(0,str(REPO/'tools'))
from PrepareRelease081 import fetch,key,RAW,API,normalize
from PrepareRelease070 import sha,verify,validate_package
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def write(p,o):p.write_text(json.dumps(o,indent=2))
def git(*args):return subprocess.check_output(['git',*args],cwd=REPO,text=True).strip()
def gate(stage):
 prep=read(stage/'preparation.json');assert prep['version']=='0.5.1-beta.1' and len(prep['assets'])==5
 assert prep['note']==read(REPO/'docs/release-patch-0.5.1-beta.1.json')
 assert '631298 assertions; 55296 selections' in (stage/'catalog-checks.log').read_text()
 matrix=read(stage/'install-matrix-summary.json');assert matrix['complete'] and matrix['planned']==12
 accept=read(stage/'native-acceptance.json');assert accept['passed'] and accept['productRuntimeUnmodified']
 for case in accept['cases']:
  proof=read(case['proof']);assert proof['passed'];assert all(proof['checks'].values())
 for required in ['new-match','paired-voices','old-save','fresh-replay']:assert any(c['id']==required for c in accept['cases']),required
 for name,row in read(Path(prep['helpers'])/'build-report.json').items():assert sha(Path(prep['helpers'])/name)==row['sha256']
 for asset in prep['assets']:validate_package(Path(asset['path']),dict(id=asset['id'],version=prep['version'],size=asset['size'],sha256=asset['sha256']))
 bundle=read(stage/'build-inputs.json');assert sha(Path(bundle['path']))==bundle['sha256']
 before=read(REPO/'outputs/arcane-051-release-20261109/preserved-work/manifest.json')
 for name in ['installed-exe','save-one','save-two']:assert sha(Path(before[name]['path'])).lower()==before[name]['sha256'].lower()
 return prep
def release(stage):
 prep=gate(stage);source=read(stage/'source-publication.json');commit=source['commit'];assert git('merge-base','--is-ancestor',commit,'HEAD')==''
 bundle=read(stage/'build-inputs.json');assets=[p['path'] for p in prep['assets']]+[bundle['path']]
 env=dict(os.environ,GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='Never')
 subprocess.run([sys.executable,str(REPO/'tools/PublishLauncherRelease.py'),prep['version'],commit,str(stage/'notes.md'),*assets,'--tag','patch-'+prep['version'],'--name','Paw’s Patch 0.5.1 beta — Arcane Wars','--prerelease'],cwd=REPO,env=env,check=True)
 result=json.loads(fetch(API+'/releases/tags/patch-'+prep['version']));assert not result['draft'] and result['prerelease'];remote={x['name']:x for x in result['assets']}
 for path in map(Path,assets):
  record=remote[path.name];raw=fetch(record['browser_download_url']);assert len(raw)==path.stat().st_size and hashlib.sha256(raw).hexdigest().upper()==sha(path) and record['digest']=='sha256:'+sha(path).lower()
 write(stage/'public-assets.json',dict(passed=True,commit=commit,url=result['html_url'],assets=len(assets)));print('ARCANE_BETA_PUBLIC_ASSETS_PASS',len(assets),flush=True)
def promote(stage):
 prep=gate(stage);assert read(stage/'public-assets.json')['passed'];scope=read(stage/'public-catalogs/scope.json');head=git('rev-parse','HEAD');assert head==scope['publicHead']==git('ls-remote','origin','refs/heads/main').split()[0]
 staged=set(git('diff','--cached','--name-only').splitlines());assert not staged.intersection(scope['allowed']),'Catalogs already staged by another operation'
 preserved_index=subprocess.check_output(['git','diff','--cached','--binary'],cwd=REPO)
 public=RAW.replace('/main/','/'+head+'/')
 for rel,h in scope['baseline'].items():assert sha(REPO/rel)==h and normalize(fetch(public+rel))==normalize((REPO/rel).read_bytes()),rel
 for rel in scope['allowed']:shutil.copy2(stage/'public-catalogs/signed'/rel,REPO/rel)
 git('add','--',*scope['allowed']);assert set(git('diff','--cached','--name-only').splitlines())==set(scope['allowed'])|staged
 git('commit','--only','-m','Publish signed Arcane Wars 0.5.1 beta catalogs','--',*scope['allowed'])
 assert subprocess.check_output(['git','diff','--cached','--binary'],cwd=REPO)==preserved_index,'Unrelated staged work changed'
 commit=git('rev-parse','HEAD');git('push','origin','HEAD:main');public=RAW.replace('/main/','/'+commit+'/')
 for rel in scope['allowed']:assert normalize(fetch(public+rel))==normalize((REPO/rel).read_bytes()),rel
 for prefix in ['v2','v3']:assert verify(json.loads(fetch(public+'feed/'+prefix+'/beta.json')),key())['patchGuide']['version']==prep['version']
 write(stage/'publication.json',dict(passed=True,version=prep['version'],sourceCommit=read(stage/'source-publication.json')['commit'],catalogCommit=commit,url=read(stage/'public-assets.json')['url'],installedGameModified=False));print('ARCANE_BETA_CATALOGS_PUBLIC_PASS',commit,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['gate','release','promote']);p.add_argument('--stage',required=True,type=Path);a=p.parse_args();globals()[a.action](a.stage.resolve())
