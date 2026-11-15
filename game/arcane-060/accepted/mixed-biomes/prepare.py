"""Private experimental fixture. No installed-game writes or network publication."""
from pathlib import Path
import json,re,shutil,hashlib,sys
HERE=Path(__file__).resolve().parent;WS=HERE.parents[3];OUT=WS/'outputs/mixed-biomes-r2-20261106';DEFS=WS/'outputs/mixed-biomes-20261106/definitions'
SOURCE=Path('G:/PawMoraleBetaQA-20261106/game');QA=Path('G:/PawMixedBiomesTest-20261106');GAME=QA/'game'
BIOMES=('temperate','arctic','desert','cursed_land')
def clean(s):return re.sub(r'/\*.*?\*/','',s,flags=re.S)
def read(p):
 b=p.read_bytes()
 return b.decode('utf-16' if b.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig').replace('\r','')
def emit(p,t):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(t,encoding='utf-16')
def roots(s):return re.split(r'(?m)(?=^\[(?:Thing|Template)\s)',s)
def biome_terrain():
 result={}
 for b,n in zip(BIOMES,('temperate','arctic','desert','cursed')):
  t=clean(read(DEFS/'Terrain'/f'{n}.tgi'))
  result[b]=re.findall(r'(?m)^\s*terrain_IDS\s*=\s*(\w+)',t)
 return result
def aliases(t,terrains):
 """Add one placement alias per explicit biome level, with weights confined to
 its original terrains. Existing biome data remains byte-for-byte equivalent."""
 result=[]
 for root in roots(t):
  if not re.match(r'^\[(Thing|[Tt]emplate)\s',root):result.append(root);continue
  # Explicit [Biome] nodes use the same indentation as their values; their
  # nested [Terrain] children are one tab further in. Generic schema is skipped.
  matches=list(re.finditer(r'(?m)^([\t ]*)\[Biome\]\s*\n',root))
  if not matches:result.append(root);continue
  entries=[]
  for m in matches:
   indent=m[1];tail=root[m.end():];end=len(tail)
   if tail.lstrip().startswith('{'):
    begin=tail.index('{');depth=0
    for at,ch in enumerate(tail[begin:],begin):
     if ch=='{':depth+=1
     if ch=='}':
      depth-=1
      if depth==0:end=at+1;break
   else:
    for q in re.finditer(r'(?m)^([\t ]*)(\[|\})',tail):
     if len(q[1].expandtabs(4))<=len(indent.expandtabs(4)):
      end=q.start();break
   block=tail[:end];ids=re.search(r'(?mi)^\s*IDS\s*=\s*(\w+)',block)
   if not ids or ids[1] not in BIOMES:continue
   head=re.split(r'\[Terrain\]',block,flags=re.I)[0]
   weight=re.search(r'(?mi)^\s*(?:fixed\s+)?weight\s*=\s*([-+.\d]+)',head)
   default=float(weight[1]) if weight else -1
   weights={n:default for n in terrains[ids[1]]}
   for terrain in re.split(r'\[Terrain\]',block,flags=re.I)[1:]:
    tid=re.search(r'(?mi)^\s*IDS\s*=\s*(\w+)',terrain);w=re.search(r'(?mi)^\s*(?:fixed\s+)?weight\s*=\s*([-+.\d]+)',terrain)
    if tid:weights[tid[1]]=float(w[1]) if w else default
   entries.append((m.start(),m.end()+end,indent,weights))
  if entries:
   weights={}
   for _,_,_,values in entries:weights.update(values)
   pos=entries[-1][1];ind=entries[-1][2]
   alias='\n'+ind+'[Biome]\n'+ind+'{\n'+ind+' IDS = paws_mixed\n'+ind+' weight = -1\n'
   for n,w in sorted(weights.items()):alias+=ind+' [Terrain]\n'+ind+' IDS = '+n+'\n'+ind+' weight = '+format(w,'.10f').rstrip('0').rstrip('.')+'\n'
   alias+=ind+'}\n'
   root=root[:pos]+alias+root[pos:]
  result.append(root)
 return ''.join(result)
def prepare():
 if QA.exists():assert (GAME/'reconnect-test.marker').read_text()=='Private mixed-biomes test only\n'
 else:QA.mkdir();shutil.copytree(SOURCE,GAME)
 for n in ('shfolder.dll','reconnect-test.marker'):
  p=Path('G:/PawMoraleBetaQA-20261106/network-r2/host')/n
  if not p.exists():
   candidates=list(Path('G:/PawMoraleBetaQA-20261106').rglob(n));assert candidates,n;p=candidates[0]
  shutil.copy2(p,GAME/n)
 (GAME/'reconnect-test.marker').write_text('Private mixed-biomes test only\n')
 # Preserve already-created private profile, never use the real save directory.
 profile=QA/'Documents/Kohan2/data/User';profile.mkdir(parents=True,exist_ok=True)
 prior=Path('G:/PawMoraleBetaQA-20261106/network-r2/host-documents/Kohan2/data/User')
 for source in Path('G:/PawMoraleBetaQA-20261106/network-r2').rglob('UVars.tgi'):
  shutil.copy2(source,profile/source.name);break
 (QA/'AppData').mkdir(exist_ok=True);(QA/'helper.txt').write_text('k2_paws_ui_1372.exe')
 terrain=biome_terrain();pieces=[]
 # Retain one sky/cloud style; merge terrain, transition and water definitions.
 base=clean(read(DEFS/'Terrain/temperate.tgi'));base=re.sub(r'(?m)^(\s*IDS\s*=)\s*temperate\s*$',r'\1 paws_mixed',base,count=1)
 for n in ('arctic','desert','cursed'):
  t=clean(read(DEFS/'Terrain'/f'{n}.tgi'));at=re.search(r'(?m)^\s*\[Terrain\]',t).start();pieces.append(t[at:t.rfind('}')])
 mixed=base[:base.rfind('}')]+''.join(pieces)+'}\n'
 emit(GAME/'data/Terrain/temperate.tgi',read(DEFS/'Terrain/temperate.tgi')+'\n'+mixed)
 # The original biomes reuse rendering priorities. A combined biome requires
 # unique priorities; preserve the order within each original climate.
 for folder,band in [('Arctic',1),('Desert',2),('Cursed',3)]:
  for path in (DEFS/'Terrain'/folder).glob('*.tgi'):
   t=read(path);t,n=re.subn(r'(?mi)^(\s*base_priority\s*=\s*)(\d+)',lambda m:m[1]+str(int(m[2])+band*40000),t)
   if n:emit(GAME/'data/Terrain'/folder/path.name,t)
 src=read(DEFS/'RandomMap/rmc_temperate03.tgi');orig=src[:src.index(';; Paw Random profile')]
 new=re.sub(r'(?mi)^(\s*IDS\s*=)\s*rmc_temperate03',r'\1 paws_mixed_biomes',orig,count=1)
 new=re.sub(r'(?mi)^\s*name\s*=.*$', '\tname = "Смешанные биомы (тест)"',new,count=1)
 new=re.sub(r'(?mi)^\s*description\s*=.*$', '\tdescription = "Крупные области: лето, зима, пустыня и проклятые земли. Общие настройки строений. Только тестовая сборка."',new,count=1)
 new=re.sub(r'(?mi)^(\s*biome\s*=)\s*temperate',r'\1 paws_mixed',new,count=1)
 # Keep the original climate groups internal. Three shared visible controls
 # are distributed by the native patch in proportion to painted biome areas.
 own=re.findall(r'\[ActorGroup\s+Template=(\w+)\]',new,re.I);extra=[]
 for n in ('arctic','desert','cursed'):
  for group in re.findall(r'\[ActorGroup\s+Template=(\w+)\]',read(DEFS/'RandomMap'/f'rmc_{n}03.tgi'),re.I):
   if group not in own:extra.append(group);own.append(group)
 climate=[g for g in own if any(x in g.lower() for x in ('temperate','arctic','desert','cursed'))]
 # Overrides need the inherited range values from the native mod template.
 template=read(DEFS/'Templates/template_rmc_k2.tgi')
 ranges={}
 for block in roots(template):
  m=re.match(r'\[Template\s+(\w+)',block,re.I);r=re.search(r'(?mi)^\s*range\s*=\s*([\d.]+),([\d.]+)',block)
  if m and r:ranges[m[1]]=(float(r[1]),float(r[2]))
 for group in climate:
  lo,hi=ranges[group]
  category='Большие логова' if 'LargeLair' in group else 'Технологии' if 'Tech' in group else 'Логова' if 'Lair' in group else 'Животные'
  structure=any(x in group for x in ('Lair','Tech'))
  # One full-range common slider; other climate groups remain internal only.
  common=structure and 'Temperate' in group
  fields='range = '+str(lo if structure else lo/4)+','+str(hi if structure else hi/4)+'\n'
  fields+='\t show_ui = '+('true' if common else 'false')+'\n'
  if common:fields+='\t name = "'+category+'"\n'
  node='[ActorGroup Template='+group+']\n\t{\n\t '+fields+'\t}\n'
  if group in extra:new=new[:new.rfind('}')]+ '\t'+node+new[new.rfind('}'):]
  else:new=new.replace('[ActorGroup Template='+group+']',node)
 emit(GAME/'data/RandomMap/rmc_temperate03.tgi',src+'\n'+new)
 # Add mixed-biome placement weights to original mod objects and templates.
 changed=[];masks={}
 for path in DEFS.rglob('*.tgi'):
  rel=path.relative_to(DEFS)
  if rel.parts[0].lower() in ('data','terrain','ui','localization'):continue
  t=read(path);updated=aliases(t,terrain)
  if updated!=t:emit(GAME/'data'/rel,updated);changed.append(str(rel))
  for block in roots(clean(t)):
   if not block.startswith('[Thing'):continue
   mid=re.search(r'(?mi)^\s*IDS\s*=\s*(\w+)',block)
   if not mid:continue
   mask=0
   for ident in re.findall(r'(?mi)^\s*random_actor_ids\s*=\s*(\w+)',block):
    for b,i in [('temperate',0),('arctic',1),('desert',2),('cursed',3)]:
     if b in ident.lower():mask|=1<<i
   if mask:masks[mid[1]]=masks.get(mid[1],0)|mask
 # Typed random actors themselves need the same restriction before resolving.
 for path in (DEFS/'Special/RandomActors').glob('*.tgi'):
  for block in roots(clean(read(path))):
   m=re.search(r'(?mi)^\s*IDS\s*=\s*(\w+)',block)
   if m:
    for b,i in [('temperate',0),('arctic',1),('desert',2),('cursed',3)]:
     if b in m[1].lower():masks[m[1]]=1<<i
 header='#define SPAWN_COUNT '+str(len(masks))+'\nstatic char*spawn_ids[]={'+','.join(json.dumps(k) for k in sorted(masks))+'};\nstatic U spawn_masks[]={'+','.join(str(masks[k]) for k in sorted(masks))+'};\n'
 (OUT/'native').mkdir(exist_ok=True);(OUT/'native/spawn-index.h').write_text(header)
 (OUT/'spawn-index.json').write_text(json.dumps(masks,indent=2))
 # Sorting belongs to each dropdown's nested ListBox, not the outer widget.
 team=read(DEFS/'UI/Shared/team_management_dialog.tgi');team=team.replace('[NumKingdoms Template=SharedDropDownWidget]\n\t{','[NumKingdoms Template=SharedDropDownWidget]\n\t{\n        [ListBox]\n        sorted = false\n')
 emit(GAME/'data/UI/Shared/team_management_dialog.tgi',team)
 for rel in ('UI/Menus/staging.tgi','UI/Menus/pcolors.tgi'):
  p=GAME/'data'/rel;baseline=SOURCE/'data'/rel;t=read(baseline) if baseline.exists() else read(DEFS/rel)
  start=t.index('[TeamFormatDropdown Template=SharedDropDownWidget]');end=t.index('[TeamFormatLabel',start)
  section=t[start:end];assert section.count('[ListBox]')==1
  section=section.replace('[ListBox]','[ListBox]\n            sorted = false')
  t=t[:start]+section+t[end:]
  emit(p,t)
 versions=GAME/'paws_patch_versions.ini';versions.write_text('[Versions]\nArcaneWars=0.82.1.8\nPawPatch=0.4.2-local-mixed.2\n')
 (OUT/'preparation.json').write_text(json.dumps(dict(fixture=str(QA),source=str(SOURCE),biomes=BIOMES,placementAliases=changed,spawnMasks=len(masks),climateGroups=climate),indent=2))
 print('PREPARED',QA,len(masks),'spawn masks',len(changed),'placement files')
if __name__=='__main__':prepare()
