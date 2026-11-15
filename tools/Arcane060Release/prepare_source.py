from release_context import *
import shutil,zipfile
PUB=O/'source-public';OLD=P.parent/'r24-racial-build-beta-20261114';ROOT=PUB/'game/arcane-060'
def put(rel,raw):f=PUB/rel;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(raw)
def main():
 for folder in ['native','helpers/source']:
  for f in(O/folder).rglob('*'):
   if f.is_file()and f.suffix in ['.c','.h','.cs','.def']:put('game/arcane-060/'+folder+'/'+f.relative_to(O/folder).as_posix(),f.read_bytes())
 # Accepted simulation/generation sources, retained under a versioned directory.
 for f in(OLD/'source/game').rglob('*'):
  if f.is_file()and f.suffix in ['.py','.c','.h','.cs','.md']and '__pycache__'not in f.parts:put('game/arcane-060/accepted/'+f.relative_to(OLD/'source/game').as_posix(),f.read_bytes())
 put('game/arcane-060/accepted/engineer-bridges/models.py',(P/'fixes/models.py').read_bytes())
 text=(OLD/'build_racial_art.py').read_text();anchor="       if isinstance(c,N.NiPSysEmitterCtlr) and c.data:\n";assert anchor in text;text=text.replace(anchor,anchor+"        if race=='undead' and kind=='finish':c.flags=(int(c.flags)&~6)|4\n")
 put('game/arcane-060/bridge-models/build_racial_art.py',text.encode())
 for name in ['build_product_helpers.py','build_product_native.py','prepare_packages.py','refresh_base_packages.py','release_context.py','catalogs.py','qa_builds.py','review.py','native_review.py','installer_qa.py','catalog_qa.py','product_smoke.py','prepare_source.py','finish_report.py','publish.py']:
  put('tools/Arcane060Release/'+name,(P/name).read_bytes())
 put('game/arcane-060/bridge-models/anchor_models.py',(OLD/'anchor_models.py').read_bytes())
 for n in ['build-report.json']:put('game/arcane-060/helpers/'+n,(O/'helpers'/n).read_bytes());put('game/arcane-060/native/'+n,(O/'native'/n).read_bytes())
 put('docs/release-patch-'+VERSION+'.json',(O/'release.json').read_bytes())
 # The build bundle includes each exact compiler input once, by SHA-256.
 files={};origins={}
 for row in read(O/'helpers/build-report.json').values():
  for path,digest in row['sources'].items():
   f=Path(path);assert sha(f)==digest;rel='inputs/'+digest+'/'+f.name;files[rel]=f.read_bytes();origins[path]=rel
 for f in ROOT.rglob('*'):
  if f.is_file()and 'helpers/source'not in f.as_posix():files['source/'+f.relative_to(ROOT).as_posix()]=f.read_bytes()
 files['helpers/build-report.json']=(O/'helpers/build-report.json').read_bytes();files['origin-map.json']=encode(origins)
 for q in read(O/'packages.json'):
  with zipfile.ZipFile(O/'assets'/(q['id']+'-'+VERSION+'.zip'))as z:files['package-manifests/'+q['id']+'.json']=z.read('module.json')
 files['packages.json']=(O/'packages.json').read_bytes();files['finish-controller-fix.json']=(P/'finish-controller-fix.json').read_bytes()
 files['README.txt']=b"Arcane Wars 0.6.0-beta.1 exact ordinary compiler inputs. No game EXE, RWD, saves, profiles, signing keys or QA DLL. Rebuild ordinary helpers using rebuild_helpers.py; C# compiler inputs and embedded payloads are resolved by SHA-256 via origin-map.json. Native module C/header inputs are under source/native; build with 32-bit TCC (-shared -Wall -Werror -lkernel32 -luser32 -lgdi32), without PAWS_BRIDGE_QA. The 10 immutable texture packages contain approved precomputed four-biome transitions; their bytes are described by package manifests. Generation scripts require the original local stock art/archives and do not redistribute those source archives. Production helpers use normal user profiles and have no private launcher/window placement.\n"
 files['rebuild_helpers.py']=b'''from pathlib import Path
import sys,json,subprocess,hashlib
root=Path(__file__).resolve().parent;mapping=json.loads((root/'origin-map.json').read_text());report=json.loads((root/'helpers/build-report.json').read_text());out=root/'rebuilt';out.mkdir(exist_ok=True)
compiler=Path(sys.argv[1]) if len(sys.argv)>1 else Path('C:/Windows/Microsoft.NET/Framework/v4.0.30319/csc.exe')
for name,row in report.items():
 args=[str(compiler)]
 for a in row['args'][1:]:
  if a.startswith('/out:'):a='/out:'+str(out/name)
  elif a in mapping:a=str(root/mapping[a])
  elif a.startswith('/resource:'):
   source,label=a[10:].rsplit(',',1);a='/resource:'+str(root/mapping[source])+','+label
  args.append(a)
 subprocess.run(args,check=True)
 print(name,hashlib.sha256((out/name).read_bytes()).hexdigest())
'''
 files['manifest.json']=encode({n:dict(size=len(b),sha256=hashlib.sha256(b).hexdigest().upper())for n,b in sorted(files.items())})
 path=O/'assets'/('arcane-'+VERSION+'-build-inputs.zip')
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
  for n,b in sorted(files.items()):z.writestr(n,b)
 write(O/'bundle.json',dict(path=str(path),sha256=sha(path),size=path.stat().st_size,files=len(files)))
 put('game/arcane-060/README.md',files['README.txt'])
 write(O/'source-scope.json',dict(files=[f.relative_to(PUB).as_posix()for f in PUB.rglob('*')if f.is_file()]))
 print('SOURCE_AND_EXACT_INPUTS_READY',len(files),'bundle files',flush=True)
if __name__=='__main__':main()
