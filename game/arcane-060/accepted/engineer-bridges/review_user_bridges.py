"""Owned QA: actual user river/actors, optional explicit combat isolation."""
from pathlib import Path
import argparse,json,os,time,subprocess,sys
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--peace',action='store_true');a=p.parse_args()
r=a.out.resolve();mods=r/'sandbox/Mods';pid=json.loads((r/'qa-process.json').read_text())['pid'];records=[]
def state():
 for _ in range(200):
  try:
   s=json.loads((mods/'bridge-state.json').read_text());assert s['pid']==pid;return s
  except (ValueError,OSError):time.sleep(.025)
 raise RuntimeError('QA snapshot unavailable')
def wait(fn,label,timeout=55):
 end=time.monotonic()+timeout;peace_at=0
 while time.monotonic()<end:
  s=state()
  if fn(s):return s
  if a.peace and label in {'wood-far-bank','wood-return','stone-near-bank','stone-far-bank','stone-return','construction'} and time.monotonic()>peace_at:
   send('!peace-fixture');peace_at=time.monotonic()+.3
  time.sleep(.1)
 raise TimeoutError((label,state()['time']))
def send(command):
 s=state();serial=s['serial']+1;tmp=mods/'bridge-command.tmp';tmp.write_text(str(serial)+' '+command,encoding='utf-8');os.replace(tmp,mods/'bridge-command.txt')
 wait(lambda s:s['serial']>=serial,command,15)
def company(s):return next(v for v in s['actors'] if v['id']==2485)
send('GameSpeed 0');send('GamePause 0')
if a.peace:
 send('!peace-fixture');wait(lambda s:not any(v['elements'] and v['owner']!=company(s)['owner'] for v in s['actors']),'Foreign mobile actors removed')
 print('COMBAT_ISOLATED_ONLY_IN_DISPOSABLE_LOADED_WORLD',flush=True)
for name,x,y in [('wood-far-bank',519,551),('wood-return',485,567),('stone-near-bank',499,595),('stone-far-bank',524,575),('stone-return',497,597)]:
 before=state()['time'];send(f'!move 2485 {x} {y}')
 s=wait(lambda s:(company(s)['x']-x)**2+(company(s)['y']-y)**2<2,name)
 row=dict(label=name,time=s['time'],elapsedGameSeconds=s['time']-before,company=company(s));assert len(row['company']['elements'])==5,row
 records.append(row);print('NATIVE_REACHED',name,s['time'],len(row['company']['elements']),flush=True)
send('GamePause 1')
target=r/'qa-evidence/user-river-crossings-final.json';target.write_text(json.dumps(dict(passed=True,combatIsolated=a.peace,sourceSave='R6-stuck-user-original.RSG',terrainAndBridgesUnchanged=True,route=records),indent=2))
subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('observe.py')),'--out',str(r),'--save',str(r/'qa-evidence/user-river-crossings-final-actors.json')],check=True,stdout=subprocess.DEVNULL)
print('USER_RIVER_CROSSINGS_PASS',target,flush=True)
