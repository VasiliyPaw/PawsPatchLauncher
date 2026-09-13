"""Build local review packages with separate text/speech; never writes to a game or publishes."""
import argparse,base64,copy,hashlib,json,re,struct,zipfile
from pathlib import Path
from datetime import datetime,timezone

def sha(raw): return hashlib.sha256(raw).hexdigest().upper()
def read(path): return json.loads(Path(path).read_text('utf-8-sig'))
def encoded(value): return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def write(path,value): path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(encoded(value))
def dec(raw):
 if raw.startswith((b'\xff\xfe',b'\xfe\xff')): return raw.decode('utf-16')
 try:return raw.decode('utf-8-sig')
 except UnicodeDecodeError:return raw.decode('cp1251')
def readpkg(package):
 path=Path(package['urls'][0]);raw=path.read_bytes()
 assert sha(raw)==package['sha256'].upper() and len(raw)==package['size'],path
 with zipfile.ZipFile(path) as archive:
  names={n.replace('\\','/').lower():n for n in archive.namelist()}
  manifest=json.loads(archive.read(names['module.json']));files={}
  for file in manifest['files']:
   path=file['path'].replace('\\','/');data=archive.read(names['payload/'+path.lower()])
   assert sha(data)==file['sha256'].upper() and len(data)==file['size']
   files[path]=data
  return files
def build(out,template,version,files):
 release=copy.deepcopy(template);release['version']=version
 path=out/'packages'/(release['id']+'-'+version+'.zip');path.parent.mkdir(parents=True,exist_ok=True)
 assert all('..' not in p.split('/') and ':' not in p and not p.startswith('/') for p in files)
 manifest=dict(schemaVersion=1,id=release['id'],version=version,files=[dict(path=p,size=len(b),sha256=sha(b)) for p,b in sorted(files.items())],remove=[])
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for name,data in [('module.json',encoded(manifest))]+[('payload/'+p,b) for p,b in sorted(files.items())]:
   info=zipfile.ZipInfo(name,(2026,9,11,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,data)
 release.update(size=path.stat().st_size,sha256=sha(path.read_bytes()),urls=[str(path.resolve())])
 assert readpkg(release)==files
 write(out/(release['id']+'-module.json'),manifest)
 print(release['id'],len(files),'files',release['size'],'bytes',flush=True)
 return release
def rwd_files(raw):
 # Find the directory then follow all fixed-format TGCK entries, checking bounds.
 candidates=[];start=max(30,len(raw)-8_000_000)
 for match in re.finditer(rb'(?:[\x20-\x7e]\x00){4,255}',raw[start:]):
  for trim in (0,2):
   pos=start+match.start()+trim;length=struct.unpack_from('<H',raw,pos-2)[0]
   if not 4<=length<=255 or pos+length*2>start+match.end() or pos+length*2+20>len(raw):continue
   end=pos+length*2;offset,size,flags=struct.unpack_from('<QQI',raw,end);offset+=30
   if 30<=offset<pos and size>0 and offset+size<=pos and flags in (0,1) and '.' in raw[pos:end].decode('utf-16-le'):candidates.append(pos-6)
 pos=min(candidates);begin=pos;files={}
 while pos<len(raw)-292:
  _,length=struct.unpack_from('<IH',raw,pos);assert 1<=length<=255
  end=pos+6+length*2;name=raw[pos+6:end].decode('utf-16-le').replace('\\','/');offset,size,flags=struct.unpack_from('<QQI',raw,end);offset+=30
  assert 30<=offset<begin and offset+size<=begin and flags==0 and name not in files
  files[name]=raw[offset:offset+size];pos=end+20
 assert pos==len(raw)-292
 return files
def dictionary(language,values):
 lines=['[Text language = '+language+']','{','\tids = Localization/strings_immortals_translation.tgi','\tname = "@Localization/strings_immortals_translation.tgi"']
 lines.extend('\t'+k+' = '+json.dumps(v,ensure_ascii=False) for k,v in values.items());lines.append('}')
 return ('\r\n'.join(lines)+'\r\n').encode('utf-16')

def main():
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
 out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
 feeds={c:json.loads(base64.b64decode(read(args.base/(c+'.json'))['payload'])) for c in ('stable','beta')}
 source={p['id']:p for p in feeds['stable']['packages']};packages={}
 base=readpkg(source['vanilla-localization-ru']);russian=rwd_files(base['Local_Ru.rwd'])
 voice={p:b for p,b in russian.items() if p.lower().endswith(('.mp3','.wav'))}
 assert len(voice)==1131
 text={'Local_base_ru/'+p:(dec(b).encode('utf-16') if p.lower().endswith(('.tgi','.txt')) else b) for p,b in russian.items() if p not in voice}
 assert len(text)==84 and not any(p.lower().endswith(('.wav','.mp3','.rwd')) for p in text)
 bootstrap=readpkg(source['game-localization-en'])['startup/autoexec.txt']
 base_ru={**text,'startup/autoexec.txt':bootstrap,'startup/autoexec_ru.txt':b'# Russian text and art; voices are selected separately.\r\naddlocaledepot Local_base_ru/\r\n'}
 for id in ['vanilla-localization-ru']:
  packages[id]=build(out,source[id],'1.1.0-split.1',base_ru)
 template=dict(id='game-voice-ru',priority=230,required=False,experimental=False,executableIndependent=True,mods=['vanilla','immortals','arcane-wars'],dependsOn=[],name=dict(ru='Русская озвучка',en='Russian speech'),description=dict(ru='Оригинальная русская озвучка Kohan II. Язык текста выбирается отдельно.',en='Original Russian Kohan II speech, independent of text language.'))
 packages[template['id']]=build(out,template,'1.0.0-split.1',{'data/'+p:b for p,b in voice.items()})
 for id in ['aw-localization-ru','localization-ru']:
  files=readpkg(source[id]);files={p:b for p,b in files.items() if p.lower()!='local_ru.rwd'}
  files['startup/autoexec.txt']=bootstrap
  if id=='localization-ru':
   files.update(text)
   for path in list(files):
    if path.lower().endswith(('.tgi','.txt')) and not path.lower().startswith('startup/'):files[path]=dec(files[path]).encode('utf-16')
  depot='Local_aw_ru/' if id=='aw-localization-ru' else 'Local_ru/'
  files['startup/autoexec_ru.txt']=('# Russian text only.\r\naddlocaledepot Local_base_ru/\r\naddlocaledepot '+depot+'\r\n').encode('ascii')
  assert not any(p.lower().endswith(('.wav','.mp3','.rwd')) for p in files)
  packages[id]=build(out,source[id],source[id]['version']+'-split.1',files)
 translations=read(Path(__file__).resolve().parents[1]/'game/localization/immortals-ru.json')
 literals=translations['literals'];en={};ru={};modified=[];original=readpkg(source['immortals']);files=dict(original)
 for i,(english,russian_text) in enumerate(literals.items()):
  key='immortals_literal_'+str(i+1);en[key]=english;ru[key]=russian_text
  pattern=re.compile(r'(^\s*(?:name|description|tooltip|text|caption|help)\s*=\s*)"'+re.escape(english)+r'"',re.M)
  matches=0
  for path,raw in list(files.items()):
   if not path.lower().endswith('.tgi') or '/sai/' in path.lower():continue
   before=dec(raw);after,count=pattern.subn(lambda m:m[1]+'"#'+key+'"',before)
   if count:
    assert after.replace('"#'+key+'"','"'+english+'"')==before
    files[path]=after.encode('utf-16');modified.append(dict(path=path,key=key,en=english,ru=russian_text,occurrences=count));matches+=count
  assert matches,english
 # These old IDs may also be supplied by the optional Paw's Patch text fixes.
 # Give the translation its own IDs, so either component can be used independently.
 remapped={}
 for old_key,values in translations['missing'].items():
  key='immortals_extra_'+old_key;en[key]=values['en'];ru[key]=values['ru'];remapped[key]=old_key
  matches=0
  for path,raw in list(files.items()):
   if not path.lower().endswith('.tgi') or '/localization/' in path.lower():continue
   before=dec(raw);after=before.replace('"#'+old_key+'"','"#'+key+'"');count=before.count('"#'+old_key+'"')
   if count:
    files[path]=after.encode('utf-16');modified.append(dict(path=path,key=key,en=values['en'],ru=values['ru'],occurrences=count,previousKey=old_key));matches+=count
  assert matches,old_key
 # Proof: replacing the new string references back recovers every original decoded template.
 for path in {item['path'] for item in modified}:
  restored=dec(files[path])
  for key,value in en.items():
   if key.startswith('immortals_literal_'):restored=restored.replace('"#'+key+'"',json.dumps(value,ensure_ascii=False))
  for key,old_key in remapped.items():restored=restored.replace('"#'+key+'"','"#'+old_key+'"')
  assert restored==dec(original[path]),path
 files['data/Localization/strings_immortals_translation.tgi']=dictionary('default',en)
 packages['immortals']=build(out,source['immortals'],'2.1.0-local.3',files)
 # Rebuild the Russian Immortals text package with its own dictionary and mount order.
 immru={**base_ru,'Local_immortals_ru/Localization/strings_immortals_translation.tgi':dictionary('Russian',ru)}
 immru['startup/autoexec_ru.txt']=b'addlocaledepot Local_base_ru/\r\naddlocaledepot Local_immortals_ru/\r\n'
 packages['immortals-localization-ru']=build(out,source['immortals-localization-ru'],'1.1.0-split.2',immru)
 write(out/'translation-verification.json',dict(entries=len(en),literalOccurrences=sum(x['occurrences'] for x in modified if 'previousKey' not in x),changedTemplates=len({x['path'] for x in modified}),changes=modified,gameplayPreserved=True,missing=translations['missing'],independentKeys=remapped))
 write(out/'packages.json',list(packages.values()))
 for channel,feed in feeds.items():
  # The localization inputs are shared in both branches. Refuse unexpected divergence.
  for package in feed['packages']:
   if package['id'] in packages:assert package['sha256']==source[package['id']]['sha256']
  feed['packages']=[copy.deepcopy(packages.get(p['id'],p)) for p in feed['packages']]
  feed['packages'].append(copy.deepcopy(packages['game-voice-ru']))
  feed['publishedAt']=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
  for entry in feed.get('patchGuide',{}).get('entries',[]):
   if entry['id']=='localization':entry.update(bodyRu=translations['help']['ru'],bodyEn=translations['help']['en'])
  for guide in feed['modGuides']:
   if guide.get('id')=='immortals' and 'patchGuide' in guide:
    guide['patchGuide']['entries']=[e for e in guide['patchGuide']['entries'] if e['id']!='missing-labels']
   for entry in guide.get('patchGuide',{}).get('entries',[]):
    if entry['id']=='negative-zero':entry.update(titleRu='Отображение лимита рот',titleEn='Company limit display',bodyRu='В лимите рот «−0» отображается как «0». Меняется только отображение числа, без изменения игровых расчётов. Требуется поддерживаемая версия Kohan II 1.3.72.',bodyEn='The company limit displays zero instead of negative zero. Only the displayed number changes; gameplay calculations are preserved. Requires supported Kohan II version 1.3.72.')
   for section in guide.get('sections',[]):
    if section['id'] in ('localization','language') or 'собственные названия и тексты добавлений' in section['body']['ru']:
     section['body']=dict(ru='Текст и озвучка выбираются отдельно и сохраняются при переключении модов. Русский перевод включает все названия и подписи дополнений Immortals. Скачиваются только выбранные языки; загруженные файлы используются повторно. Игровые характеристики сохраняются.',en='Text and speech are selected separately and retained across mods. Russian covers all added Immortals names and labels. Only selected languages are downloaded and then reused. Gameplay statistics are preserved.')
  write(out/'feeds'/(channel+'.payload.json'),feed)
 write(out/'verification.json',dict(textAssets=len(text),speechFiles=len(voice),speechBytes=sum(map(len,voice.values())),languages=['en','ru'],published=False))
 print('Prepared separate languages and 23 Immortals entries. No game files changed.',flush=True)
if __name__=='__main__':main()
