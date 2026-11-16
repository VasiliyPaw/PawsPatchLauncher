"""Three isolated peers. Native LAN console input, unchanged native CRC checks."""
from pathlib import Path
import ctypes as C,json,os,subprocess,sys,time
MODE=json.loads((Path(__file__).with_name('active-mode.json')).read_text())['mode'];N=Path('G:/PawsWork/QA/Pure050Beta7-20261116')/('network-'+MODE);W=Path('G:/CodexData/projects/Codex/2026-09-09/paws-patch-kohan-ii-3/work');ROLES=('host','client','witness');PORT=6221
k=C.WinDLL('kernel32',use_last_error=True)
class Entry(C.Structure):
 _fields_=[('size',C.c_uint),('uses',C.c_uint),('pid',C.c_uint),('heap',C.c_size_t),('module',C.c_uint),('threads',C.c_uint),('parent',C.c_uint),('priority',C.c_long),('flags',C.c_uint),('name',C.c_wchar*260)]
k.OpenProcess.argtypes=[C.c_uint,C.c_int,C.c_uint];k.OpenProcess.restype=C.c_void_p;k.CloseHandle.argtypes=[C.c_void_p]
k.QueryFullProcessImageNameW.argtypes=[C.c_void_p,C.c_uint,C.c_wchar_p,C.c_void_p];k.TerminateProcess.argtypes=[C.c_void_p,C.c_uint]
k.CreateToolhelp32Snapshot.argtypes=[C.c_uint,C.c_uint];k.CreateToolhelp32Snapshot.restype=C.c_void_p;k.Process32FirstW.argtypes=[C.c_void_p,C.POINTER(Entry)];k.Process32NextW.argtypes=[C.c_void_p,C.POINTER(Entry)]
def folder(role):
 assert role in ROLES
 return Path('G:/PawsWork/QA/Pure050Beta7-20261116')/MODE if role=='host'else N/role
def own():
 paths={folder(r)/'game'/f for r in ROLES for f in ('k2.exe','k2_paws_family_herd_relations_1372.exe','TestInstalledRuntime.exe')};out=[]
 snap=k.CreateToolhelp32Snapshot(2,0);e=Entry();e.size=C.sizeof(e);ok=k.Process32FirstW(snap,C.byref(e))
 try:
  while ok:
   if e.name.lower()in ('k2.exe','k2_paws_family_herd_relations_1372.exe','testinstalledruntime.exe'):
    h=k.OpenProcess(0x1000,False,e.pid)
    if h:
     b=C.create_unicode_buffer(32768);n=C.c_uint(32768)
     if k.QueryFullProcessImageNameW(h,0,b,C.byref(n))and Path(b.value).resolve()in paths:out.append({'pid':e.pid,'path':str(Path(b.value).resolve())})
     k.CloseHandle(h)
   ok=k.Process32NextW(snap,C.byref(e))
 finally:k.CloseHandle(snap)
 return out
last_states={}
def state(role):
 for attempt in range(10):
  try:
   s=json.loads((folder(role)/'game/Mods/network-state.json').read_text());last_states[role]=s;return s
  except ValueError:time.sleep(.003)
  except OSError:return last_states.get(role,{})
 return last_states.get(role,{})
def wait(check,seconds,label):
 end=time.monotonic()+seconds
 while not check():
  if time.monotonic()>end:raise TimeoutError(label)
  time.sleep(.15)
def command(role,text):
 r=folder(role);identity=json.loads((r/'qa-process.json').read_text());wait(lambda:state(role).get('pid')==identity['pid'],3,role+' fresh observer');s=state(role);assert s.get('pid')==identity['pid']
 mods=r/'game/Mods';serial=s['serial']+1;temp=mods/'network-command.tmp';temp.write_text(str(serial)+' '+text);
 for attempt in range(50):
  try:os.replace(temp,mods/'network-command.txt');break
  except PermissionError:
   if attempt==49:raise
   time.sleep(.02)

 wait(lambda:state(role).get('serial',0)>=serial or text=='ReallyQuit' and not any(p['pid']==identity['pid']for p in own()),15,role+' '+text)
def start(role):
 r=folder(role);exe=r/'game/k2.exe';helper=r/'game/TestInstalledRuntime.exe';assert not any(Path(p['path'])in(exe,helper)for p in own())
 archive=r/'qa-evidence/sessions'/str(time.time_ns());archive.mkdir(parents=True)
 logs=r/'game/Logs'
 if logs.exists():
  assert logs.resolve().is_relative_to(r.resolve())
  for attempt in range(30):
   try:logs.rename(archive/'Logs');break
   except PermissionError:
    if attempt==29:raise
    time.sleep(.3)
 mods=r/'game/Mods'
 for pattern in ['network-*.json*','network-command.*','bridge-command.*','bridge-state.*','rig-request-*.txt']:
  for f in mods.glob(pattern):
   if f.is_file():f.rename(archive/f.name)
 env=os.environ.copy();env.update(SteamAppId='97130',SteamGameId='97130',PAWS_TEST_DOCUMENTS=str(r/'Documents'),PAWS_TEST_APPDATA=str(r/'AppData'),TEMP=str(r/'Temp'),TMP=str(r/'Temp'),PAWS_RIG_EXTERNAL_SCRIPT='1',PAWS_TEST_JOIN=f'127.0.0.1:{PORT}',PAWS_TEST_WINDOW_COLUMN=str(ROLES.index(role)))
 with (r/'helper-console.log').open('w')as log:proc=subprocess.Popen([str(helper),'--game-dir',str(exe.parent)],cwd=exe.parent,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 wait(lambda:any(Path(p['path'])==exe for p in own())or proc.poll()is not None,45,role+' game creation')
 matches=[p for p in own()if Path(p['path'])==exe];assert len(matches)==1,(role,(r/'helper-console.log').read_text())
 identity={'pid':matches[0]['pid'],'exe':str(exe),'helperPid':proc.pid,'helper':str(helper)};(r/'qa-process.json').write_text(json.dumps(identity,indent=2))
 wait(lambda:state(role).get('pid')==identity['pid'],40,role+' native observer ready');print('PEER_STARTED',role,identity,flush=True)
def stop(role=None):
 paths={folder(r)/'game'/f for r in ((role,)if role else ROLES)for f in ('k2.exe','k2_paws_family_herd_relations_1372.exe','TestInstalledRuntime.exe')}
 for p in own():
  if Path(p['path'])not in paths:continue
  h=k.OpenProcess(0x1001,False,p['pid'])
  if not h:continue
  try:
   b=C.create_unicode_buffer(32768);n=C.c_uint(32768)
   assert k.QueryFullProcessImageNameW(h,0,b,C.byref(n))and Path(b.value).resolve()in paths
   assert k.TerminateProcess(h,125)
  finally:k.CloseHandle(h)
 wait(lambda:not any(Path(p['path'])in paths for p in own()),15,'owned peer exit')
if __name__=='__main__':
 if sys.argv[1]=='start':start(sys.argv[2])
 elif sys.argv[1]=='stop':stop(sys.argv[2]if len(sys.argv)>2 else None)
 elif sys.argv[1]=='command':command(sys.argv[2],' '.join(sys.argv[3:]));print(json.dumps(state(sys.argv[2]),indent=2))
 elif sys.argv[1]=='state':print(json.dumps({r:state(r)for r in ROLES},indent=2))
