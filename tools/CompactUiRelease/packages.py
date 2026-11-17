from context import *
import zipfile,shutil
def save_package(files,module,before,version,target,tag):
 specs=[]
 for n,value in sorted(files.items()):
  if isinstance(value,Path):size=value.stat().st_size;h=sha(value)
  else:size=len(value);h=hashlib.sha256(value).hexdigest().upper()
  specs.append(dict(path=n,size=size,sha256=h))
 module.update(version=version,files=specs)
 if target.exists():
  with zipfile.ZipFile(target)as z:assert json.loads(z.read('module.json'))==module
 else:
  with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
   z.writestr('module.json',encode(module))
   for n,value in sorted(files.items()):
    if isinstance(value,Path):z.write(value,'payload/'+n)
    else:z.writestr('payload/'+n,value)
 q=copy.deepcopy(before);q.update(version=version,size=target.stat().st_size,sha256=sha(target),urls=['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/'+tag+'/'+target.name]);validate_package(target,q);return q
def main():
 feed=verify(read(O/'before/feed/v3/beta.json'),key());old={p['id']:p for p in feed['packages']};archives=read(O/'resource-archives.json');image_paths={r['oldPath'].lower()for r in read(O/'image-export.json')['files']};assert len(image_paths)==708
 new=[];audit={}
 for group,base,version,tag,pids in[('arcane',AP,ARC,'patch-'+ARC,['pawpatch-core','player-colors','desync-continue','common-ui']),('pure',PP,PURE,'patch-pure-'+PURE,['pure-fixes-runtime','pure-fixes-data','pure-beta-common'])]:
  out=O/group/'assets';out.mkdir(parents=True,exist_ok=True);helpers=read(O/group/'helpers/build-report.json');oldver='0.6.0-beta.4'if group=='arcane'else'0.5.0-beta.8'
  for pid in pids:
   before=old[pid];src=base/'assets'/Path(before['urls'][0]).name;validate_package(src,before)
   with zipfile.ZipFile(src)as z:m=json.loads(z.read('module.json'));original={r['path']:z.read('payload/'+r['path'])for r in m['files']}
   files={n:b for n,b in original.items()if n.lower()not in image_paths or pid not in['common-ui','pure-beta-common']}
   for n in files:
    name=Path(n).name
    if name in helpers:files[n]=(O/group/'helpers'/name).read_bytes()
    if name.lower()in['paws_patch_versions.ini','paws_runtime.marker']:files[n]=files[n].replace(oldver.encode(),version.encode())
   if pid in['common-ui','pure-beta-common']:
    assert len(original)-len(files)==708
    assert files['startup/autoexec.txt'].count(b'adddepot paws-hd-ui/')==1;files['startup/autoexec.txt']=files['startup/autoexec.txt'].replace(b'adddepot paws-hd-ui/',b'adddepot paws-hd-ui.rwd')
    for n,row in archives.items():files[n]=Path(row['path'])
   changed=[n for n,b in files.items()if n not in original or isinstance(b,Path)or b!=original[n]];removed=sorted(set(original)-set(files));allowed=set(helpers)|{'paws_patch_versions.ini','paws_runtime.marker','autoexec.txt'}
   assert all(Path(n).name in allowed or n in archives for n in changed);assert all(n.lower()in image_paths for n in removed)
   v=RT if pid=='pure-fixes-runtime'else version;target=out/(pid+'-'+v+'.zip');q=save_package(files,m,before,v,target,tag)
   if pid=='pawpatch-core':q['dependsOn']=[d for d in q['dependsOn']if not d.startswith('arcane-biome-textures-')]+['arcane-biome-textures']
   new.append(q);audit[pid]=dict(path=str(target),group=group,changed=changed,removedLooseImages=len(removed),resourceArchives=len(archives)if pid in['common-ui','pure-beta-common']else 0,files=len(files),sha256=q['sha256'],size=q['size'],baselineSize=before['size']);print('COMPACT_PACKAGE_PASS',pid,q['size'],flush=True)
 # A single download containing the four existing RWD files, byte for byte.
 pid='arcane-biome-textures';out=O/'arcane/assets';terrain=O/'terrain-files';terrain.mkdir(exist_ok=True);files={};sources={};baseline=[]
 for i in range(1,5):
  p=old[f'arcane-biome-textures-{i:02}'];src=B2/'assets'/Path(p['urls'][0]).name;validate_package(src,p)
  with zipfile.ZipFile(src)as z:
   m=json.loads(z.read('module.json'));assert len(m['files'])==1;r=m['files'][0];dest=terrain/r['path']
   if not dest.exists():
    with z.open('payload/'+r['path'])as input,dest.open('wb')as output:shutil.copyfileobj(input,output,1024*1024)
   assert sha(dest)==r['sha256'].upper();files[r['path']]=dest;sources[r['path']]=dict(originalPackage=p['id'],sha256=r['sha256'],size=r['size']);baseline.append(p['size'])
 before=copy.deepcopy(old['arcane-biome-textures-01']);before['id']=pid;before['dependsOn']=[];before['name']={'ru':'Текстуры местности','en':'Terrain textures'};before['description']={'ru':'Все текстуры местности одним пакетом без снижения качества.','en':'All terrain textures in one package without quality reduction.'}
 target=out/(pid+'-'+ARC+'.zip');q=save_package(files,dict(schemaVersion=1,id=pid,version=ARC,files=[],remove=[]),before,ARC,target,'patch-'+ARC);new.append(q);audit[pid]=dict(path=str(target),group='arcane',sha256=q['sha256'],size=q['size'],files=4,baselineSize=sum(baseline),rwdFilesByteIdentical=True)
 write(O/'terrain-merge.json',dict(passed=True,downloadPackagesBefore=4,downloadPackagesAfter=1,sourcePackageBytes=sum(baseline),combinedPackageBytes=q['size'],unchangedQuality=True,files=sources));write(O/'packages.json',new);write(O/'package-audit.json',audit);print('TERRAIN_SINGLE_DOWNLOAD_PASS',q['size'],flush=True)
if __name__=='__main__':main()
