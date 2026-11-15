"""Drive the owned native art fixture and preserve complete, reproducible views."""
from pathlib import Path
import argparse,json,os,shutil,subprocess,sys,time

p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--races',nargs='+',required=True,choices=['human','gauri','drauga','haroun','shadow','undead']);a=p.parse_args()
r=a.out.resolve();assert (r/'installed-rivers.marker').exists();pid=json.loads((r/'qa-process.json').read_text())['pid'];mods=r/'sandbox/Mods';e=r/'qa-evidence/r6-native';e.mkdir(parents=True,exist_ok=True)

def state():
 for _ in range(100):
  try:
   s=json.loads((mods/'bridge-state.json').read_text());assert s['pid']==pid;return s
  except (ValueError,OSError):time.sleep(.025)
 raise RuntimeError('Native QA snapshot unavailable')

def send(command,delay=.4):
 s=state();serial=s['serial']+1;tmp=mods/'bridge-command.tmp';tmp.write_text(str(serial)+' '+command,encoding='utf-8');os.replace(tmp,mods/'bridge-command.txt')
 wait(lambda s:s['serial']>=serial,'Native command acknowledgement: '+command,12)
 time.sleep(delay)

def wait(predicate,label,seconds=25):
 deadline=time.monotonic()+seconds
 while time.monotonic()<deadline:
  s=state()
  if predicate(s):return s
  time.sleep(.1)
 raise TimeoutError(label)

def screenshot(target):
 folder=r/'Documents/Kohan2/data/Screenshots';before=set(folder.glob('*.png'));send('ScreenShot')
 paths=set(folder.glob('*.png'))-before;assert len(paths)==1
 src=paths.pop();shutil.copy2(src,target);return str(target)

def member(s):return next((v for v in s['actors'] if v['name']=='company_engineer'),None)

for race in a.races:
 print('NATIVE_REVIEW_LOADING',race,flush=True)
 send('GameLoad Save/R6-art-'+race+'.RSG',.6);send('UserReady',.6);send('GamePause 0');send('GameSpeed 4')
 s=wait(lambda s:any(k['id']==429 and k['nation'].lower()==race for k in s['kingdoms']),'Loaded nation '+race)
 send('!river-fixture',.7)
 for wood in [1,0]:
  y=40 if wood else 60;material='wood' if wood else 'stone';name=f'paws_bridge_{race}_{material}_y_16'
  send(f'!art 429 {wood} 50 {y} 65 {y}')
  wait(lambda s:any(v['name']==name for v in s['actors']),'Created native '+name)
 actor=member(state());assert actor;ident=actor['id'];route=[]
 # Natural company vision exposes both banks; saved visibility grids can
 # survive a manually changed FogOfWar rule in these old native fixtures.
 for x,y in [(130,81),(130,121),(100,121)]:
  send(f'!move {ident} {x} {y}')
  s=wait(lambda s:member(s) is not None and (member(s)['x']-x)**2+(member(s)['y']-y)**2<4,'Engineer reached viewing waypoint')
  route.append({'x':member(s)['x'],'y':member(s)['y'],'z':member(s)['z'],'time':s['time']})
 send('GameSpeed 0');views={}
 for material,y in [('wood',81),('stone',121)]:
  send(f'MoveCamera 0 0 116 {y}',.5);views[material]=screenshot(e/f'{race}-{material}.png')
 snapshot=e/f'{race}.json';subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('observe.py')),'--out',str(r),'--save',str(snapshot)],stdout=subprocess.DEVNULL,check=True)
 s=state();bridges=[v for v in s['actors'] if v['name'].startswith('paws_bridge_'+race+'_')];assert len(bridges)==2
 report={'race':race,'nativeCreated':True,'views':views,'snapshot':str(snapshot),'bridges':bridges,'engineerRoute':route,'fixtureOnly':True,'visualAcceptance':'awaiting image inspection'}
 (e/f'{race}-review.json').write_text(json.dumps(report,indent=2));print('NATIVE_REVIEW_CAPTURED',race,json.dumps(views),flush=True)
