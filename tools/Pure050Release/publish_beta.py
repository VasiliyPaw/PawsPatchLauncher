"""Publish only the accepted Pure beta; preserve all stable/other-mode catalogs."""
import argparse,base64,copy,subprocess,urllib.request,urllib.parse,time,zipfile
from datetime import datetime,timezone
from context import *
from PrepareRelease081 import fetch,key,sign,RAW,API,normalize
from PrepareRelease070 import verify,validate_package
from cryptography.hazmat.primitives import serialization

STAGE=OUT/'beta-publication';TAG='patch-pure-0.5.0-beta.1';VERSION='0.5.0-beta.1';KEY=LEG/'PawsPatchLauncher/.local/signing/pawpatch-signing-private.pem'
FEEDS=['feed/'+p+c+'.json'for p in ['v3/','v2/','']for c in ['stable','beta']]
IDS={p['id']for p in read(OUT/'beta-stage-r4/packages.json')}

def head():return subprocess.check_output(['git','ls-remote','origin','refs/heads/main'],cwd=REPO,text=True).split()[0]
def scoped(a,b,rel):
 if rel.endswith('stable.json')or'modGuides'not in a:assert a==b;return
 for k in a:
  if k not in ['packages','modGuides','changelog','publishedAt']:assert a[k]==b[k],k
 assert[p for p in a['packages']if p['id']not in IDS]==[p for p in b['packages']if p['id']not in IDS]
 assert[g for g in a['modGuides']if g['id']not in ['vanilla','immortals']]==[g for g in b['modGuides']if g['id']not in ['vanilla','immortals']]

def entry():
 sections=(REPO/('docs/release-pure-'+VERSION+'.md')).read_text().split('\n---\n');return dict(category='patch',version=VERSION,publishedAt='2026-11-09',title={lang:'Paw’s Patch 0.5.0 beta 1 — Vanilla / Immortals'for lang in ['ru','en']},body={lang:s.strip().split('\n',2)[2].strip()for lang,s in zip(['ru','en'],sections)},mods=['vanilla','immortals'],channel='beta')

def guide(g):
 g=copy.deepcopy(g);g['version']=VERSION
 for e in g['entries']:
  if e['id']=='base':e.update(bodyRu='Исправления и новые настройки карт для выбранного режима. Включаются компонентом Paw’s Patch; выбор сохраняется отдельно для каждого режима. Язык игры выбирается независимо.',bodyEn='Fixes and additional map options for the selected mode. Enabled through Paw’s Patch, with separate mode settings. Game language is selected independently.')
  if e['id']=='terrain':e.update(bodyRu='При создании карты инициализирует параметр рельефа, который мог содержать случайные данные памяти. Требуется поддерживаемый EXE 1.3.72.',bodyEn='Initializes a terrain parameter that could contain uninitialized memory during map creation. Requires the supported 1.3.72 executable.')
  if e['id']=='pure-maps':e.update(bodyRu='Случайный тип карты и время суток, до 16 королевств и 8 команд; размеры карт до 2048×2048 с расширенной вместимостью объектов. Лимиты рот и очков королевства сохраняются.',bodyEn='Random map type and time of day, up to 16 kingdoms and 8 teams; maps up to 2048×2048 with expanded object capacity. Native company and kingdom-point limits are retained.')
 additions=[
 ('pure-dynamic-day','Динамические сутки','Dynamic day and night','В параметре «Время суток» выберите «Динамически»: утро, день, вечер и ночь за 10 игровых минут со случайным началом. Часы ЧЧ:ММ сверху по центру следуют симуляции, её паузе и скорости. Фаза сохраняется в сейве.','Choose Dynamic under Time of day: morning, noon, dusk and night over 10 game minutes, with a random start. The HH:MM clock at the top center follows simulation time, pause and speed. The phase is saved with the match.'),
 ('pure-mixed-biomes','Смешанные биомы','Mixed biomes','Новый тип карты объединяет крупные области лета, зимы и пустыни с родными объектами режима. «Все» использует три биома; «Случайно» с равной вероятностью выбирает один, два или три. Общие настройки логов и технологических построек.','A new map type combines broad temperate, arctic and desert regions with native mode objects. All uses three biomes; Random chooses one, two or three with equal probability. Shared lair and technology-site density controls.'),
 ('pure-presentation','Миникарта и окна','Minimap and dialogs','Колёсико над миникартой меняет масштаб от ×1 до ×4 с шагом 0,1. Увеличенная миникарта следует за камерой и сохраняет изображение при её движении. Дополнено центрирование выхода, игрового меню, сохранения и загрузки; часы не дублируются между партиями.','Hover over the minimap and use the wheel to zoom from ×1 to ×4 in 0.1 steps. The zoomed minimap follows the camera and stays visible as it moves. Additional centering for surrender, game menu, save and load; clock reuse across match transitions.')]
 for id,ru,en,bodyru,bodyen in additions:
  assert not any(e['id']==id for e in g['entries']);g['entries'].append(dict(id=id,category='always',titleRu=ru,titleEn=en,bodyRu=bodyru,bodyEn=bodyen))
 return g

def prepare():
 STAGE.mkdir(exist_ok=True);assert not(STAGE/'preparation.json').exists();commit=head();raw=RAW.replace('/main/','/'+commit+'/');private=serialization.load_pem_private_key(KEY.read_bytes(),None);assert private.public_key().public_numbers()==key().public_numbers();packages={p['id']:p for p in read(OUT/'beta-stage-r4/packages.json')};baseline={};note=entry();write(REPO/('docs/release-pure-'+VERSION+'.json'),note)
 for rel in FEEDS:
  data=fetch(raw+rel);assert normalize(data)==normalize((REPO/rel).read_bytes()),rel;baseline[rel]=sha(REPO/rel);path=STAGE/'before'/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);a=verify(json.loads(data),key());b=copy.deepcopy(a)
  if rel.endswith('beta.json')and'modGuides'in b:
   b['packages']=[copy.deepcopy(packages.get(p['id'],p))for p in a['packages']]
   for g in b['modGuides']:
    if g['id']in ['vanilla','immortals']:g['patchGuide']=guide(g['patchGuide'])
   b['changelog']=[note]+[e for e in b['changelog']if not(e.get('version')==VERSION and e.get('mods')==['vanilla','immortals'])];b['publishedAt']=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ');result=sign(b,private)
  else:result=json.loads(data)
  scoped(a,b,rel);target=STAGE/'signed'/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)if b==a else write(target,result)
 path='feed/changelog.history.json';data=fetch(raw+path);assert normalize(data)==normalize((REPO/path).read_bytes());baseline[path]=sha(REPO/path);history=json.loads(data);history['beta']=[note]+history['beta'];write(STAGE/'changelog.history.json',history);write(STAGE/'preparation.json',dict(publicHead=commit,baseline=baseline,packages=list(packages.values())));print('PURE_050_BETA_CATALOGS_STAGED',commit)

def token():
 p=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True,cwd=REPO,check=True);values=dict(s.split('=',1)for s in p.stdout.splitlines()if'='in s);return values['password']
def request(url,method='GET',data=None,content='application/json',octets=False):
 headers={'User-Agent':'PawsPure050Release','Authorization':'Bearer '+token(),'Accept':'application/octet-stream'if octets else'application/vnd.github+json','Content-Type':content,'X-GitHub-Api-Version':'2022-11-28'}
 req=urllib.request.Request(url,data=data,method=method,headers=headers)
 with urllib.request.urlopen(req,timeout=90)as r:body=r.read()
 return body if octets else json.loads(body)

def release():
 assert read(STAGE/'acceptance.json')['passed'];notes=(REPO/('docs/release-pure-'+VERSION+'.md')).read_text();release=request(API+'/releases',method='POST',data=json.dumps(dict(tag_name=TAG,target_commitish=head(),name='Paw’s Patch 0.5.0 beta 1 — Vanilla / Immortals',body=notes,draft=False,prerelease=True,make_latest='false')).encode());proof={}
 for path in sorted((OUT/'beta-stage-r4/assets').glob('*.zip')):
  result=request(release['upload_url'].split('{')[0]+'?name='+urllib.parse.quote(path.name),method='POST',data=path.read_bytes(),content='application/zip');readback=request(result['url'],octets=True);assert hashlib.sha256(readback).hexdigest().upper()==sha(path);proof[path.name]=dict(id=result['id'],size=len(readback),sha256=sha(path));print('PURE_BETA_RELEASE_ASSET_VERIFIED',path.name,flush=True)
 write(STAGE/'release.json',dict(id=release['id'],url=release['html_url'],assets=proof));print('PURE_BETA_RELEASE_PUBLISHED',release['html_url'])

def verify_assets():
 proof={}
 for p in read(OUT/'beta-stage-r4/packages.json'):
  data=fetch(p['urls'][0]);assert len(data)==p['size']and hashlib.sha256(data).hexdigest().upper()==p['sha256'];path=STAGE/'public-assets'/p['urls'][0].rsplit('/',1)[1];path.parent.mkdir(exist_ok=True);path.write_bytes(data);validate_package(path,p);proof[p['id']]=dict(sha256=p['sha256'],primary=p['urls'][0]);print('PURE_BETA_PUBLIC_URL_PASS',p['id'],flush=True)
 write(STAGE/'public-assets.json',proof)

def mirror(commit):
 assert head()==commit;private=serialization.load_pem_private_key(KEY.read_bytes(),None);assert private.public_key().public_numbers()==key().public_numbers();packages=read(OUT/'beta-stage-r4/packages.json');proof={}
 for p in packages:
  old=p['urls'][-1];name=old.rsplit('/',1)[1];url=RAW.replace('/main/','/'+commit+'/')+'feed/assets/pure-'+VERSION+'/'+name;data=fetch(url);assert len(data)==p['size']and hashlib.sha256(data).hexdigest().upper()==p['sha256'];target=STAGE/'public-assets'/name;target.parent.mkdir(exist_ok=True);target.write_bytes(data);validate_package(target,p);p['urls']=[url,old];proof[p['id']]=dict(sha256=p['sha256'],primary=url);print('PURE_BETA_IMMUTABLE_MIRROR_PASS',p['id'],flush=True)
 replacements={p['id']:p for p in packages}
 for rel in FEEDS:
  if not rel.endswith('beta.json'):continue
  a=verify(read(STAGE/'before'/rel),key());b=verify(read(STAGE/'signed'/rel),key())
  if'modGuides'not in b:continue
  b['packages']=[copy.deepcopy(replacements.get(p['id'],p))for p in b['packages']];scoped(a,b,rel);write(STAGE/'signed'/rel,sign(b,private))
 write(OUT/'beta-stage-r4/packages.json',packages);prep=read(STAGE/'preparation.json');prep.update(packages=packages,mirrorCommit=commit);write(STAGE/'preparation.json',prep);write(STAGE/'public-assets.json',proof)

def promote():
 assert read(STAGE/'acceptance.json')['passed']and len(read(STAGE/'public-assets.json'))==7
 for rel,h in read(STAGE/'preparation.json')['baseline'].items():assert sha(REPO/rel)==h;assert normalize(fetch(RAW+rel))==normalize((REPO/rel).read_bytes())
 for rel in FEEDS:
  scoped(verify(read(REPO/rel),key()),verify(read(STAGE/'signed'/rel),key()),rel);(REPO/rel).write_bytes((STAGE/'signed'/rel).read_bytes())
 (REPO/'feed/changelog.history.json').write_bytes((STAGE/'changelog.history.json').read_bytes());print('PURE_BETA_CATALOGS_PROMOTED_LOCALLY')

def readback():
 commit=head();assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==commit;raw=RAW.replace('/main/','/'+commit+'/')
 for rel in FEEDS:
  public=verify(json.loads(fetch(raw+rel)),key());assert public==verify(read(REPO/rel),key());scoped(verify(read(STAGE/'before'/rel),key()),public,rel)
 assert json.loads(fetch(raw+'feed/changelog.history.json'))==read(REPO/'feed/changelog.history.json');write(STAGE/'readback.json',dict(passed=True,catalogCommit=commit,patch=VERSION));print('PURE_BETA_PUBLIC_READBACK_PASS',commit)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','release','verify_assets','mirror','promote','readback']);ap.add_argument('--commit');a=ap.parse_args();mirror(a.commit)if a.action=='mirror'else globals()[a.action]()
