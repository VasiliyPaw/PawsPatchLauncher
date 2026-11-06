"""Prepare the accepted Arcane stable and mixed-biomes beta, in separate stages.
No installed-game writes. Publication/catalog promotion are explicit actions.
Inputs and output directories are recorded; unchanged payloads are retained.
"""
import argparse,base64,colorsys,copy,hashlib,json,re,shutil,subprocess,sys,zipfile
from datetime import datetime,timezone
from pathlib import Path
from PrepareRelease070 import read,write,encode,sha,verify,validate_package
from PrepareRelease081 import fetch,RAW,API,key,sign,normalize
from PrepareSplitLanguages import dec
ROOT=Path(__file__).resolve().parents[1];WS=ROOT.parents[1]
OUT=WS/'outputs/release-042-050-20261106';HERE=ROOT/'game/mixed-biomes'
R2=WS/'outputs/mixed-biomes-r2-20261106'
IDS={'pawpatch-core','player-colors','desync-continue','common-ui','powers-shards-original'}
VERSIONS={'stable':'0.4.2','beta':'0.5.0-beta.1'}
FEEDS=['feed/'+x for x in ('v3/stable.json','v3/beta.json','v2/stable.json','v2/beta.json','stable.json','beta.json')]
LANGUAGES=read(HERE/'localization.json')
def data():
 target=OUT/'overrides';target.mkdir(exist_ok=True)
 fixture=Path('G:/PawMixedBiomesTest-20261106/game')
 for entry in read(R2/'final-manifest.json')['dataOverrides']:
  source=fixture/entry['path'];assert sha(source)==entry['sha256'],source
  p=target/entry['path'].lower();p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,p)
 # TGC TerrainVariation.terrain_color is the minimap color (+34/+38/+3c).
 # Texture paths, water color, rendering, collision and gameplay fields stay intact.
 audit=[]
 definitions=WS/'outputs/mixed-biomes-20261106/definitions/Terrain/Cursed'
 for source in definitions.glob('*.tgi'):
  if any(x in source.stem for x in ('lake','river')):continue
  path=target/'data/terrain/cursed'/source.name.lower()
  original=dec(path.read_bytes() if path.exists() else source.read_bytes()).replace('\r','')
  def tint(m):
   rgb=list(map(float,m.group(2).split(',')));v=max(rgb)
   color=colorsys.hsv_to_rgb(.76,.32,v)
   return m[1]+', '.join(format(c,'.4f') for c in color)
  updated,n=re.subn(r'(?mi)^(\s*terrain_color\s*=\s*)([-.\d]+\s*,\s*[-.\d]+\s*,\s*[-.\d]+)',tint,original)
  if n:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(updated,encoding='utf-16');audit.append(dict(path=str(path.relative_to(target)),variations=n))
 rmc=target/'data/randommap/rmc_temperate03.tgi';t=dec(rmc.read_bytes()).replace('\r','')
 t=t.replace('"Смешанные биомы (тест)"','"#paws_mixed_biomes_name"')
 t=re.sub(r'(?m)^(\s*description\s*=)\s*"Крупные области:[^\n]*',r'\1 "#paws_mixed_biomes_description"',t)
 for label,k in [('Логова','lairs'),('Большие логова','large_lairs'),('Технологии','tech')]:
  t=t.replace('name = "'+label+'"','name = "#paws_mixed_'+k+'_name"')
 assert 'Смешанные биомы (тест)' not in t and '#paws_mixed_biomes_description' in t
 rmc.write_text(t,encoding='utf-16')
 # RMC localized lookups use the game's existing strings_data_K2 table.
 # A standalone new table is not sufficient for locale-depot lookup.
 standalone=target/'data/localization/paws_mixed_biomes.tgi'
 if standalone.exists():standalone.unlink()
 write(OUT/'data-report.json',dict(overrides={str(p.relative_to(target)).replace('\\','/'):sha(p) for p in target.rglob('*') if p.is_file()},tinted=audit,languages=list(LANGUAGES)))
 print('PRODUCTION DATA',len(audit),'cursed minimap files; six languages',flush=True)
def dictionary(code):
 values=LANGUAGES[code];assert set(values)==set(LANGUAGES['en']) and len(values)==5
 lines=['[Text language = default]','{',' ids = Localization/paws_mixed_biomes.tgi',' name = "@Localization/paws_mixed_biomes.tgi"']
 lines += [' '+k+' = '+json.dumps(v,ensure_ascii=False) for k,v in values.items()]
 return ('\r\n'.join(lines+['}'])+'\r\n').encode('utf-16')
def localized_strings(raw,code):
 t=dec(raw).replace('\r','');values=LANGUAGES[code]
 assert not any(re.search(r'(?m)^\s*'+re.escape(k)+r'\s*=',t) for k in values)
 at=t.rfind('}');assert at>=0
 t=t[:at]+''.join('\t'+k+' = '+json.dumps(v,ensure_ascii=False)+'\n' for k,v in values.items())+t[at:]
 return t.encode('utf-16')
def english_table():
 # common-ui is the final English table in the accepted beta installation.
 # Use the same bytes in every overlapping package, independent of tie order.
 with zipfile.ZipFile(OUT/'inputs/common-ui.zip') as z:
  name=next(n for n in z.namelist() if n.lower()=='payload/data/localization/strings_data_k2.tgi')
  return localized_strings(z.read(name),'en')
def team_sort(raw):
 # Locale packages contain translated literal bot-setup labels. Change only
 # this nested list's sorting property, retaining every translated field.
 t=dec(raw).replace('\r','');start=t.index('[TeamFormatDropdown Template=SharedDropDownWidget]');end=t.index('[TeamFormatLabel',start)
 section=t[start:end];assert section.count('[ListBox]')==1
 section=re.sub(r'(?mi)^\s*sorted\s*=\s*\w+\s*\n','\n',section)
 section=section.replace('[ListBox]','[ListBox]\n            sorted = false')
 return (t[:start]+section+t[end:]).encode('utf-16')
def native():
 # Keep the already tested emitter; stop before its private-helper composition.
 source=(HERE/'build.py').read_text();source=source[:source.index('# Reuse the full beta.11 feature composition')]
 source=source.replace("OUT=WS/'outputs/mixed-biomes-r2-20261106'","OUT=WS/'outputs/release-042-050-20261106/geometry'")
 source=source.replace('MixedBiomesTestPatch','MixedBiomesPatch').replace('LOCAL_MIXED_BIOMES r2;','MIXED_BIOMES r1;')
 folder=OUT/'geometry';(folder/'native').mkdir(parents=True,exist_ok=True)
 shutil.copy2(R2/'native/spawn-index.h',folder/'native/spawn-index.h')
 exec(compile(source,str(HERE/'build.py'),'exec'),{'__file__':str(HERE/'build.py')})
 shutil.copy2(folder/'native/MixedBiomesPatch.cs',HERE/'MixedBiomesPayload.cs')
 print('PRODUCTION NATIVE READY',flush=True)
def build():
 previous=read(WS/'outputs/release-morale-20261106/build-report.json')
 rmc_hash=sha(OUT/'overrides/data/randommap/rmc_temperate03.tgi')
 for channel,version in VERSIONS.items():
  folder=OUT/channel/'helpers';sources=folder/'source';sources.mkdir(parents=True,exist_ok=True);report={};written={}
  english_hash=hashlib.sha256(english_table()).hexdigest().upper()
  with zipfile.ZipFile(OUT/'inputs/localization-bot-ui-ru.zip') as z:
   russian_hash=hashlib.sha256(localized_strings(z.read('payload/local_ru/localization/strings_data_k2.tgi'),'ru')).hexdigest().upper()
  for name,row in previous.items():
   arguments=[]
   for arg in row['args']:
    if arg.startswith('/out:'):arg='/out:'+str(folder/name)
    elif arg.lower().endswith('.cs'):
     source=Path(arg);t=source.read_text(encoding='utf-8-sig').replace('0.4.2-beta.11',version)
     if channel=='beta':
      if source.name.endswith('.generated.cs'):
       t,n=re.subn(r'(ExpectedEnglishSha256\s*=\s*)"[A-Fa-f0-9]{64}"',lambda m:m[1]+'"'+english_hash+'"',t);assert n==1
       old_russian=re.search(r'ExpectedRussianSha256\s*=\s*"([A-Fa-f0-9]{64})"',t)[1]
       t,n=re.subn(r'(ExpectedRussianSha256\s*=\s*)"[A-Fa-f0-9]{64}"',lambda m:m[1]+'"'+russian_hash+'"',t);assert n==1
       anchor='VerifyHash(russianPath, ExpectedRussianSha256, "русская локализация семей");';assert anchor in t
       t=t.replace(anchor,'if (!ComputeSha256(russianPath).Equals("'+old_russian+'", StringComparison.OrdinalIgnoreCase)) '+anchor)
      if source.name.endswith('GamePresentation1372.cs'):
       a=t.index('    // BEGIN GENERATED HUD LAYOUT');b=t.index('    // END GENERATED HUD LAYOUT',a)+len('    // END GENERATED HUD LAYOUT')
       t=t[:a]+(OUT/'geometry/hud/HudLayout.generated.txt').read_text().rstrip()+t[b:]
      if source.name.endswith('ReleaseStartup.cs'):
       anchor='                RandomMapPatch.Verify(memory, address, map);';assert anchor in t
       t=t.replace(anchor,anchor+'\n                MixedBiomesPatch.Install(memory,address,log);')
      if source.name.endswith(('ReleaseStartup.cs','RandomMapBundle.cs')):t=t.replace('75C096D8095EA5EDB93D27B06E74F8BBFBB0D557A05D311D0CFCCD4889A3D7AB',rmc_hash)
      if source.name.endswith('BuildFeatures.cs'):
       t=t.replace(' + nightmare + "}");',' + nightmare + ",\\"mixedBiomesRevision\\":1,\\"sharedBiomeSettingsRevision\\":1,\\"minimapBiomeColorsRevision\\":1,\\"largeMapCompanyLimit\\":25}");')
       assert 'mixedBiomesRevision' in t
     dest=sources/source.name
     if source.name in written:assert written[source.name]==t
     else:dest.write_text(t,encoding='utf-8');written[source.name]=t
     arg=str(dest)
    arguments.append(arg)
   if channel=='beta':arguments.append(str(HERE/'MixedBiomesPayload.cs'))
   subprocess.run(arguments,cwd=ROOT,check=True,capture_output=True)
   features=json.loads(subprocess.check_output([str(folder/name),'--features']))
   expected=dict(row['features'],patchVersion=version)
   if channel=='beta':expected.update(mixedBiomesRevision=1,sharedBiomeSettingsRevision=1,minimapBiomeColorsRevision=1,largeMapCompanyLimit=25)
   assert features==expected,(name,features,expected)
   report[name]=dict(sha256=sha(folder/name),features=features,args=arguments,sources={a:sha(Path(a)) for a in arguments if a.lower().endswith('.cs')})
   print('HELPER',channel,name,'PASS',flush=True)
  (folder/'paws_patch_versions.ini').write_text('[Versions]\nArcaneWars=0.82.1.8\nPawPatch='+version+'\n',encoding='utf-8')
  write(OUT/channel/'build-report.json',report)
def baseline(path):return verify(read(OUT/'before'/path),key())
def notes(channel):
 version=VERSIONS[channel]
 if channel=='stable':
  title={'ru':"Paw’s Patch 0.4.2 — стабильный выпуск Arcane Wars",'en':"Paw’s Patch 0.4.2 — stable Arcane Wars release"}
  body={'ru':'Текущая бета Arcane Wars стала стабильной версией 0.4.2. Включены все исправления beta.11, в том числе полное игнорирование нулевой морали при соответствующей настройке без отмены расовых порогов отступления. Смешанные биомы и новые исправления интерфейса выпускаются отдельно в бете 0.5.0.',
        'en':'The current Arcane Wars beta is now stable 0.4.2. Includes all beta.11 fixes, including fully ignoring zero morale when enabled while preserving racial retreat thresholds. Mixed biomes and the new interface fixes are released separately in the 0.5.0 beta.'}
 else:
  title={'ru':"Paw’s Patch 0.5.0 beta 1 — смешанные биомы",'en':"Paw’s Patch 0.5.0 beta 1 — mixed biomes"}
  body={'ru':'Смешанные биомы встроены в основной патч без отдельной галочки. Выбор типа карты сохранён: новый пункт создаёт крупные извилистые области лета, снега, пустыни и проклятых земель. Настройки строений общие; варианты построек соответствуют биому. Проклятая местность на миникарте имеет фиолетовый оттенок. На картах от 1200×1200 потолок рот — 25 при достаточном содержании. Исправлены числовой порядок команд и центровка меню паузы и окон сохранения/загрузки. Новые пункты переведены на все шесть языков игры.',
        'en':'Mixed biomes are built into the core patch without an extra launcher toggle. Map-type selection is retained: the new option creates large irregular regions of temperate land, snow, desert and cursed land. Building settings are shared; buildings match their biome. Cursed terrain is purple-tinted on the minimap. Maps at least 1200×1200 allow up to 25 companies with sufficient support. Team lists now sort numerically; pause and save/load dialogs are centered. New options are translated into all six game languages.'}
 return dict(category='patch',mods=['arcane-wars'],channel=channel,version=version,publishedAt='2026-11-06',title=title,body=body)
def stage(private_key):
 from cryptography.hazmat.primitives import serialization
 pkey=serialization.load_pem_private_key(Path(private_key).read_bytes(),None);assert pkey.public_key().public_numbers()==key().public_numbers()
 assert subprocess.check_output(['git','ls-remote','origin','refs/heads/main'],cwd=ROOT,text=True).split()[0]==read(OUT/'baseline.json')['head'],'Public baseline moved'
 overrides={str(p.relative_to(OUT/'overrides')).replace('\\','/'):p.read_bytes() for p in (OUT/'overrides').rglob('*') if p.is_file()}
 source={p['id']:p for p in baseline('feed/v3/beta.json')['packages']};assets=[];audit={}
 for channel,version in VERSIONS.items():
  folder=OUT/channel;changes={};seen=set();audit[channel]={}
  wanted=IDS | ({p for p in source if p.startswith(('pawpatch-data','localization-bot-ui-'))} if channel=='beta' else set())
  for ident in sorted(wanted):
   original=source[ident];src=OUT/'inputs'/(ident+'.zip');validate_package(src,original)
   with zipfile.ZipFile(src) as z:
    module=json.loads(z.read('module.json'));files={f['path']:z.read('payload/'+f['path']) for f in module['files']}
   old=copy.deepcopy(files);changed=[]
   for name in list(files):
    if name in read(ROOT/'game/beta7/variants.json') or name=='paws_patch_versions.ini':
     files[name]=(folder/'helpers'/name).read_bytes()
     if name.endswith('.exe'):seen.add(name)
    if channel=='beta' and name.lower() in overrides:
     files[name]=team_sort(files[name]) if ident.startswith('localization-bot-ui-') and name.lower() in ('data/ui/menus/staging.tgi','data/ui/menus/pcolors.tgi') else overrides[name.lower()]
   if channel=='beta' and ident=='pawpatch-core':
    index={k.lower():k for k in files}
    for name,b in overrides.items():files[index.get(name,name)]=b
   if channel=='beta':
    code=ident.rsplit('-',1)[1] if ident.startswith(('pawpatch-data-','localization-bot-ui-')) else 'en'
    for name in list(files):
     if name.lower().endswith('localization/strings_data_k2.tgi'):files[name]=english_table() if name.lower().startswith('data/') else localized_strings(files[name],code)
    if ident=='pawpatch-data-ru':
     with zipfile.ZipFile(OUT/'inputs/aw-localization-ru.zip') as z:
      name=next(n for n in z.namelist() if n.lower()=='payload/local_aw_ru/localization/strings_data_k2.tgi')
      files[name[len('payload/'):]]=localized_strings(z.read(name),'ru')
   changed=[k for k,v in files.items() if old.get(k)!=v]
   if channel=='stable':assert all(n.endswith('.exe') or n=='paws_patch_versions.ini' for n in changed)
   module.update(version=version,files=[dict(path=n,size=len(b),sha256=hashlib.sha256(b).hexdigest().upper()) for n,b in sorted(files.items())])
   target=folder/'assets'/(ident+'-'+version+'.zip');target.parent.mkdir(exist_ok=True)
   with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,b in [('module.json',encode(module))]+[('payload/'+k,v) for k,v in sorted(files.items())]:
     info=zipfile.ZipInfo(name,(2026,11,6,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
   package=dict(original,version=version,size=target.stat().st_size,sha256=sha(target),experimental=channel=='beta',urls=['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/patch-'+version+'/'+target.name])
   validate_package(target,package);changes[ident]=package
   assets.append(dict(channel=channel,id=ident,path=str(target),url=package['urls'][0],size=package['size'],sha256=package['sha256']))
   audit[channel][ident]=dict(changed=changed,priorSha256=sha(src),payloadFiles=len(files))
  assert seen==set(read(ROOT/'game/beta7/variants.json'))
  for schema in ('v3','v2'):
   path='feed/'+schema+'/'+channel+'.json';old=baseline(path);new=copy.deepcopy(old)
   new['packages']=[copy.deepcopy(changes.get(p['id'],p)) for p in old['packages']]
   new['companyBehaviorRevision']=2
   if channel=='stable':new['patchGuide']=copy.deepcopy(baseline('feed/'+schema+'/beta.json')['patchGuide'])
   new['patchGuide']['version']=version
   if channel=='stable':
    for entry in new['patchGuide']['entries']:
     if entry['category']=='beta':entry['category']='always'
    if 'modGuides' in new:
     beta_guides={x['id']:x for x in baseline('feed/'+schema+'/beta.json')['modGuides']}
     new['modGuides']=[copy.deepcopy(beta_guides[x['id']]) if x['id']=='arcane-wars' else x for x in new['modGuides']]
   else:
    new['mixedBiomesRevision']=1
    new['patchGuide']['entries'].append(dict(id='mixed-biomes',category='always',titleRu='Смешанные биомы и миникарта',titleEn='Mixed biomes and minimap',bodyRu=notes('beta')['body']['ru'],bodyEn=notes('beta')['body']['en']))
   new['changelog']=[notes(channel)]+new['changelog'];new['publishedAt']=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
   allowed={'packages','patchGuide','companyBehaviorRevision','mixedBiomesRevision','modGuides','changelog','publishedAt'}
   assert {k:v for k,v in old.items() if k not in allowed}=={k:v for k,v in new.items() if k not in allowed}
   assert [p for p in old['packages'] if p['id'] not in changes]==[p for p in new['packages'] if p['id'] not in changes]
   write(OUT/'signed'/path,sign(new,pkey))
   if schema=='v3':
    test=copy.deepcopy(new)
    for p in test['packages']:
     if p['id'] in changes:p['urls']=[str(folder/'assets'/(p['id']+'-'+version+'.zip'))]
    write(OUT/'test-feeds'/(channel+'.json'),sign(test,pkey))
 history=read(OUT/'before/feed/changelog.history.json')
 for channel in VERSIONS:history[channel]=[notes(channel)]+history[channel]
 write(OUT/'history.json',history);write(OUT/'guide-beta.json',verify(read(OUT/'signed/feed/v3/beta.json'),key())['patchGuide'])
 write(OUT/'preparation.json',dict(versions=VERSIONS,baselineHead=read(OUT/'baseline.json')['head'],assets=assets));write(OUT/'payload-audit.json',audit)
 for channel in VERSIONS:
  entry=notes(channel);write(OUT/channel/'notes.json',entry)
  text='\n\n'.join([entry['title']['ru'],entry['body']['ru'],'---',entry['title']['en'],entry['body']['en']])+'\n'
  (OUT/channel/'notes.md').write_text(text,encoding='utf-8')
 print('STAGED',len(assets),'immutable archives; Pure packages and launcher retained',flush=True)
def promote():
 assert read(OUT/'validation.json')['passed']
 for p in FEEDS+['feed/changelog.history.json','feed/patch-guide-beta.json']:
  assert normalize((ROOT/p).read_bytes())==normalize((OUT/'before'/p).read_bytes()),p
 for channel,version in VERSIONS.items():
  r=json.loads(fetch(API+'/releases/tags/patch-'+version));assert not r['draft'] and r['prerelease']==(channel=='beta')
 for a in read(OUT/'preparation.json')['assets']:
  b=fetch(a['url']);assert len(b)==a['size'] and hashlib.sha256(b).hexdigest().upper()==a['sha256']
 for p in ('feed/v3/stable.json','feed/v3/beta.json','feed/v2/stable.json','feed/v2/beta.json'):shutil.copy2(OUT/'signed'/p,ROOT/p)
 shutil.copy2(OUT/'history.json',ROOT/'feed/changelog.history.json');shutil.copy2(OUT/'guide-beta.json',ROOT/'feed/patch-guide-beta.json')
 print('CATALOGS PROMOTED LOCALLY; commit/push and public readback remain',flush=True)
def readback():
 for p in FEEDS:
  public=json.loads(fetch(RAW+p));assert public==read(ROOT/p),p;verify(public,key())
 for a in read(OUT/'preparation.json')['assets']:
  b=fetch(a['url']);assert len(b)==a['size'] and hashlib.sha256(b).hexdigest().upper()==a['sha256']
 write(OUT/'public-readback.json',dict(passed=True,versions=VERSIONS,catalogs=6,assets=len(read(OUT/'preparation.json')['assets'])))
 print('ACTIVE PUBLIC READBACK PASS',flush=True)
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['data','native','build','stage','promote','readback']);p.add_argument('--private-key');a=p.parse_args()
 if a.action=='stage':stage(a.private_key)
 else:globals()[a.action]()
if __name__=='__main__':main()
