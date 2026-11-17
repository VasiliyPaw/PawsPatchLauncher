from pathlib import Path
import os,sys,json,hashlib,subprocess,copy
P=Path(__file__).resolve().parent;WS=P.parents[1];O=WS/'outputs/ui-compact-release-20261117';REPO=WS/'work/launcher-104-release';S=P/'source'
ARC='0.6.0-beta.5';PURE='0.5.0-beta.9';RT='1.3.72-pure.21-beta.9';PR=WS/'outputs/ui-fullres-release-20261117';AP=PR/'arcane';PP=PR/'pure';HD=WS/'outputs/ui-fullres-20261116';B2=WS/'outputs/arcane060-beta2-release-20261115'
for d in[O,P/'Temp']:d.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(WS/'work/arcane-060-beta-release-20261115/source/tools'))
from PrepareRelease070 import encode,verify,validate_package
from PrepareRelease081 import key,sign,fetch,RAW,API,normalize
KEY=Path('G:/CodexData/projects/Codex/2026-08-11/kohan-ii-d-steamlibrary-steamapps-common/work/PawsPatchLauncher/.local/signing/pawpatch-signing-private.pem');SDK=Path('G:/CodexData/projects/Codex/Kohan-Reborn/.tools/dotnet/dotnet.exe')
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def write(p,v):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(encode(v))
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest().upper()
def env():
 e=os.environ.copy();e.update(TEMP=str(P/'Temp'),TMP=str(P/'Temp'),DOTNET_CLI_HOME=str(P/'dotnet-home'),NUGET_PACKAGES=str(WS/'work/arcane060-beta3-release-20261116/nuget'),DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_GENERATE_ASPNET_CERTIFICATE='false');return e
def run(a,log=None,cwd=REPO):
 q=subprocess.run(list(map(str,a)),cwd=cwd,env=env(),capture_output=True,text=True,encoding='utf-8',errors='replace')
 if log:Path(log).parent.mkdir(parents=True,exist_ok=True);Path(log).write_text(q.stdout+'\n'+q.stderr,encoding='utf-8')
 if q.returncode:raise RuntimeError(q.stdout[-3500:]+'\n'+q.stderr[-3000:])
 return q.stdout
def git(*a):return run(['git',*a]).strip()
FILES=[f'feed/{p}{c}.json'for p in['v3/','v2/','']for c in['stable','beta']]+['feed/changelog.history.json','feed/patch-guide-beta.json']
def snapshot():
 git('fetch','--no-tags','origin','main');head=git('rev-parse','FETCH_HEAD')
 for rel in FILES:
  p=O/'before'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(subprocess.check_output(['git','show',head+':'+rel],cwd=REPO))
 write(O/'catalog-baseline.json',dict(publicHead=head));return head
def baseline():
 head=snapshot();assert not S.exists();import tarfile
 with(P/'public-source.tar').open('wb')as f:subprocess.run(['git','archive',head],cwd=REPO,stdout=f,check=True)
 S.mkdir()
 with tarfile.open(P/'public-source.tar')as t:t.extractall(S,filter='data')
 (P/'staged-before.patch').write_bytes(subprocess.check_output(['git','diff','--cached','--binary'],cwd=REPO));write(P/'baseline.json',dict(publicHead=head,localHead=git('rev-parse','HEAD')))
 f=verify(read(O/'before/feed/v3/beta.json'),key());assert next(p for p in f['packages']if p['id']=='pawpatch-core')['version']=='0.6.0-beta.4';assert next(p for p in f['packages']if p['id']=='pure-fixes-data')['version']=='0.5.0-beta.8';print('COMPACT_BASELINE_PINNED',head,flush=True)
if __name__=='__main__':baseline()
