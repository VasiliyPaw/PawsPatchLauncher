"""Promote only accepted Arcane beta payloads; never upload or alter a game."""
import copy,hashlib,json,sys,zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];OUT=REPO/'outputs/arcane-051-release-20261109';STAGE=OUT/'stable'
sys.path.insert(0,str(REPO/'tools'))
from PrepareRelease081 import key,sign,fetch
from PrepareRelease070 import verify,encode,validate_package,sha
KEY=Path('G:/CodexData/projects/Codex/2026-08-11/kohan-ii-d-steamlibrary-steamapps-common/work/PawsPatchLauncher/.local/signing/pawpatch-signing-private.pem')
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(encode(o))
def arcane(p):return p.get('mods')==['arcane-wars']
def main():
 assert not (STAGE/'preparation.json').exists()
 before={c:read(OUT/'before/feed/v3'/f'{c}.payload.json') for c in ['stable','beta']}
 rows=read(STAGE/'helpers/build-report.json');assert len(rows)==8
 assert all(r['features']['patchVersion']=='0.5.0' and r['features']['hotJoinRevision']==0 and not r['features']['legacySaveLobbyRecovery'] and len(r['selfTests'])==5 for r in rows.values())
 stable={p['id']:p for p in before['stable']['packages']};wanted=[p for p in before['beta']['packages'] if arcane(p) and (p!=stable.get(p['id']) or p['id']in ['pawpatch-core','common-ui','player-colors','desync-continue'])]
 downloads=STAGE/'accepted-assets';downloads.mkdir(exist_ok=True)
 def download(p):
  assert p['urls'],p['id'];dest=downloads/(p['id']+'-'+p['version']+'.zip')
  if not dest.exists():dest.write_bytes(fetch(p['urls'][0]))
  validate_package(dest,p);return p['id'],dest
 with ThreadPoolExecutor(max_workers=4) as pool:resolved=dict(pool.map(download,wanted))
 replacements={};assets=[];scope={};seen=set()
 for p in wanted:
  with zipfile.ZipFile(resolved[p['id']]) as z:
   module=json.loads(z.read('module.json'));assert not module.get('remove');original={f['path']:z.read('payload/'+f['path']) for f in module['files']}
  payload=dict(original)
  for n in payload:
   leaf=Path(n).name
   if leaf in rows or leaf=='paws_patch_versions.ini':
    payload[n]=(STAGE/'helpers'/leaf).read_bytes()
    if leaf in rows:seen.add(leaf);assert sha(STAGE/'helpers'/leaf)==rows[leaf]['sha256']
  changed=[n for n in payload if payload[n]!=original[n]];assert all(Path(n).name in rows or Path(n).name=='paws_patch_versions.ini' for n in changed)
  module.update(version='0.5.0',files=[dict(path=n,size=len(b),sha256=hashlib.sha256(b).hexdigest().upper()) for n,b in sorted(payload.items())])
  dest=STAGE/'assets'/(p['id']+'-0.5.0.zip');dest.parent.mkdir(exist_ok=True)
  with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
   for n,b in [('module.json',encode(module))]+[('payload/'+n,b) for n,b in sorted(payload.items())]:
    i=zipfile.ZipInfo(n,(2026,11,9,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=0o100644<<16;z.writestr(i,b)
  q=copy.deepcopy(p);q.update(version='0.5.0',experimental=False,size=dest.stat().st_size,sha256=sha(dest),urls=['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/patch-0.5.0/'+dest.name])
  validate_package(dest,q);replacements[q['id']]=q;assets.append(dict(id=q['id'],path=str(dest),size=q['size'],sha256=q['sha256'],url=q['urls'][0]))
  scope[q['id']]=dict(betaVersion=p['version'],betaSha256=p['sha256'],changedPayload=changed,preservedFiles=len(payload)-len(changed))
 assert seen==set(rows)
 guide=copy.deepcopy(before['beta']['patchGuide']);guide['version']='0.5.0'
 for e in guide['entries']:
  if e['category']=='beta':e['category']='always'
  if e['id']=='base':
   for field in ['bodyRu','bodyEn']:e[field]=e[field].replace('Paw’s Patch 0.4.0','Paw’s Patch 0.5.0')
 note=read(REPO/'docs/release-patch-0.5.0.json');assert set(note['body'])=={'ru','en','de','fr','cs','uk'} and all(all(s.startswith('- ') for s in text.splitlines()) for text in note['body'].values())
 private=serialization.load_pem_private_key(KEY.read_bytes(),None);assert private.public_key().public_numbers()==key().public_numbers()
 for prefix in ['v3','v2']:
  rel=f'feed/{prefix}/stable.json';old=verify(read(OUT/'before'/rel),key());beta=verify(read(OUT/'before'/f'feed/{prefix}/beta.json'),key());after=copy.deepcopy(old)
  target={p['id']:replacements.get(p['id'],copy.deepcopy(p)) for p in beta['packages'] if arcane(p)}
  after['packages']=[target[p['id']] if arcane(p) else p for p in old['packages']];known={p['id'] for p in after['packages']};after['packages'] += [p for i,p in target.items() if i not in known]
  after.update(patchGuide=guide,publishedAt=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),changelog=[note]+old['changelog'],newsTitle=note['title'],newsBody=note['body'])
  assert [p for p in after['packages'] if not arcane(p)]==[p for p in old['packages'] if not arcane(p)]
  assert after['launcher']==old['launcher'] and after.get('modGuides')==old.get('modGuides')
  assert all(not p.get('experimental') and 'beta' not in p['version'] for p in after['packages'] if arcane(p))
  write(STAGE/'signed'/rel,sign(after,private));local=copy.deepcopy(after)
  for p in local['packages']:
   if p['id'] in resolved and arcane(p):p['urls']=[str(STAGE/'assets'/(p['id']+'-0.5.0.zip'))]
  write(STAGE/'local-feeds'/f'{prefix}-stable.json',sign(local,private))
 history=read(OUT/'before/feed/changelog.history.json');history['stable']=[note]+history['stable'];write(STAGE/'signed/feed/changelog.history.json',history);write(STAGE/'signed/feed/patch-guide.json',guide)
 (STAGE/'notes.md').write_text('\n\n'.join(note['title'][c]+'\n\n'+note['body'][c] for c in ['ru','en','de','fr','cs','uk'])+'\n',encoding='utf-8')
 write(STAGE/'preparation.json',dict(version='0.5.0',baselineCommit=read(OUT/'baseline.json')['publicHead'],assets=assets,scope=scope,helperVariants=len(rows),selfTests=40,unchanged=['beta catalogs','Pure/Immortals packages and guides','legacy catalogs','launcher'],installedGameModified=False))
 print('STABLE_PREPARED',len(assets),'archives; accepted beta payloads preserved; eight helpers;40 self-tests',flush=True)
if __name__=='__main__':main()
