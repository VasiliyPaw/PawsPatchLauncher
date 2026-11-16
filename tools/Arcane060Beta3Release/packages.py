from context import *
import zipfile,shutil

def main():
 feed=verify(read(S/'feed/v3/beta.json'),key());old={p['id']:p for p in feed['packages']};helpers=read(O/'helpers/build-report.json');out=O/'assets';out.mkdir(exist_ok=True);new=[];audit={};used=set()
 for pid in ['pawpatch-core','player-colors','desync-continue','common-ui']:
  before=old[pid];src=B2/'assets'/(pid+'-0.6.0-beta.2.zip');validate_package(src,before)
  with zipfile.ZipFile(src)as z:module=json.loads(z.read('module.json'));original={r['path']:z.read('payload/'+r['path'])for r in module['files']}
  files=dict(original)
  for rel in files:
   name=Path(rel).name
   if name in helpers:files[rel]=(O/'helpers'/name).read_bytes();used.add(name)
   if name.lower()in ['paws_patch_versions.ini','paws_runtime.marker']:files[rel]=files[rel].replace(b'0.6.0-beta.2',VERSION.encode())
  if pid=='pawpatch-core':
   files['Mods/PawsCaptureKnowledge.dll']=(CWORK/'build/PawsCaptureKnowledge.dll').read_bytes();assert sha(CWORK/'build/PawsCaptureKnowledge.dll')==read(CAND/'verification.json')['productionSha256'];files['Mods/plugins.txt']=files['Mods/plugins.txt'].rstrip()+b'\nPawsCaptureKnowledge.dll\n';assert len(files['Mods/plugins.txt'].splitlines())==10
  if pid=='common-ui':
   rel=next(n for n in files if n.lower()=='data/ui/game/paws_day_clock.tgi');files[rel]=(CWORK/'source/game/ui-scout-test/paws_day_clock.tgi').read_bytes()
  changed=[n for n in files if n not in original or files[n]!=original[n]];allowed=set(helpers)|{'paws_patch_versions.ini','paws_runtime.marker','plugins.txt','PawsCaptureKnowledge.dll','paws_day_clock.tgi'};assert all(Path(n).name in allowed for n in changed),changed
  module.update(version=VERSION,files=[dict(path=n,size=len(b),sha256=hashlib.sha256(b).hexdigest().upper())for n,b in sorted(files.items())]);dest=out/(pid+'-'+VERSION+'.zip')
  with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
   z.writestr('module.json',encode(module))
   for n,b in sorted(files.items()):z.writestr('payload/'+n,b)
  q=copy.deepcopy(before);q.update(version=VERSION,size=dest.stat().st_size,sha256=sha(dest),urls=['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/'+TAG+'/'+dest.name]);validate_package(dest,q);new.append(q);audit[pid]=dict(path=str(dest),changed=changed,preserved=len(files)-len(changed),files=len(files),size=q['size'],sha256=q['sha256']);print('BETA3_PACKAGE_PASS',pid,q['size'],flush=True)
 assert used==set(helpers);write(O/'packages.json',new);write(O/'package-audit.json',audit);write(O/'unchanged-textures.json',{p['id']:p for p in feed['packages']if p['id'].startswith('arcane-biome-textures-')});write(O/'size-result.json',dict(updateBytes=sum(p['size']for p in new),texturePackagesReused=4,textureBytesRedownloaded=0));print('TEXTURE_PACKAGES_REUSED_NO_REUPLOAD',flush=True)
if __name__=='__main__':main()
