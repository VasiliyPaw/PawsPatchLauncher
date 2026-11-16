from context import *
import zipfile
PUB=O/'source-public'
def put(rel,raw):
 p=PUB/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
def main():
 for f in(CWORK/'source').rglob('*'):
  if f.is_file():put(f.relative_to(CWORK/'source').as_posix(),f.read_bytes())
 for n in ['25-LargeMapsIdentity.cs','PawRuntimeStartup.cs']:put('game/arcane-060/helpers/source/'+n,(O/'helpers/source'/n).read_bytes())
 put('game/arcane-060/helpers/build-report.json',(O/'helpers/build-report.json').read_bytes())
 native=read(S/'game/arcane-060/native/build-report.json');row=read(CWORK/'build/build-report.json')['PawsCaptureKnowledge.dll'];assert 'PawsCaptureKnowledge.dll'not in native;native['PawsCaptureKnowledge.dll']=dict(sha256=row['sha256'],sourceSha256=row['sourceSha256'],source='game/capture-knowledge/capture_knowledge.c',args=row['command']);put('game/arcane-060/native/build-report.json',encode(native))
 put('docs/release-patch-'+VERSION+'.json',(O/'release.json').read_bytes())
 for n in ['verification.json','minimap-pixels.json']:put('docs/verification-arcane-beta3/'+n,(CAND/n).read_bytes())
 for n in ['package-audit.json','unchanged-textures.json','native-rebuild.json','startup-contract.json','beta3-upgrade-result.json','beta3-off-result.json','beta3-reapply-result.json','beta3-network-result.json','release-checks.json']:put('docs/verification-arcane-beta3/'+n,(O/n).read_bytes())
 put('docs/verification-arcane-beta3/catalog.json',(O/'catalog-qa/result.json').read_bytes())
 for f in P.glob('*.py'):put('tools/Arcane060Beta3Release/'+f.name,f.read_bytes())
 files={};mapping={}
 for row in read(O/'helpers/build-report.json').values():
  for path,digest in row['sources'].items():
   f=Path(path);assert sha(f)==digest;rel='inputs/'+digest+'/'+f.name;files[rel]=f.read_bytes();mapping[path]=rel
 files['helpers/build-report.json']=(O/'helpers/build-report.json').read_bytes();files['origin-map.json']=encode(mapping);files['packages.json']=(O/'packages.json').read_bytes()
 for f in PUB.rglob('*'):
  if f.is_file()and not f.relative_to(PUB).as_posix().startswith('game/arcane-060/helpers/'):files['source/'+f.relative_to(PUB).as_posix()]=f.read_bytes()
 for p in read(O/'packages.json'):
  with zipfile.ZipFile(O/'assets'/(p['id']+'-'+VERSION+'.zip'))as z:files['package-manifests/'+p['id']+'.json']=z.read('module.json')
 old=(P.parent/'arcane060-beta2-release-20261115/source_bundle.py').read_text();a=old.index("files['rebuild_helpers.py']=b'''")+len("files['rebuild_helpers.py']=b'''");b=old.index("'''",a);files['rebuild_helpers.py']=old[a:b].encode().decode('unicode_escape').encode()
 files['README.txt']=b'Arcane Wars 0.6.0-beta.3 exact helper source/resources and scoped capture knowledge source. Run rebuild_helpers.py with .NET Framework C# compiler. Rebuild native DLL using source/game/capture-knowledge/build.py --cc <TinyCC> --out <G: output>. See source/docs/verification-arcane-beta3 and verification-capture-fog-20261116.md for exact tested DLL identity and multiplayer evidence. All four texture packages remain the unchanged beta.2 archives. Original game executable, Data.rwd/Music.rwd, test DLLs, profiles, saves, credentials and signing key are excluded.\n'
 files['manifest.json']=encode({n:dict(size=len(b),sha256=hashlib.sha256(b).hexdigest().upper())for n,b in sorted(files.items())})
 target=O/'assets'/('arcane-'+VERSION+'-build-inputs.zip')
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
  for n,b in sorted(files.items()):z.writestr(n,b)
 with zipfile.ZipFile(target)as z:
  assert z.testzip()is None
  for n,r in json.loads(z.read('manifest.json')).items():assert hashlib.sha256(z.read(n)).hexdigest().upper()==r['sha256']
 write(O/'bundle.json',dict(path=str(target),sha256=sha(target),size=target.stat().st_size,files=len(files)));write(O/'source-scope.json',dict(files=[f.relative_to(PUB).as_posix()for f in PUB.rglob('*')if f.is_file()]));print('SOURCE_AND_BUNDLE_READY',len(files),target.stat().st_size)
if __name__=='__main__':main()
