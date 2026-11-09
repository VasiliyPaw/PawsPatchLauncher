"""Scoped 2026-11-09 color hotfix; fresh public catalog and accepted builds."""
import copy,hashlib,json,subprocess,sys
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
OUT=Path('F:/PawsLobbyColorsPublish-20261109')
LEG=Path('G:/CodexData/projects/Codex/2026-08-11/kohan-ii-d-steamlibrary-steamapps-common/work')
PYTHON=Path('C:/Users/Paw/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe')
SDK=Path('C:/Users/Paw/Documents/Codex/Kohan-Reborn/.tools/dotnet/dotnet.exe')
KEY=LEG/'PawsPatchLauncher/.local/signing/pawpatch-signing-private.pem'
sys.path.insert(0,str(REPO/'tools'))
from PrepareRelease081 import fetch,key,sign,RAW,API,normalize
from PrepareRelease070 import encode,sha,verify,validate_package
VERSIONS={'arcane':'0.5.1-beta.2','pure':'0.5.0-beta.3'}
RUNTIME='1.3.72-pure.19-beta.3'
FEEDS=[f'feed/{prefix}{channel}.json'for prefix in ['v3/','v2/','']for channel in ['stable','beta']]
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def write(p,v):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(encode(v))
def git(*args):return subprocess.check_output(['git',*args],cwd=REPO,text=True).strip()
def run(args,log=None):
 r=subprocess.run(list(map(str,args)),cwd=REPO,capture_output=True,text=True)
 if log:Path(log).write_text(r.stdout+'\n'+r.stderr)
 if r.returncode:raise RuntimeError(r.stdout[-4000:]+'\n'+r.stderr[-2000:])
 return r.stdout
