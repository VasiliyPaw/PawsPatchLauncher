from context import *
import shutil
sys.path.insert(0,str(P/'net'));import control
assert not control.own();source=FIX/'game';rows=[]
for role in ['client','witness']:
 target=control.folder(role)/'game';missing=[];changed=[]
 for name in ['data','rivers-data','skins','startup','mss','Userdata']:
  for f in(source/name).rglob('*'):
   if not f.is_file():continue
   relative=f.relative_to(source);dst=target/relative
   if not dst.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst);missing.append(relative.as_posix())
   elif sha(f)!=sha(dst):shutil.copy2(f,dst);changed.append(relative.as_posix())
 for f in source.glob('*.rwd'):
  dst=target/f.name
  if not dst.exists():shutil.copy2(f,dst);missing.append(f.name)
 rows.append(dict(role=role,missingCopied=missing,changedReplaced=changed));print('COMPLETE_RESOURCE_PEER',role,'missing',len(missing),'changed',len(changed),missing[:20],flush=True)
write(O/'network-fixture-completion.json',rows)
