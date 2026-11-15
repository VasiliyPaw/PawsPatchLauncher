from context import *
from datetime import datetime,timezone
from cryptography.hazmat.primitives import serialization
FILES=[f'feed/{p}{c}.json'for p in ['v3/','v2/','']for c in ['stable','beta']]+['feed/changelog.history.json','feed/patch-guide-beta.json']
BODIES={
'ru':'- Объём загрузки уменьшен примерно с 2,2 ГБ до 1 ГБ.\n- Текстуры переходов суши и дна сжаты без потери качества; повторные изображения больше не занимают лишнее место.',
'en':'- Reduced the download from about 2.2 GB to 1 GB.\n- Land and water-floor transition textures use lossless compression; duplicate images no longer take extra space.',
'uk':'- Обсяг завантаження зменшено приблизно з 2,2 ГБ до 1 ГБ.\n- Текстури переходів суші та дна стиснуто без втрати якості; повторні зображення більше не займають зайвого місця.',
'cs':'- Velikost stahování snížena přibližně z 2,2 GB na 1 GB.\n- Textury přechodů souše a dna jsou bezeztrátově komprimované; duplicitní obrázky již nezabírají další místo.',
'de':'- Downloadgröße von etwa 2,2 GB auf 1 GB reduziert.\n- Texturen der Land- und Gewässerbodenübergänge werden verlustfrei komprimiert; doppelte Bilder belegen keinen zusätzlichen Speicherplatz mehr.',
'fr':'- Taille du téléchargement réduite d’environ 2,2 Go à 1 Go.\n- Les textures des transitions terrestres et des fonds aquatiques sont compressées sans perte ; les images en double n’occupent plus d’espace supplémentaire.'}
REMOVED={f'arcane-biome-textures-{i:02}'for i in range(5,11)}
def note():return dict(category='patch',mods=['arcane-wars'],channel='beta',version=VERSION,publishedAt='2026-11-15',title={k:'Paw’s Patch '+VERSION+' — Arcane Wars'for k in BODIES},body=BODIES)
def snapshot():
 git('fetch','--no-tags','origin','main');head=git('rev-parse','FETCH_HEAD')
 for rel in FILES:
  target=O/'before'/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(subprocess.check_output(['git','show',head+':'+rel],cwd=REPO))
 write(O/'catalog-baseline.json',dict(publicHead=head,files={rel:sha(O/'before'/rel)for rel in FILES}));print('CATALOG_BASELINE',head,flush=True)
def catalogs():
 private=serialization.load_pem_private_key(KEY.read_bytes(),None);assert private.public_key().public_numbers()==key().public_numbers();replacement={p['id']:p for p in read(O/'packages.json')};scope=set(replacement)|REMOVED;allowed=[]
 for rel in FILES[:6]:
  raw=(O/'before'/rel).read_bytes();a=verify(json.loads(raw),key());b=copy.deepcopy(a)
  if rel in ['feed/v2/beta.json','feed/v3/beta.json']:
   assert next(p for p in a['packages']if p['id']=='pawpatch-core')['version']=='0.6.0-beta.1'
   b['packages']=[copy.deepcopy(replacement.get(p['id'],p))for p in a['packages']if p['id']not in REMOVED];assert all(not(set(p['dependsOn'])&REMOVED)for p in b['packages'])
   assert len([p for p in b['packages']if p['id'].startswith('arcane-biome-textures-')])==4
   b['patchGuide']['version']=VERSION
   for e in b['patchGuide']['entries']:
    if e['id']=='arcane-world-060':e['bodyRu']=e['bodyRu'].replace('около 2 ГБ текстур','около 900 МБ текстур');e['bodyEn']=e['bodyEn'].replace('about 2 GB of textures','about 900 MB of textures')
   b['patchGuide']['entries'].insert(0,dict(id='arcane-lossless-060-beta2',category='always',titleRu='Меньше загрузка, прежняя детализация',titleEn='Smaller download, full detail',bodyRu=BODIES['ru'],bodyEn=BODIES['en']))
   b['changelog']=[note()]+a['changelog'];b['newsTitle']=note()['title'];b['newsBody']=BODIES;b['publishedAt']=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
   for k in ['launcher','game','modGames','modGuides']:assert b[k]==a[k]
   assert [p for p in b['packages']if p['id']not in scope]==[p for p in a['packages']if p['id']not in scope]
   write(O/'signed'/rel,sign(b,private));allowed.append(rel)
  else:
   target=O/'signed'/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
 h=read(O/'before/feed/changelog.history.json');h['beta']=[note()]+h['beta'];write(O/'signed/feed/changelog.history.json',h);write(O/'signed/feed/patch-guide-beta.json',verify(read(O/'signed/feed/v3/beta.json'),key())['patchGuide']);allowed+=['feed/changelog.history.json','feed/patch-guide-beta.json'];write(O/'scope.json',dict(allowed=allowed,removedPackages=sorted(REMOVED)))
 for channel in ['stable','beta']:
  f=verify(read(O/'signed'/f'feed/v3/{channel}.json'),key())
  if channel=='beta':
   for p in f['packages']:
    if p['id']in replacement:p['urls']=[read(O/'package-audit.json')[p['id']]['path']]
  write(O/'local-feeds'/f'{channel}.json',sign(f,private))
 (O/'public.pem').write_text(read(S/'src/PawsPatchLauncher/launcher.config.json')['publicKeyPem']);write(O/'release.json',note());(O/'release-notes.md').write_text('\n\n'.join(note()['title'][k]+'\n\n'+BODIES[k]for k in BODIES)+'\n\nPaw’s Launcher: Beta → Arcane Wars → Apply → Play.\n',encoding='utf-8');print('BETA2_CATALOGS_READY',flush=True)
if __name__=='__main__':snapshot()if sys.argv[1:]and sys.argv[1]=='baseline'else catalogs()
