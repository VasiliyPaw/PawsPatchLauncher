"""Rebuild pinned Arcane helpers without active-match admission.

No installation, game launch or upload. Other native resources are retained
byte-for-byte, including the lobby DLL built without legacy match recovery.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
VERSION='0.5.0-beta.4'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def run(args):
 p=subprocess.run([str(x) for x in args],capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stdout+'\n'+p.stderr)
 return p.stdout
def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 baseline=json.loads(a.baseline.read_text());out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);sources=out/'source';sources.mkdir()
 for row in baseline.values():
  for path,digest in row['sources'].items():assert sha(path)==digest.upper(),path
 for name in ['paws_patch_versions.ini','paws_player_colors.ini']:
  b=(a.baseline.parent/name).read_bytes()
  if name=='paws_patch_versions.ini':b=b.replace(b'0.5.0-beta.3',VERSION.encode())
  (out/name).write_bytes(b)
 report={}
 for name,row in baseline.items():
  args=[];removed=[]
  for arg in row['args']:
   if arg=='/define:PAW_HOTJOIN' or (arg.startswith('/resource:') and arg.endswith(',PawHotJoinNative')) or (arg.lower().endswith('.cs') and Path(arg).name=='PawHotJoin.cs'):
    removed.append(arg);continue
   if arg.startswith('/out:'):arg='/out:'+str(out/name)
   elif arg.lower().endswith('.cs'):
    source=Path(arg);text=source.read_text(encoding='utf-8-sig')
    if source.name.endswith('.generated.cs'):
     for call in [' PawHotJoin.Prepare(gameDirectory);',' PawHotJoin.Install(game, imageBase, delegate(string m) { AppendLog(logPath, m); });']:
      assert text.count(call)==1;text=text.replace(call,'')
     assert 'PawHotJoin' not in text
    if source.name.endswith('LargeMapsIdentity.cs'):
     assert text.count('0.5.0-beta.3')==1;text=text.replace('0.5.0-beta.3',VERSION)
    if source.name.endswith('BuildFeatures.cs'):
     anchor='#else\n        const string hotjoin = "";'
     assert text.count(anchor)==1
     current=re.search(r'        const string hotjoin = .*;',text).group(0)
     disabled=current.replace('hotJoinRevision\\\":1','hotJoinRevision\\\":0').replace(',\\\"hotJoinProtocol\\\":\\\"R\\\"','')
     assert disabled!=current and 'hotJoinProtocol' not in disabled
     text=text.replace(anchor,'#elif PAW_NO_HOTJOIN\n'+disabled+'\n'+anchor)
    target=sources/source.name
    if target.exists():assert target.read_text(encoding='utf-8')==text
    else:target.write_text(text,encoding='utf-8')
    arg=str(target)
   args.append(arg)
  assert len(removed)==3 and not any('PAW_PURE_RECOVERY' in x or 'PawMultiplayerSavesNative' in x for x in args)
  args.append('/define:PAW_NO_HOTJOIN');run(args)
  exe=out/name;features=json.loads(run([exe,'--features']))
  expected=dict(row['features'],patchVersion=VERSION,hotJoinRevision=0,legacySaveLobbyRecovery=False);expected.pop('hotJoinProtocol')
  assert features==expected
  assert b'PawHotJoin' not in exe.read_bytes() and b'PawMultiplayerSavesNative' not in exe.read_bytes()
  tests={flag:run([exe,flag]).strip() for flag in ['--quiet-startup-self-test','--common-ui-self-test','--lobby-payload-test','--assistant-self-test','--fast-transfer-self-test']}
  paths=[Path(x) for x in args if x.lower().endswith('.cs')]+[Path(x[10:].rsplit(',',1)[0]) for x in args if x.startswith('/resource:')]
  lobby=[x for x in paths if x.name=='paws_lobby_compatibility.dll'];assert len(lobby)==1 and b'PawRecovery' not in lobby[0].read_bytes()
  report[name]=dict(sha256=sha(exe),features=features,args=args,sources={str(x):sha(x) for x in paths},selfTests=tests,removedInputs=removed)
  print('NO_HOTJOIN_HELPER_PASS',name,flush=True)
 (out/'build-report.json').write_text(json.dumps(report,indent=2))
 (out/'acceptance.json').write_text(json.dumps(dict(accepted=True,version=VERSION,variants=len(report),selfTests=sum(len(x['selfTests']) for x in report.values()),activeMatchAdmission=False,legacySaveLobbyRecovery=False,otherResourcesRetained=True,liveGameLaunched=False),indent=2))
if __name__=='__main__':main()
