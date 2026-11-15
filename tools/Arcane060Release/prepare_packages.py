"""Compose Arcane-only packages from verified beta.5 plus accepted R24 assets."""
from pathlib import Path
import sys,json,hashlib,zipfile,copy,re,os
P=Path(__file__).resolve().parent;R=Path((P/'target.txt').read_text());OLD=P.parent/'r24-racial-build-beta-20261114';OUT=P.parents[1]/'outputs/arcane-060-beta-release-20261115';VERSION='0.6.0-beta.1';TAG='patch-'+VERSION
sys.path.insert(0,str(P/'source/tools'));from PrepareRelease070 import verify,validate_package
from PrepareRelease081 import key
def sha(b):return hashlib.sha256(b).hexdigest().upper()
def encoded(x):return(json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
feed=verify(json.loads((P/'source/feed/v3/beta.json').read_text()),key());selected={p['id']:p for p in feed['packages']if p['id']in['pawpatch-core','common-ui','player-colors','desync-continue']};assert len(selected)==4 and all(p['version']=='0.5.1-beta.5'for p in selected.values())
payloads={};modules={};originals={}
for pid,p in selected.items():
 f=OLD/'published'/(pid+'-0.5.1-beta.5.zip');validate_package(f,p)
 with zipfile.ZipFile(f)as z:
  module=json.loads(z.read('module.json'));files={m['path'].replace('\\','/'):z.read('payload/'+m['path'].replace('\\','/'))for m in module['files']}
 originals[pid]=copy.deepcopy(files);payloads[pid]=files;modules[pid]=module
helpers=json.loads((OUT/'helpers/build-report.json').read_text());used=set()
for pid,files in payloads.items():
 for rel in list(files):
  if Path(rel).name in helpers:files[rel]=(OUT/'helpers'/Path(rel).name).read_bytes();used.add(Path(rel).name)
  if Path(rel).name.lower()=='paws_patch_versions.ini':files[rel]=files[rel].replace(b'0.5.1-beta.5',VERSION.encode())
assert set(helpers)==used
core=payloads['pawpatch-core'];common=payloads['common-ui'];native=json.loads((OUT/'native/build-report.json').read_text())
for name,row in native.items():
 raw=(OUT/'native'/name).read_bytes();assert sha(raw)==row['sha256'];core['Mods/'+name]=raw
plugin_order=['PawsMilitia.dll','PawsSiege.dll','PawsBridges.dll','PawsWideBiomes.dll','PawsWaterBiomes.dll','PawsCameraRange.dll','PawsMinimapBiomes.dll','PawsStartupOptimizations.dll','PawsFontMetrics.dll'];assert set(plugin_order)==set(native)
core['Mods/plugins.txt']=('\n'.join(plugin_order)+'\n').encode();core['paws_runtime.marker']=('Paw\'s Patch '+VERSION+' / Arcane Wars\n').encode();core['avifil32.dll']=(R/'sandbox/avifil32.dll').read_bytes()
startup=P/'source/packages/startup-base-1.3.72-startup.1.zip'
with zipfile.ZipFile(startup)as z:
 name=next(n for n in z.namelist()if n.lower()=='payload/startup/autoexec.txt');raw=z.read(name)
core['startup/autoexec.txt']=raw.rstrip()+b'\r\n\r\n# Paw\'s Patch world features\r\nadddepot rivers-data/\r\n'
# Preserve the accepted mount order, without shipping profiles or cache files.
for f in(R/'sandbox/rivers-data').rglob('*'):
 if f.is_file():core['rivers-data/'+f.relative_to(R/'sandbox/rivers-data').as_posix()]=f.read_bytes()
# Capture changed and new loose assets, including the 84 approved HUD files
# and 477 icon exports. Existing package ownership identifies actual changes.
state=json.loads((R/'sandbox/.pawpatch/state.json').read_text());winners={}
for pid,m in sorted(state['modules'].items(),key=lambda v:(v[1].get('priority',0),v[0].lower())):
 if m.get('enabled'):
  for f in m.get('files',[]):winners[f['path'].replace('\\','/').lower()]=f['sha256'].upper()
loose=[]
for folder in ['data','skins']:
 for f in(R/'sandbox'/folder).rglob('*'):
  if not f.is_file():continue
  rel=f.relative_to(R/'sandbox').as_posix()
  if rel.lower()=='data/uvars.tgi':continue
  raw=f.read_bytes()
  if winners.get(rel.lower())!=sha(raw):
   assert f.suffix.lower()in['.tgi','.png','.tga','.dds','.nif','.bmp','.ttf','.otf'],rel
   common[rel]=raw;loose.append({'path':rel,'sha256':sha(raw)})
# New literal labels use native multilingual string tables. They do not depend
# on a user's chosen locale or change saved IDs, geometry, costs or behavior.
codes=['en','ru','uk','cs','de','fr'];langs=['Default','Russian','Ukrainian','Czech','Deutsch','Français']
rows=[
 ['Rivers','Реки','Річки','Řeky','Flüsse','Rivières'],
 ['Number of rivers. Random chooses any number from zero to the maximum for the map size.','Количество рек. Случайно: любое количество от нуля до максимума для размера карты.','Кількість річок. Випадково: від нуля до максимуму для розміру мапи.','Počet řek. Náhodně vybírá od nuly po maximum pro velikost mapy.','Anzahl der Flüsse. Zufällig wählt von null bis zum Maximum der Kartengröße.','Nombre de rivières. Aléatoire choisit de zéro au maximum pour la taille de la carte.'],
 ['Random','Случайно','Випадково','Náhodně','Zufällig','Aléatoire'],
 ['Map shape','Форма карты','Форма мапи','Tvar mapy','Kartenform','Forme de la carte'],
 ['Classic','Обычная','Звичайна','Klasická','Klassisch','Classique'],
 ['Pangaea','Пангея','Пангея','Pangea','Pangäa','Pangée'],
 ['Mediterranean','Средиземноморье','Середземномор’я','Středomoří','Mittelmeer','Méditerranée'],
 ['Bridge','Мост','Міст','Most','Brücke','Pont'],
 ['An automatic crossing between solid banks.','Автоматическая переправа между твёрдыми берегами.','Автоматична переправа між твердими берегами.','Automatický přechod mezi pevnými břehy.','Automatischer Übergang zwischen festen Ufern.','Passage automatique entre deux rives fermes.'],
 ['Wooden bridge','Деревянный мост','Дерев’яний міст','Dřevěný most','Holzbrücke','Pont en bois'],
 ['A crossing between solid banks.','Переправа между твёрдыми берегами.','Переправа між твердими берегами.','Přechod mezi pevnými břehy.','Brücke zwischen festen Ufern.','Passage entre deux rives fermes.'],
 ['Stone bridge','Каменный мост','Кам’яний міст','Kamenný most','Steinbrücke','Pont en pierre'],
 ['A durable crossing between solid banks.','Прочная переправа между твёрдыми берегами.','Міцна переправа між твердими берегами.','Odolný přechod mezi pevnými břehy.','Stabile Brücke zwischen festen Ufern.','Passage solide entre deux rives fermes.']]
mapping={row[1]:'paws_060_label_'+str(i)for i,row in enumerate(rows)};changed_labels={}
for rel,raw in list(core.items()):
 if not rel.startswith('rivers-data/')or not rel.endswith('.tgi'):continue
 text=raw.decode('utf-16');before=text
 for literal,k in mapping.items():text=text.replace('"'+literal+'"','"#'+k+'"')
 if text!=before:core[rel]=text.encode('utf-16');changed_labels[rel]=[v for v in mapping if'"'+v+'"'in before]
 table_literals=re.findall(r'(?m)^\s*(?:name|description|text|tooltip(?:_name)?)\s*=\s*"([^"\r\n]*)"',text)
 assert not any(re.search('[А-Яа-яЁё]',t)for t in table_literals),rel
tables=[]
for j in [1,2,3,4,5,0]:
 code,lang=codes[j],langs[j]
 lines=['[Text language = '+lang+']','{',' ids = Localization/paws_060_'+code+'.tgi',' name = "@Localization/paws_060_'+code+'.tgi"']
 lines += [' paws_060_label_'+str(i)+' = "'+row[j]+'"'for i,row in enumerate(rows)];lines+=['}'];tables.append('\n'.join(lines))
core['rivers-data/Localization/paws_060.tgi']=('\n\n'.join(tables)+'\n').encode('utf-16')
# Immutable texture dependencies keep each download bounded. All raster bytes
# remain exactly the accepted R24 assets; patch-off and other mods do not select
# these optional dependency IDs.
texture_files=[(n,b)for n,b in sorted(core.items())if n.startswith('rivers-data/Textures/')]
chunks=[];chunk={};size=0
for name,raw in texture_files:
 if chunk and size+len(raw)>220*1024*1024:chunks.append(chunk);chunk={};size=0
 chunk[name]=raw;size+=len(raw);del core[name]
if chunk:chunks.append(chunk)
for i,files in enumerate(chunks,1):
 pid=f'arcane-biome-textures-{i:02}'
 q={'id':pid,'version':VERSION,'priority':95,'required':False,'experimental':True,'executableIndependent':True,'mods':['arcane-wars'],'dependsOn':['arcane-wars'],'name':{'ru':'Текстуры ландшафта','en':'Terrain textures','uk':'Текстури ландшафту','cs':'Textury terénu','de':'Geländetexturen','fr':'Textures de terrain'},'description':{'ru':'Плавные переходы между биомами и цветами дна.','en':'Smooth biome and water-floor transitions.'}}
 selected[pid]=q;payloads[pid]=files;modules[pid]={'id':pid,'version':VERSION,'files':[],'remove':[]};originals[pid]={};selected['pawpatch-core']['dependsOn']=selected['pawpatch-core']['dependsOn']+[pid]
print('TEXTURE_DEPENDENCIES_READY',len(chunks),'parts;',sum(len(b)for _,b in texture_files),'bytes; all pixels unchanged',flush=True)
packages=[];audit={};(OUT/'assets').mkdir(exist_ok=True)
for pid,p in selected.items():
 # Existing archives and Windows loose paths can differ only in capitalization.
 # Apply the actual overlay once, with one manifest row per case-insensitive path.
 normalized={}
 for n,b in payloads[pid].items():normalized[n.lower()]=(n,b)
 files=dict(normalized.values());assert not any(n.lower().endswith(('.rsg','.rwd','.pem','.pfx','.dmp'))or'network-test'in n.lower()or'qa.dll'in n.lower()or'shfolder.dll'in n.lower()for n in files)
 module=modules[pid];module.update(version=VERSION,files=[{'path':rel,'size':len(raw),'sha256':sha(raw)}for rel,raw in sorted(files.items())])
 path=OUT/'assets'/(pid+'-'+VERSION+'.zip')
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
  for name,raw in [('module.json',encoded(module))]+[('payload/'+n,b)for n,b in sorted(files.items())]:
   item=zipfile.ZipInfo(name,(2026,11,15,0,0,0));item.compress_type=zipfile.ZIP_STORED if name.lower().endswith('.png')else zipfile.ZIP_DEFLATED;z.writestr(item,raw)
 q=copy.deepcopy(p);q.update(version=VERSION,size=path.stat().st_size,sha256=sha(path.read_bytes()),urls=['https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/'+TAG+'/'+path.name]);validate_package(path,q);packages.append(q)
 audit[pid]={'path':str(path),'size':path.stat().st_size,'sha256':q['sha256'],'payloadFiles':len(files),'changed':[n for n in files if originals[pid].get(n)!=files[n]],'preserved':sum(originals[pid].get(n)==files[n]for n in files)}
 print('ARCANE_060_PACKAGE_READY',pid,len(files),path.stat().st_size,flush=True)
(OUT/'packages.json').write_bytes(encoded(packages));(OUT/'package-audit.json').write_bytes(encoded(audit));(OUT/'loose-assets.json').write_bytes(encoded(loose));(OUT/'localization.json').write_bytes(encoded({'languages':codes,'keys':len(rows),'changedFiles':changed_labels}))
print('ARCANE_PACKAGES_READY',VERSION,'base modules',4,'texture dependencies',len(chunks),'loose assets',len(loose))
