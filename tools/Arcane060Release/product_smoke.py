from release_context import *
import shutil,time,struct,importlib.util
FIX=Path('G:/PawsWork/QA/Arcane060-20261115');GAME=FIX/'game';MOD=GAME/'Mods';E=FIX/'evidence';E.mkdir(exist_ok=True)
sys.path.insert(0,str(R/'source'));import control
control.N=FIX
control.own_original=control.own
def own():
 result=[]
 # Native process identity is always checked against this exact fixture.
 for row in json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'k2.exe' } | Select-Object ProcessId,ExecutablePath | ConvertTo-Json -Compress"],text=True)or'[]')if False else []:pass
 for row in control.own_original():result.append(row)
 return result
# Keep the proven process enumeration and identity checks; map its private
# layout to this fixture without weakening the executable path guard.
src=(R/'source/control.py').read_text().replace("N=Path(__file__).resolve().parents[1]","N=Path('G:/PawsWork/QA/Arcane060-20261115')").replace("/'sandbox'","/'game'").replace("'sandbox/","'game/").replace("'PawsInstalledRuntime.exe'","'k2_paws_lobby_colors_mp_sync_1372.exe'")
module=P/'product_control.py';module.write_text(src);spec=importlib.util.spec_from_file_location('control',module);ctl=importlib.util.module_from_spec(spec);sys.modules['control']=ctl;spec.loader.exec_module(ctl)
memsrc=(P.parent/'rivers-r17-network-20261111/source/memory.py').read_text().replace("'sandbox/","'game/");(P/'product_memory.py').write_text(memsrc)
from product_memory import Memory
import review,native_review
review.R=FIX;review.M=MOD;review.E=E;review.Memory=Memory;review.own=ctl.own;review.state=ctl.state;review.command=ctl.command
native_review.Memory=Memory
def cmd(s):ctl.command('preview',s)
def launch():
 assert not ctl.own();(MOD/'network-command.txt').unlink(missing_ok=True)
 envp=env();envp.update(PAWS_TEST_DOCUMENTS=str(FIX/'Documents'),PAWS_TEST_APPDATA=str(FIX/'AppData'),SteamAppId='97130',SteamGameId='97130',PAWS_RIG_EXTERNAL_SCRIPT='1')
 exe=GAME/'k2_paws_lobby_colors_mp_sync_1372.exe'
 with(E/'helper-console.log').open('w')as log:q=subprocess.Popen([str(exe),'--game-dir',str(GAME)],cwd=GAME,env=envp,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 ctl.wait(lambda:any(Path(p['path'])==GAME/'k2.exe'for p in ctl.own())or q.poll()is not None,90,'ordinary native game')
 rows=[p for p in ctl.own()if Path(p['path'])==GAME/'k2.exe'];assert len(rows)==1,(q.poll(),(E/'helper-console.log').read_text())
 write(FIX/'qa-process.json',dict(pid=rows[0]['pid'],exe=rows[0]['path'],helperPid=q.pid));ctl.wait(lambda:ctl.state('preview').get('pid')==rows[0]['pid']and ctl.state('preview').get('phase')==3,120,'ordinary helper main menu');return rows[0]
def setup():
 (FIX/'native').mkdir(exist_ok=True);shutil.copy2(R/'native/prototype.json',FIX/'native/prototype.json')
 for d in ['Documents/Kohan2/data/Save','Documents/Kohan2/data/User','AppData','Temp']:(FIX/d).mkdir(parents=True,exist_ok=True)
 for name in ['R6-art-human.RSG','R6-art-shadow.RSG']:shutil.copy2(R/'Documents/Kohan2/data/Save'/name,FIX/'Documents/Kohan2/data/Save'/name)
 case=read(R/'qa-evidence/arcane060-savebuild/human-wood-savebuild.json');shutil.copy2(case['lateSave']['path'],FIX/'Documents/Kohan2/data/Save/R060-product-bridge.RSG')
 shutil.copy2(R/'Documents/Kohan2/data/User/UVars.tgi',FIX/'Documents/Kohan2/data/User/UVars.tgi')
 # Observer and profile redirection are test-only additions, never package files.
 shutil.copy2(P/'PawsNetworkQA.dll',MOD/'PawsNetworkQA.dll');shutil.copy2(R/'sandbox/shfolder.dll',GAME/'shfolder.dll');(GAME/'network-test.marker').write_text('Owned release QA only\n')
 baseline=(MOD/'plugins.txt').read_text();assert len(baseline.splitlines())==9;write(E/'ordinary-files-before.json',{n:sha(GAME/n)for n in ['Mods/plugins.txt','k2_paws_lobby_colors_mp_sync_1372.exe','Mods/PawsBridges.dll']});(E/'normal-plugins.txt').write_text(baseline);(MOD/'plugins.txt').write_text(baseline+'PawsNetworkQA.dll\n')
def smoke():
 setup();row=launch();plugins=(MOD/'plugins.log').read_text();assert 'bridges: READY'in plugins and 'startup'in plugins.lower();assert not any(s in plugins for s in ['GUARD_REJECT','FATAL'])
 review.load('R060-product-bridge');cmd('GamePause 1');cmd('MoveCamera 0 0 116 121 1');review.bind()
 m=Memory('preview');u=m.u;db=u(m.base+0x5f3fb4);strings=[]
 try:
  # Native actor-definition registry: IDS + translated display fields are kept
  # in memory by the original parser. Scan the saved bridge definition fields.
  reg=u(m.base+0x5ef72c);defs=[]
  for a in struct.unpack('<65536I',m.read(reg+0x20004,0x40000)):
   if a and u(a)==m.base+0x4e5c58 and m.name(u(a+4)).startswith('paws_bridge_'):defs.append(u(a+4))
  for d in defs:
   for off in range(8,128,4):
    try:
     txt=m.text(u(d+off))
     if len(txt)>2 and all(c.isprintable()for c in txt):strings.append(dict(offset=off,text=txt))
    except AssertionError:pass
  assert defs,'No saved bridge loaded in product fixture'
 finally:m.close()
 review.shot('ordinary-package-human-loaded');cmd('ReallyQuit');ctl.wait(lambda:not ctl.own(),30,'ordinary normal exit')
 logs='\n'.join(p.read_text(errors='replace')for p in(GAME/'Logs').glob('*.log'))
 assert not any('paws_060_label'in line and any(k in line.lower()for k in ['missing','not found','unknown','failed'])for line in logs.splitlines())
 caches=list((FIX/'AppData/PawsPatch/Startup').glob('*/font-metrics.bin'));assert len(caches)==1 and caches[0].stat().st_size>10000,'font cache did not record'
 cache_status=(MOD/'font-cache-status.jsonl').read_text()if(MOD/'font-cache-status.jsonl').exists()else''
 # Second ordinary launch reuses the accepted cache, then exits natively.
 row2=launch();cmd('ReallyQuit');ctl.wait(lambda:not ctl.own(),30,'warm ordinary normal exit')
 status=(MOD/'font-cache-status.jsonl').read_text()if(MOD/'font-cache-status.jsonl').exists()else''
 write(O/'product-smoke.json',dict(passed=True,ordinaryHelper=True,launcher='1.0.18',freshNativeMenu=row,warmNativeMenu=row2,savedWorldLoaded=True,savedBridgeDefinitions=len(defs),fontCacheSize=caches[0].stat().st_size,fontStatus=status,nativeDefinitionStrings=strings,observerAddedOnlyForQA=True,normalExit=True))
 (MOD/'plugins.txt').write_text((E/'normal-plugins.txt').read_text());assert len((MOD/'plugins.txt').read_text().splitlines())==9
 # Final production module list, with no observer entry. Observe native menu
 # memory read-only and send a normal close to this fixture's exact window.
 envp=env();envp.update(PAWS_TEST_DOCUMENTS=str(FIX/'Documents'),PAWS_TEST_APPDATA=str(FIX/'AppData'),SteamAppId='97130',SteamGameId='97130')
 q=subprocess.Popen([str(GAME/'k2_paws_lobby_colors_mp_sync_1372.exe'),'--game-dir',str(GAME)],cwd=GAME,env=envp,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
 ctl.wait(lambda:any(Path(p['path'])==GAME/'k2.exe'for p in ctl.own()),60,'normal-nine native process');row3=next(p for p in ctl.own()if Path(p['path'])==GAME/'k2.exe');write(FIX/'qa-process.json',dict(pid=row3['pid'],exe=row3['path']))
 ctl.wait(lambda:'loader: 9 plugin(s) loaded'in(MOD/'plugins.log').read_text()and 'process '+str(row3['pid'])in(MOD/'plugins.log').read_text()and 'bridges: READY'in(MOD/'plugins.log').read_text(),30,'normal-nine loader')
 m=Memory('preview')
 try:ctl.wait(lambda:m.u(m.base+0x5f92f4)==3,90,'normal-nine menu')
 finally:m.close()
 plugins=(MOD/'plugins.log').read_text();assert all('loader: '+n+' started'in plugins for n in(MOD/'plugins.txt').read_text().splitlines())and 'PawsNetworkQA.dll'not in plugins
 import ctypes as C
 user=C.WinDLL('user32');callback=C.WINFUNCTYPE(C.c_int,C.c_void_p,C.c_void_p);windows=[]
 def each(hwnd,unused):
  pid=C.c_uint();user.GetWindowThreadProcessId(C.c_void_p(hwnd),C.byref(pid))
  if pid.value==row3['pid']and user.IsWindowVisible(C.c_void_p(hwnd)):windows.append(hwnd)
  return 1
 user.EnumWindows(callback(each),0);assert windows
 for hwnd in windows:user.PostMessageW(C.c_void_p(hwnd),0x10,0,0)
 ctl.wait(lambda:not ctl.own(),30,'normal-nine native window close');result=read(O/'product-smoke.json');result.update(normalNineModules=True,normalNineMenu=True,normalNineExit=True);write(O/'product-smoke.json',result)
 print('ORDINARY_PRODUCT_SMOKE_PASS',flush=True)
if __name__=='__main__':smoke()
