from context import *
import zipfile
def main():
 original={q['id']:q for q in read(B1/'packages.json')};parts=read(LOSS/'packed.json');helpers=read(O/'helpers/build-report.json');out=O/'assets';out.mkdir(exist_ok=True);packages=[];audit={};used=set()
 for pid in ['pawpatch-core','player-colors','desync-continue','common-ui']+[f'arcane-biome-textures-{i:02}'for i in range(1,5)]:
  before=original[pid]
  if pid.startswith('arcane-biome'):
   index=int(pid[-2:])-1;r=parts[index];path=Path(r['path']);assert sha(path)==r['sha256'].upper();files={path.name:path.read_bytes()};module=dict(schemaVersion=1,id=pid,version=VERSION,files=[],remove=[]);changed=list(files);preserved=0
  else:
   src=B1/'assets'/(pid+'-0.6.0-beta.1.zip');validate_package(src,before)
   with zipfile.ZipFile(src)as z:module=json.loads(z.read('module.json'));old={r['path']:z.read('payload/'+r['path'])for r in module['files']};files=dict(old)
   for rel in files:
    leaf=Path(rel).name
    if leaf in helpers:files[rel]=(O/'helpers'/leaf).read_bytes();used.add(leaf)
    if leaf.lower()=='paws_patch_versions.ini':files[rel]=files[rel].replace(b'0.6.0-beta.1',VERSION.encode())
    if rel.lower()=='paws_runtime.marker':files[rel]=files[rel].replace(b'0.6.0-beta.1',VERSION.encode())
    if rel.lower()=='startup/autoexec.txt':
     files[rel]=files[rel].rstrip()+b'\r\n\r\n# Lossless terrain resource archives\r\n'+''.join('adddepot '+Path(r['path']).name+'\r\n'for r in parts).encode()
   changed=[n for n in files if files[n]!=old[n]];preserved=len(files)-len(changed)
  module.update(version=VERSION,files=[dict(path=n,size=len(b),sha256=hashlib.sha256(b).hexdigest().upper())for n,b in sorted(files.items())])
  dest=out/(pid+'-'+VERSION+'.zip')
  with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
   z.writestr('module.json',encode(module))
   for name,data in sorted(files.items()):
    info=zipfile.ZipInfo('payload/'+name,(2026,11,15,0,0,0));info.compress_type=zipfile.ZIP_STORED if name.lower().endswith('.png')else zipfile.ZIP_DEFLATED;z.writestr(info,data)
  q=copy.deepcopy(before);q.update(version=VERSION,size=dest.stat().st_size,sha256=sha(dest),urls=['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/'+TAG+'/'+dest.name])
  if pid=='pawpatch-core':q['dependsOn']=[d for d in q['dependsOn']if not d.startswith('arcane-biome-textures-')]+[f'arcane-biome-textures-{i:02}'for i in range(1,5)]
  validate_package(dest,q);packages.append(q);audit[pid]=dict(path=str(dest),size=q['size'],sha256=q['sha256'],changed=changed,preserved=preserved,files=len(files));print('BETA2_PACKAGE_READY',pid,q['size'],flush=True)
 assert len(used)==8;write(O/'packages.json',packages);write(O/'package-audit.json',audit)
 total=sum(p['size']for p in packages);write(O/'size-result.json',dict(passed=True,oldBytes=sum(p['size']for p in original.values()),newBytes=total,savedPercent=round(100*(1-total/sum(p['size']for p in original.values())),2),textureBytes=sum(p['size']for p in packages if p['id'].startswith('arcane-biome'))));print('BETA2_SIZE',total,flush=True)
if __name__=='__main__':main()
