"""Stage/sign Arcane beta without active-match return. No install/upload."""
import argparse,copy,hashlib,json,subprocess,zipfile
from datetime import datetime,timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from PrepareRelease081 import key,sign,fetch,RAW,normalize
from PrepareRelease070 import verify,encode,validate_package
ROOT=Path(__file__).resolve().parents[1]
VERSION='0.5.0-beta.4'
def sha(b):return hashlib.sha256(b).hexdigest().upper()
def main():
 ap=argparse.ArgumentParser()
 for name in ['out','helpers','baseline-assets','private-key']:ap.add_argument('--'+name,type=Path,required=True)
 a=ap.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 private=serialization.load_pem_private_key(a.private_key.read_bytes(),None);assert private.public_key().public_numbers()==key().public_numbers()
 report=json.loads((a.helpers/'build-report.json').read_text());assert len(report)==8
 assert all(r['features']['patchVersion']==VERSION and r['features']['hotJoinRevision']==0 and r['features']['legacySaveLobbyRecovery'] is False and 'hotJoinProtocol' not in r['features'] for r in report.values())
 notes=json.loads((ROOT/('docs/release-'+VERSION+'.json')).read_text(encoding='utf-8'));assert set(notes['body'])=={'en','ru','de','fr','cs','uk'}
 revision=subprocess.check_output(['git','ls-remote','origin','refs/heads/main'],cwd=ROOT,text=True).split()[0]
 remote=RAW.replace('/main/','/'+revision+'/');before={};assets={};audits={};feeds={}
 paths=['feed/v3/beta.json','feed/v2/beta.json','feed/changelog.history.json','feed/patch-guide-beta.json']
 for path in paths:
  raw=(ROOT/path).read_bytes();assert normalize(fetch(remote+path))==normalize(raw),path
  dst=out/'before'/path;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(raw);before[path]=raw
 for path in paths[:2]:
  previous=verify(json.loads(before[path]),key());feed=copy.deepcopy(previous)
  for package in feed['packages']:
   if package.get('mods')!=['arcane-wars'] or package['version']!='0.5.0-beta.3':continue
   src=a.baseline_assets/(package['id']+'-'+package['version']+'.zip');assert sha(src.read_bytes())==package['sha256']
   with zipfile.ZipFile(src) as z:
    module=json.loads(z.read('module.json'));files={f['path']:z.read('payload/'+f['path']) for f in module['files']}
   changed=[]
   for rel in files:
    leaf=Path(rel).name
    if leaf in report:
     b=(a.helpers/leaf).read_bytes();assert sha(b)==report[leaf]['sha256'];files[rel]=b;changed.append(rel)
    elif leaf=='paws_patch_versions.ini':files[rel]=(a.helpers/leaf).read_bytes();changed.append(rel)
   if not changed:continue
   pid=package['id']
   if pid not in assets:
    module['version']=VERSION;module['files']=[dict(path=n,size=len(b),sha256=sha(b)) for n,b in sorted(files.items())]
    target=out/'assets'/(pid+'-'+VERSION+'.zip');target.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
     z.writestr('module.json',encode(module))
     for n,b in sorted(files.items()):z.writestr('payload/'+n,b)
    assets[pid]=dict(path=str(target),sha256=sha(target.read_bytes()),size=target.stat().st_size);audits[pid]=changed
    validate_package(target,dict(package,version=VERSION,**{k:assets[pid][k] for k in ['sha256','size']}))
   item=assets[pid];package.update(version=VERSION,sha256=item['sha256'],size=item['size'],urls=['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/patch-'+VERSION+'/'+Path(item['path']).name]);package.pop('url',None)
  assert set(assets)=={'pawpatch-core','player-colors','desync-continue','common-ui'}
  assert [p for p in previous['packages'] if p['id'] not in assets]==[p for p in feed['packages'] if p['id'] not in assets]
  assert feed['launcher']==previous['launcher']
  feed.update(publishedAt=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),newsTitle=notes['title'],newsBody=notes['body'])
  feed['changelog']=[notes]+[x for x in feed['changelog'] if x.get('version')!=VERSION]
  guide=feed['patchGuide'];guide['version']=VERSION
  guide['entries']=[dict(id='network-session',category='always',titleRu='Сетевые партии',titleEn='Multiplayer matches',bodyRu=notes['body']['ru'],bodyEn=notes['body']['en'])]+[x for x in guide['entries'] if x['id'] not in ['hotjoin','network-session']]
  dst=out/'signed'/path;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(encode(sign(feed,private)));feeds[path]=feed
 history=json.loads(before['feed/changelog.history.json']);history['beta']=[notes]+[x for x in history['beta'] if x.get('version')!=VERSION]
 for path,obj in [('feed/changelog.history.json',history),('feed/patch-guide-beta.json',feeds[paths[0]]['patchGuide'])]:
  dst=out/'signed'/path;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(encode(obj))
 (out/'preparation.json').write_bytes(encode(dict(version=VERSION,baselineCommit=revision,assets=assets,changedFiles=audits,activeMatchAdmission=False,legacySaveLobbyRecovery=False,launcherChanged=False)))
 (out/'notes.md').write_text(notes['title']['ru']+'\n\n'+notes['body']['ru']+'\n\n'+notes['title']['en']+'\n\n'+notes['body']['en']+'\n',encoding='utf-8')
 print('NO_HOTJOIN_BETA_STAGED',len(assets),'Arcane packages; no game launch/install/upload')
if __name__=='__main__':main()
