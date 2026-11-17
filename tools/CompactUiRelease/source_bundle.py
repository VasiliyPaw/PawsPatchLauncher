from context import *
import zipfile
PUB=O/'source-public'
def put(rel,b):p=PUB/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
def main():
 rows={g:read(O/g/'helpers/build-report.json')for g in['arcane','pure']}
 for group,target,name in[('arcane','game/arcane-060/helpers/source/25-LargeMapsIdentity.cs','25-LargeMapsIdentity.cs'),('pure','game/pure-capture-knowledge/managed/4-PureChannel.cs','4-PureChannel.cs')]:
  sources={p:h for r in rows[group].values()for p,h in r['sources'].items()};p=next(Path(p)for p in sources if Path(p).name==name);put(target,p.read_bytes())
 for group in['arcane','pure']:
  put('docs/release-'+('patch-'if group=='arcane'else'pure-')+(ARC if group=='arcane'else PURE)+'.json',(O/group/'release.json').read_bytes());put('game/ui-compact/helpers-'+group+'-build-report.json',encode(rows[group]))
 for n in['verification.json','image-export.json','package-audit.json','resource-archives.json','base-skin-preservation.json','terrain-merge.json','reader-result.json','live-result.json','live-cleanup.json','arcane-installer-result.json','vanilla-installer-result.json','immortals-installer-result.json']:
  put('docs/verification-ui-compact-20261117/'+n,(O/n).read_bytes())
 put('docs/verification-ui-compact-20261117/catalog.json',(O/'catalog-qa/result.json').read_bytes())
 put('game/ui-compact/README.md',b'''# Compact HD UI and one terrain download

Icons have at most 512 pixels per dimension, with original aspect ratios. Frame halves are 2048x1024; centers are 512x1024. Approved source masters are unchanged. Exported pixels are verified against the exact Lanczos resize. PNG and TGA artwork use their existing logical resource names.

The existing TGCK RWD format stores each unique byte sequence once while preserving all aliases. The terrain release already used this shared-offset representation. The image-only paws-hd-ui.rwd contains 645 icon aliases and nine spectator-frame aliases. Six faction skin RWDs preserve all 53 original retail entries byte for byte and add nine frame aliases each. Loose overrides are retired by the ordinary ModuleInstaller transaction; disabling restores the stock skin archives. The public 1.0.19 launcher reads and installs ordinary schema-1 ZIP modules; no new launcher format is required.

Arcane terrain is a single module containing the same four RWD files, with identical SHA-256, sizes, stamps and pixels. Game startup and helper archive guards keep their four existing names. Only download grouping/dependencies change. Existing installations download the combined archive once when migrating from the four-package layout; subsequent UI changes need not download terrain again.

All production native inputs, clocks, widget layouts, filtering and gameplay TGIs match the preceding betas. Managed changes are version identity constants only. Local release checks cover 18 transactional installer cases on three games, stock skin restoration, published RwdTool.dll alias reads, and a private Arcane 2560x1440 saved-match load with actual Direct3D dimensions (512x512 icons; 2048x1024 frame halves; 512x1024 center). Other factions are verified by archive content and production-reader checks, not claimed as individually inspected in matches. No new multiplayer match is claimed. The temporary QA observer and process-scoped helper are excluded from every package.
''')
 for f in P.glob('*.py'):put('tools/CompactUiRelease/'+f.name,f.read_bytes())
 for group in['arcane','pure']:
  files={};mapping={}
  for row in rows[group].values():
   for path,h in row['sources'].items():
    f=Path(path);assert sha(f)==h;rel='inputs/'+h+'/'+f.name;files[rel]=f.read_bytes();mapping[path]=rel
  files['helpers/build-report.json']=encode(rows[group]);files['origin-map.json']=encode(mapping)
  with zipfile.ZipFile(AP/'assets'/('arcane-0.6.0-beta.4-build-inputs.zip'))as z:files['rebuild_helpers.py']=z.read('rebuild_helpers.py')
  for n in['resource-archives.json','image-export.json','terrain-merge.json']:files[n]=(O/n).read_bytes()
  files['README.txt']=b'Exact helper compiler inputs for the compact UI beta release. Only managed version identities change; native resources are identical to the preceding beta. Artwork and skin archives are in the immutable UI module asset. Terrain RWD payloads are byte-identical to beta.2; the new terrain module only groups their download. No QA plugin, user profile, save, original game executable or signing key is included. All build output must stay on G:.\n'
  files['manifest.json']=encode({n:dict(size=len(b),sha256=hashlib.sha256(b).hexdigest().upper())for n,b in sorted(files.items())});v=ARC if group=='arcane'else PURE;target=O/group/'assets'/(group+'-'+v+'-build-inputs.zip')
  with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
   for n,b in sorted(files.items()):z.writestr(n,b)
  with zipfile.ZipFile(target)as z:assert z.testzip()is None
  write(O/group/'bundle.json',dict(path=str(target),sha256=sha(target),size=target.stat().st_size,files=len(files)))
 write(O/'source-scope.json',dict(files=sorted(f.relative_to(PUB).as_posix()for f in PUB.rglob('*')if f.is_file())));print('COMPACT_SOURCE_BUNDLES_READY',flush=True)
if __name__=='__main__':main()
