from context import *
from datetime import datetime,timezone
from cryptography.hazmat.primitives import serialization
BODIES={
'ru':'- Уменьшен размер загрузки HD-интерфейса: оптимизировано разрешение иконок и рамок, удалены повторяющиеся данные.\n- Текстуры местности Arcane Wars объединены в один загружаемый пакет без снижения качества.',
'en':'- Smaller HD interface download: optimized icon and frame resolutions and removed duplicate data.\n- Arcane Wars terrain textures now download as one package with no quality reduction.',
'uk':'- Зменшено розмір завантаження HD-інтерфейсу: оптимізовано роздільну здатність іконок і рамок, видалено повторювані дані.\n- Текстури місцевості Arcane Wars об’єднано в один пакет без зниження якості.',
'cs':'- Menší stahování HD rozhraní díky optimalizovanému rozlišení ikon a rámečků a odstranění duplicitních dat.\n- Textury terénu Arcane Wars se stahují v jednom balíčku bez snížení kvality.',
'de':'- Kleinerer Download der HD-Oberfläche durch optimierte Symbol- und Rahmenauflösungen und entfernte doppelte Daten.\n- Arcane-Wars-Geländetexturen werden ohne Qualitätsverlust in einem Paket heruntergeladen.',
'fr':'- Téléchargement de l’interface HD réduit grâce à des résolutions optimisées et à la suppression des données en double.\n- Les textures du terrain d’Arcane Wars sont regroupées dans un seul téléchargement sans perte de qualité.'}
def bodies(group):return{k:(v if group=='arcane'else v.split('\n')[0])for k,v in BODIES.items()}
def note(group):
 v=ARC if group=='arcane'else PURE;name='Arcane Wars'if group=='arcane'else'Vanilla / Immortals';return dict(category='patch',mods=['arcane-wars']if group=='arcane'else['vanilla','immortals'],channel='beta',version=v,publishedAt='2026-11-17',title={k:'Paw’s Patch '+v+' — '+name for k in BODIES},body=bodies(group))
def catalogs():
 private=serialization.load_pem_private_key(KEY.read_bytes(),None);assert private.public_key().public_numbers()==key().public_numbers();replacement={p['id']:p for p in read(O/'packages.json')};retired={f'arcane-biome-textures-{i:02}'for i in range(1,5)};allowed=[]
 for rel in FILES[:6]:
  raw=(O/'before'/rel).read_bytes();a=verify(json.loads(raw),key());b=copy.deepcopy(a)
  if rel in['feed/v2/beta.json','feed/v3/beta.json']:
   assert next(p for p in a['packages']if p['id']=='pawpatch-core')['version']=='0.6.0-beta.4';assert next(p for p in a['packages']if p['id']=='pure-fixes-data')['version']=='0.5.0-beta.8'
   b['packages']=[copy.deepcopy(replacement.get(p['id'],p))for p in a['packages']if p['id']not in retired]+[copy.deepcopy(replacement['arcane-biome-textures'])]
   entry=lambda group:dict(id='compact-ui-20261117',category='always',titleRu='Компактный HD-интерфейс',titleEn='Compact HD interface',bodyRu=bodies(group)['ru'],bodyEn=bodies(group)['en'])
   b['patchGuide']['version']=ARC;b['patchGuide']['entries'].insert(0,entry('arcane'))
   for g in b['modGuides']:
    if g['id']in['vanilla','immortals']:g['patchGuide']['version']=PURE;g['patchGuide']['entries'].insert(0,entry('pure'))
   b['changelog']=[note('arcane'),note('pure')]+a['changelog'];b['newsTitle']={k:'Paw’s Patch — HD UI'for k in BODIES};b['newsBody']=BODIES;b['publishedAt']=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
   for k in['launcher','game','modGames']:assert b[k]==a[k]
   assert[p for p in b['packages']if p['id']not in replacement]==[p for p in a['packages']if p['id']not in replacement and p['id']not in retired]
   write(O/'signed'/rel,sign(b,private));allowed.append(rel)
  else:
   p=O/'signed'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
 h=read(O/'before/feed/changelog.history.json');assert not any(x.get('version')in[ARC,PURE]for x in h['beta']);h['beta']=[note('arcane'),note('pure')]+h['beta'];write(O/'signed/feed/changelog.history.json',h);allowed.append('feed/changelog.history.json');write(O/'signed/feed/patch-guide-beta.json',verify(read(O/'signed/feed/v3/beta.json'),key())['patchGuide']);allowed.append('feed/patch-guide-beta.json');write(O/'scope.json',dict(allowed=allowed))
 for channel in['stable','beta']:
  f=verify(read(O/'signed'/f'feed/v3/{channel}.json'),key())
  if channel=='beta':
   for q in f['packages']:
    if q['id']in replacement:q['urls']=[read(O/'package-audit.json')[q['id']]['path']]
  write(O/'local-feeds'/f'{channel}.json',sign(f,private))
 (O/'public.pem').write_text(read(S/'src/PawsPatchLauncher/launcher.config.json')['publicKeyPem'])
 for group in['arcane','pure']:
  write(O/group/'release.json',note(group));(O/group/'release-notes.md').write_text('\n\n'.join(note(group)['title'][k]+'\n\n'+bodies(group)[k]for k in BODIES)+'\n',encoding='utf-8')
 print('COMPACT_CATALOGS_SIGNED',flush=True)
if __name__=='__main__':catalogs()
