from context import *
from datetime import datetime,timezone
from cryptography.hazmat.primitives import serialization
FILES=[f'feed/{p}{c}.json'for p in ['v3/','v2/','']for c in ['stable','beta']]+['feed/changelog.history.json','feed/patch-guide-beta.json']
BODIES={'ru': '- Исправлено отображение владельца и цвета захваченных городов и построек с учётом тумана войны.\n- Исправлены клики по кнопкам групп в верхней части экрана.', 'en': '- Fixed captured city and building ownership and colors while respecting fog of war.\n- Fixed clicks on the group buttons at the top of the screen.', 'uk': '- Виправлено відображення власника та кольору захоплених міст і споруд з урахуванням туману війни.\n- Виправлено натискання кнопок груп у верхній частині екрана.', 'cs': '- Opraveno zobrazení vlastníka a barev dobytých měst a budov s ohledem na válečnou mlhu.\n- Opraveno klikání na tlačítka skupin v horní části obrazovky.', 'de': '- Besitzer und Farben eroberter Städte und Gebäude werden unter Berücksichtigung des Kriegsnebels korrekt angezeigt.\n- Klicks auf die Gruppenschaltflächen am oberen Bildschirmrand funktionieren wieder.', 'fr': '- Correction de l’affichage du propriétaire et des couleurs des villes et bâtiments capturés, en respectant le brouillard de guerre.\n- Correction des clics sur les boutons de groupe en haut de l’écran.'}

def note():return dict(category='patch',mods=['vanilla','immortals'],channel='beta',version=VERSION,publishedAt='2026-11-16',title={k:'Paw’s Patch '+VERSION+' — Vanilla / Immortals'for k in BODIES},body=BODIES)
def snapshot():
 git('fetch','--no-tags','origin','main');head=git('rev-parse','FETCH_HEAD')
 for rel in FILES:
  p=O/'before'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(subprocess.check_output(['git','show',head+':'+rel],cwd=REPO))
 write(O/'catalog-baseline.json',dict(publicHead=head))
def catalogs():
 private=serialization.load_pem_private_key(KEY.read_bytes(),None);replacement={p['id']:p for p in read(O/'packages.json')};allowed=[]
 for rel in FILES[:6]:
  raw=(O/'before'/rel).read_bytes();a=verify(json.loads(raw),key());b=copy.deepcopy(a)
  if rel in ['feed/v2/beta.json','feed/v3/beta.json']:
   assert next(p for p in a['packages']if p['id']=='pure-fixes-data')['version']=='0.5.0-beta.6'
   b['packages']=[copy.deepcopy(replacement.get(p['id'],p))for p in a['packages']]
   for g in b['modGuides']:
    if g['id']in['vanilla','immortals']:
     g['patchGuide']['version']=VERSION;g['patchGuide']['entries'].insert(0,dict(id='pure-capture-hud-beta7',category='always',titleRu='Владельцы построек и верхние кнопки',titleEn='Building ownership and top buttons',bodyRu=BODIES['ru'],bodyEn=BODIES['en']))
   b['changelog']=[note()]+a['changelog'];b['newsTitle']=note()['title'];b['newsBody']=BODIES;b['publishedAt']=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
   for k in ['launcher','game','modGames','patchGuide']:assert a[k]==b[k]
   assert[p for p in b['packages']if p['id']not in replacement]==[p for p in a['packages']if p['id']not in replacement]
   write(O/'signed'/rel,sign(b,private));allowed.append(rel)
  else:
   p=O/'signed'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
 h=read(O/'before/feed/changelog.history.json');assert not any(x.get('version')==VERSION and x.get('mods')==['vanilla','immortals']for x in h['beta']);h['beta'].insert(0,note());write(O/'signed/feed/changelog.history.json',h);allowed.append('feed/changelog.history.json')
 p=O/'signed/feed/patch-guide-beta.json';p.write_bytes((O/'before/feed/patch-guide-beta.json').read_bytes());write(O/'scope.json',dict(allowed=allowed))
 for channel in ['stable','beta']:
  f=verify(read(O/'signed'/f'feed/v3/{channel}.json'),key())
  for q in f['packages']:
   if channel=='beta'and q['id']in replacement:q['urls']=[read(O/'package-audit.json')[q['id']]['path']]
  write(O/'local-feeds'/f'{channel}.json',sign(f,private))
 (O/'public.pem').write_text(read(S/'src/PawsPatchLauncher/launcher.config.json')['publicKeyPem']);write(O/'release.json',note());(O/'release-notes.md').write_text('\n\n'.join(note()['title'][k]+'\n\n'+BODIES[k]for k in BODIES)+'\n',encoding='utf-8');print('PURE_BETA7_CATALOGS_SIGNED')
if __name__=='__main__':snapshot();catalogs()
