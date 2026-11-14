"""Minimal beta packages, signed candidates and exact build-input bundles."""
import argparse,zipfile
from datetime import datetime,timezone
from cryptography.hazmat.primitives import serialization
from context import *
BODIES={
'ru':'- Увеличены кэши моделей, анимаций, эффектов и земли.\n- Объём кэша подстраивается под доступную память.\n- Отключены экспериментальные оптимизации отрисовки.\n- Исправлено зависание погибших воздушных разведчиков.',
'en':'- Increased caches for models, animations, effects and terrain.\n- Cache budgets adapt to available memory.\n- Disabled experimental rendering optimizations.\n- Fixed dead aerial scouts getting stuck in the air.',
'uk':'- Збільшено кеші моделей, анімацій, ефектів і місцевості.\n- Обсяг кешу підлаштовується під доступну пам’ять.\n- Вимкнено експериментальні оптимізації відображення.\n- Виправлено зависання загиблих повітряних розвідників.',
'cs':'- Zvětšeny mezipaměti modelů, animací, efektů a terénu.\n- Velikost mezipaměti se přizpůsobuje dostupné paměti.\n- Vypnuty experimentální optimalizace vykreslování.\n- Opraveni mrtví letečtí průzkumníci zůstávající ve vzduchu.',
'de':'- Größere Zwischenspeicher für Modelle, Animationen, Effekte und Gelände.\n- Die Cache-Größe passt sich dem verfügbaren Speicher an.\n- Experimentelle Rendering-Optimierungen deaktiviert.\n- Tote Luftaufklärer bleiben nicht mehr in der Luft hängen.',
'fr':'- Augmentation des caches des modèles, animations, effets et terrains.\n- La taille des caches s’adapte à la mémoire disponible.\n- Désactivation des optimisations expérimentales du rendu.\n- Correction des éclaireurs aériens morts restant bloqués en vol.'}
def note(kind):
 title='Paw’s Patch '+VERSIONS[kind]+' — '+('Arcane Wars'if kind=='arcane'else'Vanilla / Immortals')
 return dict(category='patch',mods=['arcane-wars']if kind=='arcane'else['vanilla','immortals'],channel='beta',version=VERSIONS[kind],publishedAt='2026-11-14',title={k:title for k in BODIES},body=BODIES)
def assets():
 f=verify(read(OUT/'before/feed/v3/beta.json'),key());folder=OUT/'baseline-assets';folder.mkdir(exist_ok=True)
 for p in f['packages']:
  if p['id']not in IDS:continue
  dest=folder/(p['id']+'.zip')
  if not dest.exists():dest.write_bytes(fetch(p['urls'][0]))
  validate_package(dest,p)
 for kind in VERSIONS:
  write(OUT/('release-'+kind+'.json'),note(kind));(OUT/(kind+'-notes.md')).write_text('\n\n'.join(note(kind)['title'][k]+'\n\n'+BODIES[k]for k in BODIES)+'\n',encoding='utf-8')
 print('PUBLIC_BASELINE_ASSETS_VERIFIED',flush=True)
def archives():
 f=verify(read(OUT/'before/feed/v3/beta.json'),key());packages=[];audit={};seen_helpers=set();overlay_count=0
 for p in f['packages']:
  if p['id']not in IDS:continue
  kind='pure'if p['id'].startswith('pure-')else'arcane';version=RUNTIME if p['id']=='pure-fixes-runtime'else VERSIONS[kind]
  source=OUT/'baseline-assets'/(p['id']+'.zip');validate_package(source,p)
  with zipfile.ZipFile(source)as z:
   module=json.loads(z.read('module.json'));before={r['path']:z.read('payload/'+r['path'])for r in module['files']};files=dict(before)
  folder=OUT/(kind+'-helpers');rows=read(folder/'build-report.json')
  for path in files:
   leaf=Path(path).name
   if leaf in rows:
    assert hashlib.sha256(before[path]).hexdigest().upper()==rows[leaf]['baselineSha256'],(p['id'],path)
    files[path]=(folder/leaf).read_bytes();seen_helpers.add((kind,leaf))
   if path.replace('\\','/').lower()=='data/uvars_k2.tgi':
    assert hashlib.sha256(before[path]).hexdigest().upper()=='BB73F2CDF722024F89B7C57865A9D33FFE855D80637D7F3FCADEAD8089D25FCA'
    files[path]=(OUT/'overlay/data/UVars_k2.tgi').read_bytes();overlay_count+=1
   if leaf=='paws_patch_versions.ini':files[path]=files[path].replace(p['version'].encode(),VERSIONS[kind].encode())
  changed=[n for n in files if files[n]!=before[n]]
  assert all(Path(n).name.lower() in {x.lower()for x in rows}|{'paws_patch_versions.ini','uvars_k2.tgi'}for n in changed),changed
  assert all(Path(n).name.lower()!='d3d9.dll'for n in changed)
  module.update(version=version,files=[dict(path=n,size=len(b),sha256=hashlib.sha256(b).hexdigest().upper())for n,b in sorted(files.items())])
  dest=OUT/kind/'assets'/(p['id']+'-'+version+'.zip');dest.parent.mkdir(parents=True,exist_ok=True)
  with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
   for n,b in [('module.json',encode(module))]+[('payload/'+n,b)for n,b in sorted(files.items())]:
    item=zipfile.ZipInfo(n,(2026,11,14,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED;z.writestr(item,b)
  q=copy.deepcopy(p);tag=('patch-pure-'if kind=='pure'else'patch-')+VERSIONS[kind];q.update(version=version,size=dest.stat().st_size,sha256=sha(dest),urls=['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/'+tag+'/'+dest.name]);validate_package(dest,q)
  packages.append(q);audit[p['id']]=dict(archive=str(dest),source=str(source),kind=kind,changed=changed,preserved=len(files)-len(changed))
 assert len(seen_helpers)==12 and overlay_count==2,(seen_helpers,overlay_count)
 write(OUT/'packages.json',packages);write(OUT/'package-audit.json',audit);print('SEVEN_MINIMAL_BETA_ARCHIVES_READY',flush=True)
def guide(g,kind):
 g=copy.deepcopy(g);g['version']=VERSIONS[kind]
 for e in g['entries']:
  if e['id']=='pure-optimizations':
   e.update(titleRu='Кэши ресурсов',titleEn='Resource caches',bodyRu='Увеличены кэши ресурсов и земли. При нехватке памяти объём кэша автоматически уменьшается.',bodyEn='Increased resource and terrain caches. Cache budgets automatically decrease when memory is low.')
 g['entries'].insert(0,dict(id='cache-stability-20261114',category='always',titleRu='Память и воздушная разведка',titleEn='Memory and aerial scouts',bodyRu=BODIES['ru'],bodyEn=BODIES['en']))
 return g
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
   dest=OUT/'signed'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
 h=read(OUT/'before/feed/changelog.history.json');h['beta']=[note('arcane'),note('pure')]+h['beta'];write(OUT/'signed/feed/changelog.history.json',h)
 write(OUT/'signed/feed/patch-guide-beta.json',verify(read(OUT/'signed/feed/v3/beta.json'),key())['patchGuide']);allowed+=['feed/changelog.history.json','feed/patch-guide-beta.json'];write(OUT/'scope.json',dict(allowed=allowed,versions=VERSIONS))
 for channel in ['stable','beta']:
  f=verify(read(OUT/'signed/feed/v3'/f'{channel}.json'),key())
  if channel=='beta':
   for p in f['packages']:
    if p['id']in IDS:p['urls']=[read(OUT/'package-audit.json')[p['id']]['archive']]
  write(OUT/'local-feeds'/f'{channel}.json',sign(f,private))
 (OUT/'public.pem').write_text(read(REPO/'src/PawsPatchLauncher/launcher.config.json')['publicKeyPem']);print('SIGNED_BETA_CANDIDATES_READY',flush=True)
def bundle():
 for kind in VERSIONS:
  folder=OUT/(kind+'-helpers');files={}
  for row in read(folder/'build-report.json').values():
   for p,digest in row['sources'].items():
    p=Path(p);assert sha(p)==digest and p.suffix.lower()not in['.pem','.rsg','.rwd']and p.name.lower()!='k2.exe';files['inputs/'+digest+'/'+p.name]=p.read_bytes()
  for name in ['build-report.json','changed-inputs.json']:files[name]=(folder/name).read_bytes()
  for p in(OUT/'native').rglob('*'):
   if p.is_file()and 'payload-r'not in p.as_posix()and p.suffix in['.c','.h','.py','.json']:files['native/'+p.relative_to(OUT/'native').as_posix()]=p.read_bytes()
  for folder_name in ['ExpandedCache','CacheStabilityRelease','NativeRenderPolicy']:
   for p in(REPO/'tools'/folder_name).iterdir():
    if p.suffix in['.py','.c','.cs','.md']:files['tools/'+folder_name+'/'+p.name]=p.read_bytes()
  for n in ['policy.c','expanded.c','build_native.py']:files['cache/'+n]=(REPO/'game/resource-cache'/n).read_bytes()
  for p in(OUT/(kind+'-native')).iterdir():
   if p.suffix in['.c','.h']:files['presentation/'+p.name]=p.read_bytes()
  files['policy.json']=(OUT/'policy.json').read_bytes();files['data/UVars_k2.tgi']=(OUT/'overlay/data/UVars_k2.tgi').read_bytes()
  files['README.txt']=b'Exact ordinary helper inputs for the three-beta cache/scout release. No game EXE, saves, RWD, personal profiles or signing keys. Remap build-report.json compiler inputs by SHA-256 to inputs/<hash>/<filename>. Cache source and emitted hook metadata are under native/. The 90% coefficient, no prewarm/Find, and aircraft zero-speed fall repair are enabled. Presentation source is unchanged from the preceding native-Find candidate. QA-only helper/profile/pressure injection is not shipped in the ordinary helpers.\n'
  files['manifest.json']=encode({n:dict(size=len(b),sha256=hashlib.sha256(b).hexdigest().upper())for n,b in sorted(files.items())})
  dest=OUT/kind/('cache-stability-'+VERSIONS[kind]+'-build-inputs.zip')
  with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
   for n,b in sorted(files.items()):z.writestr(n,b)
  write(OUT/kind/'bundle.json',dict(path=str(dest),sha256=sha(dest),size=dest.stat().st_size,files=len(files)))
 print('EXACT_RELEASE_INPUTS_BUNDLED',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['assets','archives','catalogs','bundle']);globals()[p.parse_args().action]()
