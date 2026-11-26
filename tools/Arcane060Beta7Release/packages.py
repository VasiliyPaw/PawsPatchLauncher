from context import *
import zipfile
OLD=WS/'outputs/ui-revert-release-20261118/arcane/assets'
FIX=WS/'outputs/arcane-bridge-terrain-fixes-20261125'
PIDS=['pawpatch-core','common-ui','player-colors','desync-continue']
def validate(path,p):
 assert sha(path)==p['sha256'].upper() and path.stat().st_size==p['size']
 with zipfile.ZipFile(path)as z:
  m=readzip(z,'module.json');assert m['id']==p['id'] and m['version']==p['version'];seen=set()
  for r in m['files']:
   n=r['path'];assert not n.startswith('/')and ':'not in n and '..'not in n.split('/') and n.lower()not in seen;seen.add(n.lower());b=z.read('payload/'+n);assert len(b)==r['size'] and hashlib.sha256(b).hexdigest().upper()==r['sha256'].upper(),n
  assert set(z.namelist())=={'module.json'}|{'payload/'+r['path']for r in m['files']}
 return len(m['files'])
def readzip(z,n):return json.loads(z.read(n))
def main():
 feed=verify(read(O/'before/feed/v3/beta.json'));old={p['id']:p for p in feed['packages']};helpers=read(O/'helpers/build-report.json')['helpers'];assert len(helpers)==8
 model=read(O/'materials/manifest.json');assert model['models']==672 and model['newProjectedShadows']==False and model['gameplayDefinitionsIncluded']==False
 replacements=[];audit={};out=O/'assets';out.mkdir(exist_ok=True)
 for pid in PIDS:
  previous=old[pid];src=OLD/Path(previous['urls'][0]).name;validate(src,previous)
  with zipfile.ZipFile(src)as z:m=readzip(z,'module.json');before={r['path']:z.read('payload/'+r['path'])for r in m['files']}
  files=dict(before)
  for n in files:
   name=Path(n).name
   if name in helpers:files[n]=(O/'helpers'/name).read_bytes();assert hashlib.sha256(files[n]).hexdigest().upper()==helpers[name]['sha256']
   if name.lower()in['paws_runtime.marker','paws_patch_versions.ini']:files[n]=files[n].replace(b'0.6.0-beta.6',V.encode())
  if pid=='pawpatch-core':
   for f in [FIX/'final-native-v2/sandbox/Mods/PawsBridges.dll',FIX/'water/PawsWaterBiomes.dll']:files['Mods/'+f.name]=f.read_bytes()
   for root,prefix,count in[(FIX/'shadow/payload','',56),(FIX/'water/assets','rivers-data/',952)]:
    rows=[f for f in root.rglob('*')if f.is_file()];assert len(rows)==count
    for f in rows:files[prefix+f.relative_to(root).as_posix()]=f.read_bytes()
   # Owner material manifest uses paths relative to rivers-data; textures are unchanged.
   ao=0
   for n,r in model['files'].items():
    f=O/'materials/payload'/n;b=f.read_bytes();assert hashlib.sha256(b).hexdigest().lower()==r['sha256'].lower()
    target='rivers-data/'+n.replace('\\','/')
    if r['kind']=='unchanged-texture':assert before[target]==b;continue
    assert target in before and target.lower().endswith('.nif') and '/racialbuild/'not in target.lower()
    assert hashlib.sha256(before[target]).hexdigest().lower()==r['sourceSha256'].lower(),('Material source differs from signed beta.6',target)
    files[target]=b;ao+=1
   assert ao==672
  changed=sorted(n for n,b in files.items()if before.get(n)!=b);new=sorted(set(files)-set(before));assert set(before)<=set(files)
  allowed={n for n in before if Path(n).name in helpers or Path(n).name.lower()in['paws_runtime.marker','paws_patch_versions.ini']}
  if pid=='pawpatch-core':allowed|={'Mods/PawsBridges.dll','Mods/PawsWaterBiomes.dll'}|{n for n in changed if n.startswith('rivers-data/Paws/Bridges/')or n.startswith('rivers-data/Textures/PawsWaterFloor/')}
  assert set(changed)<=allowed,(pid,set(changed)-allowed)
  m.update(version=V,files=[dict(path=n,size=len(b),sha256=hashlib.sha256(b).hexdigest().upper())for n,b in sorted(files.items())]);dest=out/(pid+'-'+V+'.zip')
  with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
   z.writestr('module.json',encode(m))
   for n,b in sorted(files.items()):z.writestr('payload/'+n,b)
  q=copy.deepcopy(previous);q.update(version=V,size=dest.stat().st_size,sha256=sha(dest),urls=['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/'+TAG+'/'+dest.name]);validate(dest,q);replacements.append(q)
  audit[pid]=dict(path=str(dest),size=q['size'],sha256=q['sha256'],files=len(files),changed=changed,added=new,removed=[],previousSha256=previous['sha256'],removalRulesPreserved=True)
  print('PACKAGE_VERIFIED',pid,len(files),q['size'],flush=True)
 write(O/'packages.json',replacements);write(O/'package-audit.json',audit);write(O/'terrain-preserved.json',old['arcane-biome-textures'])
if __name__=='__main__':main()
