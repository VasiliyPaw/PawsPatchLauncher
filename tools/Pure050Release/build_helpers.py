"""Rebuild four Pure variants from verified beta.12 sources without recovery."""
import argparse,subprocess,shutil
from context import *
def run(args):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 return p.stdout
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve();out.mkdir(exist_ok=False,parents=True);native=out/'native';native.mkdir();sources=out/'source';sources.mkdir()
 # Compile the lobby-only DLL: no reconnect.c, integrated.inc or recovery macro.
 for name in ['lobby_compatibility.c','native_tests.c']:shutil.copy2(REPO/'game/lobby-compatibility'/name,native/name)
 (native/'build.log').write_text(run([TCC,'-shared','-Wall','-Werror',native/'lobby_compatibility.c','-o',native/'paws_lobby_compatibility.dll','-lkernel32','-luser32']))
 run([TCC,'-Wall','-Werror',native/'native_tests.c','-o',native/'LobbyTests.exe','-lkernel32','-luser32'])
 (native/'tests.log').write_text(run([native/'LobbyTests.exe',LEG/'k2_runtime_1372_20260904.bin']))
 import pefile
 pe=pefile.PE(str(native/'paws_lobby_compatibility.dll'));assert not any(b'Recovery' in e.name for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name)
 report={}
 for name,row in read(OUT/'accepted-build.json').items():
  args=[]
  for arg in row['args']:
   if arg.startswith('/out:'):arg='/out:'+str(out/name)
   elif arg.startswith('/define:'):arg=';'.join(x for x in arg.split(';') if x!='PAW_PURE_RECOVERY');assert 'PAW_PURE_RECOVERY' not in arg
   elif arg.startswith('/resource:') and arg.endswith(',PawLobbyCompatibilityNative'):arg='/resource:'+str(native/'paws_lobby_compatibility.dll')+',PawLobbyCompatibilityNative'
   elif arg.startswith('/resource:'):
    path,label=arg[10:].rsplit(',',1);arg='/resource:'+str(OUT/'accepted-resources'/Path(path).name)+','+label
   elif arg.lower().endswith('.cs'):
    src=OUT/'accepted-inputs'/Path(arg).name;text=src.read_text(encoding='utf-8-sig')
    if src.name.endswith('PureChannel.cs'):
     text=text.replace('"stable", Version = "1.3.72-pure.14", PatchVersion = "0.4.0"','"stable", Version = "1.3.72-pure.16", PatchVersion = "0.4.1"')
     anchor='                return result;';assert anchor in text;text=text.replace(anchor,'                result = result.TrimEnd(\'}\') + ",\\\"matchRecoveryEnabled\\\":false}";\n'+anchor)
    if src.name.endswith('Program.cs'):text=text.replace('1.3.72.12','1.3.72.16')
    dst=sources/src.name
    if dst.exists():assert dst.read_text(encoding='utf-8')==text
    else:dst.write_text(text,encoding='utf-8')
    arg=str(dst)
   args.append(arg)
  run(args);features=json.loads(run([out/name,'--features']));assert features['patchVersion']=='0.4.1' and features['channel']=='stable' and features['version']=='1.3.72-pure.16';assert features['matchRecoveryEnabled'] is False and 'matchRecoveryRevision' not in features;assert features['multiplayerSavesRevision']==2
  for flag in ['cityAssistant','automaticMilitia','additionalBuildingSlots','foundationDistribution','fractionalKingdomPoints']:assert features[flag] is False
  assert {k:v for k,v in features.items() if k not in ['version','channel','patchVersion','matchRecoveryEnabled']}=={k:v for k,v in row['features'].items() if k not in ['version','channel','patchVersion','matchRecoveryRevision','saveSourceGuardRevision','saveCoordinationRevision','matchRecoveryMode','automaticDropVoting']}
  paths=[Path(x) for x in args if x.lower().endswith('.cs')]+[Path(x[10:].rsplit(',',1)[0]) for x in args if x.startswith('/resource:')]
  report[name]=dict(sha256=sha(out/name),features=features,args=args,sources={str(x):sha(x) for x in paths})
  if 'fixes_' in name:
   test=out/'CompositionTests.exe';ta=[('/target:exe' if x.startswith('/target:') else '/out:'+str(test) if x.startswith('/out:') else '/main:PawPureFixes.PureBetaNativeTests' if x.startswith('/main:') else x) for x in args]+[str(REPO/'game/pure-fixes/PureBetaNativeTests.cs')]
   run(ta);(out/'composition-tests.log').write_text(run([test,LEG/'k2_runtime_1372_20260904.bin']))
  print('PURE_041_HELPER_PASS',name,flush=True)
 write(out/'build-report.json',report)
if __name__=='__main__':main()
