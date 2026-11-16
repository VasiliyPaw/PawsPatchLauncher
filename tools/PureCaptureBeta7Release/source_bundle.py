from context import *
import zipfile
PUB=O/'source-public'
def put(rel,b):p=PUB/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
def main():
 native=O/'native';put('game/capture-knowledge/capture_knowledge.c',(native/'capture_knowledge.c').read_bytes())
 for n in ['runtime.c','ui.c','day_clock.h','build-report.json']:put('game/pure-capture-knowledge/'+n,(native/n).read_bytes())
 put('game/pure-capture-knowledge/build.py',b'''from pathlib import Path
import argparse,subprocess,os
p=argparse.ArgumentParser();p.add_argument('--cc',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert a.out.resolve().drive.upper()=='G:';a.out.mkdir(parents=True,exist_ok=True);root=Path(__file__).resolve().parent;temp=a.out/'Temp';temp.mkdir(exist_ok=True);env=os.environ.copy();env.update(TEMP=str(temp),TMP=str(temp));subprocess.run([a.cc,'-shared','-Wall','-Werror','-DCAPTURE_KNOWLEDGE_EMBEDDED',str(root/'runtime.c'),str(root/'ui.c'),str(root.parent/'capture-knowledge/capture_knowledge.c'),'-o',str(a.out/'PawsPurePresentation1372.dll'),'-lkernel32','-luser32'],check=True,env=env)
''')
 put('game/pure-capture-knowledge/README.md',b'''# Pure beta.7 capture ownership memory

Vanilla and Immortals use the existing queued helper-owned presentation runtime. Compile the shared capture handler with CAPTURE_KNOWLEDGE_EMBEDDED. The queued installer starts the capture hook while original threads are suspended and reports failure if its native prologue guard fails. Its managed PC guard includes RVA 228B6C. No Arcane module loader, marker, bridges or gameplay assets are installed by Pure.

The capture callback is shared with Arcane beta.3: previous owner, new owner and pre-change viewers learn ownership; hidden third parties keep last observed knowledge until normal sight. Only existing ownership records change. Native extended GetThingByID and normal AI bookkeeping remain active. The standalone Arcane compilation remains byte-identical (D1944EA3B487E031064A0F274556CB4C0A1F9ED513B1DD3150E6C57C0CAB95A4).

The published package includes the production native DLL inside each of four managed helper resources. QA observers and the process-scoped multi-instance helper are excluded. See release verification for separate three-peer smoke and single-player native combat capture checks; a live three-peer capture is not claimed for this Pure build. UI picking tests execute original engine routines over the shared corrected clock asset. Existing ten-minute Pure day cycle and other features are preserved.
''')
 rows=read(O/'helpers/build-report.json')
 for path in next(iter(rows.values()))['sources']:
  if Path(path).name in ['4-PureChannel.cs','PurePresentationRuntimePatch.cs','PurePresentationRuntimePayload.cs']:put('game/pure-capture-knowledge/managed/'+Path(path).name,Path(path).read_bytes())
 put('game/pure-capture-knowledge/helpers-build-report.json',encode(rows));put('docs/release-pure-'+VERSION+'.json',(O/'release.json').read_bytes())
 for n in ['callback-tests.json','clock-tests.json','package-audit.json','vanilla-installer-result.json','immortals-installer-result.json','vanilla-network-result.json','immortals-network-result.json','vanilla-capture-result.json','immortals-capture-result.json','verification.json']:
  put('docs/verification-pure-beta7/'+n,(O/n).read_bytes())
 put('docs/verification-pure-beta7/catalog.json',(O/'catalog-qa/result.json').read_bytes())
 for f in P.glob('*.py'):put('tools/PureCaptureBeta7Release/'+f.name,f.read_bytes())
 files={};mapping={}
 for row in rows.values():
  for path,h in row['sources'].items():
   f=Path(path);assert sha(f)==h;rel='inputs/'+h+'/'+f.name;files[rel]=f.read_bytes();mapping[path]=rel
 files['helpers/build-report.json']=encode(rows);files['origin-map.json']=encode(mapping)
 for f in PUB.rglob('*'):
  if f.is_file():files['source/'+f.relative_to(PUB).as_posix()]=f.read_bytes()
 for p in read(O/'packages.json'):
  with zipfile.ZipFile(O/'assets'/(p['id']+'-'+p['version']+'.zip'))as z:files['package-manifests/'+p['id']+'.json']=z.read('module.json')
 # Portable compiler invocation, with all compiler inputs mapped by content hash.
 with zipfile.ZipFile(WS/'outputs/arcane060-beta3-release-20261116/assets/arcane-0.6.0-beta.3-build-inputs.zip')as z:files['rebuild_helpers.py']=z.read('rebuild_helpers.py')
 files['README.txt']=b'Pure 0.5.0-beta.7 helper inputs and native capture integration for Vanilla and Immortals. Rebuild helpers with rebuild_helpers.py and .NET Framework C# compiler. Native source build entry is source/game/pure-capture-knowledge/build.py. All project output must stay on G:. No base game executable/archive, QA DLL, private profile, save or signing key is included. Only shared ownership-memory handling and clock picking are changed.\n'
 files['manifest.json']=encode({n:dict(size=len(b),sha256=hashlib.sha256(b).hexdigest().upper())for n,b in sorted(files.items())});target=O/'assets'/('pure-'+VERSION+'-build-inputs.zip')
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
  for n,b in sorted(files.items()):z.writestr(n,b)
 with zipfile.ZipFile(target)as z:assert z.testzip()is None
 write(O/'bundle.json',dict(path=str(target),sha256=sha(target),size=target.stat().st_size,files=len(files)));write(O/'source-scope.json',dict(files=[f.relative_to(PUB).as_posix()for f in PUB.rglob('*')if f.is_file()]));print('PURE_SOURCE_BUNDLE_READY',len(files),target.stat().st_size)
if __name__=='__main__':main()
