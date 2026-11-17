from context import *
import zipfile
PUB=O/'source-public'
def put(rel,b):p=PUB/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
def main():
 rows={g:read(O/g/'helpers/build-report.json')for g in['arcane','pure']}
 for group,target,name in [('arcane','game/arcane-060/helpers/source/25-LargeMapsIdentity.cs','25-LargeMapsIdentity.cs'),('pure','game/pure-capture-knowledge/managed/4-PureChannel.cs','4-PureChannel.cs')]:
  sources={p:h for r in rows[group].values()for p,h in r['sources'].items()};p=next(Path(p)for p in sources if Path(p).name==name);put(target,p.read_bytes())
 for group in['arcane','pure']:
  put('docs/release-'+('patch-'if group=='arcane'else'pure-')+(ARC if group=='arcane'else PURE)+'.json',(O/group/'release.json').read_bytes())
  put('game/ui-full-resolution/helpers-'+group+'-build-report.json',encode(rows[group]))
 for n in['package-audit.json','image-export.json','arcane-installer-result.json','vanilla-installer-result.json','immortals-installer-result.json','verification.json']:
  put('docs/verification-ui-full-resolution-20261117/'+n,(O/n).read_bytes())
 put('docs/verification-ui-full-resolution-20261117/catalog.json',(O/'catalog-qa/result.json').read_bytes())
 put('game/ui-full-resolution/README.md',b'''# Full-resolution approved UI artwork

Arcane Wars 0.6.0-beta.4 and Vanilla/Immortals 0.5.0-beta.8 use the approved HD artwork at its original resolution. Most icons are 1254x1254; three are 1024x1024 and one is 1402x1254. Seven 5016x1254 faction masters retain lossless exact left/right 2508x1254 and center 627x1254 crops. No source image is resized while exporting. PNG bytes are preserved; TGA exports preserve exact RGBA pixels. Existing widget dimensions, filtering and native gameplay modules are unchanged.

The UI packages contain 645 icon paths in an image-only paws-hd-ui/ depot and 63 existing faction/spectator frame paths. Generic, 800 and 1280 resource paths are provided. The depot mounts after the existing depots, without the flag that previously prevented the override. Custom RWD startup composition continues through the launcher's existing mechanism. Removing the UI module restores startup and the previous textures through ModuleInstaller.

Accepted artwork provenance and SHA-256 hashes are in image-export.json. Payloads are distributed in the immutable common-ui and pure-beta-common release assets, not Git. Build-input bundles contain the exact compiler inputs and a portable rebuild script; only the managed version identities changed. Native code, day-cycle settings, gameplay TGIs and terrain archives are retained from the preceding betas.

Live 2560x1440 and Direct3D texture-upload evidence comes from the accepted Arcane candidate. Other race masters were checked by dimensions and exact pixels. The release verification distinguishes installer/preflight checks from in-match visual acceptance. No new multiplayer match is claimed for this image-only update.
''')
 put('game/ui-full-resolution/image-export.json',(O/'image-export.json').read_bytes())
 for f in P.glob('*.py'):put('tools/FullResolutionUiRelease/'+f.name,f.read_bytes())
 for group in['arcane','pure']:
  files={};mapping={}
  for row in rows[group].values():
   for path,h in row['sources'].items():
    f=Path(path);assert sha(f)==h;rel='inputs/'+h+'/'+f.name;files[rel]=f.read_bytes();mapping[path]=rel
  files['helpers/build-report.json']=encode(rows[group]);files['origin-map.json']=encode(mapping)
  with zipfile.ZipFile(AP/'assets/arcane-0.6.0-beta.3-build-inputs.zip')as z:files['rebuild_helpers.py']=z.read('rebuild_helpers.py')
  files['image-export.json']=(O/'image-export.json').read_bytes();files['README.txt']=b'Exact helper compiler inputs for the full-resolution UI release. Artwork is in the immutable UI module archive. Only version identity constants changed from the previous beta; all native resources are identical. No QA plugin, save, user profile, signing key or original game archive is included. Build output must remain on G:.\n'
  files['manifest.json']=encode({n:dict(size=len(b),sha256=hashlib.sha256(b).hexdigest().upper())for n,b in sorted(files.items())});v=ARC if group=='arcane'else PURE;target=O/group/'assets'/(group+'-'+v+'-build-inputs.zip')
  with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
   for n,b in sorted(files.items()):z.writestr(n,b)
  with zipfile.ZipFile(target)as z:assert z.testzip()is None
  write(O/group/'bundle.json',dict(path=str(target),sha256=sha(target),size=target.stat().st_size,files=len(files)))
 write(O/'source-scope.json',dict(files=sorted(f.relative_to(PUB).as_posix()for f in PUB.rglob('*')if f.is_file())));print('SOURCE_BUNDLES_PASS',flush=True)
if __name__=='__main__':main()
