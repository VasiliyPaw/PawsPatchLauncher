from pathlib import Path
import hashlib,json,os,subprocess,sys
HERE=Path(__file__).resolve().parent
if HERE.parent.name=='tools':
    REPO=HERE.parents[1];WS=Path(os.environ.get('PAWS_PROMOTE_WORKSPACE',str(REPO.parents[1])))
else:
    WS=HERE.parents[1];REPO=WS/'work/launcher-104-release'
OUT=WS/'outputs/arcane-promote-20261115'
sys.path.insert(0,str(REPO/'tools'))
from PrepareRelease081 import fetch,key,sign,RAW,API,normalize
from PrepareRelease070 import verify,encode,validate_package
VERSION='0.5.1';BETA='0.5.1-beta.5';TAG='patch-'+VERSION
BASE=WS/'outputs/cache-stability-release-20261114/arcane-helpers'
KEY=Path('G:/CodexData/projects/Codex/2026-08-11/kohan-ii-d-steamlibrary-steamapps-common/work/PawsPatchLauncher/.local/signing/pawpatch-signing-private.pem')
SDK=Path('C:/Users/Paw/Documents/Codex/Kohan-Reborn/.tools/dotnet/dotnet.exe')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,obj):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(encode(obj))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def env():
    e=os.environ.copy();e.update(TEMP=str(OUT/'temp'),TMP=str(OUT/'temp'),PYTHONDONTWRITEBYTECODE='1',DOTNET_CLI_HOME=str(OUT/'dotnet-home'),NUGET_PACKAGES=str(OUT/'nuget'),DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_GENERATE_ASPNET_CERTIFICATE='false',GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='Never')
    for p in ['temp','dotnet-home','nuget']:(OUT/p).mkdir(exist_ok=True)
    return e
def run(args,log=None):
    r=subprocess.run(list(map(str,args)),cwd=REPO,env=env(),capture_output=True,text=True)
    if log:Path(log).write_text(r.stdout+'\n'+r.stderr,encoding='utf-8')
    if r.returncode:raise RuntimeError(r.stdout[-2500:]+'\n'+r.stderr[-2500:])
    return r.stdout
def git(*args):return run(['git',*args]).strip()
def head():return git('ls-remote','origin','refs/heads/main').split()[0]

