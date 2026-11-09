"""Package accepted compiler inputs for rebuilding the scoped stable change."""
import zipfile
from context import *
NAMES=['context.py','preflight.py','build_helpers.py','prepare_041.py','live_stable.py','live_single.py','publish_041.py','bundle_sources.py']
def main():
 path=OUT/'stable-stage/assets/pure-0.4.1-build-inputs.zip';files={}
 for name in NAMES:
  p=HERE/name;files[str(p.relative_to(REPO)).replace('\\','/')]=p.read_bytes()
 for name in ['accepted-inputs','accepted-resources']:
  for p in (OUT/name).glob('*'):files[str(p.relative_to(REPO)).replace('\\','/')]=p.read_bytes()
 for name in ['accepted-build.json','baseline.json']:
  p=OUT/name;files[str(p.relative_to(REPO)).replace('\\','/')]=p.read_bytes()
 files['BUILD-INPUTS.txt']=b'Extract into the corresponding source checkout. Run tools/Pure050Release/build_helpers.py --out <new-directory>. Python, x86 TinyCC and the hash-bound 1.3.72 analysis image are external build dependencies. No signing key is included. Public runtime binaries are the immutable accepted build, not a claim of deterministic PE metadata.\n'
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
  for name,data in sorted(files.items()):
   i=zipfile.ZipInfo(name,(2026,11,9,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,data)
 write(OUT/'stable-stage/source-bundle.json',dict(path=str(path),sha256=sha(path),files=len(files),bytes=path.stat().st_size));print('PURE_BUILD_INPUTS_BUNDLED',len(files),path.stat().st_size)
if __name__=='__main__':main()
