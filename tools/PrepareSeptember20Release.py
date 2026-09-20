"""Stage stable 0.3.3 and beta 0.4.0; no game launches or installed-game writes.

Stable inherits the published beta payload. New experimental changes are added
only to the next beta. Launcher advertisement is finalized after CI publication.
"""
import argparse,copy,hashlib,importlib.util,json,shutil,subprocess,zipfile
from datetime import datetime,timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from PrepareRelease081 import FEEDS,RAW,API,key,normalize,fetch,sign
from PrepareRelease070 import read,write,encode,sha,verify,validate_package
from GameplayPresentationData import apply_modules,AMBIENT,MAELSTROM,SLAANRI_ENCLAVE

REPO=Path(__file__).resolve().parents[1]
STABLE='0.3.3'; BETA='0.4.0-beta.1'; LAUNCHER='0.8.6'
DOWNLOAD='https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/'
VARIANTS=read(REPO/'game/beta7/variants.json')
def digest(b):return hashlib.sha256(b).hexdigest().upper()
def contents(path,p):
 validate_package(path,p)
 with zipfile.ZipFile(path) as z:
  m=json.loads(z.read('module.json'));assert not m.get('remove')
  return {f['path'].replace('\\','/').lower():z.read('payload/'+f['path'].replace('\\','/')) for f in m['files']}
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def versions(channel):
 return {'pawpatch-core':STABLE,'player-colors':STABLE,'common-ui':'1.3.72-ui.12','desync-continue':'1.3.72-r8','powers-shards-original':'1.3.72-powers.3',**{'localization-'+c:'1.0.2' for c in ['de','fr','cs','uk']}} if channel=='stable' else {}
def notes(group):
 d=read(REPO/'docs/release-20260920.json')[group];version={'stable':STABLE,'beta':BETA,'launcher':LAUNCHER}[group]
 return dict(category='launcher' if group=='launcher' else 'patch',version=version,publishedAt='2026-09-20',
             **({} if group=='launcher' else dict(mods=['arcane-wars'],channel=group)),title=d['title'],body=d['body'])
def feature(helper):
 return json.loads(subprocess.check_output([str(helper),'--features'],text=True,creationflags=subprocess.CREATE_NO_WINDOW))
def baseline():
 head=json.loads(fetch(API+'/git/ref/heads/main'))['object']['sha']
 for name in [*FEEDS.values(),'feed/changelog.history.json','feed/patch-guide-beta.json']:
  assert normalize(fetch(RAW.replace('/main/','/'+head+'/')+name))==normalize((REPO/name).read_bytes()),'Public baseline changed: '+name
 return head
def emit(out,channel,p,files,version,assets):
 p=copy.deepcopy(p);p['version']=version;p['experimental']=channel=='beta'
 manifest=dict(id=p['id'],version=version,files=[dict(path=n,size=len(b),sha256=digest(b)) for n,b in sorted(files.items())],remove=[])
 tag='patch-'+(STABLE if channel=='stable' else BETA)
 path=out/'assets'/tag/(p['id']+'-'+version+'.zip');path.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for n,b in [('module.json',encode(manifest))]+[('payload/'+n,b) for n,b in sorted(files.items())]:
   i=zipfile.ZipInfo(n,(2026,9,20,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=0o100644<<16;z.writestr(i,b)
 p.update(size=path.stat().st_size,sha256=sha(path),urls=[DOWNLOAD+tag+'/'+path.name]);validate_package(path,p)
 assets.append(dict(channel=channel,tag=tag,id=p['id'],path=str(path),size=p['size'],sha256=p['sha256'],url=p['urls'][0]));return p
def prepare(a):
 out=a.out.resolve();assert not (out/'preparation.json').exists();out.mkdir(parents=True,exist_ok=True)
 head=baseline();before={c:verify(read(REPO/p),key()) for c,p in FEEDS.items()};beta=before['beta']
 assert beta['patchGuide']['version']=='0.3.2-beta.2' and before['stable']['patchGuide']['version']=='0.3.1'
 assert beta['playerColorCount']==39
 private=serialization.load_pem_private_key((a.signing_dir/'pawpatch-signing-private.pem').read_bytes(),None)
 assert private.public_key().public_numbers()==key().public_numbers()
 for c,p in FEEDS.items():dest=out/'previous'/(c+'.json');dest.parent.mkdir(exist_ok=True);shutil.copyfile(REPO/p,dest)
 packages={p['id']:p for p in beta['packages']};original={}
 for archive in sorted((a.stage/'baseline').glob('*.zip')):
  original[archive.stem]=contents(archive,packages[archive.stem])
 stable_ids=set(versions('stable'))
 assert stable_ids=={p['id'] for p in beta['packages'] if p.get('mods')==['arcane-wars'] and p!=next((q for q in before['stable']['packages'] if q['id']==p['id']),None)}
 expected=read(a.prior_features);features={};assets=[];scope={};feeds={}
 for channel,version in [('stable',STABLE),('beta',BETA)]:
  helpers=a.stage/(channel+'-helpers');features[channel]={}
  for name,flags in VARIANTS.items():
   f=feature(helpers/name);assert f['patchVersion']==version
   old=copy.deepcopy(expected[name]['features']);old['patchVersion']=version
   if channel=='stable':assert f==old,(name,f,old)
   else:
    assert all(f[k]==v for k,v in old.items()),'Lost historical helper feature'
    for k,v in dict(aiPolicyRevision=5,aiImprovementsSelectable=True,bulkBotLobbyRevision=1,exhaustionRecoveryRevision=1,fractionalKingdomPointsRevision=1,builtInGraphicsDiagnosticsRevision=1,settlementBuildingSlotsRevision=2,allyEconomyRevision=2).items():assert f[k]==v,(name,k)
   features[channel][name]=dict(sha256=sha(helpers/name),features=f)
  feed=copy.deepcopy(before[channel]);files={i:dict(v) for i,v in original.items()};extra={}
  if channel=='beta':
   index=read(a.rwd_index);stock={}
   with (a.game/'Data.rwd').open('rb') as f:
    for name in ['Units/Ambient/lake_fish.tgi','UI/Menus/staging.tgi']:
     row=index[name];f.seek(row['offset']);stock['data/'+name.lower()]=f.read(row['size']);assert len(stock['data/'+name.lower()])==row['size']
   apply_modules(files,stock)
   for i in files:
    if i.startswith('pawpatch-data'):
     for path in AMBIENT|{SLAANRI_ENCLAVE}:files[i][path]=files['pawpatch-core'][path]
   ai=REPO/'game/ai-policy/data';ai_files={}
   for row in read(ai/'manifest.json'):
    path=row['path'].lower();prior=files['pawpatch-core'].get(path,files['arcane-wars'].get(path))
    assert prior is not None and digest(prior).lower()==row['before'],('AI baseline mismatch',path)
    blob=(ai/row['path']).read_bytes();assert digest(blob).lower()==row['after'];ai_files[path]=blob
   files['ai-improvements']=ai_files
   extra['ai-improvements']=dict(id='ai-improvements',priority=950,required=False,executableIndependent=False,mods=['arcane-wars'],dependsOn=['pawpatch-core','common-ui'],name=dict(ru='Улучшения ботов',en='AI improvements'),description=dict(ru='Новые параметры и исправления поведения ботов.',en='New AI parameters and behavior fixes.'))
   ui=module('bulk_ui',REPO/'game/bot-lobby/prepare_ui.py')
   compact=original['player-colors']['data/ui/menus/pcolors.tgi'];normal=stock['data/ui/menus/staging.tgi']
   for lang in ui.TEXT:
    pair={f'data/ui/menus/{n}.tgi':ui.transform(b,lang) for n,b in [('pcolors',compact),('staging',normal)]}
    if lang=='en':files['common-ui'].update(pair);files['player-colors']['data/ui/menus/pcolors.tgi']=pair['data/ui/menus/pcolors.tgi']
    else:
     i='localization-bot-ui-'+lang;files[i]=pair
     extra[i]=dict(id=i,priority=1000,required=False,executableIndependent=False,mods=['arcane-wars'],dependsOn=['common-ui'],name=dict(ru='Настройки ботов: '+lang,en='Bot setup: '+lang),description=dict(ru='Перевод общих настроек ботов.',en='Translated shared bot setup.'))
  copies=[]
  for i,payload in files.items():
   if channel=='stable' and i not in stable_ids:continue
   for n in list(payload):
    if n in VARIANTS or n=='paws_patch_versions.ini':
     payload[n]=(helpers/n).read_bytes()
     if n in VARIANTS:copies.append(n)
  assert len(copies)==11 and set(copies)==set(VARIANTS)
  replacements={}
  for i,payload in files.items():
   if (channel=='stable' and i in stable_ids) or (channel=='beta' and payload!=original.get(i)):
    changed=[p for p in payload if payload[p]!=original.get(i,{}).get(p)]
    if channel=='stable':assert all(p in VARIANTS or p=='paws_patch_versions.ini' for p in changed)
    replacements[i]=emit(out,channel,packages.get(i,extra.get(i)),payload,versions(channel).get(i,version),assets)
    scope[channel+':'+i]=dict(changed=changed,preservedFiles=len(payload)-len(changed),baselineSha256=packages.get(i,{}).get('sha256'))
  feed['packages']=[replacements.get(p['id'],p) for p in feed['packages']]+[p for i,p in replacements.items() if i in extra]
  # All unrelated mods retain their original package references and documentation.
  assert [p for p in feed['packages'] if p.get('mods')!=['arcane-wars']]==[p for p in before[channel]['packages'] if p.get('mods')!=['arcane-wars']]
  guide=copy.deepcopy(beta['patchGuide']);guide['version']=version
  if channel=='stable':
   for e in guide['entries']:
    if e['category']=='beta':e['category']='optional' if e['id']=='colors' else 'always'
  else:
   additions=read(REPO/'docs/release-20260920.json')['guide']
   guide['entries']=[e for e in guide['entries'] if e['id'] not in {x['id'] for x in additions}]+additions
  feed.update(patchGuide=guide,playerColorCount=39,publishedAt=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),changelog=[notes(channel)]+feed['changelog'])
  feeds[channel]=feed
  write(out/'signed'/(channel+'.json'),sign(feed,private));local=copy.deepcopy(feed)
  for p in local['packages']:
   own=next((x for x in assets if x['id']==p['id'] and x['channel']==channel),None)
   if own:p['urls']=[own['path']]
   elif p['id'] in original:p['urls']=[str((a.stage/'baseline'/(p['id']+'.zip')).resolve())] if packages[p['id']]['sha256']==p['sha256'] else p['urls']
  write(out/'test-feeds'/(channel+'.json'),sign(local,private))
 write(out/'features.json',features);write(out/'scope.json',scope)
 write(out/'preparation.json',dict(baselineCommit=head,assets=assets,before={c:sha(REPO/p) for c,p in FEEDS.items()},historyBefore=sha(REPO/'feed/changelog.history.json'),guideBefore=sha(REPO/'feed/patch-guide-beta.json')))
 print('STAGED',len(assets),'packages; game was not launched')
def finalize(a):
 out=a.out;prep=read(out/'preparation.json');private=serialization.load_pem_private_key((a.signing_dir/'pawpatch-signing-private.pem').read_bytes(),None)
 artifact=read(a.launcher.parent/'launcher-artifact.json');assert artifact['version']==LAUNCHER and artifact['sourceCommit']==a.commit
 exe=next(x for x in artifact['files'] if x['name']=='PawsPatchLauncher.exe');assert sha(a.launcher)==exe['sha256'] and a.launcher.stat().st_size==exe['size']
 for c,p in FEEDS.items():assert sha(REPO/p)==prep['before'][c]
 history=read(REPO/'feed/changelog.history.json');assert sha(REPO/'feed/changelog.history.json')==prep['historyBefore']
 for c,p in FEEDS.items():
  f=verify(read(out/'signed'/(c+'.json') if c in ['stable','beta'] else REPO/p),key())
  f['launcher']=dict(version=LAUNCHER,size=exe['size'],sha256=exe['sha256'],urls=[DOWNLOAD+'v'+LAUNCHER+'/PawsPatchLauncher.exe'])
  f.update(changelog=[notes('launcher')]+f['changelog'],newsTitle=notes('launcher')['title'],newsBody=notes('launcher')['body'])
  write(out/'final'/(c+'.json'),sign(f,private))
  if c in history:history[c]=f['changelog']
 write(out/'final/changelog.history.json',history)
 write(out/'final/patch-guide-beta.json',verify(read(out/'final/beta.json'),key())['patchGuide'])
 write(out/'finalization.json',dict(sourceCommit=a.commit,launcher=exe))
 print('FINALIZED four signed catalogs')
def promote(a):
 out=a.out;prep=read(out/'preparation.json');fin=read(out/'finalization.json')
 assert read(a.stage/'installation-verification.json')['passed'];assert read(out/'public-verification.json')['passed']
 for c,p in FEEDS.items():assert sha(REPO/p)==prep['before'][c]
 assert sha(REPO/'feed/changelog.history.json')==prep['historyBefore']
 for c,p in FEEDS.items():verify(read(out/'final'/(c+'.json')),key());shutil.copyfile(out/'final'/(c+'.json'),REPO/p)
 for n in ['changelog.history.json','patch-guide-beta.json']:shutil.copyfile(out/'final'/n,REPO/'feed'/n)
 print('PROMOTED stable 0.3.3, beta 0.4.0-beta.1 and launcher 0.8.6')
def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--signing-dir',type=Path);p.add_argument('--game',type=Path);p.add_argument('--rwd-index',type=Path);p.add_argument('--prior-features',type=Path);p.add_argument('--launcher',type=Path);p.add_argument('--commit');p.add_argument('--finalize',action='store_true');p.add_argument('--promote',action='store_true');a=p.parse_args();a.stage=a.stage.resolve();a.out=a.stage/'publication'
 if a.promote:promote(a)
 elif a.finalize:finalize(a)
 else:prepare(a)
if __name__=='__main__':main()
