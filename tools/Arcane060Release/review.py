"""R24 native-engine review. Never controls any process outside this candidate."""
from pathlib import Path
import sys,os,json,time,re,shutil,subprocess
P=Path(__file__).resolve().parent
R=Path((P/'target.txt').read_text()); M=R/'sandbox/Mods'; E=R/'qa-evidence/arcane060-savebuild'
E.mkdir(exist_ok=True)
sys.path.insert(0,str(R/'source'))
from control import *
sys.path.insert(1,str(P.parent/'rivers-r17-network-20261111/source'))
from memory import Memory

def cmd(s):command('preview',s)
def snap():
 m=Memory('preview');u=m.u;out={'native':state('preview'),'kingdoms':[],'actors':[]}
 try:
  w=u(m.base+0x5f3fb8)
  if not w:return out
  owners={}
  for i in range(u(w+0x154)):
   a=u(u(w+0x150)+4*i)
   if not a:continue
   nation=u(a+0x240)
   if a and nation:owners[a]=u(a+0x14);out['kingdoms'].append({'id':owners[a],'nation':m.name(nation)})
  import struct
  reg=u(m.base+0x5ef72c)
  for a in struct.unpack('<65536I',m.read(reg+0x20004,0x40000)):
   if not a or u(a)!=m.base+0x4e5c58 or u(a+8)&3:continue
   name=m.name(u(a+4));org=u(a+0x7c)
   if not org and not name.startswith('paws_bridge_'):continue
   body=u(a+0x60)
   out['actors'].append({'id':u(a+0x14),'name':name,'owner':owners.get(u(a+0xe8)),
    'position':list(struct.unpack('<3f',m.read(a+0x20,12))),
    'hp':m.f(body+0x10) if body else None,'construction':bool(u(a+0x100)&0x200000)})
  return out
 finally:m.close()

def bind():
 m=Memory('preview')
 try:
  (M/'network-sp-api.txt').write_text(f"{m.road} {m.export('bridge_fixture_offset')} {m.export('bridge_art_request')}")
  (M/'network-bridge-api.txt').write_text(f"{m.road} {m.export('bridge_net_input')} {m.export('bridge_net_order_input')}")
 finally:m.close()

def shot(name):
 cmd('!clear-review-messages');time.sleep(.2)
 folder=R/'Documents/Kohan2/data/Screenshots';old=set(folder.glob('*.png'));cmd('Screenshot')
 wait(lambda:bool(set(folder.glob('*.png'))-old),15,'native screenshot')
 p=max(set(folder.glob('*.png'))-old,key=lambda p:p.stat().st_mtime_ns)
 wait(lambda:p.read_bytes().endswith(b'\x00\x00\x00\x00IEND\xaeB\x60\x82'),15,'complete PNG')
 for ext in ['.png','.json']:
  target=E/(name+ext)
  if target.exists():target.rename(E/(name+'-previous-'+str(time.time_ns())+ext))
 shutil.copy2(p,E/(name+'.png'));(E/(name+'.json')).write_text(json.dumps(snap(),indent=2))
 # Retain the verified evidence copy, avoiding a second native screenshot
 # occupying the same nearly-full project drive.
 assert p.resolve().is_relative_to(folder.resolve()) and p.read_bytes()==(E/(name+'.png')).read_bytes()
 p.unlink()

def launch():
 assert not own()
 (E/'final-plugins.txt').write_text((M/'plugins.txt').read_text())
 (M/'plugins.txt').write_text((M/'plugins.txt').read_text()+'PawsNetworkQA.dll\n')
 archive=E/('before-'+str(time.time_ns()));archive.mkdir()
 for pattern in ['network-*.json*','network-command.*','bridge-command.*','rig-request-*.txt','font-cache-status.jsonl','plugins.log']:
  for p in M.glob(pattern):
   if p.is_file():p.rename(archive/p.name)
 env=os.environ.copy();env.update(TEMP=str(R/'Temp'),TMP=str(R/'Temp'),PAWS_RIG_EXTERNAL_SCRIPT='1')
 subprocess.Popen([str(R/'PawsRiversTest.exe')],cwd=R,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
 wait(lambda:any(Path(p['path'])==R/'sandbox/k2.exe' for p in own()),90,'root launch')
 p=next(p for p in own()if Path(p['path'])==R/'sandbox/k2.exe');(R/'qa-process.json').write_text(json.dumps({'pid':p['pid'],'exe':p['path']}))
 wait(lambda:state('preview').get('pid')==p['pid'] and state('preview').get('phase')==3,75,'fresh menu')

def load(name):
 before=state('preview')
 if before.get('world'):
  cmd('GameLoad Save/'+name+'.RSG')
 else:
  for c in ['RequestSinglePlayer','RequestCustom','SelectLaunchType LOAD_SAVED_GAME','Select Save/'+name+'.RSG','Commit','StagingLaunch']:cmd(c);time.sleep(.25)
 wait(lambda:state('preview').get('world') and state('preview').get('mode')==2,100,'world')
 cmd('UserReady');wait(lambda:state('preview').get('phase')==4 and not state('preview').get('frozen'),90,'interface')
 time.sleep(1);bind()

def scene(race):
 load('R6-art-'+race)
 wait(lambda:any(v['id']==429 and v['nation'].lower()==race for v in snap()['kingdoms']),30,'race identity')
 cmd('GamePause 0');cmd('GameSpeed 0');cmd('!sp-river');time.sleep(.5)
 for wood,y in [(1,40),(0,60)]:
  cmd(f'!sp-art 429 {wood} 50 {y} 65 {y}');time.sleep(.4)
 wait(lambda:len([v for v in snap()['actors'] if v['name'].startswith('paws_bridge_'+race+'_')])==2,20,'both completed bridges')
 time.sleep(1)
 for material,y in [('wood',81),('stone',121)]:
  cmd(f'MoveCamera 0 0 116 {y} 1');time.sleep(.6);shot(race+'-'+material)
  cmd(f'MoveCamera 0 1 101 {y} 2');time.sleep(.6);shot(race+'-'+material+'-bank-left')
  cmd(f'MoveCamera 0 1 131 {y} 2');time.sleep(.6);shot(race+'-'+material+'-bank-right')
 print('SCENE_CAPTURED',race,flush=True)

if __name__=='__main__':
 action=sys.argv[1]
 if action=='launch':launch()
 elif action=='load':load(sys.argv[2])
 elif action=='shot':shot(sys.argv[2])
 elif action=='scenes':
  for race in sys.argv[2:]:scene(race)
 elif action=='uis':
  for race in sys.argv[2:]:
   load('R6-art-'+race);cmd('GamePause 1');shot('ui1920-'+race);print('UI_CAPTURED',race,flush=True)
 elif action=='cmd':
  for c in sys.argv[2:]:cmd(c);time.sleep(.25)
 elif action=='state':print(json.dumps(snap(),indent=2))
 elif action=='quit':
  cmd('ReallyQuit');wait(lambda:not own(),30,'normal exit')
  (M/'plugins.txt').write_text((E/'final-plugins.txt').read_text())
 print('REVIEW_DONE',action,flush=True)
