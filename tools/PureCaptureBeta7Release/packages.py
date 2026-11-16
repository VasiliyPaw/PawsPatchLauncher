from context import *
import zipfile

def main():
 feed=verify(read(S/'feed/v3/beta.json'),key());assets=O/'assets';assets.mkdir(exist_ok=True);oldAssets=O/'baseline-assets';oldAssets.mkdir(exist_ok=True);out=[];audit={}
 for p in feed['packages']:
  if p['id']not in ['pure-fixes-runtime','pure-fixes-data','pure-beta-common']:continue
  src=BASE/'pure/assets'/Path(p['urls'][0]).name;validate_package(src,p)
  public=fetch(p['urls'][0]);assert hashlib.sha256(public).hexdigest().upper()==p['sha256'];(oldAssets/src.name).write_bytes(public)
  with zipfile.ZipFile(src)as z:m=json.loads(z.read('module.json'));old={r['path']:z.read('payload/'+r['path'])for r in m['files']}
  files=dict(old)
  if p['id']=='pure-fixes-runtime':
   for n in read(O/'helpers/build-report.json'):assert n in files;files[n]=(O/'helpers'/n).read_bytes()
  if p['id']=='pure-beta-common':files['data/ui/game/paws_day_clock.tgi']=(S/'game/ui-scout-test/paws_day_clock.tgi').read_bytes();assert b'client_L' in files['data/ui/game/paws_day_clock.tgi']
  for n in files:
   if Path(n).name=='paws_patch_versions.ini':files[n]=files[n].replace(b'0.5.0-beta.6',VERSION.encode())
  version=RUNTIME if p['id']=='pure-fixes-runtime'else VERSION;changed=[n for n in files if files[n]!=old[n]];assert changed or p['id']=='pure-fixes-data',p['id']
  allowed=set(read(O/'helpers/build-report.json'))|{'paws_patch_versions.ini','data/ui/game/paws_day_clock.tgi'};assert set(changed)<=allowed
  m.update(version=version,files=[dict(path=n,size=len(b),sha256=hashlib.sha256(b).hexdigest().upper())for n,b in sorted(files.items())]);target=assets/(p['id']+'-'+version+'.zip')
  with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
   z.writestr('module.json',encode(m))
   for n,b in sorted(files.items()):z.writestr('payload/'+n,b)
  q=copy.deepcopy(p);q.update(version=version,size=target.stat().st_size,sha256=sha(target),urls=['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/'+TAG+'/'+target.name]);validate_package(target,q);out.append(q);audit[p['id']]=dict(path=str(target),changed=changed,preserved=len(files)-len(changed),sha256=q['sha256'],size=q['size']);print('PURE_PACKAGE_PASS',p['id'],q['size'],flush=True)
 write(O/'packages.json',out);write(O/'package-audit.json',audit)
if __name__=='__main__':main()

