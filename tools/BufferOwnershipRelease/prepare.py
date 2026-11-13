"""Freeze current public bytes, rebuild helpers, package and sign beta candidates."""
import argparse,re,zipfile
from datetime import datetime,timezone
from cryptography.hazmat.primitives import serialization
from context import *
BODIES={
 'ru':'- Исправлена ошибка, которая могла повреждать отображение моделей во время боя.',
 'en':'- Fixed an issue that could corrupt model rendering during battles.',
 'uk':'- Виправлено помилку, яка могла спотворювати відображення моделей під час бою.',
 'cs':'- Opravena chyba, která mohla během bojů poškodit vykreslování modelů.',
 'de':'- Einen Fehler behoben, der während Kämpfen die Darstellung von Modellen beschädigen konnte.',
 'fr':'- Correction d’un problème pouvant altérer l’affichage des modèles pendant les combats.'}
def note(kind):
 title='Paw’s Patch '+VERSIONS[kind]+' — '+('Arcane Wars'if kind=='arcane'else'Vanilla / Immortals')
 return dict(category='patch',mods=['arcane-wars']if kind=='arcane'else['vanilla','immortals'],channel='beta',version=VERSIONS[kind],publishedAt='2026-11-13',title={k:title for k in BODIES},body=BODIES)
def baseline():
 OUT.mkdir(exist_ok=False);(OUT/'temp').mkdir();h=head();git('fetch','origin','main');assert git('rev-parse','FETCH_HEAD')==h
 hashes={}
 for rel in FILES:
  data=fetch(RAW.replace('/main/','/'+h+'/')+rel)
  if rel in FEEDS:verify(json.loads(data),key())
  p=OUT/'before'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);hashes[rel]=sha(p)
 f=verify(read(OUT/'before/feed/v3/beta.json'),key());assert f['patchGuide']['version']=='0.5.1-beta.3'
 assert next(p for p in f['packages']if p['id']=='pure-fixes-data')['version']=='0.5.0-beta.4'
 assert {p['id']for p in f['packages']}>=IDS
 write(OUT/'baseline.json',dict(publicHead=h,files=hashes,launcher=f['launcher']['version'],localHead=git('rev-parse','HEAD')))
 (OUT/'staged-before.patch').write_bytes(subprocess.check_output(['git','diff','--cached','--binary'],cwd=REPO));(OUT/'dirty-before.txt').write_text(git('status','--porcelain=v1'))
 (OUT/'baseline-assets').mkdir()
 for p in f['packages']:
  if p['id']not in IDS:continue
  path=OUT/'baseline-assets'/(p['id']+'.zip');path.write_bytes(fetch(p['urls'][0]));validate_package(path,p)
 for kind in VERSIONS:
  write(OUT/('release-'+kind+'.json'),note(kind));(OUT/(kind+'-notes.md')).write_text('\n\n'.join(note(kind)['title'][k]+'\n\n'+BODIES[k]for k in BODIES)+'\n',encoding='utf-8')
 print('LIVE_BASELINE_VERIFIED',h,'launcher',f['launcher']['version'],flush=True)
def once(s,a,b):assert s.count(a)==1,(a[:80],s.count(a));return s.replace(a,b)
def helpers():
 proof=read(GRAPHICS/'product.json');new=sha(GRAPHICS/'d3d9.dll');assert proof['nativeBufferOwnership']and proof['bufferReuseRevision']==0 and new==proof['sha256']
 for kind in VERSIONS:
  base=FROZEN/(kind+'-helpers');rows=read(base/'build-report.json');out=OUT/(kind+'-helpers');out.mkdir();(out/'inputs').mkdir()
  previous=next(iter(rows.values()))['features']['patchVersion'];runtime=next(iter(rows.values()))['features'].get('version');mapped={};audit={}
  for name,row in rows.items():
   assert sha(base/name)==row['sha256']
   for p,h in row['sources'].items():assert sha(p)==h,p
  for name in ['paws_player_colors.ini','paws_patch_versions.ini']:
   if(base/name).exists():(out/name).write_bytes((base/name).read_bytes().replace(previous.encode(),VERSIONS[kind].encode()))
  for p in sorted({p for r in rows.values()for p in r['sources']}):
   src=Path(p);original=src.read_bytes();data=original
   if src.suffix.lower()=='.cs':
    s=original.decode('utf-8-sig');s=s.replace(previous,VERSIONS[kind])
    if kind=='pure':s=s.replace(runtime,RUNTIME)
    if src.name.endswith('PresentationRuntimePayload.cs'):s=once(s,OLD_GRAPHICS,new)
    if src.name.endswith('PresentationRuntimePatch.cs'):s=once(s,'bufferReuse=32MiB','bufferReuse=disabled/native-allocation')
    # Pure emits these fields from its beta wrapper, not generic BuildFeatures.
    s=s.replace(r'\"bufferReuseRevision\":1',r'\"bufferReuseRevision\":0')
    if kind=='pure':s=s.replace(r'\"bufferReuseBudgetMiB\":32',r'\"bufferReuseBudgetMiB\":0')
    data=s.encode('utf-8')
   dest=out/'inputs'/hashlib.sha256(data).hexdigest().upper()/src.name;dest.parent.mkdir(exist_ok=True);dest.write_bytes(data);mapped[p]=str(dest)
   if data!=original:audit[p]=dict(before=sha(src),after=sha(dest))
  report={}
  for name,row in rows.items():
   args=[]
   for arg in row['args']:
    if arg.startswith('/out:'):arg='/out:'+str(out/name)
    elif arg.startswith('/resource:'):
     p,res=arg[10:].rsplit(',',1);arg='/resource:'+mapped[p]+','+res
    elif arg in mapped:arg=mapped[arg]
    args.append(arg)
   run(args);features=json.loads(run([out/name,'--features']));expected=dict(row['features'],patchVersion=VERSIONS[kind],bufferReuseRevision=0)
   if kind=='pure':expected.update(version=RUNTIME,bufferReuseBudgetMiB=0)
   assert features==expected,(name,features,expected)
   flags=[]if kind=='pure'else['--quiet-startup-self-test','--common-ui-self-test','--lobby-payload-test','--assistant-self-test','--fast-transfer-self-test']
   tests={flag:run([out/name,flag])for flag in flags}
   paths=[Path(p)for p in args if p.lower().endswith('.cs')]+[Path(p[10:].rsplit(',',1)[0])for p in args if p.startswith('/resource:')]
   for arg in args:
    if arg.startswith('/resource:'):
     changed=Path(arg[10:].rsplit(',',1)[0]);assert sha(changed)==changed.parent.name,'Other native payload changed'
   report[name]=dict(sha256=sha(out/name),features=features,args=args,sources={str(p):sha(p)for p in paths},selfTests=tests,baselineSha256=row['sha256'])
   print('HELPER_READY',kind,name,flush=True)
  write(out/'build-report.json',report);write(out/'changed-inputs.json',audit)
 print('ALL_TWELVE_HELPERS_READY',new,flush=True)
def archives():
 f=verify(read(OUT/'before/feed/v3/beta.json'),key());packages=[];audit={}
 for p in f['packages']:
  if p['id']not in IDS:continue
  kind='pure'if p['id'].startswith('pure-')else'arcane';version=RUNTIME if p['id']=='pure-fixes-runtime'else VERSIONS[kind]
  source=OUT/'baseline-assets'/(p['id']+'.zip');validate_package(source,p)
  with zipfile.ZipFile(source)as z:
   m=json.loads(z.read('module.json'));before={r['path']:z.read('payload/'+r['path'])for r in m['files']};files=dict(before)
  folder=OUT/(kind+'-helpers');rows=read(folder/'build-report.json')
  for path in files:
   leaf=Path(path).name
   if leaf in rows:
    assert hashlib.sha256(files[path]).hexdigest().upper()==rows[leaf]['baselineSha256'];files[path]=(folder/leaf).read_bytes()
   if leaf=='paws_patch_versions.ini':files[path]=(folder/leaf).read_bytes()
   if leaf.lower()=='d3d9.dll':assert hashlib.sha256(files[path]).hexdigest().upper()==OLD_GRAPHICS;files[path]=(GRAPHICS/'d3d9.dll').read_bytes()
  changed=[n for n in files if files[n]!=before[n]];assert set(files)==set(before)
  assert all(Path(n).name in set(rows)|{'paws_patch_versions.ini','d3d9.dll'}for n in changed)
  m.update(version=version,files=[dict(path=n,size=len(b),sha256=hashlib.sha256(b).hexdigest().upper())for n,b in sorted(files.items())])
  dest=OUT/kind/'assets'/(p['id']+'-'+version+'.zip');dest.parent.mkdir(parents=True,exist_ok=True)
  with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
   for n,b in [('module.json',encode(m))]+[('payload/'+n,b)for n,b in sorted(files.items())]:
    item=zipfile.ZipInfo(n,(2026,11,13,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED;z.writestr(item,b)
  q=copy.deepcopy(p);tag=('patch-pure-'if kind=='pure'else'patch-')+VERSIONS[kind];q.update(version=version,size=dest.stat().st_size,sha256=sha(dest),urls=['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/'+tag+'/'+dest.name]);validate_package(dest,q)
  packages.append(q);audit[p['id']]=dict(archive=str(dest),source=str(source),kind=kind,changed=changed,preserved=len(files)-len(changed))
 write(OUT/'packages.json',packages);write(OUT/'package-audit.json',audit);print('SEVEN_ARCHIVES_READY',flush=True)
def guide(g,kind):
 g=copy.deepcopy(g);g['version']=VERSIONS[kind];g['entries'].insert(0,dict(id='native-buffer-ownership',category='always',titleRu='Отображение моделей',titleEn='Model rendering',bodyRu=BODIES['ru'],bodyEn=BODIES['en']));return g
def catalogs():
 private=serialization.load_pem_private_key(KEY.read_bytes(),None);assert private.public_key().public_numbers()==key().public_numbers()
 replacements={p['id']:p for p in read(OUT/'packages.json')};allowed=[]
 for rel in FEEDS:
  raw=(OUT/'before'/rel).read_bytes();a=verify(json.loads(raw),key());b=copy.deepcopy(a)
  if rel in ['feed/v2/beta.json','feed/v3/beta.json']:
   b['packages']=[copy.deepcopy(replacements.get(p['id'],p))for p in a['packages']];b['patchGuide']=guide(a['patchGuide'],'arcane')
   for g in b['modGuides']:
    if g['id']in['vanilla','immortals']:g['patchGuide']=guide(g['patchGuide'],'pure')
   b['changelog']=[note('arcane'),note('pure')]+a['changelog'];b['newsTitle']=note('arcane')['title'];b['newsBody']=BODIES;b['publishedAt']=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
   for k in ['launcher','game','modGames']:assert b[k]==a[k]
   assert [p for p in b['packages']if p['id']not in IDS]==[p for p in a['packages']if p['id']not in IDS]
   write(OUT/'signed'/rel,sign(b,private));allowed.append(rel)
  else:
   target=OUT/'signed'/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
 h=read(OUT/'before/feed/changelog.history.json');h['beta']=[note('arcane'),note('pure')]+h['beta'];write(OUT/'signed/feed/changelog.history.json',h)
 write(OUT/'signed/feed/patch-guide-beta.json',verify(read(OUT/'signed/feed/v3/beta.json'),key())['patchGuide']);allowed+=['feed/changelog.history.json','feed/patch-guide-beta.json'];write(OUT/'scope.json',dict(allowed=allowed,versions=VERSIONS))
 for channel in ['stable','beta']:
  f=verify(read(OUT/'signed/feed/v3'/f'{channel}.json'),key())
  if channel=='beta':
   for p in f['packages']:
    if p['id']in IDS:p['urls']=[read(OUT/'package-audit.json')[p['id']]['archive']]
  write(OUT/'local-feeds'/f'{channel}.json',sign(f,private))
 (OUT/'public.pem').write_text(read(REPO/'src/PawsPatchLauncher/launcher.config.json')['publicKeyPem']);print('SIGNED_CANDIDATES_READY',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['baseline','helpers','archives','catalogs']);globals()[p.parse_args().action]()
