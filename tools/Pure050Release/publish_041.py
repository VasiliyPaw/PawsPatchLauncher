"""Serial Pure-only promotion; public package verification precedes catalog writes."""
import argparse,copy,subprocess,zipfile
from datetime import datetime,timezone
from context import *
from cryptography.hazmat.primitives import serialization
from PrepareRelease081 import fetch,key,sign,RAW,normalize
from PrepareRelease070 import verify,encode,validate_package
STAGE=OUT/'stable-publication'
KEY=LEG/'PawsPatchLauncher/.local/signing/pawpatch-signing-private.pem'
FEEDS=['feed/'+p+c+'.json'for p in ['v3/','v2/','']for c in ['stable','beta']]
IDS={'pure-fixes-data','pure-fixes-runtime','pure-beta-common'}
def head():return subprocess.check_output(['git','ls-remote','origin','refs/heads/main'],cwd=REPO,text=True).split()[0]
def scoped(a,b):
 for k in a:
  if k not in ['packages','modGuides','changelog','publishedAt']:assert a[k]==b[k],k
 assert [p for p in a['packages']if p['id']not in IDS]==[p for p in b['packages']if p['id']not in IDS]
 assert [g for g in a.get('modGuides',[])if g['id']not in ['vanilla','immortals']]==[g for g in b.get('modGuides',[])if g['id']not in ['vanilla','immortals']]
def prepare():
 STAGE.mkdir(exist_ok=True);assert not (STAGE/'preparation.json').exists();commit=head();raw=RAW.replace('/main/','/'+commit+'/');private=serialization.load_pem_private_key(KEY.read_bytes(),None);assert private.public_key().public_numbers()==key().public_numbers()
 notes=(REPO/'docs/release-pure-0.4.1.md').read_text();sections=notes.split('\n---\n');body={lang:part.strip().split('\n',2)[2].strip()for lang,part in zip(['ru','en'],sections)}
 entry=dict(category='patch',version='0.4.1',publishedAt='2026-11-09',title={lang:'Paw’s Patch 0.4.1 — Vanilla / Immortals'for lang in ['ru','en']},body=body,mods=['vanilla','immortals'],channel='stable');write(REPO/'docs/release-pure-0.4.1.json',entry)
 packages={p['id']:p for p in read(OUT/'stable-stage/packages.json')};before={};after={};baseline={}
 # Fetch the newest catalogs after Arcane's independently completed promotion.
 for rel in FEEDS:
  data=fetch(raw+rel);assert normalize(data)==normalize((REPO/rel).read_bytes()),rel;baseline[rel]=sha(REPO/rel);p=STAGE/'before'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);before[rel]=verify(json.loads(data),key())
 guide=copy.deepcopy(next(g for g in before['feed/v3/beta.json']['modGuides']if g['id']=='vanilla')['patchGuide']);guide['version']='0.4.1';guide['entries']=[e for e in guide['entries']if e['id']!='pure-match-recovery']
 guide['entries'].append(dict(id='pure-multiplayer-saves',category='always',titleRu='Сетевые сохранения',titleEn='Multiplayer saves',bodyRu='Автосохранение сетевого матча каждые пять игровых минут в MP Autosave A и B. При сохранении хостом клиенты записывают локальную копию, если карта поддерживает сохранение. Автоматическое восстановление после отключения игрока выключено; продолжить можно обычной загрузкой сейва в лобби.',bodyEn='Multiplayer autosaves every five game minutes, alternating MP Autosave A and B. Clients write a local copy when the host saves if the loaded map supports saving. Automatic recovery after disconnection is disabled; load a save through the normal lobby flow to continue.'))
 for rel,a in before.items():
  if 'modGuides' not in a:
   target=STAGE/'signed'/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((STAGE/'before'/rel).read_bytes());continue
  b=copy.deepcopy(a);b['packages']=[copy.deepcopy(packages.get(p['id'],p))for p in a['packages']]
  for g in b['modGuides']:
   if g['id']in ['vanilla','immortals']:
    own=copy.deepcopy(next(x for x in before['feed/v3/beta.json']['modGuides']if x['id']==g['id'])['patchGuide']);own['version']='0.4.1';own['entries']=[e for e in own['entries']if e['id']!='pure-match-recovery']+[copy.deepcopy(guide['entries'][-1])];g['patchGuide']=own
  b['changelog']=[entry]+[e for e in b['changelog']if not(e.get('category')=='patch'and e.get('version')=='0.4.1'and e.get('mods')==['vanilla','immortals'])];b['publishedAt']=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ');scoped(a,b);after[rel]=b;write(STAGE/'signed'/rel,sign(b,private))
 history_path='feed/changelog.history.json';data=fetch(raw+history_path);assert normalize(data)==normalize((REPO/history_path).read_bytes());baseline[history_path]=sha(REPO/history_path);history=json.loads(data)
 for channel in ['stable','beta']:history[channel]=[entry]+history[channel]
 write(STAGE/'changelog.history.json',history);write(STAGE/'preparation.json',dict(publicHead=commit,baseline=baseline,packages=list(packages.values()),notesSha256=sha(REPO/'docs/release-pure-0.4.1.md')))
 print('PURE_041_CATALOGS_STAGED',commit,len(FEEDS),'Arcane and launcher preserved')
def verify_assets():
 proof={}
 for p in read(OUT/'stable-stage/packages.json'):
  data=fetch(p['urls'][0]);assert len(data)==p['size']and hashlib.sha256(data).hexdigest().upper()==p['sha256'];path=STAGE/'public-assets'/p['urls'][0].rsplit('/',1)[1];path.parent.mkdir(exist_ok=True);path.write_bytes(data);validate_package(path,p);proof[p['id']]=p['sha256'];print('PURE_PUBLIC_ASSET_VERIFIED',p['id'],flush=True)
 write(STAGE/'public-assets.json',proof)
def promote():
 prep=read(STAGE/'preparation.json');assert read(STAGE/'public-assets.json');assert (STAGE/'acceptance.json').is_file()and read(STAGE/'acceptance.json')['passed']
 for rel,digest in prep['baseline'].items():assert sha(REPO/rel)==digest,rel
 for rel in FEEDS:
  assert normalize(fetch(RAW+rel))==normalize((REPO/rel).read_bytes()),rel;scoped(verify(read(REPO/rel),key()),verify(read(STAGE/'signed'/rel),key()))
 for rel in FEEDS:(REPO/rel).write_bytes((STAGE/'signed'/rel).read_bytes())
 (REPO/'feed/changelog.history.json').write_bytes((STAGE/'changelog.history.json').read_bytes());print('PURE_041_PROMOTED_LOCALLY; push/readback required')
def readback():
 commit=head();assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==commit;raw=RAW.replace('/main/','/'+commit+'/')
 for rel in FEEDS:
  public=verify(json.loads(fetch(raw+rel)),key());assert public==verify(read(REPO/rel),key());scoped(verify(read(STAGE/'before'/rel),key()),public)
 assert json.loads(fetch(raw+'feed/changelog.history.json'))==read(REPO/'feed/changelog.history.json');write(STAGE/'readback.json',dict(passed=True,catalogCommit=commit,patch='0.4.1'));print('PURE_041_PUBLIC_READBACK_PASS',commit)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','verify_assets','promote','readback']);a=p.parse_args();globals()[a.action]()
