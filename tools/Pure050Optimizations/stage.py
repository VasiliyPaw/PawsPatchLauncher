"""Replace only the native Pure module; mode-native world/data remain exact."""
import copy,zipfile,shutil,os
from context import *
from PrepareRelease070 import validate_package,encode
def main():
 stage=OUT/'stage-r3';stage.mkdir(exist_ok=False);assets=stage/'assets';assets.mkdir();previous=read(PREVIOUS/'beta-stage-r4/packages.json');old=next(p for p in previous if p['id']=='pure-fixes-runtime')
 original=PREVIOUS/'beta-stage-r4/assets'/old['urls'][-1].rsplit('/',1)[1]
 with zipfile.ZipFile(original)as z:
  module=__import__('json').loads(z.read('module.json'));files={n[8:]:z.read(n)for n in z.namelist()if n.startswith('payload/')and not n.endswith('/')}
 before=dict(files);report=read(OUT/'helpers-r1/build-report.json')
 for name,row in report.items():assert sha(OUT/'helpers-r1'/name)==row['sha256'];files[name]=(OUT/'helpers-r1'/name).read_bytes()
 assert files['paws_presentation.ini']==b'[Runtime]\nstartupReadyEvent=1\n'
 module.update(version=RUNTIME,files=[dict(path=n,size=len(b),sha256=hashlib.sha256(b).hexdigest().upper())for n,b in sorted(files.items())]);archive=assets/('pure-fixes-runtime-'+RUNTIME+'.zip')
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
  for n,b in [('module.json',encode(module))]+[('payload/'+n,b)for n,b in sorted(files.items())]:
   item=zipfile.ZipInfo(n,(2026,11,9,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED;z.writestr(item,b)
 package=copy.deepcopy(old);package.update(version=RUNTIME,sha256=sha(archive),size=archive.stat().st_size,urls=['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/patch-pure-'+PATCH+'/'+archive.name]);validate_package(archive,package)
 # The lobby contract requires the data package's version to equal the patch
 # version. Its payload stays byte-identical; only module/catalog identity moves.
 data=copy.deepcopy(next(p for p in previous if p['id']=='pure-fixes-data'))
 with zipfile.ZipFile(PREVIOUS/'beta-stage-r4/assets'/data['urls'][-1].rsplit('/',1)[1])as z:
  contents={n:z.read(n)for n in z.namelist()};manifest=__import__('json').loads(contents['module.json']);manifest['version']=PATCH;contents['module.json']=encode(manifest)
 data_archive=assets/('pure-fixes-data-'+PATCH+'.zip')
 with zipfile.ZipFile(data_archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
  for n,b in contents.items():
   item=zipfile.ZipInfo(n,(2026,11,9,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED;z.writestr(item,b)
 data.update(version=PATCH,sha256=sha(data_archive),size=data_archive.stat().st_size,urls=['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/patch-pure-'+PATCH+'/'+data_archive.name]);validate_package(data_archive,data)
 # d3d9 already belongs to the higher-priority native-only common module.
 # Keep one owner and replace that exact payload, so real installer ordering
 # cannot restore the old DLL over the optimization.
 common=copy.deepcopy(next(p for p in previous if p['id']=='pure-beta-common'))
 with zipfile.ZipFile(PREVIOUS/'beta-stage-r4/assets'/common['urls'][-1].rsplit('/',1)[1])as z:
  common_module=__import__('json').loads(z.read('module.json'));common_files={n[8:]:z.read(n)for n in z.namelist()if n.startswith('payload/')and not n.endswith('/')}
 assert 'd3d9.dll'in common_files;common_before=dict(common_files);common_files['d3d9.dll']=(OUT/'native-r1/graphics/d3d9.dll').read_bytes()
 common_module.update(version=PATCH,files=[dict(path=n,size=len(b),sha256=hashlib.sha256(b).hexdigest().upper())for n,b in sorted(common_files.items())]);common_archive=assets/('pure-beta-common-'+PATCH+'.zip')
 with zipfile.ZipFile(common_archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
  for n,b in [('module.json',encode(common_module))]+[('payload/'+n,b)for n,b in sorted(common_files.items())]:
   item=zipfile.ZipInfo(n,(2026,11,9,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED;z.writestr(item,b)
 common.update(version=PATCH,sha256=sha(common_archive),size=common_archive.stat().st_size,urls=['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/patch-pure-'+PATCH+'/'+common_archive.name]);validate_package(common_archive,common);write(stage/'packages.json',[package,data,common])
 common_changes=[n for n,b in common_files.items()if common_before.get(n)!=b];assert common_changes==['d3d9.dll']
 write(stage/'audit.json',dict(changed=[n for n,b in files.items()if before.get(n)!=b],unchanged=[n for n,b in files.items()if before.get(n)==b],commonChanged=common_changes,dataPayloadUnchanged=True,previousPackages={p['id']:p['sha256']for p in previous if p['id']not in ['pure-fixes-runtime','pure-fixes-data','pure-beta-common']},worldAndLocalizationUnchanged=True))
 for mode in ['vanilla','immortals']:
  root=Path('G:/PawPure050OptQA-20261109/fixtures-r3')/mode/'game';root.parent.mkdir(parents=True,exist_ok=False)
  def ignore(folder,names):
   if Path(folder).name=='.pawpatch':return[n for n in names if n!='state.json']
   return shutil.ignore_patterns('Logs','Mods','*.log','*.dmp','*status*.txt','paws_ai_diagnostics')(folder,names)
  shutil.copytree(Path('G:/PawPure050QA-20261109/fixtures-r4')/mode/'game',root,ignore=ignore,copy_function=lambda x,y:os.link(x,y)if Path(x).suffix.lower()=='.rwd'else shutil.copy2(x,y))
  for n,b in files.items():p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
  for n,b in common_files.items():p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
  state=read(root/'.pawpatch/state.json');state['modules']['pure-fixes-runtime']=dict(enabled=True,version=RUNTIME,files=module['files']);state['modules']['pure-fixes-data']['version']=PATCH;state['modules']['pure-beta-common']=dict(enabled=True,version=PATCH,files=common_module['files']);write(root/'.pawpatch/state.json',state)
  (root/'paws_launch_versions.ini').write_text('[Versions]\nMod='+mode+'\n'+('ModVersion=2.1\n'if mode=='immortals'else'')+'PawPatch='+PATCH+'\nPatchChannel=beta\n')
  print('PURE_OPT_INSTALLED_FIXTURE',mode,flush=True)
 print('PURE_OPT_NATIVE_PACKAGE_STAGED',sha(archive))
if __name__=='__main__':main()
