"""Preserve the exact installed helper composition; isolate its profile paths."""
from pathlib import Path
import argparse,json,hashlib,re,subprocess
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--baseline',type=Path,default=Path('F:/PawsMinimapCrashPublish-20261109/arcane-helpers'));a=p.parse_args()
out=a.out.resolve();assert (out/'installed-rivers.marker').is_file()
name='k2_paws_lobby_colors_mp_sync_1372.exe';report=json.loads((a.baseline/'build-report.json').read_text());row=report[name]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
baseline=json.loads((out/'installed-baseline.json').read_text());assert sha(Path(baseline['game'])/name)==row['sha256']
src=out/'helper-source';src.mkdir(exist_ok=True);changes={};args=[]
for arg in row['args']:
 if arg.startswith('/out:'):args.append('/out:'+str(out/'sandbox/PawsInstalledRuntime.exe'));continue
 if arg.lower().endswith('.cs'):
  path=Path(arg);assert sha(path)==row['sources'][str(path)];text=path.read_text(encoding='utf-8-sig');count=0
  for folder,property in [('MyDocuments','Documents'),('LocalApplicationData','AppData')]:
   text,n=re.subn(r'Environment\.GetFolderPath\(\s*Environment\.SpecialFolder\.'+folder+r'\s*\)','global::PawRiverPrivatePaths.'+property,text);count+=n
  if path.name.endswith('.generated.cs'):
   assert text.count('                    UseShellExecute = true,')==1
   text=text.replace('                    UseShellExecute = true,','                    UseShellExecute = false,')
  target=src/path.name;target.write_text(text,encoding='utf-8');args.append(str(target))
  if count:changes[path.name]=count
 else:
  if arg.startswith('/resource:'):
   path=Path(arg[10:].rsplit(',',1)[0]);assert sha(path)==row['sources'][str(path)]
  args.append(arg)
private=src/'PawRiverPrivatePaths.cs';private.write_text('''using System;using System.IO;
internal static class PawRiverPrivatePaths {
 internal static string Documents {get{return Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"..","Documents"));}}
 internal static string AppData {get{return Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"..","AppData"));}}
}
''');args.append(str(private))
result=subprocess.run(args,capture_output=True,text=True);assert result.returncode==0,result.stdout+result.stderr
exe=out/'sandbox/PawsInstalledRuntime.exe';features=json.loads(subprocess.check_output([str(exe),'--features'],text=True));assert features==row['features']
tests={}
for flag in ['--quiet-startup-self-test','--common-ui-self-test','--lobby-payload-test','--assistant-self-test','--fast-transfer-self-test']:
 result=subprocess.run([str(exe),flag],capture_output=True,text=True);assert result.returncode==0,result.stdout+result.stderr;tests[flag]=result.stdout.strip()
(out/'installed-helper.json').write_text(json.dumps(dict(installedHelper=name,installedSha256=row['sha256'],privateHelperSha256=sha(exe),features=features,profilePathSubstitutions=changes,selfTests=tests,args=args),indent=2));print('FULL_INSTALLED_HELPER_READY',exe,'features',len(features),'profileOnlyChanges',changes)
