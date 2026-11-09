"""Preserve exact build inputs as a release attachment, without private keys."""
import argparse,hashlib,json,zipfile
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
def sha(b):return hashlib.sha256(b).hexdigest().upper()
def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',required=True,type=Path);a=p.parse_args();stage=a.stage.resolve();prep=json.loads((stage/'preparation.json').read_text());helpers=Path(prep['helpers']);native=Path(prep['native']);files={}
 def add(path,name,expected=None):
  b=path.read_bytes();assert expected is None or sha(b)==expected.upper(),path
  assert name not in files or files[name]==b,name;files[name]=b
 for row in json.loads((helpers/'build-report.json').read_text()).values():
  for path,h in row['sources'].items():
   path=Path(path)
   if path.suffix=='.cs':add(path,'helpers/source/'+path.name,h)
 for path in native.iterdir():
  if path.suffix in ['.c','.h'] and path.name not in ['ui-qa.c','qa.h']:add(path,'native/'+path.name)
 add(native/'cache/cache.c','native/cache/cache.c')
 for path in (native/'graphics').iterdir():
  if path.suffix in ['.c','.h','.def'] and 'fixture' not in path.name:add(path,'native/graphics/'+path.name)
 for path in (REPO/'game/resource-cache').iterdir():
  if path.suffix in ['.py','.cs'] and path.name!='ResourceCachePayload.cs':add(path,'tools/resource-cache/'+path.name)
 for path in (REPO/'tools/Arcane051Release').iterdir():
  if path.suffix in ['.py','.cs']:add(path,'tools/release/'+path.name)
 add(REPO/'game/graphics-guard/prepare_guard_exports.py','tools/prepare_guard_exports.py')
 add(REPO/'game/presentation-runtime/PresentationRuntimePatch.cs','helpers/PresentationRuntimePatch.cs')
 for name in ['runtime.json','cache-build/payload.json','graphics/product.json']:add(native/name,'metadata/'+name.replace('/','-'))
 add(helpers/'build-report.json','metadata/helper-build-report.json')
 files['README.md']=b'''# Arcane Wars 0.5.1-beta.1 exact build inputs\n\nAll eight generated managed helper sources and the exact native UI/Find/cache/graphics sources are included. No installed game, saves, credentials or signing keys are included. The separate launcher source is in the tagged Git revision.\n\nManaged helpers: .NET Framework 4 x86 csc, arguments in metadata/helper-build-report.json (replace local paths with helpers/source paths). Build PawsPresentation1372.dll first using TinyCC x86: -shared -Wall -Werror native/runtime.c native/ui.c native/find.c -lkernel32 -luser32. Embed it as PawPresentationNative.\n\nGraphics: TinyCC -shared -Wall -Werror native/graphics/graphics_guard_gpu.c -lkernel32 -luser32, then tools/prepare_guard_exports.py. QA fixture DLLs are excluded. GPU warming is disabled.\n\nResource-cache payload: helpers/source/ResourceCachePayload.cs preserves the exact accepted emitted bytes and relocation table; native/cache/cache.c preserves its C source. Emitter and regression tools are included. Stock runtime bytes and local Python disassembly/emulation dependencies are required to regenerate, as documented by the release scripts. Hashes and source manifests are under metadata/.\n\nThe game itself is Kohan II 1.3.72 and is not distributed here. The included C is recovered patch logic, not a full decompilation of the game.\n'''
 manifest={n:dict(size=len(b),sha256=sha(b)) for n,b in sorted(files.items())};files['manifest.json']=json.dumps(manifest,indent=2).encode()
 out=stage/'arcane-0.5.1-beta.1-build-inputs.zip'
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for n,b in sorted(files.items()):
   i=zipfile.ZipInfo(n,(2026,11,9,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=0o100644<<16;z.writestr(i,b)
 proof=dict(path=str(out),sha256=sha(out.read_bytes()),size=out.stat().st_size,files=len(files));(stage/'build-inputs.json').write_text(json.dumps(proof,indent=2));print('EXACT_BETA_BUILD_INPUTS_BUNDLED',len(files),'files',flush=True)
if __name__=='__main__':main()
