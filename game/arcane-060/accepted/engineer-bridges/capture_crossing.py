"""Record real simulation AND rendered heights while the owned QA company moves."""
from pathlib import Path
import argparse,json,subprocess,sys,time
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--x',type=float,required=True);p.add_argument('--y',type=float,required=True);p.add_argument('--tag',required=True);p.add_argument('--seconds',type=float,default=35);a=p.parse_args()
here=Path(__file__).resolve().parent;root=a.out.resolve();rows=[];pictured=False
def command(text):
 subprocess.run([sys.executable,'-B',str(here/'qa_client.py'),'--out',str(root),'--wait','0',text],check=True,capture_output=True,text=True)
command(f'!move 432 {a.x} {a.y}')
deadline=time.monotonic()+a.seconds
while time.monotonic()<deadline:
 result=subprocess.run([sys.executable,'-B',str(here/'observe.py'),'--out',str(root)],check=True,capture_output=True,text=True)
 row=json.loads(result.stdout)
 rows.append({'time':row['time'],'actors':[{k:v for k,v in actor.items() if k in ('id','name','simulation','visualTarget','health','construction')} for actor in row['actors']]})
 members=[v for v in rows[-1]['actors'] if 433<=v['id']<=439]
 if not pictured and any(111<v['simulation'][0]<121 for v in members):command('ScreenShot');pictured=True
 if len(members)==7 and all(abs(v['simulation'][0]-a.x)<5 and abs(v['simulation'][1]-a.y)<5 for v in members):break
 time.sleep(.15)
dest=root/'qa-evidence'/f'{a.tag}.json';dest.write_text(json.dumps(rows,indent=2),encoding='utf-8')
wet=[v for row in rows for v in row['actors'] if 433<=v['id']<=439 and 111<v['simulation'][0]<121]
summary={'samples':len(rows),'wetMembers':sorted({v['id'] for v in wet}),'simulationHeights':sorted({v['simulation'][2] for v in wet}),'renderedHeights':sorted({v['visualTarget'][2] for v in wet}),'finalMembers':[(v['id'],v['simulation']) for v in members],'file':str(dest)}
print(json.dumps(summary,ensure_ascii=False))
if len({v['id'] for v in wet})!=7:raise SystemExit('Not all seven real units were observed over water')
