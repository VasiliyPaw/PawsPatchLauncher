"""Commit only the reviewed integration; preserve unrelated work and index."""
import argparse,hashlib,json,subprocess
from pathlib import Path
REPO=Path(__file__).resolve().parents[2];STAGE=REPO/'outputs/arcane-051-release-20261109/beta-r2'
MANIFEST=REPO.parents[1]/'outputs/launcher-1.0.13-generic-readiness-qa/intended-files-candidate.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def git(*args):return subprocess.check_output(['git',*args],cwd=REPO,text=True).strip()
def selected():
 rows=json.loads(MANIFEST.read_text())['intended'];paths=[]
 for row in rows:
  name=row['path'];path=REPO/name
  if row['action']=='delete':assert not path.exists()
  else:assert sha(path)==row.get('candidateSha256',row['sha256']),name
  paths.append(name)
 explicit={
  'game/presentation-runtime':['runtime.c','PresentationRuntimePatch.cs','path_fixture.c'],
  'game/resource-cache':['cache.c','ResourceCachePatch.cs','build_native.py','test_native.py','README.md'],
  'game/find-local-cache':['local_find.h','plugin.c','build.py','test_native.py','test_contract.py','test_readonly.py','README.md'],
  'game/ui-scout-test':['runtime.c','day_clock.h','qa.h','paws_day_clock.tgi','build.py','test_native.py','test_hud.py','README.md'],
  'docs':['release-1.0.13.json','release-1.0.13.md','release-patch-0.5.1-beta.1.json','verification-arcane-051-20261109.md','verification-combined-optimizations-20261109.md','verification-buffer-retest-20261109.md','verification-find-local-cache-20261109.md','verification-ui-scout-20261109.md']}
 for folder,names in explicit.items():
  for name in names:
   p=REPO/folder/name;assert p.is_file(),p;paths.append(p.relative_to(REPO).as_posix())
 for p in (REPO/'tools/Arcane051Release').iterdir():
  if p.suffix in ['.py','.cs']:paths.append(p.relative_to(REPO).as_posix())
 paths=sorted(set(paths));assert not any(n.startswith(('supabase/','outputs/','tools/Pure')) for n in paths)
 return paths
def prepare():
 paths=selected();head=git('rev-parse','HEAD');assert git('ls-remote','origin','refs/heads/main').split()[0]==head
 assert not git('ls-remote','origin','refs/tags/v1.0.13'),'Launcher version already exists'
 native=Path('C:/PawsArcane051ReleaseQA-20261109/native-r7')
 assert sha(REPO/'game/presentation-runtime/runtime.c')==sha(native/'runtime.c')
 proof=dict(base=head,files={p:(sha(REPO/p) if (REPO/p).exists() else None) for p in paths})
 (STAGE/'source-scope.json').write_text(json.dumps(proof,indent=2));print('REVIEWED_SOURCE_SCOPE_READY',len(paths),head)
def publish():
 proof=json.loads((STAGE/'source-scope.json').read_text());paths=selected();assert set(paths)==set(proof['files'])
 assert git('rev-parse','HEAD')==git('ls-remote','origin','refs/heads/main').split()[0]==proof['base']
 for p,h in proof['files'].items():assert (sha(REPO/p) if (REPO/p).exists() else None)==h,p
 staged=set(git('diff','--cached','--name-only').splitlines());assert not staged.intersection(paths),'Selected files already staged by someone else'
 index=subprocess.check_output(['git','diff','--cached','--binary'],cwd=REPO)
 git('add','--',*paths);git('commit','--only','-m','Integrate faction speech and Arcane Wars 0.5.1 beta optimizations','--',*paths)
 assert subprocess.check_output(['git','diff','--cached','--binary'],cwd=REPO)==index,'Unrelated staged work changed'
 commit=git('rev-parse','HEAD');changed=git('diff-tree','--no-commit-id','--name-only','-r',commit).splitlines();assert set(changed)<=set(paths)
 git('push','origin','HEAD:main');(STAGE/'source-publication.json').write_text(json.dumps(dict(commit=commit,files=changed,preservedStagedFiles=sorted(staged)),indent=2));print('INTEGRATED_SOURCE_PUBLIC',commit,len(changed))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','publish']);a=p.parse_args();globals()[a.action]()
