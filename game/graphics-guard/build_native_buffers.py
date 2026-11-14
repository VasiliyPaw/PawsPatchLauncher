"""Product graphics guard with native buffer allocation and lifetime semantics."""
import argparse,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
WS=REPO.parents[1]
TCC=WS/'work/crash-20260914-continue/tools/tinycc/tcc/tcc.exe'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()
def build(out):
 out=Path(out).resolve()
 if out.drive.upper()!='G:':raise ValueError('Project build output must be on G:')
 out.mkdir(parents=True,exist_ok=False);temp=out/'temp';temp.mkdir()
 env=os.environ.copy();env.update(TEMP=str(temp),TMP=str(temp))
 source=(HERE/'graphics_guard.c').read_text()
 anchor='static void hook_device(Com *dev) {'
 assert source.count(anchor)==1 and 'gpu_hook_device'not in source
 source=source.replace(anchor,'#include "native_buffers.h"\n'+anchor)
 (out/'graphics_guard_native.c').write_text(source)
 for name in ['d3d_abi_slots.h','native_buffers.h']:shutil.copy2(HERE/name,out/name)
 command=[str(TCC),'-shared','-Wall','-Werror',str(out/'graphics_guard_native.c'),'-o',str(out/'d3d9.dll'),'-lkernel32']
 subprocess.run(command,env=env,check=True)
 subprocess.run([sys.executable,str(HERE/'prepare_guard_exports.py'),str(out/'d3d9.dll')],env=env,check=True,stdout=subprocess.DEVNULL)
 proof=dict(sha256=sha(out/'d3d9.dll'),nativeBufferOwnership=True,bufferReuseRevision=0,warmAlwaysDisabled=True,fixtureNotShipped=True,drawGuardSourceSha256=sha(HERE/'graphics_guard.c'),compiler=command,sources={p.name:sha(p)for p in out.iterdir()if p.suffix in ['.c','.h']})
 (out/'product.json').write_text(json.dumps(proof,indent=2))
 return proof
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args();print(json.dumps(build(a.out),indent=2))
if __name__=='__main__':main()
