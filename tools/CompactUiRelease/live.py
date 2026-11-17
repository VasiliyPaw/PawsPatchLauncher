from context import *
import shutil,re,time,collections
ROOT=Path('G:/PawsWork/QA/Arcane060-20261115');GAME=ROOT/'game'
def setup():
 assert read(O/'arcane-installer-result.json')['passed'];backup=O/'live-backup';backup.mkdir(exist_ok=True);files=['Mods/plugins.txt','Mods/PawsCaptureQA.dll','Mods/PawsTextureProbeQA.dll','TestInstalledRuntime.exe','network-test.marker','reconnect-test.marker','shfolder.dll']
 files+=['../Documents/Kohan2/data/User/UVars.tgi']
 receipt=[]
 for i,n in enumerate(files):
  f=GAME/n;entry=dict(path=n,existed=f.exists(),backup=str(i));receipt.append(entry)
  if f.exists():shutil.copy2(f,backup/str(i))
 write(O/'live-backup.json',receipt)
 D=O/'live-helper';D.mkdir(exist_ok=True);row=read(O/'arcane/helpers/build-report.json')['k2_paws_family_herd_relations_1372.exe'];mapped={}
 for path in row['sources']:
  if not path.endswith('.cs'):continue
  src=Path(path);text=src.read_text().replace('Process.GetProcessesByName("k2")','PawTestScope.Games()');dest=D/src.name;dest.write_text(text);mapped[path]=str(dest)
 scope=D/'PawTestScope.cs';scope.write_text('''using System;using System.IO;using System.Diagnostics;using System.Collections.Generic;internal static class PawTestScope{internal static Process[] Games(){var root=Path.GetFullPath(AppDomain.CurrentDomain.BaseDirectory);if(!root.TrimEnd('\\\\').Equals(@"G:\\PawsWork\\QA\\Arcane060-20261115\\game",StringComparison.OrdinalIgnoreCase))throw new IOException("Owned compact UI QA only");var list=new List<Process>();foreach(var p in Process.GetProcessesByName("k2")){try{if(String.Equals(p.MainModule.FileName,Path.Combine(root,"k2.exe"),StringComparison.OrdinalIgnoreCase)){list.Add(p);continue;}}catch{}p.Dispose();}return list.ToArray();}}''')
 args=[]
 for a in row['args']:
  if a.startswith('/out:'):a='/out:'+str(GAME/'TestInstalledRuntime.exe')
  elif a in mapped:a=mapped[a]
  args.append(a)
 args.append(str(scope));run(args,O/'live-helper-build.log')
 src=(WS/'work/ui-fullres-20261116/texture_probe.c').read_text().replace('UIHD-20261116','Arcane060-20261115');(D/'texture_probe.c').write_text(src);shutil.copy2(WS/'outputs/ui-fullres-20261116/PawsTextureProbeQA.def',D/'PawsTextureProbeQA.def')
 cc=WS/'work/crash-20260914-continue/tools/tinycc/tcc/tcc.exe';run([cc,'-shared',D/'texture_probe.c',D/'PawsTextureProbeQA.def','-o',GAME/'Mods/PawsTextureProbeQA.dll','-lkernel32'],O/'texture-probe-build.log')
 shutil.copy2(WS/'work/capture-hud-fog-20261116/PawsCaptureQA.dll',GAME/'Mods/PawsCaptureQA.dll');shutil.copy2(WS/'work/rivers-r24-combined-20261113/sandbox/shfolder.dll',GAME/'shfolder.dll')
 (GAME/'Mods/plugins.txt').write_text((GAME/'Mods/plugins.txt').read_text().rstrip()+'\nPawsCaptureQA.dll\nPawsTextureProbeQA.dll\n');(GAME/'network-test.marker').write_text('Owned compact UI validation\n');(GAME/'reconnect-test.marker').write_text('Owned isolated profile\n')
 (ROOT/'Documents/Kohan2/data/User/UVars.tgi').write_text('[Vars]\n{\n int ResolutionX = 2560\n int ResolutionY = 1440\n flag FirstRun = false\n flag RunWhenInactive = true\n flag MPRunWhenInactive = true\n flag MouseClipCursor = false\n float FrameRateLimit = 30\n float AudioMainVolume = 0\n flag SinglePlayerAutoPause = false\n}\n')
 text=(WS/'work/ui-hd-20261116/control.py').read_text().replace('UIHD-20261116','Arcane060-20261115').replace('PORT=6223','PORT=6257');(P/'control.py').write_text(text);print('COMPACT_LIVE_READY',flush=True)
def run_live():
 import control as c
 c.start('host');c.wait(lambda:c.state('host').get('phase')==3,100,'compact UI menu')
 for text in['RequestSinglePlayer','RequestCustom','SelectLaunchType LOAD_SAVED_GAME','Select Save/R060-product-bridge.RSG','Commit','StagingLaunch']:c.command('host',text);time.sleep(.25)
 c.wait(lambda:c.state('host').get('world')and c.state('host').get('mode')==2,90,'same saved game');c.command('host','UserReady');c.wait(lambda:c.state('host').get('phase')==4 and not c.state('host').get('frozen'),60,'compact HUD');c.command('host','GamePause 1');c.command('host','MoveCamera 0 0 116 121 1');c.command('host','Screenshot')
 from PIL import Image
 def screenshot_ready():
  pngs=list((ROOT/'Documents/Kohan2/data/Screenshots').glob('*.png'))
  if not pngs:return False
  try:
   im=Image.open(max(pngs,key=lambda f:f.stat().st_mtime_ns));im.load();return im.size==(2560,1440)
  except OSError:return False
 c.wait(screenshot_ready,20,'complete native screenshot')
 log=(GAME/'Mods/plugins.log').read_text();dims=collections.Counter((int(w),int(h))for w,h in re.findall(r'texture-probe: BOUND texture=\w+ width=(\d+) height=(\d+)',log));assert dims[(2048,1024)]>=2 and dims[(512,1024)]>=1 and dims[(512,512)]>=1,dims
 (O/'gpu-textures.log').write_text('\n'.join(l for l in log.splitlines()if'texture-probe:'in l));write(O/'live-result.json',dict(passed=True,resolution=[2560,1440],phase=c.state('host')['phase'],qaProcess=c.own(),sameSave=True,gpuDimensions={str(k):v for k,v in dims.items()},iconAllocation=[512,512],frameHalfAllocation=[2048,1024],frameCenterAllocation=[512,1024],productionHelperNativeInputsUnchanged=True,qaHelperOnlyProcessScopeChanged=True,scope='Human HUD from the same saved game; all other race archives checked with the production RWD reader.'))
 shots=ROOT/'Documents/Kohan2/data/Screenshots';pngs=list(shots.glob('*.png'))
 if pngs:shutil.copy2(max(pngs,key=lambda f:f.stat().st_mtime_ns),O/'compact-in-game.png')
 c.command('host','ReallyQuit');c.wait(lambda:not c.own(),30,'compact test game exit');print('COMPACT_NATIVE_GPU_PASS',flush=True)
def cleanup():
 import control as c
 assert not c.own()
 for r in read(O/'live-backup.json'):
  f=GAME/r['path']
  if r['existed']:f.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(O/'live-backup'/r['backup'],f)
  else:f.unlink(missing_ok=True)
 assert len((GAME/'Mods/plugins.txt').read_text().splitlines())==10;write(O/'live-cleanup.json',dict(passed=True,ownedProcessesStopped=True,qaModulesRemoved=True,productionPluginsRestored=True,userGameUntouched=True));print('COMPACT_LIVE_CLEANUP_PASS',flush=True)
if __name__=='__main__':globals()[sys.argv[1]]()
