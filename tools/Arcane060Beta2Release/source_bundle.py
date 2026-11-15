from context import *
import zipfile,shutil
PUB=O/'source-public'
def put(rel,raw):p=PUB/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
def main():
 for name in ['25-LargeMapsIdentity.cs','PawRuntimeStartup.cs']:put('game/arcane-060/helpers/source/'+name,(O/'helpers/source'/name).read_bytes())
 put('game/arcane-060/helpers/build-report.json',(O/'helpers/build-report.json').read_bytes())
 for name in ['audit.py','optimize.py','pack_candidate.py','reader_check.py']:put('game/terrain-transitions/lossless/'+name,(LP/name).read_bytes())
 for f in P.glob('*.py'):
  if f.name not in ['review.py','native_review.py','product_control.py','product_memory.py','product_smoke.py']:put('tools/Arcane060Beta2Release/'+f.name,f.read_bytes())
 put('docs/release-patch-'+VERSION+'.json',(O/'release.json').read_bytes())
 files={};mapping={}
 for row in read(O/'helpers/build-report.json').values():
  for path,digest in row['sources'].items():
   f=Path(path);assert sha(f)==digest;rel='inputs/'+digest+'/'+f.name;files[rel]=f.read_bytes();mapping[path]=rel
 for n in ['build-report.json']:files['helpers/'+n]=(O/'helpers'/n).read_bytes()
 files['origin-map.json']=encode(mapping);files['packages.json']=(O/'packages.json').read_bytes();files['packed.json']=(LOSS/'packed.json').read_bytes()
 for n in ['audit.json','optimization.json','packing-result.json','RESULT.json','original-files.json','optimized-files.json','duplicates.json','reader-result.json','native-result.json']:
  files['lossless-verification/'+n]=(LOSS/n).read_bytes()
 for f in(PUB/'game/terrain-transitions/lossless').glob('*.py'):files['lossless-source/'+f.name]=f.read_bytes()
 for f in P.glob('*.py'):
  if f.name not in ['review.py','native_review.py','product_control.py','product_memory.py','product_smoke.py']:files['tools/'+f.name]=f.read_bytes()
 for p in read(O/'packages.json'):
  with zipfile.ZipFile(O/'assets'/(p['id']+'-'+VERSION+'.zip'))as z:files['package-manifests/'+p['id']+'.json']=z.read('module.json')
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
 subprocess.run(args,check=True);print(name,hashlib.sha256((out/name).read_bytes()).hexdigest())
'''
 files['README.txt']=b"Arcane Wars 0.6.0-beta.2 exact helper inputs and lossless terrain packing evidence. Rebuild helpers with rebuild_helpers.py and the original Framework C# compiler. All native DLL payloads and gameplay/actor/bridge assets are unchanged from 0.6.0-beta.1. Ten loose texture packages are replaced by four own RWD texture archives. No original Data.rwd/Music.rwd, game EXE, test DLL, signing key, user profile or save is included. The 22,464 resource names resolve to 16,759 compressed PNG blobs; pixels, alpha, dimensions, PNG header and metadata are unchanged. Reproduce optimization from verified beta.1 archives with the lossless-source scripts and the recorded Oxipng 10.2.1 build; remap workspace paths and use a fresh G: output. RWD headers use the documented K2 TGCK v2 layout and content-derived stamps. Runtime launch checks archive presence, size, format, stamp and mount; full SHA-256 validation remains the installer responsibility.\n"
 files['manifest.json']=encode({n:dict(size=len(b),sha256=hashlib.sha256(b).hexdigest().upper())for n,b in sorted(files.items())})
 path=O/'assets'/('arcane-'+VERSION+'-build-inputs.zip')
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
  for n,b in sorted(files.items()):z.writestr(n,b)
 write(O/'bundle.json',dict(path=str(path),sha256=sha(path),size=path.stat().st_size,files=len(files)));write(O/'source-scope.json',dict(files=[f.relative_to(PUB).as_posix()for f in PUB.rglob('*')if f.is_file()]));print('BETA2_SOURCE_AND_BUNDLE_READY',len(files),path.stat().st_size,flush=True)
if __name__=='__main__':main()
