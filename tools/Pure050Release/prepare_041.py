"""Stage immutable Pure0.4.1 assets and owned installed QA copies."""
import copy,zipfile,shutil,os
from context import *
from PrepareRelease070 import encode,validate_package
def main():
 stage=OUT/'stable-stage';stage.mkdir(exist_ok=True);assert not (stage/'packages.json').exists();assets=stage/'assets';assets.mkdir(exist_ok=True);packages=[]
 feed=read(OUT/'before/feed/v3/beta.payload.json');helpers=OUT/'stable-helpers-r2';report=read(helpers/'build-report.json')
 for package in feed['packages']:
  if package['id'] not in {'pure-fixes-data','pure-fixes-runtime','pure-beta-common'}:continue
  original=OUT/'accepted-assets'/package['urls'][0].rsplit('/',1)[1]
  with zipfile.ZipFile(original) as z:
   manifest=json.loads(z.read('module.json'));files={n[8:]:z.read(n) for n in z.namelist() if n.startswith('payload/') and not n.endswith('/')}
  if package['id']=='pure-fixes-runtime':
   for name,row in report.items():assert sha(helpers/name)==row['sha256'];files[name]=(helpers/name).read_bytes()
  version='1.3.72-pure.16' if package['id']=='pure-fixes-runtime' else '0.4.1';manifest['version']=version
  manifest['files']=[dict(path=n,size=len(data),sha256=hashlib.sha256(data).hexdigest().upper()) for n,data in sorted(files.items())]
  path=assets/(package['id']+'-'+version+'.zip')
  with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
   for n,data in [('module.json',encode(manifest))]+[('payload/'+n,data) for n,data in sorted(files.items())]:
    info=zipfile.ZipInfo(n,(2026,11,9,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,data)
  fresh=copy.deepcopy(package);fresh.update(version=version,sha256=sha(path),size=path.stat().st_size,experimental=False,urls=['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/patch-pure-0.4.1/'+path.name]);validate_package(path,fresh);packages.append(fresh)
 write(stage/'packages.json',packages)
 for mode in ['vanilla','immortals']:
  source=Path('G:/PawCompanyQA-20261029-postboot-r2')/mode/'host/game';assert (source/'.paw-live-matrix.json').is_file();assert sha(source/'k2.exe')=='1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45'
  game=OUT/'stable-fixtures'/mode/'game';game.parent.mkdir(parents=True)
  def ignore(folder,names):
   if Path(folder).name=='.pawpatch':return [n for n in names if n!='state.json']
   return shutil.ignore_patterns('Logs','Mods','*.log','*.dmp','*status*.txt','paws_ai_diagnostics')(folder,names)
  def copy_file(src,dst):
   if Path(src).suffix.lower()=='.rwd':os.link(src,dst);return dst
   return shutil.copy2(src,dst)
  shutil.copytree(source,game,ignore=ignore,copy_function=copy_file)
  state=read(game/'.pawpatch/state.json');state['appliedSettings']['channel']='stable'
  for package in packages:
   with zipfile.ZipFile(assets/package['urls'][0].rsplit('/',1)[1]) as z:
    manifest=json.loads(z.read('module.json'))
    for row in manifest['files']:
     target=game/row['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read('payload/'+row['path']))
   state['modules'][package['id']].update(version=package['version'],files=manifest['files'])
  write(game/'.pawpatch/state.json',state)
  print('PURE_041_FIXTURE_READY',mode,game,flush=True)
 print('PURE_041_ASSETS_READY',len(packages))
if __name__=='__main__':main()
