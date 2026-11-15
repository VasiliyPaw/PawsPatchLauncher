"""Rebuild all eight private variants from the pinned, accepted beta.2 inputs."""
import argparse,hashlib,json,re,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--baseline',type=Path,required=True);ap.add_argument('--native',type=Path,required=True);ap.add_argument('--fixture',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--version',default='0.5.0-local-world.1');a=ap.parse_args()
 baseline=json.loads(a.baseline.read_text());prep=json.loads((a.fixture/'preparation.json').read_text(encoding='utf-8'));out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);sources=out/'source';sources.mkdir()
 cycle=json.loads((a.native/'native/payload.json').read_text()).get('dynamicDayCycleSeconds',600)
 assert prep.get('dynamicDayCycleSeconds',600)==cycle,'Data/native cycle mismatch'
 version=a.version;assert re.fullmatch(r'[0-9A-Za-z.-]+',version)
 mapping={prep['baseline'][rel]:h for rel,h in prep['changed'].items() if rel in prep['baseline']};report={}
 for row in baseline.values():
  for p,h in row['sources'].items():assert sha(p)==h,p
 for name in ('paws_patch_versions.ini','paws_player_colors.ini'):
  value=(a.baseline.parent/name).read_bytes()
  if name=='paws_patch_versions.ini':value=value.replace(b'0.5.0-beta.2',version.encode())
  (out/name).write_bytes(value)
 for name,row in baseline.items():
  args=[]
  for arg in row['args']:
   if arg.startswith('/out:'):arg='/out:'+str(out/name)
   elif arg.lower().endswith('.cs'):
    p=Path(arg);text=p.read_text(encoding='utf-8-sig')
    if p.name=='MixedBiomesPayload.cs':text=(a.native/'native/MixedBiomesPatch.cs').read_text()
    else:
     for old,new in mapping.items():text=text.replace(old,new)
     if p.name.endswith('LargeMapsIdentity.cs'):text=text.replace('0.5.0-beta.2',version)
     if p.name.endswith('BuildFeatures.cs'):
      anchor='\\\"hotJoinRevision\\\":1';assert anchor in text
      text=text.replace(anchor,'\\\"dynamicDayCycleSeconds\\\":'+str(cycle)+',\\\"mixedBiomeSelectionRevision\\\":1,'+anchor)
    target=sources/p.name
    if target.exists():assert target.read_text(encoding='utf-8')==text
    else:target.write_text(text,encoding='utf-8')
    arg=str(target)
   args.append(arg)
  run=subprocess.run(args,capture_output=True,text=True);assert run.returncode==0,run.stdout+run.stderr
  features=json.loads(subprocess.check_output([str(out/name),'--features']));expected=dict(row['features'],patchVersion=version,dynamicDayCycleSeconds=cycle,mixedBiomeSelectionRevision=1);assert features==expected
  tests={}
  for flag in ('--quiet-startup-self-test','--common-ui-self-test','--lobby-payload-test','--assistant-self-test','--fast-transfer-self-test'):
   tests[flag]=subprocess.check_output([str(out/name),flag],text=True).strip()
  paths=[Path(p) for p in args if p.lower().endswith('.cs')]+[Path(p[10:].rsplit(',',1)[0]) for p in args if p.startswith('/resource:')]
  report[name]=dict(sha256=sha(out/name),features=features,args=args,sources={str(p):sha(p) for p in paths},selfTests=tests)
  print('PRIVATE_HELPER_PASS',name,flush=True)
 (out/'build-report.json').write_text(json.dumps(report,indent=2))
 shutil.copy2(out/'paws_patch_versions.ini',a.fixture/'game/paws_patch_versions.ini')
 for name in report:shutil.copy2(out/name,a.fixture/'game'/name)
 from refresh_state import refresh
 refresh(a.fixture,report,version)
 print('PRIVATE_WORLD_OPTIONS_HELPERS_READY',len(report))
if __name__=='__main__':main()
