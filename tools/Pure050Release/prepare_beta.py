"""Stage seven scoped beta packages and fresh installed Pure QA fixtures."""
import copy,zipfile,shutil,os,re
from context import *
from PrepareRelease070 import encode,validate_package
from rwd import decode

def main():
 stage=OUT/'beta-stage-r4';stage.mkdir(exist_ok=True);assert not (stage/'packages.json').exists();assets=stage/'assets';assets.mkdir(exist_ok=True);packages=[]
 old={p['id']:p for p in read(OUT/'before/feed/v3/beta.payload.json')['packages']};helpers=OUT/'beta-helpers-r4';report=read(helpers/'build-report.json');world=OUT/'world-data-r2';optional=OUT/'optional-data-r1';overlays=read(optional/'preparation.json')
 ids=['pure-fixes-data','pure-fixes-runtime','pure-beta-common','pure-vanilla-rules','pure-immortals-rules']+[id for id,row in overlays.items()if row['changed']]
 for id in ids:
  package=old[id];source=OUT/'accepted-assets'/package['urls'][0].rsplit('/',1)[1]if id not in overlays else Path(overlays[id]['input'])
  with zipfile.ZipFile(source)as z:manifest=json.loads(z.read('module.json'));files={n[8:]:z.read(n)for n in z.namelist()if n.startswith('payload/')and not n.endswith('/')}
  if id=='pure-fixes-runtime':
   for name,row in report.items():assert sha(helpers/name)==row['sha256'];files[name]=(helpers/name).read_bytes()
   files['paws_presentation.ini']=b'[Runtime]\nstartupReadyEvent=1\n'
  if id=='pure-beta-common':
   for p in (world/'common/payload').rglob('*'):
    if p.is_file():files[p.relative_to(world/'common/payload').as_posix()]=p.read_bytes()
   files['data/ui/game/paws_day_clock.tgi']=(REPO/'outputs/ui-scout-20261109/build-r26/paws_day_clock.tgi').read_bytes()
   # Use the native game menu; only the surrender panel's vertical anchor moves.
   text=(REPO/'outputs/ui-scout-20261109/stock/UI/Game/game_menu.tgi').read_text();at=text.index('[GameMenuResignDialog Inherit=GamePanelWidget]');tail,n=re.subn(r'\bT = 142\b','T = 258',text[at:],count=1);assert n==1;files['data/ui/game/game_menu.tgi']=(text[:at]+tail).encode('utf-16')
  if id.endswith('-rules'):
   mode='vanilla'if'vanilla'in id else'immortals'
   for p in (world/mode/'payload').rglob('*'):
    if p.is_file():files[p.relative_to(world/mode/'payload').as_posix()]=p.read_bytes()
  if id in overlays:
   for rel,h in overlays[id]['changed'].items():
    p=optional/id/'payload'/rel;assert sha(p)==h;files[rel]=p.read_bytes()
  version='1.3.72-pure.17-beta.1'if id=='pure-fixes-runtime'else'0.5.0-beta.1';manifest['version']=version;assert len({n.lower()for n in files})==len(files)
  manifest['files']=[dict(path=n,size=len(data),sha256=hashlib.sha256(data).hexdigest().upper())for n,data in sorted(files.items())]
  target=assets/(id+'-'+version+'.zip')
  with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
   for n,data in [('module.json',encode(manifest))]+[('payload/'+n,data)for n,data in sorted(files.items())]:
    info=zipfile.ZipInfo(n,(2026,11,9,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,data)
  fresh=copy.deepcopy(package);fresh.update(version=version,sha256=sha(target),size=target.stat().st_size,experimental=True,urls=['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/patch-pure-0.5.0-beta.1/'+target.name]);validate_package(target,fresh);packages.append(fresh)
 write(stage/'packages.json',packages)
 for mode in ['vanilla','immortals']:
  source=OUT/'stable-fixtures'/mode/'game';game=Path('G:/PawPure050QA-20261109')/'fixtures-r4'/mode/'game';game.parent.mkdir(parents=True,exist_ok=False)
  def ignore(folder,names):
   if Path(folder).name=='.pawpatch':return[n for n in names if n!='state.json']
   return shutil.ignore_patterns('Logs','Mods','*.log','*.dmp','*status*.txt','paws_ai_diagnostics')(folder,names)
  def copy_file(src,dst):
   if Path(src).suffix.lower()=='.rwd':os.link(src,dst);return dst
   return shutil.copy2(src,dst)
  shutil.copytree(source,game,ignore=ignore,copy_function=copy_file);state=read(game/'.pawpatch/state.json');state['appliedSettings']['channel']='beta'
  for p in packages:
   if mode not in p['mods']or p['id']not in state['modules']:continue
   with zipfile.ZipFile(assets/p['urls'][0].rsplit('/',1)[1])as z:
    manifest=json.loads(z.read('module.json'))
    for f in manifest['files']:
     path=game/f['path'];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read('payload/'+f['path']))
   state['modules'][p['id']]=dict(enabled=True,version=p['version'],files=manifest['files'])
  write(game/'.pawpatch/state.json',state);print('PURE_050_INSTALLED_FIXTURE',mode,flush=True)
 print('PURE_050_BETA_PACKAGES_STAGED',len(packages))
if __name__=='__main__':main()
