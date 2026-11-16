from context import *
import shutil,re
Q=O/'network-qa';Q.mkdir(exist_ok=True)
def build():
 row=read(O/'helpers/build-report.json')['k2_paws_pure_fixes_1372.exe'];mapped={}
 for path in row['sources']:
  if not path.endswith('.cs'):continue
  src=Path(path);s=src.read_text();s=s.replace('Process.GetProcessesByName("k2")','PawTestScope.Games()');dest=Q/src.name;dest.write_text(s);mapped[path]=str(dest)
 scope=Q/'PawTestScope.cs';scope.write_text('''using System;using System.IO;using System.Linq;using System.Diagnostics;using System.Collections.Generic;
internal static class PawTestScope{internal static Process[] Games(){string root=Path.GetFullPath(AppDomain.CurrentDomain.BaseDirectory);if(!root.StartsWith(@"G:\\PawsWork\\QA\\Pure050Beta7-20261116\\",StringComparison.OrdinalIgnoreCase))throw new InvalidOperationException("Owned QA fixture only");var r=new List<Process>();foreach(var p in Process.GetProcessesByName("k2")){try{if(String.Equals(Path.GetFullPath(p.MainModule.FileName),Path.Combine(root,"k2.exe"),StringComparison.OrdinalIgnoreCase)){r.Add(p);continue;}}catch{}p.Dispose();}return r.ToArray();}}''')
 args=[]
 for a in row['args']:
  if a.startswith('/out:'):a='/out:'+str(Q/'TestInstalledRuntime.exe')
  elif a in mapped:a=mapped[a]
  args.append(a)
 args.append(str(scope));run(args,Q/'build.log');write(Q/'build-report.json',dict(sha256=sha(Q/'TestInstalledRuntime.exe'),productionHelper=row['sha256'],nativeSha256=read(O/'native/build-report.json')['sha256'],onlyQaSourceChange='Process discovery restricted to exact current owned fixture',nativePayloadUnchanged=True));print('PURE_SCOPED_QA_HELPER_READY')
def setup(mode):
 root=FIX/mode;game=root/'game';assert read(game/'.pawpatch/state.json')['modules']['pure-fixes-runtime']['version']==RUNTIME
 # Create just the two peers needed for this mode. Immutable archives are hardlinked.
 for role in ['client','witness']:
  dest=FIX/('network-'+mode)/role/'game'
  assert not dest.exists(),dest;dest.parent.mkdir(parents=True,exist_ok=True)
  def omit(folder,names):return [n for n in names if n in ['.pawpatch','Logs','Mods']or n.endswith('-status.txt')]
  shutil.copytree(game,dest,ignore=omit,copy_function=lambda a,b:os.link(a,b)if Path(a).suffix.lower()=='.rwd'else shutil.copy2(a,b))
  (dest/'.pawpatch').mkdir(exist_ok=True);shutil.copy2(game/'.pawpatch/state.json',dest/'.pawpatch/state.json')
 for role in ['host','client','witness']:
  r=root if role=='host'else FIX/('network-'+mode)/role;g=r/'game';mods=g/'Mods';mods.mkdir(exist_ok=True)
  before={str(f.relative_to(g)):f.read_bytes().hex()if f.exists()else None for f in [g/'avifil32.dll',g/'shfolder.dll',mods/'plugins.txt',g/'network-test.marker']};write(r/'qa-before.json',before)
  shutil.copy2(Q/'TestInstalledRuntime.exe',g/'TestInstalledRuntime.exe');shutil.copy2(WS/'work/capture-hud-fog-20261116/PawsCaptureQA.dll',mods/'PawsCaptureQA.dll');shutil.copy2(WS/'work/rivers-r24-combined-20261113/sandbox/shfolder.dll',g/'shfolder.dll')
  shutil.copy2(Path('G:/PawsWork/QA/Arcane060-20261115/game/avifil32.dll'),g/'avifil32.dll');(mods/'plugins.txt').write_text('PawsCaptureQA.dll\n');(g/'network-test.marker').write_text('Pure beta.7 owned QA only\n');(g/'steam_appid.txt').write_text('97130\n')
  shutil.copy2(Q/'RigInput.dll',mods/'RigInput.dll');(mods/'plugins.txt').write_text('RigInput.dll\nPawsCaptureQA.dll\n');(g/'reconnect-test.marker').write_text('Owned QA private profile and Direct IP only\n')
  for d in ['Documents/Kohan2/data/User','Documents/Kohan2/data/Save','AppData','Temp']:(r/d).mkdir(parents=True,exist_ok=True)
  profile=r/'Documents/Kohan2/data/User/UVars.tgi';profile.write_text('[Vars]\n{\n int ResolutionX = 800\n int ResolutionY = 600\n flag FirstRun = false\n flag RunWhenInactive = true\n flag MPRunWhenInactive = true\n flag MouseClipCursor = false\n float FrameRateLimit = 30\n float AudioMainVolume = 0\n flag ViewShadows = false\n int ResourceCacheTextureRAMWeight = 5\n int ResourceCacheTextureVRAMWeight = 5\n}\n')
 print('PURE_THREE_QA_PEERS_READY',mode)
if __name__=='__main__':build()if sys.argv[1]=='build'else setup(sys.argv[1])
