"""Isolated optimization port; accepted Pure world/UI and Arcane performance inputs."""
import hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1];WS=REPO.parents[1]
PREVIOUS=REPO/'outputs/pure-041-050-20261109'
OUT=REPO/'outputs/pure-050-optimizations-20261109'
LEG=Path('G:/CodexData/projects/Codex/2026-08-11/kohan-ii-d-steamlibrary-steamapps-common/work')
TCC=WS/'work/crash-20260914-continue/tools/tinycc/tcc/tcc.exe'
PATCH='0.5.0-beta.2';RUNTIME='1.3.72-pure.18-beta.2'
sys.path[:0]=[str(REPO/'tools'),str(LEG/'pydeps_readable'),str(LEG/'lobby_colors_1372/deps_r15')]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def write(p,value):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
def once(s,old,new):assert s.count(old)==1,(old[:100],s.count(old));return s.replace(old,new)
