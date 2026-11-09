"""Scoped Pure publication inputs; shared Arcane sources remain read-only."""
import hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
WS=REPO.parents[1]
OUT=REPO/'outputs/pure-041-050-20261109'
LEG=Path('G:/CodexData/projects/Codex/2026-08-11/kohan-ii-d-steamlibrary-steamapps-common/work')
TCC=WS/'work/crash-20260914-continue/tools/tinycc/tcc/tcc.exe'
BASE=WS/'outputs/release-company-20261029/pure'
sys.path[:0]=[str(REPO/'tools'),str(LEG/'pydeps_readable'),str(LEG/'lobby_colors_1372/deps_r15')]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
