from context import *
sys.path.insert(0,str(P/'net'));import control
assert not control.own()
rows=[]
for role in ['client','witness']:
 root=control.folder(role)/'game';assert root.resolve().is_relative_to(Path('G:/PawsWork/QA/Arcane060Beta2Net-20261115').resolve());changes=[]
 for directory in ['data','rivers-data','skins','startup']:
  for src in sorted((FIX/'game'/directory).rglob('*'),key=lambda f:len(f.parts)):
   dst=root/src.relative_to(FIX/'game')
   if not dst.exists():continue
   physical=next((p for p in dst.parent.iterdir()if p.name.lower()==dst.name.lower()),None)
   if physical and physical.name!=src.name:
    temp=physical.with_name(physical.name+'.qa-case-tmp');assert not temp.exists();physical.rename(temp);temp.rename(dst);changes.append([str(physical.relative_to(root)),str(dst.relative_to(root))])
 rows.append(dict(role=role,changes=changes));print('PEER_CASE_PRESERVED',role,len(changes),flush=True)
write(O/'peer-case.json',rows)
