"""Own and restart only the exact marked private bridge test process."""
from pathlib import Path
import argparse,json,ctypes as c,shutil,os,subprocess,time,sys
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--refresh-definitions',action='store_true');p.add_argument('--stop',action='store_true');p.add_argument('--boot',action='store_true');a=p.parse_args()
r=a.out.resolve();assert (r/'sandbox/terrain-prototype.marker').exists()
state=r/'qa-process.json';exe=(r/'sandbox/k2.exe').resolve()
if state.exists():
 old=json.loads(state.read_text());assert Path(old['exe']).resolve()==exe
 k=c.WinDLL('kernel32',use_last_error=True);k.OpenProcess.restype=c.c_void_p;k.OpenProcess.argtypes=[c.c_uint,c.c_int,c.c_uint]
 k.QueryFullProcessImageNameW.argtypes=[c.c_void_p,c.c_uint,c.c_wchar_p,c.POINTER(c.c_uint)];k.TerminateProcess.argtypes=[c.c_void_p,c.c_uint];k.CloseHandle.argtypes=[c.c_void_p]
 h=k.OpenProcess(0x1001,False,old['pid'])
 if h:
  k.GetExitCodeProcess.argtypes=[c.c_void_p,c.POINTER(c.c_uint)];exit_code=c.c_uint()
  assert k.GetExitCodeProcess(h,c.byref(exit_code))
  if exit_code.value==259:
   buf=c.create_unicode_buffer(32768);n=c.c_uint(32768)
   assert k.QueryFullProcessImageNameW(h,0,buf,c.byref(n)) and Path(buf.value).resolve()==exe
   k.TerminateProcess(h,125);time.sleep(.5)
  k.CloseHandle(h)
 if old.get('helperPid') and old.get('helper'):
  helper_path=Path(old['helper']).resolve();assert helper_path==r/'sandbox/PawsInstalledRuntime.exe'
  hh=k.OpenProcess(0x1001,False,old['helperPid'])
  if hh:
   hb=c.create_unicode_buffer(32768);hn=c.c_uint(32768)
   if k.QueryFullProcessImageNameW(hh,0,hb,c.byref(hn)) and Path(hb.value).resolve()==helper_path:k.TerminateProcess(hh,125)
   k.CloseHandle(hh)
 backup=r/'qa-evidence'/(time.strftime('%Y%m%d-%H%M%S')+'-'+str(time.time_ns()%1000000000));backup.mkdir(parents=True)
 for folder in [r/'sandbox/Logs',r/'sandbox/Mods']:
  for f in folder.glob('*'):
   if f.is_file() and f.suffix in ('.log','.json','.dmp'):shutil.copy2(f,backup/f.name)
if a.refresh_definitions:
 from models import definitions,construction_effect
 sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
 from PrepareSplitLanguages import rwd_files,dec
 effects_stock=dec(rwd_files((r/'sandbox/Data.rwd').read_bytes())['Effects/construction.tgi'])
 for root in [*(r/'locales').iterdir(),r/'sandbox/probe-data']:
  file=root/'Special/Things/thing_visibilityactors.tgi';s=file.read_text(encoding='utf-16').split('[Template PawsBridge')[0];file.write_text(s+definitions(root.name if root.name!='probe-data' else 'ru'),encoding='utf-16')
  effects=root/'Effects/construction.tgi';effects.parent.mkdir(parents=True,exist_ok=True);effects.write_text(effects_stock+construction_effect(),encoding='utf-16')
  for path in ['Units/Human/engineer.tgi','Units/Haroun/caretaker.tgi','Units/Gauri/forge.tgi','Units/Drauga/crafter.tgi','Units/Shadow/nightbringer.tgi','Units/Undead/boneweaver.tgi']:
   worker=root/path;text=worker.read_text(encoding='utf-16')
   if 'actor_ids = paws_bridge_site' in text:
    text=text.replace('actor_ids = paws_bridge_site','actor_ids = paws_bridge_wood_site\n\n [BuildActor]\n actor_ids = paws_bridge_stone_site')
    worker.write_text(text,encoding='utf-16')
if a.stop:print('Stopped owned bridge test');raise SystemExit(0)
(r/'sandbox/Mods/bridge-command.txt').write_text('0')
env=os.environ.copy();env.update(SteamAppId='97130',SteamGameId='97130',PAWS_TEST_DOCUMENTS=str(r/'Documents'),PAWS_TEST_APPDATA=str(r/'AppData'))
temp=r/'Temp';temp.mkdir(exist_ok=True);env.update(TEMP=str(temp),TMP=str(temp))
boot=r/'sandbox/Mods/bridge-boot.txt'
boot.write_text('Wait 3\nRequestSinglePlayer\nWait 2\nRequestCustom\nWait 2\nSelectLaunchType LOAD_SAVED_GAME\nWait 4\nSelect Save/Bridge-ready.RSG\nWait 2\nCommit\nWait 4\nStagingLaunch\n')
if (r/'installed-rivers.marker').is_file():
 helper=r/'sandbox/PawsInstalledRuntime.exe';assert helper.is_file()
 proc=subprocess.Popen([str(helper),'--game-dir',str(exe.parent)],cwd=exe.parent,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
 class Entry(c.Structure):
  _fields_=[('dwSize',c.c_uint),('cntUsage',c.c_uint),('th32ProcessID',c.c_uint),('th32DefaultHeapID',c.c_size_t),('th32ModuleID',c.c_uint),('cntThreads',c.c_uint),('th32ParentProcessID',c.c_uint),('pcPriClassBase',c.c_long),('dwFlags',c.c_uint),('szExeFile',c.c_wchar*260)]
 k=c.WinDLL('kernel32',use_last_error=True);k.CreateToolhelp32Snapshot.argtypes=[c.c_uint,c.c_uint];k.CreateToolhelp32Snapshot.restype=c.c_void_p;k.Process32FirstW.argtypes=[c.c_void_p,c.POINTER(Entry)];k.Process32NextW.argtypes=[c.c_void_p,c.POINTER(Entry)];k.OpenProcess.argtypes=[c.c_uint,c.c_int,c.c_uint];k.OpenProcess.restype=c.c_void_p;k.QueryFullProcessImageNameW.argtypes=[c.c_void_p,c.c_uint,c.c_wchar_p,c.POINTER(c.c_uint)];k.CloseHandle.argtypes=[c.c_void_p]
 deadline=time.monotonic()+20;pid=0
 while time.monotonic()<deadline and not pid:
  snap=k.CreateToolhelp32Snapshot(2,0);entry=Entry();entry.dwSize=c.sizeof(entry);ok=k.Process32FirstW(snap,c.byref(entry))
  while ok:
   if entry.szExeFile.lower()=='k2.exe':
    h=k.OpenProcess(0x1000,False,entry.th32ProcessID)
    if h:
     buf=c.create_unicode_buffer(32768);size=c.c_uint(32768)
     if k.QueryFullProcessImageNameW(h,0,buf,c.byref(size)) and Path(buf.value).resolve()==exe:pid=entry.th32ProcessID
     k.CloseHandle(h)
   ok=k.Process32NextW(snap,c.byref(entry))
  k.CloseHandle(snap)
  if not pid:time.sleep(.1)
 assert pid,'The private installed helper did not start its own game'
 state.write_text(json.dumps(dict(pid=pid,exe=str(exe),helperPid=proc.pid,helper=str(helper))))
 print('Started installed-runtime river QA',pid,'helper',proc.pid)
else:
 proc=subprocess.Popen([str(exe),*(['+Exec Mods/bridge-boot.txt'] if a.boot else [])],cwd=exe.parent,env=env)
 state.write_text(json.dumps(dict(pid=proc.pid,exe=str(exe))))
 print('Started owned bridge QA',proc.pid)
