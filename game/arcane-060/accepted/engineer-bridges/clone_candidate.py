"""Create a separate local candidate; never mutate the source game."""
from pathlib import Path
import argparse,json,os,shutil,time

p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
src=a.source.resolve();dst=a.out.resolve();workspace=Path(__file__).resolve().parents[4]
assert src!=dst and dst.parent==workspace/'work' and not dst.exists()
assert (src/'installed-rivers.marker').is_file() and (src/'sandbox/terrain-prototype.marker').is_file()
dst.mkdir();(dst/'installed-rivers.marker').write_text('Private next river/bridge candidate; not published\n')
skip={'qa-evidence','Documents','AppData'};omit={'qa-process.json','validation.json','Как проверить.txt'}
count=0;copied=0;linked=0
for path in src.rglob('*'):
 rel=path.relative_to(src)
 if rel.parts[0] in skip or rel.as_posix() in omit:continue
 if path.is_dir():continue
 if path.suffix.lower() in ('.log','.dmp'):continue
 if rel.parts[:2]==('sandbox','Mods') and path.name in {'bridge-command.txt','bridge-command.tmp','bridge-state.json','bridge-state.tmp'}:continue
 target=dst/rel;target.parent.mkdir(parents=True,exist_ok=True)
 if rel.as_posix() in ('sandbox/Data.rwd','sandbox/Music.rwd'):
  os.link(path,target);linked+=path.stat().st_size
 else:shutil.copy2(path,target);copied+=path.stat().st_size
 count+=1
(dst/'qa-evidence').mkdir();(dst/'Documents/Kohan2/data/Save').mkdir(parents=True);(dst/'AppData').mkdir()
user=src/'Documents/Kohan2/data/User'
if user.exists():shutil.copytree(user,dst/'Documents/Kohan2/data/User')
for name in ('R3-angle-completed.RSG','R5-style-shadow.RSG','R5-style-undead.RSG','R5-depth-user-case.RSG','R5-depth-earlier-case.RSG'):
 path=src/'Documents/Kohan2/data/Save'/name
 if path.exists():shutil.copy2(path,dst/'Documents/Kohan2/data/Save'/name)
report={'source':str(src),'target':str(dst),'files':count,'copiedBytes':copied,'immutableArchiveHardLinkBytes':linked,'phase':'Preparing six-race art; not accepted or published'}
(dst/'preparation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
