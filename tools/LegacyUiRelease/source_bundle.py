from context import *
import zipfile
PUB=O/'source-public'
def put(rel,b):p=PUB/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
def main():
 rows={g:read(O/g/'helpers/build-report.json')for g in ['arcane','pure']}
 for group,target,name in [('arcane','game/arcane-060/helpers/source/25-LargeMapsIdentity.cs','25-LargeMapsIdentity.cs'),('pure','game/pure-capture-knowledge/managed/4-PureChannel.cs','4-PureChannel.cs')]:
  sources={p:h for r in rows[group].values()for p,h in r['sources'].items()};p=next(Path(p)for p in sources if Path(p).name==name);put(target,p.read_bytes())
 app=['.gitattributes']+['src/PawsPatchLauncher/'+n for n in ['RetiredHdUi.cs','StorageMaintenance.cs','MainWindow.xaml.cs','MainWindow.Enhancements.cs','PawsPatchLauncher.csproj']]+['tests/PawsPatchLauncher.Tests/'+n for n in ['RetiredHdUiTests.cs','Program.cs','PawsPatchLauncher.Tests.csproj']]+['docs/release-1.0.22.json','docs/release-1.0.22.md']
 app +=[p.relative_to(S).as_posix()for p in (S/'tests/PawsPatchLauncher.Tests/Fixtures/RetiredHd').glob('*.json')]
 for rel in app:put(rel,(S/rel).read_bytes())
 for group in ['arcane','pure']:
  put('docs/release-'+('patch-'if group=='arcane'else'pure-')+(ARC if group=='arcane'else PURE)+'.json',(O/group/'release.json').read_bytes());put('game/ui-revert/helpers-'+group+'-build-report.json',encode(rows[group]))
 for n in ['verification.json','package-audit.json','graphics-baseline.json','hd-removals.json','stock-skins.json','stock-frames-proof.json','stock-icons-proof.json','terrain-preserved.json','launcher-tests.json',*[m+'-'+c+'.json'for m in ['arcane','vanilla','immortals']for c in ['installer-result','fullres-upgrade']]]:put('docs/verification-ui-revert-20261118/'+n,(O/n).read_bytes())
 put('docs/verification-ui-revert-20261118/catalog.json',(O/'catalog-qa/result.json').read_bytes());put('docs/verification-ui-revert-20261118/cache-cleanup.json',(O/'cleanup-integration/result.json').read_bytes())
 put('game/ui-revert/README.md',b'''# Restore the pre-HD artwork

Arcane beta.6 and Vanilla/Immortals beta.10 restore stock artwork from hash-verified retail archives. All 63 frame pieces are lossless crops of the original 21 atlases; 477 earlier downscaled AI icon overrides are retired as well. Six retail skin RWDs are restored explicitly. UI manifests retire 1132 reserved artwork paths from both prior releases. Startup no longer mounts paws-hd-ui.rwd. Original icon resources remain in existing game archives. Widget layouts, capture knowledge, minimap ownership, filtering and gameplay remain unchanged. Twelve native helper inputs are identical; managed changes are version identities only.

The combined terrain module is reused with the same identity and bytes. No repeat download of its 900 MB archive is needed when already cached/prepared.

Launcher 1.0.22 retires only four precisely identified official HD package versions after a successful legacy-art update. It checks archive/manifest hashes and owned paths; rejects junctions, pending transactions, unrecognized downloads and extra user files. Installed/pinned/inactive versions remain protected. Originals and all transaction snapshots remain untouched; rollback uses captured bytes without prepared packages. Locked files are skipped without failing installation.

Verification covers 18 installer cases across three mods, three upgrades from the first HD release, 28,944 catalog selections, cleanup protection tests, actual official ZIP removal and rollback after cache deletion. No new native game launch or multiplayer session is claimed. QA follows the silent-before-start policy. Source art and immutable historical releases are retained.
''')
 for f in P.glob('*.py'):put('tools/LegacyUiRelease/'+f.name,f.read_bytes())
 for group in ['arcane','pure']:
  files={};mapping={}
  for row in rows[group].values():
   for path,h in row['sources'].items():
    f=Path(path);assert sha(f)==h;rel='inputs/'+h+'/'+f.name;files[rel]=f.read_bytes();mapping[path]=rel
  files['helpers/build-report.json']=encode(rows[group]);files['origin-map.json']=encode(mapping)
  with zipfile.ZipFile(AP/'assets/arcane-0.6.0-beta.5-build-inputs.zip')as z:files['rebuild_helpers.py']=z.read('rebuild_helpers.py')
  files['README.txt']=b'Exact helper compiler inputs. Native gameplay inputs unchanged; managed version identities only. Terrain unchanged. No original executable, signing key, profile or save. All project work on G:.\n'
  files['manifest.json']=encode({n:dict(size=len(b),sha256=hashlib.sha256(b).hexdigest().upper())for n,b in sorted(files.items())});v=ARC if group=='arcane'else PURE;target=O/group/'assets'/(group+'-'+v+'-build-inputs.zip')
  with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
   for n,b in sorted(files.items()):z.writestr(n,b)
  with zipfile.ZipFile(target)as z:assert z.testzip()is None
  write(O/group/'bundle.json',dict(path=str(target),sha256=sha(target),size=target.stat().st_size,files=len(files)))
 write(O/'source-scope.json',dict(files=sorted(f.relative_to(PUB).as_posix()for f in PUB.rglob('*')if f.is_file())));print('LEGACY_UI_SOURCE_BUNDLES_READY',flush=True)
if __name__=='__main__':main()
