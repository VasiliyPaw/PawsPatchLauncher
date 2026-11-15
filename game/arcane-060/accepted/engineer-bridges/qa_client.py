"""Request a native test action from the marked, owned bridge QA process."""
from pathlib import Path
import argparse,json,time,os
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--wait',type=float,default=1);p.add_argument('--brief',action='store_true');p.add_argument('commands',nargs='+');a=p.parse_args()
mods=a.out/'sandbox/Mods'
def state():
 for attempt in range(100):
  try:
   raw=(mods/'bridge-state.json').read_text()
   # Compatibility with the previous QA serializer's empty first roster slot.
   return json.loads(raw.replace('[,','['))
  except (ValueError,OSError):time.sleep(.025)
 return {}
assert (a.out/'sandbox/terrain-prototype.marker').exists()
expected=json.loads((a.out/'qa-process.json').read_text())['pid']
deadline=time.monotonic()+25
while state().get('pid')!=expected:
 if time.monotonic()>deadline:raise TimeoutError('The owned QA process has not produced its first snapshot')
 time.sleep(.1)
for command in a.commands:
 current=state();assert current.get('pid')==expected,current
 serial=current.get('serial',0)+1;tmp=mods/'bridge-command.tmp';tmp.write_text(str(serial)+' '+command,encoding='utf-8');os.replace(tmp,mods/'bridge-command.txt')
 deadline=time.monotonic()+10
 while state().get('serial',0)<serial:
  if time.monotonic()>deadline:raise TimeoutError(command)
  time.sleep(.1)
 time.sleep(a.wait)
s=state()
print(json.dumps({k:s.get(k) for k in ['pid','serial','time','painted','completed','rejected','built','failed','error']},ensure_ascii=False))
if not a.brief:
 print('Actors:',[(v['id'],v['name'],v['x'],v['y'],v['z']) for v in s.get('actors',[])])
 print('Kingdoms:',[(v['nation'],v['upkeep']) for v in s.get('kingdoms',[])])
