"""Compose local beta archives; public catalog promotion remains separate."""
import argparse,copy,hashlib,json,re,sys,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];OUT=REPO/'outputs/arcane-051-release-20261109';VERSION='0.5.1-beta.1'
sys.path.insert(0,str(REPO/'tools'))
from PrepareRelease070 import encode,sha,validate_package
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(encode(o))
def tune_recon(raw):
 text=raw.decode('cp1252');m=re.search(r'\[AirReconGoals\]\s*\{[^}]*\}',text);assert m
 block,n=re.subn(r'(num_goals\s*=\s*)0\b',r'\g<1>1',m.group());assert n==1
 assert 'grey_fog_priority' not in block and 'percent_to_count_region_explored' not in block
 block=block[:-1]+'\n                grey_fog_priority = 0\n                percent_to_count_region_explored = 1\n            }'
 return (text[:m.start()]+block+text[m.end():]).encode('cp1252')
def main():
 p=argparse.ArgumentParser();p.add_argument('--helpers',required=True,type=Path);p.add_argument('--native',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 helpers=a.helpers.resolve();native=a.native.resolve();rows=read(helpers/'build-report.json');assert len(rows)==8
 assert all(r['features']['patchVersion']==VERSION and r['features']['hotJoinRevision']==0 and not r['features']['legacySaveLobbyRecovery'] for r in rows.values())
 for name,row in rows.items():assert sha(helpers/name)==row['sha256']
 beta=read(OUT/'before/feed/v3/beta.payload.json');assets=[];replacements={};audits={};seen=set();source=OUT/'stable/accepted-assets'
 menu=(REPO/'outputs/ui-scout-20261109/stock/UI/Game/game_menu.tgi').read_text();at=menu.index('[GameMenuResignDialog Inherit=GamePanelWidget]');tail,n=re.subn(r'\bT = 142\b','T = 258',menu[at:],count=1);assert n==1;menu=(menu[:at]+tail).encode('utf-8')
 clock=(REPO/'game/ui-scout-test/paws_day_clock.tgi').read_bytes();graphics=native/'graphics/d3d9.dll';assert sha(graphics)==read(native/'graphics/product.json')['sha256']
 ids={'pawpatch-core','common-ui','player-colors','desync-continue','powers-shards-original'}
 for package in beta['packages']:
  pid=package['id']
  if pid not in ids:continue
  original=source/(pid+'-'+package['version']+'.zip');validate_package(original,package)
  with zipfile.ZipFile(original) as z:
   module=json.loads(z.read('module.json'));files={f['path'].replace('\\','/').lower():z.read('payload/'+f['path']) for f in module['files']};before=dict(files)
  for name in list(files):
   leaf=Path(name).name
   if leaf in rows:files[name]=(helpers/leaf).read_bytes();seen.add(leaf)
   elif leaf=='paws_patch_versions.ini':files[name]=(helpers/leaf).read_bytes()
   elif name=='d3d9.dll':files[name]=graphics.read_bytes()
   elif name=='data/templates/template_sai_k2.tgi':files[name]=tune_recon(files[name])
  if pid=='common-ui':files.update({'data/ui/game/game_menu.tgi':menu,'data/ui/game/paws_day_clock.tgi':clock})
  if pid=='pawpatch-core':files['paws_presentation.ini']=b'[Runtime]\nstartupReadyEvent=1\n'
  assert files!=before,pid
  assert not any(n.endswith('.marker') or 'qa.dll' in n.lower() or 'plugins.txt' in n.lower() or 'avifil32.dll' in n.lower() for n in files)
  module.update(version=VERSION,files=[dict(path=n,size=len(b),sha256=hashlib.sha256(b).hexdigest().upper()) for n,b in sorted(files.items())]);assert not module.get('remove')
  archive=out/'assets'/(pid+'-'+VERSION+'.zip');archive.parent.mkdir(exist_ok=True)
  with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
   for n,b in [('module.json',encode(module))]+[('payload/'+n,b) for n,b in sorted(files.items())]:
    i=zipfile.ZipInfo(n,(2026,11,9,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=0o100644<<16;z.writestr(i,b)
  q=copy.deepcopy(package);q.update(version=VERSION,experimental=True,size=archive.stat().st_size,sha256=sha(archive),urls=['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/patch-'+VERSION+'/'+archive.name]);validate_package(archive,q);replacements[pid]=q
  assets.append(dict(id=pid,path=str(archive),size=q['size'],sha256=q['sha256'],url=q['urls'][0]));audits[pid]=dict(changed=[n for n,b in files.items() if before.get(n)!=b],preservedFiles=sum(before.get(n)==b for n,b in files.items()))
 assert seen==set(rows)
 note=read(REPO/'docs/release-patch-0.5.1-beta.1.json');assert set(note['body'])=={'ru','en','de','fr','cs','uk'}
 write(out/'preparation.json',dict(version=VERSION,assets=assets,replacements=replacements,scope=audits,helpers=str(helpers),native=str(native),note=note,installedGameModified=False))
 (out/'notes.md').write_text('\n\n'.join(note['title'][c]+'\n\n'+note['body'][c] for c in ['ru','en','de','fr','cs','uk'])+'\n',encoding='utf-8')
 print('BETA_ARCHIVES_PREPARED',len(assets),'archives; eight product helpers; no catalog changes',flush=True)
if __name__=='__main__':main()
