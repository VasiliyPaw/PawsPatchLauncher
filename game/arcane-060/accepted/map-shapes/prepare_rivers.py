"""Prepare a fresh river+bridge test without altering the accepted bridge copy."""
from pathlib import Path
import argparse,shutil,os,sys,json,hashlib,zipfile
from rivers_data import add_ui,rule_definition
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'game/lobby-colors')]
from PrepareSplitLanguages import rwd_files,dec
from compact_menu import span
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
source=a.source.resolve();out=a.out.resolve();assert source!=out and (source/'sandbox/terrain-prototype.marker').is_file()
assert not out.exists() or (out/'rivers-prototype.marker').is_file()
if not out.exists():
 out.mkdir();(out/'rivers-prototype.marker').write_text('Private random rivers and accepted model bridges\n')
 def copy(src,dst):
  if Path(src).name.lower() in ('data.rwd','music.rwd') and Path(src).parent==source/'sandbox':os.link(src,dst);return dst
  return shutil.copy2(src,dst)
 shutil.copytree(source/'sandbox',out/'sandbox',copy_function=copy,ignore=shutil.ignore_patterns('Logs','*.log','*.dmp','*.mdmp','bridge-command.*','bridge-state.*'))
 shutil.copytree(source/'locales',out/'locales')
 (out/'native').mkdir();(out/'qa-evidence').mkdir();(out/'Documents').mkdir();(out/'AppData').mkdir()
 with zipfile.ZipFile(out/'accepted-bridge-source.zip','w',zipfile.ZIP_DEFLATED) as z:
  for folder in ('engineer-bridges','engineer-roads','map-shapes'):
   for file in (ROOT/'game'/folder).rglob('*'):
    if file.is_file() and '__pycache__' not in file.parts:z.write(file,file.relative_to(ROOT).as_posix())
files=rwd_files((source/'sandbox/Data.rwd').read_bytes())
for language,root in [(p.name,p) for p in (out/'locales').iterdir()]+[('ru',out/'sandbox/probe-data')]:
 path=root/'UI/Shared/random_map_dialog.tgi';path.write_text(add_ui(path.read_text(encoding='utf-16'),language,span),encoding='utf-16')
 path=root/'Game/world_rules_k2.tgi';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(dec(files['Game/world_rules_k2.tgi'])+rule_definition(language),encoding='utf-16')
 path=root/'Game/SVars.tgi';text=dec(files['Game/SVars.tgi']);at=text.index('{')+1;path.write_text(text[:at]+'\n int PawsRivers = 17\n'+text[at:],encoding='utf-16')
 # The former river shape is retained for saved profile IDs; river count now
 # controls it just like all other shapes, with no three mandatory fords.
 for path in (root/'RandomMap').glob('*.tgi'):
  text=path.read_text(encoding='utf-16')
  if 'paws_shape_rivers' in text:
   import re
   descriptions={'en':'Open terrain with rivers controlled by the Rivers setting.','ru':'Открытая местность. Количество рек задаётся настройкой «Реки».','de':'Offenes Gelände. Flüsse werden separat eingestellt.','fr':'Terrain ouvert. Les rivières se règlent séparément.','cs':'Otevřený terén. Počet řek se nastavuje samostatně.','uk':'Відкрита місцевість. Кількість річок задається окремо.'}
   text=re.sub(r'\bdescription\s*=\s*"[^"]*"','description = "'+descriptions[language]+'"',text,count=1);path.write_text(text,encoding='utf-16')
manifest={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (out/'locales').rglob('*') if p.is_file()}
(out/'menu-manifest.json').write_text(json.dumps(manifest,indent=2));print('RIVERS_BRIDGES_PREPARED',out)
