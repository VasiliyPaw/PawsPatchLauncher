"""Stage signed Arcane beta catalogs against a fresh public baseline only."""
import argparse,copy,json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization
REPO=Path(__file__).resolve().parents[2];sys.path.insert(0,str(REPO/'tools'))
from PrepareRelease081 import fetch,key,sign,RAW,normalize
from PrepareRelease070 import verify,encode,sha,validate_package
KEY=Path('G:/CodexData/projects/Codex/2026-08-11/kohan-ii-d-steamlibrary-steamapps-common/work/PawsPatchLauncher/.local/signing/pawpatch-signing-private.pem')
FEEDS=[f'feed/{prefix}{channel}.json' for prefix in ['v3/','v2/',''] for channel in ['stable','beta']]
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(encode(o))
def stage(root):
 prep=read(root/'preparation.json');version=prep['version'];assert version=='0.5.1-beta.1'
 for asset in prep['assets']:validate_package(Path(asset['path']),dict(id=asset['id'],version=version,sha256=asset['sha256'],size=asset['size']))
 head=subprocess.check_output(['git','ls-remote','origin','refs/heads/main'],cwd=REPO,text=True).split()[0]
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==head
 public=RAW.replace('/main/','/'+head+'/');out=root/'public-catalogs';assert not out.exists();out.mkdir();baseline={}
 private=serialization.load_pem_private_key(KEY.read_bytes(),None);assert private.public_key().public_numbers()==key().public_numbers()
 allowed=[];guide=None
 for relative in FEEDS:
  original=(REPO/relative).read_bytes();assert normalize(fetch(public+relative))==normalize(original),relative
  before=verify(json.loads(original),key());write(out/'before'/relative,json.loads(original));baseline[relative]=sha(REPO/relative)
  after=copy.deepcopy(before)
  if relative in ['feed/v3/beta.json','feed/v2/beta.json']:
   assert next(p for p in before['packages'] if p['id']=='pawpatch-core')['version']=='0.5.0-beta.4'
   after['packages']=[copy.deepcopy(prep['replacements'][p['id']]) if p.get('mods')==['arcane-wars'] and p['id'] in prep['replacements'] else p for p in before['packages']]
   assert [p for p in after['packages'] if p.get('mods')!=['arcane-wars']]==[p for p in before['packages'] if p.get('mods')!=['arcane-wars']]
   after['patchGuide']['version']=version
   after['patchGuide']['entries'].insert(0,dict(id='presentation-051',category='always',titleRu='Плавность и интерфейс',titleEn='Performance and interface',bodyRu='- Улучшена работа кэшей моделей и анимаций.\n- Добавлены часы суток и масштабирование миникарты колёсиком.\n- Исправлены окно выхода и статистика фортов.\n- Улучшена воздушная разведка ботов.',bodyEn='- Improved model and animation caching.\n- Added a time-of-day clock and minimap zoom with the mouse wheel.\n- Fixed the exit dialog and fort statistics.\n- Improved AI aerial scouting.'))
   after.update(publishedAt=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),changelog=[prep['note']]+before['changelog'],newsTitle=prep['note']['title'],newsBody=prep['note']['body'])
   assert {k:v for k,v in before.items() if k not in ['packages','patchGuide','publishedAt','changelog','newsTitle','newsBody']}=={k:v for k,v in after.items() if k not in ['packages','patchGuide','publishedAt','changelog','newsTitle','newsBody']}
   write(out/'signed'/relative,sign(after,private));allowed.append(relative)
   if guide is None:guide=after['patchGuide']
  else:assert after==before
 for relative in ['feed/changelog.history.json','feed/patch-guide-beta.json']:
  original=(REPO/relative).read_bytes();assert normalize(fetch(public+relative))==normalize(original),relative
  baseline[relative]=sha(REPO/relative);write(out/'before'/relative,json.loads(original))
 history=read(REPO/'feed/changelog.history.json');history['beta']=[prep['note']]+history['beta']
 write(out/'signed/feed/changelog.history.json',history);write(out/'signed/feed/patch-guide-beta.json',guide)
 allowed+=['feed/changelog.history.json','feed/patch-guide-beta.json']
 write(out/'scope.json',dict(publicHead=head,baseline=baseline,allowed=allowed,version=version,unchanged=['all stable gameplay','Pure and Immortals beta','legacy gameplay','launcher']))
 print('ARCANE_BETA_PUBLIC_CATALOGS_STAGED',head,'no public writes')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);a=p.parse_args();stage(a.stage.resolve())
