from context import *
from publish import request,head,unchanged
import urllib.request,zipfile
VERSION='1.0.22'
def tag():
 h=read(O/'source-publication.json')['commit'];assert head()==h;assert read(O/'launcher-tests.json')['passed']
 assert not request(API+'/git/matching-refs/tags/v'+VERSION)
 request(API+'/git/refs','POST',dict(ref='refs/tags/v'+VERSION,sha=h));write(O/'launcher-tag.json',dict(tag='v'+VERSION,commit=h));print('LAUNCHER_TAG_PUSHED',VERSION,h,flush=True)
def ci():
 h=read(O/'source-publication.json')['commit'];runs=request(API+'/actions/runs?head_sha='+h+'&per_page=30')['workflow_runs'];proof={}
 for name,label in [('Build and test','source'),('Publish launcher','release')]:
  found=[r for r in runs if r['name']==name and r['head_sha']==h]
  if not found:print('PENDING',label,flush=True);continue
  r=max(found,key=lambda r:r['run_number']);p={k:r[k]for k in ['id','head_sha','status','conclusion','html_url']};proof[label]=p
  if label=='source':write(O/'source-ci.json',p)
  if r['status']=='completed'and r['conclusion']!='success':raise RuntimeError('CI failed: '+r['html_url'])
 write(O/'launcher-ci.json',proof);print(json.dumps(proof),flush=True)
def download():
 checks=read(O/'launcher-ci.json');assert all(checks[k]['conclusion']=='success'for k in ['source','release'])
 r=request(API+'/releases/tags/v'+VERSION);assert not r['draft']and not r['prerelease'];h=read(O/'source-publication.json')['commit'];assert request(API+'/git/ref/tags/v'+VERSION)['object']['sha']==h
 out=O/'public-launcher';out.mkdir(exist_ok=True)
 for a in r['assets']:
  assert Path(a['name']).name==a['name'];p=out/a['name'];digest=hashlib.sha256();n=0
  with urllib.request.urlopen(urllib.request.Request(a['browser_download_url'],headers={'User-Agent':'PawsLegacyUiRelease'}),timeout=120)as response,p.open('wb')as f:
   for b in iter(lambda:response.read(4*1024*1024),b''):f.write(b);digest.update(b);n+=len(b)
  assert n==a['size']and a['digest']=='sha256:'+digest.hexdigest();print('PUBLIC_LAUNCHER_ASSET_VERIFIED',p.name,flush=True)
 m=read(out/'launcher-artifact.json');assert m['version']==VERSION and m['sourceCommit']==h
 for row in m['files']:
  p=out/row['name']
  if p.exists():assert sha(p)==row['sha256'].upper()and p.stat().st_size==row['size']
 exe=out/'PawsPatchLauncher.exe'
 with zipfile.ZipFile(out/('PawsPatchLauncher-v'+VERSION+'-win-x64.zip'))as z:
  assert set(z.namelist())=={'PawsPatchLauncher.exe','launcher.config.json','ThirdPartyNotices.txt'};assert hashlib.sha256(z.read('PawsPatchLauncher.exe')).hexdigest().upper()==sha(exe)
  assert json.loads(z.read('launcher.config.json'))==read(S/'src/PawsPatchLauncher/launcher.config.json')
 write(O/'launcher-package.json',dict(version=VERSION,size=exe.stat().st_size,sha256=sha(exe),urls=['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/v'+VERSION+'/PawsPatchLauncher.exe']))
 write(O/'public-launcher-result.json',dict(passed=True,version=VERSION,sourceCommit=h,url=r['html_url'],sha256=sha(exe),size=exe.stat().st_size));unchanged();print('PUBLIC_LAUNCHER_ACCEPTED',flush=True)
if __name__=='__main__':globals()[sys.argv[1]]()
