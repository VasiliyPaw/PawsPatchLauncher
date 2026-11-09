"""Explicit publication gates for the authorized accepted-beta promotion."""
import argparse,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];OUT=REPO/'outputs/arcane-051-release-20261109';STAGE=OUT/'stable'
sys.path.insert(0,str(REPO/'tools'))
from PrepareRelease081 import fetch,key,RAW,API,normalize
from PrepareRelease070 import verify,sha,validate_package
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def write(p,o):p.write_text(json.dumps(o,indent=2,ensure_ascii=False))
def git(*args):return subprocess.check_output(['git',*args],cwd=REPO,text=True).strip()
def gate():
 prep=read(STAGE/'preparation.json');assert prep['version']=='0.5.0' and len(prep['assets'])==17
 assert '619010 assertions; 55296 selections' in (STAGE/'catalog-checks.log').read_text()
 summary=read('C:/PawsArcane051ReleaseQA-20261109/stable-install/summary.json');assert summary['complete'] and summary['planned']==12
 for n,row in read(STAGE/'helpers/build-report.json').items():assert sha(STAGE/'helpers'/n)==row['sha256']
 for a in prep['assets']:validate_package(Path(a['path']),dict(id=a['id'],version='0.5.0',sha256=a['sha256'],size=a['size']))
 for prefix in ['v2','v3']:
  before=verify(read(OUT/'before/feed'/prefix/'stable.json'),key());after=verify(read(STAGE/'signed/feed'/prefix/'stable.json'),key())
  assert before['launcher']==after['launcher'] and before.get('modGuides')==after.get('modGuides')
  assert [p for p in before['packages'] if p.get('mods')!=['arcane-wars']]==[p for p in after['packages'] if p.get('mods')!=['arcane-wars']]
  assert after['patchGuide']['version']=='0.5.0'
 for label in ['installed-exe','save-one','save-two']:
  saved=read(OUT/'preserved-work/manifest.json')[label];assert sha(Path(saved['path'])).lower()==saved['sha256'].lower()
 return prep
def source():
 prep=gate();assert not git('diff','--cached','--name-only'),'Another chat has staged work'
 assert git('rev-parse','HEAD')==prep['baselineCommit'] and git('ls-remote','origin','refs/heads/main').split()[0]==prep['baselineCommit']
 git('add','--','tools/Arcane051Release','docs/release-patch-0.5.0.json','docs/verification-arcane-stable-0.5.0-20261109.md')
 names=git('diff','--cached','--name-only').splitlines();assert all(n.startswith('tools/Arcane051Release/') or n in ['docs/release-patch-0.5.0.json','docs/verification-arcane-stable-0.5.0-20261109.md'] for n in names)
 git('commit','-m','Prepare Arcane Wars 0.5.0 promotion from the accepted beta');commit=git('rev-parse','HEAD');git('push','origin','HEAD:main')
 write(STAGE/'source-publication.json',dict(commit=commit,files=names));print('STABLE_SOURCE_PUSHED',commit,flush=True)
def release():
 prep=gate();commit=read(STAGE/'source-publication.json')['commit'];env=dict(os.environ,GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='Never')
 args=[sys.executable,str(REPO/'tools/PublishLauncherRelease.py'),'0.5.0',commit,str(STAGE/'notes.md'),*[a['path'] for a in prep['assets']],'--tag','patch-0.5.0','--name',"Paw’s Patch 0.5.0 — Arcane Wars"]
 subprocess.run(args,cwd=REPO,env=env,check=True)
 r=json.loads(fetch(API+'/releases/tags/patch-0.5.0'));assert not r['draft'] and not r['prerelease'];assets={a['name']:a for a in r['assets']}
 for a in prep['assets']:
  public=fetch(a['url']);remote=assets[Path(a['path']).name];assert len(public)==a['size']==remote['size'] and hashlib.sha256(public).hexdigest().upper()==a['sha256'] and remote['digest']=='sha256:'+a['sha256'].lower()
 write(STAGE/'public-assets.json',dict(passed=True,commit=commit,url=r['html_url'],assets=len(assets)));print('STABLE_PUBLIC_ASSETS_PASS',len(assets),flush=True)
def promote():
 gate();assert read(STAGE/'public-assets.json')['passed'];head=git('ls-remote','origin','refs/heads/main').split()[0];assert head==git('rev-parse','HEAD')
 allowed=['feed/v3/stable.json','feed/v2/stable.json','feed/changelog.history.json','feed/patch-guide.json']
 # Serialize publications and reject public/local catalog movement, including other channels.
 for p in [*allowed,'feed/v3/beta.json','feed/v2/beta.json','feed/stable.json','feed/beta.json','feed/patch-guide-beta.json']:
  old=(OUT/'before'/p).read_bytes();assert normalize((REPO/p).read_bytes())==normalize(old) and normalize(fetch(RAW.replace('/main/','/'+head+'/')+p))==normalize(old),p
 assert not git('diff','--cached','--name-only')
 for rel in allowed:shutil.copy2(STAGE/'signed'/rel,REPO/rel)
 git('add','--',*allowed);assert set(git('diff','--cached','--name-only').splitlines())==set(allowed)
 git('commit','-m','Publish signed Arcane Wars 0.5.0 stable catalogs');commit=git('rev-parse','HEAD');git('push','origin','HEAD:main')
 for rel in allowed:assert normalize(fetch(RAW.replace('/main/','/'+commit+'/')+rel))==normalize((REPO/rel).read_bytes()),rel
 for prefix in ['v2','v3']:assert verify(json.loads(fetch(RAW.replace('/main/','/'+commit+'/')+'feed/'+prefix+'/stable.json')),key())['patchGuide']['version']=='0.5.0'
 write(STAGE/'publication.json',dict(passed=True,version='0.5.0',sourceCommit=read(STAGE/'source-publication.json')['commit'],catalogCommit=commit,assets=17,installationCases=12,catalogSelections=55296,installedGameModified=False))
 print('STABLE_CATALOGS_PUBLIC_PASS',commit,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['gate','source','release','promote']);args=p.parse_args();globals()[args.action]()
