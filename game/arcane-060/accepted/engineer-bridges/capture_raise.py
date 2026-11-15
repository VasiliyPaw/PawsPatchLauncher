"""Capture native construction stages at observed health, without fast-forward."""
from pathlib import Path
import argparse,subprocess,sys,json,time
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--tag',required=True);p.add_argument('--seconds',type=float,default=130);p.add_argument('--minimum-id',type=int,default=1);a=p.parse_args()
root=a.out.resolve();here=Path(__file__).resolve().parent;rows=[];stages=set();start=time.monotonic()
while time.monotonic()-start<a.seconds:
 result=subprocess.run([sys.executable,'-B',str(here/'observe.py'),'--out',str(root)],capture_output=True,text=True,check=True)
 row=json.loads(result.stdout);bridges=[v for v in row['actors'] if v['name'].startswith('paws_bridge_') and v['id']>=a.minimum_id]
 if bridges:
  b=max(bridges,key=lambda v:v['id']);stage=min(4,int(4*b['health']/b['maxHealth']))
  rows.append({'time':row['time'],'bridge':b})
  if stage not in stages:
   stages.add(stage)
   subprocess.run([sys.executable,'-B',str(here/'qa_client.py'),'--out',str(root),'--wait','.2','ScreenShot'],capture_output=True,check=True)
   screenshots=sorted((root/'sandbox/Userdata/Screenshots').glob('*.png'),key=lambda f:f.stat().st_mtime)
   (root/'qa-evidence'/f'{a.tag}-stage{stage}.json').write_text(json.dumps(dict(observation=row,screenshot=str(screenshots[-1])),indent=2))
   print('STAGE',stage,'health',b['health'],'file',screenshots[-1].name,flush=True)
  if not b['construction']:break
 time.sleep(.15)
(root/'qa-evidence'/f'{a.tag}-trace.json').write_text(json.dumps(rows,indent=2));print('CAPTURED',len(rows),'samples',sorted(stages))
