"""Three-beta native-buffer hotfix. Isolated outputs/index; shared checkout retained."""
import copy,hashlib,json,os,subprocess,sys
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
WS=REPO.parents[1]
OUT=WS/'outputs/buffer-ownership-release-20261113'
FROZEN=Path('G:/PawsWork/Retained/PawsMinimapCrashPublish-20261109')
LEG=Path('G:/CodexData/projects/Codex/2026-08-11/kohan-ii-d-steamlibrary-steamapps-common/work')
PYTHON=Path(sys.executable)
SDK=Path('C:/Users/Paw/Documents/Codex/Kohan-Reborn/.tools/dotnet/dotnet.exe')
KEY=LEG/'PawsPatchLauncher/.local/signing/pawpatch-signing-private.pem'
sys.path.insert(0,str(REPO/'tools'))
from PrepareRelease081 import fetch,key,sign,RAW,API,normalize
from PrepareRelease070 import encode,sha,verify,validate_package
VERSIONS={'arcane':'0.5.1-beta.4','pure':'0.5.0-beta.5'}
RUNTIME='1.3.72-pure.19-beta.5'
FEEDS=[f'feed/{prefix}{channel}.json'for prefix in ['v3/','v2/','']for channel in ['stable','beta']]
FILES=FEEDS+['feed/changelog.history.json','feed/patch-guide-beta.json']
IDS={'pawpatch-core','player-colors','desync-continue','common-ui','pure-fixes-runtime','pure-fixes-data','pure-beta-common'}
GRAPHICS=Path('G:/PawGraphicsQA-20261113/product-graphics')
OLD_GRAPHICS='112920FF0CB9A38158A12E9F8875B6B4FBBCE9ADA5C364EF55936EBBE4A83179'
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def write(p,v):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(encode(v))
def env():
 e=os.environ.copy();e.update(TEMP=str(OUT/'temp'),TMP=str(OUT/'temp'),PYTHONDONTWRITEBYTECODE='1',DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_CLI_HOME=str(OUT/'dotnet-home'),NUGET_PACKAGES=str(OUT/'nuget'));return e
def run(args,log=None):
 r=subprocess.run(list(map(str,args)),cwd=REPO,env=env(),capture_output=True,text=True)
 if log:Path(log).write_text(r.stdout+'\n'+r.stderr)
 if r.returncode:raise RuntimeError(r.stdout[-3500:]+'\n'+r.stderr[-2500:])
 return r.stdout
def git(*args):return run(['git',*args]).strip()
def head():return git('ls-remote','origin','refs/heads/main').split()[0]
