"""Archive exact accepted helper sources/resources and mode data provenance."""
import zipfile
from context import *

def main():
 files={};report=read(OUT/'beta-helpers-r4/build-report.json')
 def add(path):
  path=Path(path);rel=path.relative_to(REPO).as_posix();data=path.read_bytes();assert rel not in files or files[rel]==data;files[rel]=data
 for row in report.values():
  for path,h in row['sources'].items():assert sha(path)==h;add(path)
 for name in ['beta-helpers-r4/build-report.json','world-native-r2/build-inputs.json','world-native-r2/native/payload.json','world-data-r2/preparation.json','world-data-r2/localization.json','optional-data-r1/preparation.json','ui-native-r3/build.json','registry-native-r1/registry.json','baseline.json']:
  add(OUT/name)
 for folder,extensions in [('world-native-r2/source',{'.c','.h'}),('world-native-r2/native',{'.h'}),('ui-native-r3',{'.c','.h'}),('registry-native-r1',{'.c','.h'})]:
  for p in (OUT/folder).rglob('*'):
   if p.suffix in extensions:add(p)
 for p in HERE.glob('*.py'):add(p)
 files['BUILD-INPUTS.txt']=b'Exact Pure 0.5.0-beta.1 helper compiler inputs, resource binaries, and generated native source snapshots. No signing key or original game archive is included. build-report.json binds every accepted helper input by SHA-256 and records its compiler invocation. Original native game analysis image, x86 TinyCC/.NET Framework compilers and original game are external dependencies. Rebuild under corresponding paths or remap recorded paths. PE timestamps are not claimed deterministic. QA-only input/observer drivers are never part of installed packages. See the public source commit and release verification for scope, failed attempts and accepted live runs.\n'
 path=OUT/'beta-stage-r4/assets/pure-0.5.0-beta.1-build-inputs.zip'
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
  for name,data in sorted(files.items()):
   info=zipfile.ZipInfo(name,(2026,11,9,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,data)
 write(OUT/'beta-stage-r4/source-bundle.json',dict(path=str(path),files=len(files),size=path.stat().st_size,sha256=sha(path)));print('PURE_BETA_BUILD_INPUTS_BUNDLED',len(files),path.stat().st_size)
if __name__=='__main__':main()
