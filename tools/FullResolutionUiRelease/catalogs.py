from context import *
from datetime import datetime,timezone
from cryptography.hazmat.primitives import serialization
BODIES={
'ru':'- Иконки действий, построек и технологий используют полное разрешение HD-исходников.\n- Повышена чёткость расовых рамок интерфейса, в том числе при 2К и выше.',
'en':'- Action, building and technology icons now use the full resolution of their HD artwork.\n- Sharper faction interface frames, including at 1440p and higher resolutions.',
'uk':'- Іконки дій, споруд і технологій використовують повну роздільну здатність HD-оригіналів.\n- Покращено чіткість расових рамок інтерфейсу, зокрема при 2К і вище.',
'cs':'- Ikony akcí, budov a technologií nyní využívají plné rozlišení HD předloh.\n- Ostřejší rámečky rozhraní ras, také při rozlišení 1440p a vyšším.',
'de':'- Aktions-, Gebäude- und Technologie-Symbole nutzen jetzt die volle Auflösung ihrer HD-Vorlagen.\n- Schärfere Völkerrahmen der Benutzeroberfläche, auch bei 1440p und höheren Auflösungen.',
'fr':'- Les icônes d’action, de bâtiment et de technologie utilisent désormais la pleine résolution des images HD.\n- Cadres d’interface des factions plus nets, y compris en 1440p et au-delà.'}
def note(group):
 v=ARC if group=='arcane'else PURE;name='Arcane Wars'if group=='arcane'else'Vanilla / Immortals'
 return dict(category='patch',mods=['arcane-wars']if group=='arcane'else['vanilla','immortals'],channel='beta',version=v,publishedAt='2026-11-17',title={k:'Paw’s Patch '+v+' — '+name for k in BODIES},body=BODIES)
def catalogs():
 private=serialization.load_pem_private_key(KEY.read_bytes(),None);assert private.public_key().public_numbers()==key().public_numbers();replacement={p['id']:p for p in read(O/'packages.json')};allowed=[]
 for rel in FILES[:6]:
  raw=(O/'before'/rel).read_bytes();a=verify(json.loads(raw),key());b=copy.deepcopy(a)
  if rel in['feed/v2/beta.json','feed/v3/beta.json']:
   assert next(p for p in a['packages']if p['id']=='pawpatch-core')['version']=='0.6.0-beta.3'
   assert next(p for p in a['packages']if p['id']=='pure-fixes-data')['version']=='0.5.0-beta.7'
   b['packages']=[copy.deepcopy(replacement.get(p['id'],p))for p in a['packages']]
   b['patchGuide']['version']=ARC
   entry=dict(id='fullres-ui-20261117',category='always',titleRu='Чёткий HD-интерфейс',titleEn='Sharper HD interface',bodyRu=BODIES['ru'],bodyEn=BODIES['en'])
   b['patchGuide']['entries'].insert(0,entry)
   for g in b['modGuides']:
    if g['id']in['vanilla','immortals']:g['patchGuide']['version']=PURE;g['patchGuide']['entries'].insert(0,copy.deepcopy(entry))
   b['changelog']=[note('arcane'),note('pure')]+a['changelog'];b['newsTitle']={k:'Paw’s Patch — HD UI'for k in BODIES};b['newsBody']=BODIES;b['publishedAt']=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
   for k in['launcher','game','modGames']:assert b[k]==a[k]
   assert[p for p in b['packages']if p['id']not in replacement]==[p for p in a['packages']if p['id']not in replacement]
   write(O/'signed'/rel,sign(b,private));allowed.append(rel)
  else:
   p=O/'signed'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
 h=read(O/'before/feed/changelog.history.json');assert not any(x.get('version')in[ARC,PURE]for x in h['beta']);h['beta']=[note('arcane'),note('pure')]+h['beta'];write(O/'signed/feed/changelog.history.json',h);allowed.append('feed/changelog.history.json')
 write(O/'signed/feed/patch-guide-beta.json',verify(read(O/'signed/feed/v3/beta.json'),key())['patchGuide']);allowed.append('feed/patch-guide-beta.json');write(O/'scope.json',dict(allowed=allowed))
 for channel in['stable','beta']:
  f=verify(read(O/'signed'/f'feed/v3/{channel}.json'),key())
  if channel=='beta':
   for q in f['packages']:
    if q['id']in replacement:q['urls']=[read(O/'package-audit.json')[q['id']]['path']]
  write(O/'local-feeds'/f'{channel}.json',sign(f,private))
 (O/'public.pem').write_text(read(S/'src/PawsPatchLauncher/launcher.config.json')['publicKeyPem'])
 for group in['arcane','pure']:
  write(O/group/'release.json',note(group));(O/group/'release-notes.md').write_text('\n\n'.join(note(group)['title'][k]+'\n\n'+BODIES[k]for k in BODIES)+'\n',encoding='utf-8')
 print('ALL_BETA_CATALOGS_SIGNED',flush=True)
if __name__=='__main__':catalogs()
