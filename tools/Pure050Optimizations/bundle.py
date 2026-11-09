"""Archive exact generated helper and native inputs; no game or private key."""
import zipfile
from context import *
def main():
 files={}
 def add(p):
  p=Path(p);name=p.relative_to(REPO).as_posix();data=p.read_bytes();assert name not in files or files[name]==data;files[name]=data
 for name,row in read(OUT/'helpers-r1/build-report.json').items():
  assert sha(OUT/'helpers-r1'/name)==row['sha256']
  for p,h in row['sources'].items():assert sha(p)==h;add(p)
 for folder in ['native-r1','helpers-r1/source']:
  for p in(OUT/folder).rglob('*'):
   if p.suffix in['.c','.h','.cs']:add(p)
 for n in ['baseline.json','helpers-r1/build-report.json','native-r1/build.json','native-r1/cache-build/payload.json','native-r1/graphics/product.json','stage-r3/audit.json']:add(OUT/n)
 for p in HERE.glob('*.py'):add(p)
 files['BUILD-INPUTS.txt']=b'Pure 0.5.0-beta.2 exact helper compiler inputs/resources and generated native C/header snapshots. No signing keys, game EXE, original game archives or private QA loader are included. Resource-cache emitted bytes/relocations are preserved in ResourceCachePayload.cs. Compile the Pure native DLL with TinyCC x86 using the recorded build.json arguments. Graphics C/headers preserve the accepted 112920FF production DLL; game/graphics-guard/prepare_guard_exports.py from the public source revision completes exports. Managed helpers use x86 .NET Framework csc with the recorded arguments. Paths can be remapped to this archive. PE timestamps are not claimed deterministic. QA scripts are provided for evidence/reproduction and are never installed. See the release verification for actual native checks, scoped live acceptance and limitations.\n'
 target=OUT/'stage-r3/assets'/('pure-'+PATCH+'-build-inputs.zip')
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
  for name,data in sorted(files.items()):
   item=zipfile.ZipInfo(name,(2026,11,9,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED;z.writestr(item,data)
 write(OUT/'stage-r3/source-bundle.json',dict(files=len(files),size=target.stat().st_size,sha256=sha(target)));print('PURE_OPT_BUILD_INPUTS_BUNDLED',len(files),target.stat().st_size)
if __name__=='__main__':main()
