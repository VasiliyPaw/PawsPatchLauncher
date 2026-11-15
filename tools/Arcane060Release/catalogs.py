from release_context import *
from datetime import datetime,timezone
from cryptography.hazmat.primitives import serialization
BODIES={
'ru':'- Добавлены дороги и мосты всех рас; боты строят и используют переправы.\n- Мосты получили расовые леса и эффекты строительства по всей длине.\n- Добавлены выбор формы карты и количества рек, плавные переходы суши и дна.\n- Полный цикл времени суток длится 24 минуты.\n- Обновлены интерфейсы рас, значки и мини-карта.\n- Ускорена загрузка игры, улучшена реакция ополчения и осадных отрядов.\n- Сохранены исправления оптимизации и воздушной разведки из предыдущей беты.',
'en':'- Added roads and bridges for every race; bots build and use crossings.\n- Bridges use racial scaffolding and construction effects across their full length.\n- Added map shapes, river counts and smooth land and water-floor transitions.\n- A full time-of-day cycle lasts 24 minutes.\n- Updated racial interfaces, icons and the minimap.\n- Faster game startup and improved militia and siege responses.\n- Includes the previous beta’s optimization and aerial scout fixes.',
'uk':'- Додано дороги й мости всіх рас; боти будують і використовують переправи.\n- Мости отримали расові риштування й ефекти будівництва по всій довжині.\n- Додано вибір форми мапи й кількості річок, плавні переходи суші та дна.\n- Повний цикл часу доби триває 24 хвилини.\n- Оновлено інтерфейси рас, значки й мінімапу.\n- Прискорено запуск гри, поліпшено реакцію ополчення й облогових загонів.\n- Збережено виправлення оптимізації та повітряних розвідників із попередньої бети.',
'cs':'- Přidány cesty a mosty všech ras; boti stavějí a používají přechody.\n- Mosty mají rasová lešení a stavební efekty po celé délce.\n- Přidána volba tvaru mapy a počtu řek, plynulé přechody souše a dna.\n- Celý cyklus denní doby trvá 24 minut.\n- Aktualizována rasová rozhraní, ikony a minimapa.\n- Rychlejší spouštění hry a lepší reakce milice a obléhacích jednotek.\n- Zachovány opravy optimalizace a leteckých průzkumníků z předchozí bety.',
'de':'- Straßen und Brücken für alle Völker hinzugefügt; Bots bauen und nutzen Übergänge.\n- Brücken erhalten volksspezifische Gerüste und Baueffekte über die gesamte Länge.\n- Kartenformen, Flussanzahl und weiche Übergänge von Land und Gewässerböden hinzugefügt.\n- Ein vollständiger Tageszeitenzyklus dauert 24 Minuten.\n- Benutzeroberflächen der Völker, Symbole und Minikarte aktualisiert.\n- Schnellerer Spielstart und bessere Reaktionen von Miliz und Belagerungseinheiten.\n- Enthält die Optimierungs- und Luftaufklärer-Korrekturen der vorherigen Beta.',
'fr':'- Ajout de routes et de ponts pour toutes les races ; les bots construisent et utilisent les passages.\n- Les ponts disposent des échafaudages et effets de construction propres à chaque race sur toute leur longueur.\n- Ajout du choix de la forme de carte, du nombre de rivières et de transitions douces des terres et des fonds aquatiques.\n- Un cycle complet des heures de la journée dure 24 minutes.\n- Interfaces des races, icônes et mini-carte mises à jour.\n- Démarrage plus rapide et meilleure réaction des milices et unités de siège.\n- Inclut les corrections d’optimisation et des éclaireurs aériens de la bêta précédente.'}
FILES=[f'feed/{p}{c}.json'for p in ['v3/','v2/','']for c in ['stable','beta']]+['feed/changelog.history.json','feed/patch-guide-beta.json']
def note():return dict(category='patch',mods=['arcane-wars'],channel='beta',version=VERSION,publishedAt='2026-11-15',title={k:'Paw’s Patch '+VERSION+' — Arcane Wars'for k in BODIES},body=BODIES)
def baseline():
 run(['git','fetch','--no-tags','origin','main']);head=run(['git','rev-parse','FETCH_HEAD']).strip()
 for rel in FILES:
  dest=O/'before'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(subprocess.check_output(['git','show',head+':'+rel],cwd=REPO))
 write(O/'catalog-baseline.json',dict(publicHead=head,files={rel:sha(O/'before'/rel)for rel in FILES}));print('BASELINE',head,flush=True)
def catalogs():
 private=serialization.load_pem_private_key(KEY.read_bytes(),None);assert private.public_key().public_numbers()==key().public_numbers()
 replacements={q['id']:q for q in read(O/'packages.json')};allowed=[]
 for rel in FILES[:6]:
  raw=(O/'before'/rel).read_bytes();a=verify(json.loads(raw),key());b=copy.deepcopy(a)
  if rel in ['feed/v2/beta.json','feed/v3/beta.json']:
   assert next(p for p in a['packages']if p['id']=='pawpatch-core')['version']in ['0.5.1-beta.5',VERSION]
   b['packages']=[copy.deepcopy(replacements.get(p['id'],p))for p in a['packages']]+[copy.deepcopy(p)for pid,p in replacements.items()if pid not in {r['id']for r in a['packages']}]
   b['patchGuide']['version']=VERSION
   b['patchGuide']['entries']=[e for e in b['patchGuide']['entries']if e['id']!='arcane-world-060']
   b['patchGuide']['entries'].insert(0,dict(id='arcane-world-060',category='always',titleRu='Дороги, мосты и живой мир',titleEn='Roads, bridges and a living world',bodyRu=BODIES['ru']+'\nПервое обновление загрузит около 2 ГБ текстур.',bodyEn=BODIES['en']+'\nThe first update downloads about 2 GB of textures.'))
   b['changelog']=[note()]+[n for n in a['changelog']if not(n.get('version')==VERSION and n.get('mods')==['arcane-wars'])];b['newsTitle']=note()['title'];b['newsBody']=BODIES;b['publishedAt']=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
   for k in ['launcher','game','modGames','modGuides']:assert b[k]==a[k]
   assert [p for p in b['packages']if p['id']not in replacements]==[p for p in a['packages']if p['id']not in replacements]
   dest=O/'signed'/rel;write(dest,sign(b,private));allowed.append(rel)
  else:
   dest=O/'signed'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
 h=read(O/'before/feed/changelog.history.json');h['beta']=[note()]+[n for n in h['beta']if not(n.get('version')==VERSION and n.get('mods')==['arcane-wars'])];write(O/'signed/feed/changelog.history.json',h)
 write(O/'signed/feed/patch-guide-beta.json',verify(read(O/'signed/feed/v3/beta.json'),key())['patchGuide']);allowed+=['feed/changelog.history.json','feed/patch-guide-beta.json'];write(O/'scope.json',dict(allowed=allowed))
 for channel in ['stable','beta']:
  f=verify(read(O/'signed/feed/v3'/f'{channel}.json'),key())
  if channel=='beta':
   for q in f['packages']:
    if q['id']in replacements:q['urls']=[read(O/'package-audit.json')[q['id']]['path']]
  write(O/'local-feeds'/f'{channel}.json',sign(f,private))
 (O/'public.pem').write_text(read(S/'src/PawsPatchLauncher/launcher.config.json')['publicKeyPem'])
 write(O/'release.json',note());(O/'release-notes.md').write_text('\n\n'.join(note()['title'][k]+'\n\n'+BODIES[k]for k in BODIES)+'\n\nInstall using Paw’s Launcher: Beta → Arcane Wars → Apply → Play. Initial texture download: about 2 GB.\n',encoding='utf-8')
 print('SIGNED_CATALOGS_READY',flush=True)
if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='baseline':baseline()
 else:catalogs()
