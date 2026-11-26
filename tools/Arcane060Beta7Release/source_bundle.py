from context import *
from catalogs import note
import shutil,zipfile
FIX=WS/'outputs/arcane-bridge-terrain-fixes-20261125'; INPUT=WS/'work/arcane-bridge-terrain-fixes-20261125/helper-inputs'
def stage_fixes():
 scope=read(O/'source-fixes-scope.json');paths=[]
 for row in scope['changedOrNewSourceFixes']:
  assert row['shipAsSourceFix'];src=Path(row['source']);assert sha(src).lower()==row['sha256'].lower();dst=S/row['path'];dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);paths.append(row['path'])
 for row in read(O/'helpers/source-replacements.json')['files']:
  src=Path(row['replacement']);assert sha(src)==row['replacementSha256'];dst=S/'game/arcane-060/helpers/source'/src.name;shutil.copy2(src,dst);paths.append(dst.relative_to(S).as_posix())
 write(O/'fixes-staged.json',dict(files=sorted(set(paths)),productionBridgesSha256=sha(FIX/'final-native-v2/sandbox/Mods/PawsBridges.dll'),waterSha256=sha(FIX/'water/PawsWaterBiomes.dll')))
 print('SOURCE_FIXES_STAGED',len(set(paths)),flush=True)
def main():
 stage_fixes();paths=read(O/'fixes-staged.json')['files']
 def put(rel,raw):
  dst=S/rel;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(raw);paths.append(rel)
 put('docs/release-patch-'+V+'.json',encode(note()))
 put('docs/release-patch-'+V+'.md',(O/'release-notes.md').read_bytes())
 verification=read(O/'verification.json');put('docs/verification-arcane-beta7-20261126.json',encode(verification))
 # These files are supplied by the material owner; no experimental shadow definitions.
 for f in (O/'materials/source').rglob('*'):
  if f.is_file():put('game/arcane-060/bridge-models/materials/'+f.relative_to(O/'materials/source').as_posix(),f.read_bytes())
 put('game/arcane-060/bridge-models/materials/manifest.json',(O/'materials/manifest.json').read_bytes())
 put('game/arcane-060/README-beta7.md',b'''# Arcane Wars 0.6.0-beta.7

Built on public beta.6, retaining the current optimization lineage, stock UI, capture-knowledge fixes, native network contract and combined terrain package. Production PawsBridges has 109 checked hooks and a 128-entry wrapper table. Wetland rendering changes do not modify simulation tiles. Generator depth correction preserves native lakes and passable wetlands on newly generated maps; saved terrain heights remain serialized. Automatic bridge attacks are filtered, explicit player attacks remain possible. Proactive AI crossings require explored valid rivers, an available engineer and normal resources, with river-end and crossing-spacing limits.

The approved bridge material overlay changes vertex-color AO only for 672 racial NIFs. Geometry, indices, normals, UV and selection geometry remain exact; textures and cast-shadow definitions are retained. Shadow construction particle assets are a separate 56-model correction. No QA module, profile, save or personal configuration belongs to production packages. The beta.6 HD artwork removal list remains intact.

Verification is scoped in docs/verification-arcane-beta7-20261126.json. Compiled host/remote replicas do not constitute a new live multiplayer session. The bounded native engine smoke verifies paid Shadow construction, opacity and stable detach rotation. The immutable build-inputs asset contains the hash-pinned helper compiler inputs and the accepted source fixes. Original model inputs can be recovered from the immutable beta.6 core package using the recorded model source hashes.
''')
 for f in P.glob('*.py'):put('tools/Arcane060Beta7Release/'+f.name,f.read_bytes())
 for f in (P/'qa').glob('*'):
  if f.is_file()and f.suffix in['.py','.cs','.csproj','.md']:put('tools/Arcane060Beta7Release/qa/'+f.name,f.read_bytes())
 # Portable exact inputs; immutable origin paths are mapped to hash-addressed entries.
 files={};mapping={};reports=copy.deepcopy(read(O/'helpers/build-report.json')['helpers'])
 input_manifest=read(INPUT/'manifest.json')
 replacement_pins={r['replacement']:r['replacementSha256']for r in read(O/'helpers/source-replacements.json')['files']}
 for row in reports.values():
  sources={}
  for arg in row['args'][1:]:
   origin=arg[10:].rsplit(',',1)[0]if arg.startswith('/resource:')else arg if arg.lower().endswith('.cs')and not arg.startswith('/')else None
   if origin is None:continue
   src=Path(origin);digest=sha(src)
   if origin in replacement_pins:assert digest==replacement_pins[origin]
   else:
    rel=src.relative_to(INPUT).as_posix();assert digest==input_manifest[rel]['sha256'].upper()
   sources[origin]=digest
  assert sources;row['sources']=sources
  for origin,digest in row['sources'].items():
   src=Path(origin);assert sha(src)==digest.upper();rel='inputs/'+digest.upper()+'/'+src.name;files[rel]=src.read_bytes();mapping[origin]=rel
 files['origin-map.json']=encode(mapping);files['helpers/build-report.json']=encode(reports)
 files['rebuild_helpers.py']=(P/'rebuild_helpers.py').read_bytes()
 owner=WS/'work/bridge-materials-full-20261126';model_inputs=read(owner/'inputs-manifest.json');old_models=WS/'work/bridge-natural-look-20261125'
 for name in ['inputs-manifest.json','checkpoint.json','final-manifest.json','compile.json','mini-all-closure.json']:
  files['model-replay/work/bridge-materials-full-20261126/'+name]=(owner/name).read_bytes()
 for src in (O/'materials/source').iterdir():
  if src.is_file():
   folder='bridge-natural-look-20261125'if src.name=='build_candidate.py'else'bridge-materials-full-20261126'
   files['model-replay/work/'+folder+'/'+src.name]=src.read_bytes()
 for rel,row in model_inputs['approvedReferences'].items():
  src=old_models/row['after'];assert sha(src).lower()==row['candidateSha256'].lower()
  files['model-replay/work/bridge-natural-look-20261125/'+row['after']]=src.read_bytes()
 for name in ['candidate-manifest.json','candidate-manifest-16.json']:
  files['model-replay/work/bridge-natural-look-20261125/'+name]=(old_models/name).read_bytes()
 for rel in sorted(set(paths)):
  if rel.startswith('game/arcane-060/')or rel.startswith('docs/verification-'):files['source/'+rel]=(S/rel).read_bytes()
 files['README.txt']=b'Exact beta.7 helper compiler inputs and accepted native/material source. Use process-only DOTNET_ADD_GLOBAL_TOOLS_TO_PATH=false and G: TEMP. No signing key, original game executable, QA DLL, user profile or save is included.\n'
 files['manifest.json']=encode({n:dict(size=len(b),sha256=hashlib.sha256(b).hexdigest().upper())for n,b in sorted(files.items())});dest=O/'assets'/('arcane-'+V+'-build-inputs.zip')
 with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
  for n,b in sorted(files.items()):z.writestr(n,b)
 with zipfile.ZipFile(dest)as z:assert z.testzip()is None
 write(O/'bundle.json',dict(path=str(dest),sha256=sha(dest),size=dest.stat().st_size,files=len(files)))
 write(O/'source-scope.json',dict(files=sorted(set(paths))));print('SOURCE_AND_INPUTS_READY',len(set(paths)),dest.stat().st_size,flush=True)
if __name__=='__main__':stage_fixes()if len(sys.argv)>1 and sys.argv[1]=='stage'else main()
