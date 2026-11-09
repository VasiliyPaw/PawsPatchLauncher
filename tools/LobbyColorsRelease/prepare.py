"""Snapshot public inputs, compose minimal immutable archives and signed candidates."""
import argparse,configparser,zipfile
from datetime import datetime,timezone
from cryptography.hazmat.primitives import serialization
from context import *
BODIES={
 'ru':'- Исправлено перепутывание цветов игроков в новом лобби после матча.',
 'en':'- Fixed players receiving each other’s colors in a new lobby after a match.',
 'de':'- Falsche Spielerfarben in einer neuen Lobby nach einer Partie behoben.',
 'fr':'- Correction de l’échange des couleurs des joueurs dans un nouveau salon après une partie.',
 'cs':'- Opraveno zaměňování barev hráčů v nové místnosti po zápase.',
 'uk':'- Виправлено переплутування кольорів гравців у новому лобі після матчу.'}

def note(kind):
 modes=['arcane-wars']if kind=='arcane'else['vanilla','immortals']
 title='Paw’s Patch '+VERSIONS[kind]+' — '+('Arcane Wars'if kind=='arcane'else'Vanilla / Immortals')
 return dict(category='patch',mods=modes,channel='beta',version=VERSIONS[kind],publishedAt='2026-11-09',title={k:title for k in BODIES},body=BODIES)

def baseline():
 OUT.mkdir(exist_ok=True);head=git('ls-remote','origin','refs/heads/main').split()[0];assert head==git('rev-parse','HEAD')
 if (OUT/'baseline.json').exists():assert read(OUT/'baseline.json')['publicHead']==head
 files=FEEDS+['feed/changelog.history.json','feed/patch-guide-beta.json'];hashes={}
 for rel in files:
  data=fetch(RAW.replace('/main/','/'+head+'/')+rel);assert normalize(data)==normalize((REPO/rel).read_bytes()),rel
  if rel in FEEDS:verify(json.loads(data),key())
  p=OUT/'before'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);hashes[rel]=sha(p)
 write(OUT/'baseline.json',dict(publicHead=head,files=hashes))
 (OUT/'staged-before.patch').write_bytes(subprocess.check_output(['git','diff','--cached','--binary'],cwd=REPO))
 (OUT/'dirty-before.txt').write_text(git('status','--porcelain=v1'))
 for kind in VERSIONS:
  n=note(kind);write(REPO/('docs/release-'+('patch-'if kind=='arcane'else'pure-')+VERSIONS[kind]+'.json'),n)
  (OUT/(kind+'-notes.md')).write_text('\n\n'.join(n['title'][k]+'\n\n'+n['body'][k] for k in BODIES)+'\n',encoding='utf-8')
 # Preserve and verify the actual public Pure palette, independent of old notes.
 f=verify(read(OUT/'before/feed/v3/beta.json'),key());p=next(p for p in f['packages']if p['id']=='pure-player-colors')
 archive=OUT/'pure-player-colors-baseline.zip';archive.write_bytes(fetch(p['urls'][0]));validate_package(archive,p)
 with zipfile.ZipFile(archive)as z:
  raw=z.read('payload/paws_player_colors.ini');(OUT/'pure-palette.ini').write_bytes(raw)
 c=configparser.ConfigParser();c.read(OUT/'pure-palette.ini',encoding='utf-8-sig');assert len(c.sections())==39
 print('PUBLIC_BASELINE_SNAPSHOTTED',head,flush=True)

def build():
 for kind,base in [('arcane',Path('C:/PawsArcane051ReleaseQA-20261109/helpers-r3')),('pure',REPO/'outputs/pure-050-optimizations-20261109/helpers-r1')]:
  args=[PYTHON,REPO/'game/lobby-colors/build_lifetime_candidate.py','--helpers',base,'--native','F:/PawsLobbyColorsQA-20261109/final-native','--loader',REPO/'game/beta7/LobbyColorsNative.cs','--patch-version',VERSIONS[kind],'--out',OUT/(kind+'-helpers')]
  if kind=='pure':args+=['--runtime-version',RUNTIME,'--assembly-version','1.3.72.19','--palette',OUT/'pure-palette.ini']
  print(run(args,OUT/(kind+'-build.log')),flush=True)

def archives():
 f=verify(read(OUT/'before/feed/v3/beta.json'),key());packages=[];audit={}
 ids={'pawpatch-core','player-colors','desync-continue','common-ui','pure-fixes-runtime','pure-fixes-data'}
 for p in f['packages']:
  if p['id']not in ids:continue
  kind='pure'if p['id'].startswith('pure-')else'arcane';version=RUNTIME if p['id']=='pure-fixes-runtime'else VERSIONS[kind]
  source=REPO/('outputs/pure-050-optimizations-20261109/stage-r3/assets'if kind=='pure'else'outputs/arcane-051-release-20261109/beta-r2/assets')/p['urls'][-1].rsplit('/',1)[1]
  validate_package(source,p)
  # Confirm public bytes of the baseline package before reusing local inputs.
  public=fetch(p['urls'][0]);assert hashlib.sha256(public).hexdigest().upper()==p['sha256'].upper()
  with zipfile.ZipFile(source)as z:
   m=json.loads(z.read('module.json'));before={r['path']:z.read('payload/'+r['path'])for r in m['files']};files=dict(before)
  helpers=OUT/(kind+'-helpers');rows=read(helpers/'build-report.json')
  for path in files:
   leaf=Path(path).name
   if leaf in rows:files[path]=(helpers/leaf).read_bytes()
   if leaf=='paws_patch_versions.ini':files[path]=(helpers/leaf).read_bytes()
  changed=[n for n in files if files[n]!=before[n]]
  assert set(files)==set(before)
  assert all(Path(n).name in set(rows)|{'paws_patch_versions.ini'}for n in changed),changed
  assert changed or p['id']=='pure-fixes-data'
  m.update(version=version,files=[dict(path=n,size=len(b),sha256=hashlib.sha256(b).hexdigest().upper())for n,b in sorted(files.items())])
  dest=OUT/kind/'assets'/(p['id']+'-'+version+'.zip');dest.parent.mkdir(parents=True,exist_ok=True)
  with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
   for n,b in [('module.json',encode(m))]+[('payload/'+n,b)for n,b in sorted(files.items())]:
    item=zipfile.ZipInfo(n,(2026,11,9,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED;z.writestr(item,b)
  q=copy.deepcopy(p);tag=('patch-pure-'if kind=='pure'else'patch-')+VERSIONS[kind]
  q.update(version=version,sha256=sha(dest),size=dest.stat().st_size,urls=['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/'+tag+'/'+dest.name])
  validate_package(dest,q);packages.append(q);audit[p['id']]=dict(source=str(source),sourceSha256=p['sha256'],archive=str(dest),changed=changed,preserved=len(files)-len(changed),kind=kind)
 write(OUT/'packages.json',packages);write(OUT/'package-audit.json',audit)
 print('MINIMAL_ARCHIVES_READY',len(packages),flush=True)

def guide(g,kind):
 g=copy.deepcopy(g);g['version']=VERSIONS[kind]
 g['entries'].insert(0,dict(id='lobby-colors-lifetime',category='always',titleRu='Цвета игроков',titleEn='Player colors',bodyRu=BODIES['ru'],bodyEn=BODIES['en']))
 return g

def catalogs():
 private=serialization.load_pem_private_key(KEY.read_bytes(),None);assert private.public_key().public_numbers()==key().public_numbers()
 replacements={p['id']:p for p in read(OUT/'packages.json')};allowed=[]
 for rel in FEEDS:
  raw=(OUT/'before'/rel).read_bytes();a=verify(json.loads(raw),key());b=copy.deepcopy(a)
  if rel in ['feed/v2/beta.json','feed/v3/beta.json']:
   b['packages']=[copy.deepcopy(replacements.get(p['id'],p))for p in a['packages']]
   b['patchGuide']=guide(a['patchGuide'],'arcane')
   for g in b['modGuides']:
    if g['id']in['vanilla','immortals']:g['patchGuide']=guide(g['patchGuide'],'pure')
   b['changelog']=[note('arcane'),note('pure')]+a['changelog'];b['newsTitle']=note('arcane')['title'];b['newsBody']=BODIES
   b['publishedAt']=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
   assert b['launcher']==a['launcher'] and b['game']==a['game'] and b['modGames']==a['modGames']
   assert [p for p in b['packages']if p['id']not in replacements]==[p for p in a['packages']if p['id']not in replacements]
   write(OUT/'signed'/rel,sign(b,private));allowed.append(rel)
  else:
   target=OUT/'signed'/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
 h=read(OUT/'before/feed/changelog.history.json');h['beta']=[note('arcane'),note('pure')]+h['beta'];write(OUT/'signed/feed/changelog.history.json',h)
 g=verify(read(OUT/'signed/feed/v3/beta.json'),key())['patchGuide'];write(OUT/'signed/feed/patch-guide-beta.json',g)
 allowed+=['feed/changelog.history.json','feed/patch-guide-beta.json']
 write(OUT/'scope.json',dict(allowed=allowed,versions=VERSIONS,preserved=['stable feeds','legacy feeds','launcher','all other package payloads']))
 for channel in ['stable','beta']:
  f=verify(read(OUT/'signed/feed/v3'/f'{channel}.json'),key())
  if channel=='beta':
   for p in f['packages']:
    if p['id']in replacements:p['urls']=[read(OUT/'package-audit.json')[p['id']]['archive']]
  write(OUT/'local-feeds'/f'{channel}.json',sign(f,private))
 (OUT/'public.pem').write_text(read(REPO/'src/PawsPatchLauncher/launcher.config.json')['publicKeyPem'])
 print('BETA_CATALOG_CANDIDATES_SIGNED',flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['baseline','build','archives','catalogs']);a=p.parse_args();globals()[a.action]()
