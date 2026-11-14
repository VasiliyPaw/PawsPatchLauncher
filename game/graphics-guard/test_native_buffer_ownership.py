"""Real D3D9 ownership regressions; optionally compare the retired QA pool.

Usage: --out G:/... --candidate G:/.../d3d9.dll [--legacy-fixture G:/.../d3d9-fixture.dll]
Requires a desktop with a working D3D9 HAL. Exit 2 from C fixture is setup failure.
"""
import argparse,json,os,subprocess
from pathlib import Path
from build_native_buffers import TCC
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--candidate',required=True,type=Path);p.add_argument('--legacy-fixture',type=Path);a=p.parse_args()
 out=a.out.resolve();assert out.drive.upper()=='G:';out.mkdir(parents=True,exist_ok=False);temp=out/'temp';temp.mkdir();env=os.environ.copy();env.update(TEMP=str(temp),TMP=str(temp))
 exe=out/'test_buffer_ownership.exe';subprocess.run([str(TCC),'-Wall','-Werror',str(Path(__file__).with_name('test_buffer_ownership.c')),'-o',str(exe),'-luser32','-lkernel32'],env=env,check=True)
 versions={'candidate':a.candidate}
 if a.legacy_fixture:versions['legacy']=a.legacy_fixture
 results=[];failed=False
 for version,dll in versions.items():
  for kind in ['vb','ib']:
   for flags in ['0x24','0x44','0x84']:
    for mode in ['apply','record','retained']:
     r=subprocess.run([str(exe),str(dll.resolve()),mode,kind,flags],env=env,capture_output=True,text=True);expected=1 if version=='legacy' and mode!='apply'else 0
     results.append(dict(version=version,kind=kind,flags=flags,mode=mode,exitCode=r.returncode,expected=expected,stdout=r.stdout,stderr=r.stderr));failed|=r.returncode!=expected
 (out/'ownership-regressions.json').write_text(json.dumps(results,indent=2));print('OWNERSHIP_MATRIX',len(results),'FAIL'if failed else'PASS');raise SystemExit(int(failed))
if __name__=='__main__':main()
