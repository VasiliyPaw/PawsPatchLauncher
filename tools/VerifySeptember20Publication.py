"""Read back immutable release bytes and signed catalogs. Never publishes."""
import argparse,json,hashlib,zipfile
from pathlib import Path
from PrepareRelease081 import API,RAW,FEEDS,fetch,key,normalize
from PrepareRelease070 import read,write,sha,verify

p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--commit',required=True)
p.add_argument('--launcher',action='store_true');p.add_argument('--catalog',action='store_true');a=p.parse_args()
stage=a.stage.resolve();out=stage/'publication';repo=Path(__file__).resolve().parents[1]
def get(path):return json.loads(fetch(API+path))
def release(tag,prerelease):
 r=get('/releases/tags/'+tag);assert not r['draft'] and r['prerelease']==prerelease
 ref=get('/git/ref/tags/'+tag)['object']
 while ref['type']=='tag':ref=get('/git/tags/'+ref['sha'])['object']
 assert ref['type']=='commit' and ref['sha']==a.commit,'Release source mismatch'
 return r
if a.catalog:
 proof=[]
 for channel,path in FEEDS.items():
  b=fetch(RAW.replace('/main/','/'+a.commit+'/')+path);f=verify(json.loads(b),key())
  assert normalize(b)==normalize((repo/path).read_bytes()),'Published catalog differs'
  assert f['launcher']['version']=='0.8.6'
  if channel in ('stable','beta'):assert f['patchGuide']['version']==('0.3.3' if channel=='stable' else '0.4.0-beta.1')
  proof.append(dict(channel=channel,sha256=hashlib.sha256(b).hexdigest(),signatureValid=True))
 for path in ['feed/changelog.history.json','feed/patch-guide-beta.json']:
  assert normalize(fetch(RAW.replace('/main/','/'+a.commit+'/')+path))==normalize((repo/path).read_bytes())
 write(out/'catalog-readback.json',dict(passed=True,commit=a.commit,catalogs=proof));print('PUBLIC_CATALOGS_PASS',len(proof))
elif a.launcher:
 r=release('v0.8.6',False);dest=stage/'ci-launcher';dest.mkdir(exist_ok=True)
 for asset in r['assets']:
  if asset['name'] not in ('PawsPatchLauncher.exe','launcher-artifact.json'):continue
  target=dest/asset['name'];blob=fetch(asset['browser_download_url']);target.write_bytes(blob)
  assert len(blob)==asset['size'] and 'sha256:'+hashlib.sha256(blob).hexdigest()==asset['digest']
 artifact=read(dest/'launcher-artifact.json');assert artifact['version']=='0.8.6' and artifact['sourceCommit']==a.commit
 exe=next(f for f in artifact['files'] if f['name']=='PawsPatchLauncher.exe')
 assert sha(dest/'PawsPatchLauncher.exe')==exe['sha256']
 write(dest/'public-verification.json',dict(passed=True,sourceCommit=a.commit,sha256=exe['sha256'],release=r['html_url']))
 print('CI_LAUNCHER_READBACK_PASS',exe['sha256'])
else:
 prep=read(out/'preparation.json');proof=[]
 for channel,tag in [('stable','patch-0.3.3'),('beta','patch-0.4.0-beta.1')]:
  r=release(tag,channel=='beta');remote={x['name']:x for x in r['assets']}
  for row in [x for x in prep['assets'] if x['channel']==channel]:
   asset=remote[Path(row['path']).name];blob=fetch(row['url'])
   assert len(blob)==row['size']==asset['size']
   assert hashlib.sha256(blob).hexdigest().upper()==row['sha256']
   assert asset['digest']=='sha256:'+row['sha256'].lower()
   proof.append(dict(id=row['id'],channel=channel,sha256=row['sha256'],size=len(blob)))
 write(out/'public-verification.json',dict(passed=True,sourceCommit=a.commit,assets=proof));print('PUBLIC_PATCH_ASSETS_PASS',len(proof))
