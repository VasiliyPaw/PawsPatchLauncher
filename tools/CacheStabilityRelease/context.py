"""Pinned three-beta release, private indexes and G:-only artifacts."""
import copy,hashlib,json,os,subprocess,sys
from pathlib import Path
REPO=Path(__file__).resolve().parents[2];WS=REPO.parents[1];OUT=WS/'outputs/cache-stability-release-20261114'
VERSIONS={'arcane':'0.5.1-beta.5','pure':'0.5.0-beta.6'};RUNTIME='1.3.72-pure.20-beta.6'
LEG=Path('G:/CodexData/projects/Codex/2026-08-11/kohan-ii-d-steamlibrary-steamapps-common/work')
KEY=LEG/'PawsPatchLauncher/.local/signing/pawpatch-signing-private.pem'
SDK=Path('C:/Users/Paw/Documents/Codex/Kohan-Reborn/.tools/dotnet/dotnet.exe')
sys.path.insert(0,str(REPO/'tools'))
from PrepareRelease081 import fetch,key,sign,RAW,API,normalize
from PrepareRelease070 import encode,verify,validate_package
FILES=[f'feed/{p}{c}.json'for p in ['v3/','v2/','']for c in ['stable','beta']]+['feed/changelog.history.json','feed/patch-guide-beta.json']
FEEDS=FILES[:6];IDS={'pawpatch-core','player-colors','desync-continue','common-ui','pure-fixes-runtime','pure-fixes-data','pure-beta-common'}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def write(p,d):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(encode(d))
def env():
 e=os.environ.copy();e.update(TEMP=str(OUT/'temp'),TMP=str(OUT/'temp'),PYTHONDONTWRITEBYTECODE='1',DOTNET_CLI_HOME=str(OUT/'dotnet-home'),NUGET_PACKAGES=str(OUT/'nuget'),DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_GENERATE_ASPNET_CERTIFICATE='false',PAW_EXPANDED_OUT=str(OUT),PAW_EXPANDED_RAM_PERCENT='90',PAW_AIRCRAFT_FALL_REPAIR='1',PAW_PATCH_ARCANE_VERSION=VERSIONS['arcane'],PAW_PATCH_PURE_VERSION=VERSIONS['pure'],PAW_PATCH_PURE_RUNTIME=RUNTIME);return e
def run(args,log=None):
 p=subprocess.run(list(map(str,args)),cwd=REPO,env=env(),capture_output=True,text=True)
 if log:Path(log).write_text(p.stdout+'\n'+p.stderr)
 if p.returncode:raise RuntimeError(p.stdout[-3000:]+'\n'+p.stderr[-2500:])
 return p.stdout
def git(*args):return run(['git',*args]).strip()
def head():return git('ls-remote','origin','refs/heads/main').split()[0]
