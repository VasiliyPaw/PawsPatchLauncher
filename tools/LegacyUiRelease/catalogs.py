from context import *
from datetime import datetime,timezone
from cryptography.hazmat.primitives import serialization
BODIES={'ru': '- Возвращены прежние иконки и оформление интерфейса всех рас.', 'en': '- Restored the previous icons and interface artwork for every faction.', 'uk': '- Повернуто попередні іконки та оформлення інтерфейсу всіх рас.', 'cs': '- Obnoveny původní ikony a vzhled rozhraní všech ras.', 'de': '- Frühere Symbole und das Oberflächendesign aller Völker wiederhergestellt.', 'fr': '- Rétablissement des anciennes icônes et de l’habillage de l’interface de toutes les factions.'}
REMOVAL={'ru':'Удалены файлы прежних HD-иконок и интерфейса.','en':'Removed the previous HD icon and interface files.','uk':'Видалено файли попередніх HD-іконок та інтерфейсу.','cs':'Odstraněny soubory předchozích HD ikon a rozhraní.','de':'Die bisherigen HD-Symbol- und Oberflächendateien wurden entfernt.','fr':'Suppression des anciens fichiers HD des icônes et de l’interface.'}
BODIES={k:v+'\n- '+REMOVAL[k]for k,v in BODIES.items()}

def note(group):
 v=ARC if group=='arcane'else PURE;name='Arcane Wars'if group=='arcane'else'Vanilla / Immortals'
 return dict(category='patch',mods=['arcane-wars']if group=='arcane'else['vanilla','immortals'],channel='beta',version=v,publishedAt='2026-11-18',title={k:'Paw’s Patch '+v+' — '+name for k in BODIES},body=BODIES)
def catalogs():
 private=serialization.load_pem_private_key(KEY.read_bytes(),None);assert private.public_key().public_numbers()==key().public_numbers();replacement={p['id']:p for p in read(O/'packages.json')};allowed=[]; launcher_note=read(S/'docs/release-1.0.22.json'); launcher=read(O/'launcher-package.json') if (O/'launcher-package.json').exists() else None
 for rel in FILES[:6]:
  raw=(O/'before'/rel).read_bytes();a=verify(json.loads(raw),key());b=copy.deepcopy(a)
  if rel in['feed/v2/beta.json','feed/v3/beta.json']:
   assert next(p for p in a['packages']if p['id']=='pawpatch-core')['version']=='0.6.0-beta.5'
   assert next(p for p in a['packages']if p['id']=='pure-fixes-data')['version']=='0.5.0-beta.9'
   b['packages']=[copy.deepcopy(replacement.get(p['id'],p))for p in a['packages']]
   b['patchGuide']['version']=ARC;b['patchGuide']['entries']=[e for e in b['patchGuide']['entries']if e['id']not in ['fullres-ui-20261117','compact-ui-20261117']]
   entry=dict(id='legacy-ui-20261118',category='always',titleRu='Прежние иконки и интерфейс',titleEn='Previous icons and interface',bodyRu=BODIES['ru'],bodyEn=BODIES['en'])
   b['patchGuide']['entries'].insert(0,entry)
   for g in b['modGuides']:
    if g['id']in['vanilla','immortals']:g['patchGuide']['version']=PURE;g['patchGuide']['entries']=[e for e in g['patchGuide']['entries']if e['id']not in ['fullres-ui-20261117','compact-ui-20261117']];g['patchGuide']['entries'].insert(0,copy.deepcopy(entry))
   b['changelog']=[note('arcane'),note('pure')]+a['changelog'];b['newsTitle']={k:'Paw’s Patch — UI'for k in BODIES};b['newsBody']=BODIES;b['publishedAt']=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
   for k in['game','modGames']:assert b[k]==a[k]
   assert[p for p in b['packages']if p['id']not in replacement]==[p for p in a['packages']if p['id']not in replacement]
   allowed.append(rel)
  if launcher:
   b['launcher'].update(launcher);b['changelog']=[launcher_note]+b.get('changelog',[]);b['publishedAt']=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
   if rel not in allowed:allowed.append(rel)
  write(O/'signed'/rel,sign(b,private))
 h=read(O/'before/feed/changelog.history.json');assert not any(x.get('version')in[ARC,PURE]for x in h['beta']);h['beta']=[note('arcane'),note('pure')]+h['beta'];
 if launcher:
  for c in ['stable','beta']:h[c].insert(0,launcher_note)
 write(O/'signed/feed/changelog.history.json',h);allowed.append('feed/changelog.history.json')
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
