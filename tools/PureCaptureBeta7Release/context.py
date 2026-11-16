from pathlib import Path
import os,sys,json,hashlib,subprocess,copy
P=Path(__file__).resolve().parent;WS=P.parents[1];O=WS/'outputs/pure050-beta7-release-20261116';PREV=WS/'work/arcane-060-beta-release-20261115';B1=WS/'outputs/arcane-060-beta-release-20261115';LOSS=WS/'outputs/arcane060-lossless-20261115';LP=WS/'work/arcane060-lossless-20261115';REPO=WS/'work/launcher-104-release';S=P/'source';VERSION='0.5.0-beta.7';TAG='patch-pure-'+VERSION;FIX=Path('G:/PawsWork/QA/Pure050Beta7-20261116');R=WS/'work/rivers-r24-combined-20261113'
for d in [O,P/'Temp']:d.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(PREV/'source/tools'))
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
 e=os.environ.copy();e.update(TEMP=str(P/'Temp'),TMP=str(P/'Temp'),DOTNET_CLI_HOME=str(P/'dotnet-home'),NUGET_PACKAGES=str(P/'nuget'),DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_GENERATE_ASPNET_CERTIFICATE='false');return e
def run(a,log=None,cwd=REPO):
 q=subprocess.run(list(map(str,a)),cwd=cwd,env=env(),capture_output=True,text=True,encoding='utf-8',errors='replace')
 if log:Path(log).write_text(q.stdout+'\n'+q.stderr,encoding='utf-8')
 if q.returncode:raise RuntimeError(q.stdout[-3500:]+'\n'+q.stderr[-3000:])
 return q.stdout
def git(*args):return run(['git',*args]).strip()
def baseline():
 git('fetch','--no-tags','origin','main');head=git('rev-parse','FETCH_HEAD');assert not S.exists()
 archive=P/'public-source.tar'
 with archive.open('wb')as f:subprocess.run(['git','archive',head],cwd=REPO,stdout=f,check=True)
 import tarfile
 S.mkdir()
 with tarfile.open(archive)as t:t.extractall(S,filter='data')
 (P/'staged-before.patch').write_bytes(subprocess.check_output(['git','diff','--cached','--binary'],cwd=REPO));write(P/'baseline.json',dict(publicHead=head,localHead=git('rev-parse','HEAD')))
 print('LIVE_SOURCE_PINNED',head,flush=True)
if __name__=='__main__':baseline()

B2=WS/'outputs/arcane060-beta2-release-20261115'
CAND=WS/'outputs/capture-hud-fog-20261116'
CWORK=WS/'work/capture-hud-fog-20261116'

BASE=WS/"outputs/cache-stability-release-20261114"
RUNTIME="1.3.72-pure.21-beta.7"
CC=WS/"work/crash-20260914-continue/tools/tinycc/tcc/tcc.exe"
LEGACY=Path("G:/CodexData/projects/Codex/2026-08-11/kohan-ii-d-steamlibrary-steamapps-common/work")
sys.path[:0]=[str(LEGACY/"pydeps_readable"),str(LEGACY/"lobby_colors_1372/deps_r15")]
