"""Stage/sign Arcane world options from accepted inputs. No upload or install."""
import argparse,copy,hashlib,json,re,shutil,subprocess,zipfile
from datetime import datetime,timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from PrepareRelease081 import key,sign,fetch,RAW,normalize
from PrepareRelease070 import verify,encode,validate_package
ROOT=Path(__file__).resolve().parents[1]
VERSION='0.5.0-beta.3'
def sha(data):return hashlib.sha256(data).hexdigest().upper()
def main():
 ap=argparse.ArgumentParser()
 for name in ('out','helpers','fixture','baseline-assets','private-key','launcher-artifacts'):ap.add_argument('--'+name,type=Path,required=True)
 a=ap.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 private=serialization.load_pem_private_key(a.private_key.read_bytes(),None);assert private.public_key().public_numbers()==key().public_numbers()
 prep=json.loads((a.fixture/'preparation.json').read_text(encoding='utf-8'));assert prep['dynamicDayCycleSeconds']==600
 overrides={rel.lower().replace('\\','/'):(a.fixture/'game'/rel).read_bytes() for rel in prep['changed']}
 assert all(sha(overrides[rel.lower().replace('\\','/')])==digest for rel,digest in prep['changed'].items())
 report=json.loads((a.helpers/'build-report.json').read_text());assert len(report)==8
 assert all(r['features']['patchVersion']==VERSION and r['features']['dynamicDayCycleSeconds']==600 and r['features']['legacySaveLobbyRecovery'] is False for r in report.values())
 launcher=json.loads((a.launcher_artifacts/'launcher-artifact.json').read_text(encoding='utf-8-sig'));assert launcher['version']=='1.0.8'
 assert launcher['authenticodeStatus']=='NotSigned' and not launcher['authenticodeRequired']
 revision=subprocess.check_output(['git','ls-remote','origin','refs/heads/main'],cwd=ROOT,text=True).split()[0]
 assert launcher['sourceCommit']==revision
 remote=RAW.replace('/main/','/'+revision+'/');base={};assets={};audits={}
 targets=('feed/v3/beta.json','feed/v2/beta.json')
 for path in (*targets,'feed/v3/stable.json','feed/v2/stable.json','feed/beta.json','feed/stable.json','feed/changelog.history.json','feed/patch-guide-beta.json'):
  raw=(ROOT/path).read_bytes();assert normalize(fetch(remote+path))==normalize(raw),path
  p=out/'before'/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
  if path in targets:base[path]=verify(json.loads(raw),key())
 notes=json.loads((ROOT/'docs/release-0.5.0-beta.3.json').read_text(encoding='utf-8'));assert set(notes['body'])=={'en','ru','de','fr','cs','uk'}
 for package in base[targets[0]]['packages']:
  pid=package['id']
  if package.get('mods')!=['arcane-wars'] or package['version']!='0.5.0-beta.2':continue
  src=a.baseline_assets/(pid+'-'+package['version']+'.zip');assert sha(src.read_bytes())==package['sha256']
  with zipfile.ZipFile(src) as z:
   module=json.loads(z.read('module.json'));files={f['path']:z.read('payload/'+f['path']) for f in module['files']}
  old=copy.deepcopy(files)
  for rel in list(files):
   leaf=Path(rel).name
   if leaf in report:
    value=(a.helpers/leaf).read_bytes();assert sha(value)==report[leaf]['sha256'];files[rel]=value
   elif leaf=='paws_patch_versions.ini':files[rel]=(a.helpers/leaf).read_bytes()
   if rel.lower().replace('\\','/') in overrides:files[rel]=overrides[rel.lower().replace('\\','/')]
  # Core covers shared definitions. Every locale overlay must keep identical
  # shared bytes and own its final text layer, including Russian's hotfix.
  index={p.lower().replace('\\','/'):p for p in files}
  wanted=set(overrides) if pid=='pawpatch-core' else set()
  if pid.startswith('pawpatch-data'):
   wanted|={'data/sun/paws_dynamic_sun.tgi'}
   if pid=='pawpatch-data-ru':wanted|={'local_aw_ru_hotfix/localization/strings_data_k2.tgi'}
  for rel in wanted:files[index.get(rel,rel)]=overrides[rel]
  module['version']=VERSION;module['files']=[dict(path=n,size=len(b),sha256=sha(b)) for n,b in sorted(files.items())]
  target=out/'assets'/(pid+'-'+VERSION+'.zip');target.parent.mkdir(exist_ok=True)
  with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
   z.writestr('module.json',encode(module))
   for n,b in sorted(files.items()):z.writestr('payload/'+n,b)
  assets[pid]=dict(path=str(target),sha256=sha(target.read_bytes()),size=target.stat().st_size)
  validate_package(target,dict(package,version=VERSION,**{k:assets[pid][k] for k in ('sha256','size')}))
  audits[pid]=[p for p,b in files.items() if old.get(p)!=b]
 assert len(assets)==10
 for f in launcher['files']:
  p=a.launcher_artifacts/f['name'];assert sha(p.read_bytes())==f['sha256'] and p.stat().st_size==f['size'];shutil.copy2(p,out/'assets'/p.name)
 shutil.copy2(a.launcher_artifacts/'launcher-artifact.json',out/'assets/launcher-artifact.json')
 exe=next(f for f in launcher['files'] if f['name']=='PawsPatchLauncher.exe')
 launch=dict(version='1.0.8',size=exe['size'],sha256=exe['sha256'],urls=['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/patch-'+VERSION+'/PawsPatchLauncher.exe'])
 afters={}
 for path in targets:
  after=copy.deepcopy(base[path])
  for p in after['packages']:
   if p['id'] not in assets:continue
   item=assets[p['id']];p.update(version=VERSION,sha256=item['sha256'],size=item['size'],urls=['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/patch-'+VERSION+'/'+Path(item['path']).name]);p.pop('url',None)
  assert [p for p in after['packages'] if p['id'] not in assets]==[p for p in base[path]['packages'] if p['id'] not in assets]
  after.update(launcher=launch,publishedAt=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),newsTitle=notes['title'],newsBody=notes['body'])
  after['changelog']=[notes]+after.get('changelog',[])
  if isinstance(after.get('patchGuide'),dict):
   after['patchGuide']['version']=VERSION
   after['patchGuide']['entries']=[dict(id='world-options',category='always',titleRu='Динамические сутки и выбор биомов',titleEn='Dynamic daylight and biome selection',bodyRu=notes['body']['ru'],bodyEn=notes['body']['en'])]+[e for e in after['patchGuide']['entries'] if e.get('id')!='world-options']
  p=out/'signed'/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(encode(sign(after,private)));afters[path]=after
 history=json.loads((ROOT/'feed/changelog.history.json').read_text());history['beta']=[notes]+history['beta']
 for path,obj in [('feed/changelog.history.json',history),('feed/patch-guide-beta.json',afters[targets[0]]['patchGuide'])]:
  p=out/'signed'/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(encode(obj))
 (out/'preparation.json').write_bytes(encode(dict(version=VERSION,sourceCommit=revision,assets=assets,dataOverrides=prep['changed'],changedFiles=audits,launcher=launch,cycleSeconds=600)))
 (out/'notes.md').write_text(notes['title']['ru']+'\n\n'+notes['body']['ru']+'\n\n'+notes['title']['en']+'\n\n'+notes['body']['en']+'\n\nЛаунчер 1.0.8 включён в каталог беты. Stable/Pure/Immortals не изменены.\n',encoding='utf-8')
 print('WORLD_OPTIONS_BETA_STAGED',len(assets),'patch packages; cycle=600; launcher=1.0.8; no upload or install')
if __name__=='__main__':main()
