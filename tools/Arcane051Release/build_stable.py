"""Rebuild the accepted beta.4 snapshot, changing only its release identity."""
import hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
OUT=REPO/'outputs/arcane-051-release-20261109/stable';BASE=Path('C:/PawsNoHotJoinQA-20261107/helpers-r2')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def run(args):
 r=subprocess.run(list(map(str,args)),capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 if r.returncode:raise RuntimeError(r.stdout+'\n'+r.stderr)
 return r.stdout
def main():
 rows=json.loads((BASE/'build-report.json').read_text());out=OUT/'helpers';out.mkdir(parents=True,exist_ok=False);src=out/'source';src.mkdir();report={}
 for row in rows.values():
  assert row['features']['hotJoinRevision']==0 and row['features']['legacySaveLobbyRecovery'] is False
  for path,h in row['sources'].items():assert sha(path)==h.upper(),path
 for n in ['paws_patch_versions.ini','paws_player_colors.ini']:
  b=(BASE/n).read_bytes();(out/n).write_bytes(b.replace(b'0.5.0-beta.4',b'0.5.0') if 'versions' in n else b)
 for n,row in rows.items():
  args=[]
  for arg in row['args']:
   if arg.startswith('/out:'):arg='/out:'+str(out/n)
   elif arg.lower().endswith('.cs'):
    p=Path(arg);b=p.read_bytes()
    if p.name.endswith('LargeMapsIdentity.cs'):
     assert b.count(b'0.5.0-beta.4')==1;b=b.replace(b'0.5.0-beta.4',b'0.5.0')
    q=src/p.name
    if q.exists():assert q.read_bytes()==b
    else:q.write_bytes(b)
    arg=str(q)
   args.append(arg)
  run(args);f=json.loads(run([out/n,'--features']));assert f==dict(row['features'],patchVersion='0.5.0'),n
  tests={flag:run([out/n,flag]).strip() for flag in ['--quiet-startup-self-test','--common-ui-self-test','--lobby-payload-test','--assistant-self-test','--fast-transfer-self-test']}
  inputs=[Path(x) for x in args if x.lower().endswith('.cs')]+[Path(x[10:].rsplit(',',1)[0]) for x in args if x.startswith('/resource:')]
  assert all('PawHotJoinNative' not in x and 'PawMultiplayerSavesNative' not in x for x in args)
  report[n]=dict(sha256=sha(out/n),features=f,args=args,sources={str(p):sha(p) for p in inputs},selfTests=tests)
  print('STABLE_HELPER_PASS',n,flush=True)
 (out/'build-report.json').write_text(json.dumps(report,indent=2))
 print('STABLE_SNAPSHOT_PASS eight variants,40 self-tests, no new gameplay/runtime changes',flush=True)
if __name__=='__main__':main()
