"""Create mode-native three-biome data; never imports Arcane objects or rules."""
import copy,importlib.util,re,zipfile
from context import *
from rwd import entries,decode
spec=importlib.util.spec_from_file_location('placement_aliases',REPO/'game/mixed-biomes/prepare.py');alias=importlib.util.module_from_spec(spec);spec.loader.exec_module(alias)
BIOMES=('temperate','arctic','desert')
def clean(text):return re.sub(r'/\*.*?\*/','',text,flags=re.S)
def split(text):return re.split(r'(?im)(?=^\[(?:Thing|Template)\s)',text)
def payload(path):
 with zipfile.ZipFile(path) as z:return {n[8:].lower():z.read(n) for n in z.namelist() if n.startswith('payload/') and n.lower().endswith('.tgi')}
def block(text,anchor):
 start=text.lower().index(anchor.lower());brace=text.index('{',start);depth=1;end=brace+1
 while depth:depth+=(text[end]=='{')-(text[end]=='}');end+=1
 return start,end,text[start:end]
def main():
 out=OUT/'world-data-r2';out.mkdir(exist_ok=True);assert not (out/'preparation.json').exists();stock=entries(OUT/'stable-fixtures/vanilla/game/Data.rwd');accepted=OUT/'accepted-assets';audits={}
 for mode in ['vanilla','immortals']:
  native=dict(stock)
  if mode=='immortals':native.update(payload(next(accepted.glob('immortals-*.zip'))))
  for id in ['pure-fixes-data','pure-beta-common','pure-'+mode+'-rules']:native.update(payload(next(accepted.glob(id+'-*.zip'))))
  original=dict(native);result={}
  def put(name,text):result[name]=text.encode('utf-16')
  terrains={b:re.findall(r'(?im)^\s*terrain_ids\s*=\s*(\w+)',clean(decode(native['data/terrain/'+b+'.tgi']))) for b in BIOMES};assert all(terrains.values())
  base=clean(decode(native['data/terrain/temperate.tgi']));mixed=re.sub(r'(?im)^(\s*IDS\s*=)\s*temperate\s*$',r'\1 paws_mixed',base,count=1)
  for b in ['arctic','desert']:
   text=clean(decode(native['data/terrain/'+b+'.tgi']));at=re.search(r'(?m)^\s*\[Terrain\]',text).start();mixed=mixed[:mixed.rfind('}')]+text[at:text.rfind('}')]+'}\n'
  put('data/terrain/temperate.tgi',decode(native['data/terrain/temperate.tgi'])+'\n'+mixed)
  for name,raw in native.items():
   if not name.startswith('data/terrain/'):continue
   band=next((i for i,b in enumerate(BIOMES) if name.startswith('data/terrain/'+b+'/')),0)
   if band:
    text,n=re.subn(r'(?im)^(\s*base_priority\s*=\s*)(\d+)',lambda m:m[1]+str(int(m[2])+band*40000),decode(raw))
    if n:put(name,text)
  template=clean(decode(native['data/templates/template_rmc_k2.tgi']));groups={}
  for root in split(template):
   name=re.match(r'\[Template\s+(\w+)',root,re.I);id=re.search(r'(?im)^\s*ids\s*=\s*(\w+)',root);rng=re.search(r'(?im)^\s*range\s*=\s*([\d.]+),([\d.]+)',root)
   if name and id and rng:groups[name[1]]=dict(id=id[1],range=list(map(float,rng.groups())))
  rmc=decode(native['data/randommap/rmc_temperate03.tgi']);_,_,rmc_root=block(rmc,'[RMC');mixed=re.sub(r'(?im)^(\s*IDS\s*=)\s*rmc_temperate03\b',r'\1 paws_mixed_biomes',rmc_root,count=1)
  mixed=re.sub(r'(?im)^(\s*name\s*=).*$',r'\1 "#paws_mixed_name"',mixed,count=1);mixed=re.sub(r'(?im)^(\s*description\s*=).*$',r'\1 "#paws_mixed_description"',mixed,count=1);mixed=re.sub(r'(?im)^(\s*biome\s*=)\s*temperate\b',r'\1 paws_mixed',mixed,count=1)
  all_groups=[]
  for b in BIOMES:
   text=decode(native['data/randommap/rmc_'+b+'03.tgi'])
   for name in re.findall(r'\[ActorGroup\s+Template=(\w+)\]',text,re.I):
    if name not in all_groups:all_groups.append(name)
  climate=[g for g in all_groups if any(b in g.lower()for b in BIOMES)];existing=re.findall(r'\[ActorGroup\s+Template=(\w+)\]',mixed,re.I);visible=[]
  for name in climate:
   structure='Lair' in name or 'Tech' in name;common=structure and 'Temperate' in name;lo,hi=groups[name]['range'];lo,hi=(lo,hi)if structure else(lo/3,hi/3)
   node='[ActorGroup Template='+name+']\n {\n range = '+str(lo)+','+str(hi)+'\n show_ui = '+str(common).lower()+'\n'
   if common:node+=' name = "#'+('paws_mixed_tech' if 'Tech' in name else 'paws_mixed_lairs')+'"\n';visible.append(name)
   node+=' }\n'
   if name in existing:mixed=mixed.replace('[ActorGroup Template='+name+']',node)
   else:mixed=mixed[:mixed.rfind('}')]+node+mixed[mixed.rfind('}'):]
  assert len(visible)==2
  rmc+='\n'+mixed;put('data/randommap/rmc_temperate03.tgi',rmc)
  masks={};alias_files=[]
  for name,raw in native.items():
   if name.startswith(('data/terrain/','data/ui/','data/localization/')):continue
   text=decode(raw);changed=alias.aliases(text,terrains)
   if changed!=text:put(name,changed);alias_files.append(name)
   for root in split(clean(text)):
    if not re.match(r'\[Thing\b',root,re.I):continue
    id=re.search(r'(?im)^\s*IDS\s*=\s*(\w+)',root)
    if not id:continue
    mask=0
    for ref in re.findall(r'(?im)^\s*random_actor_ids\s*=\s*(\w+)',root):
     for i,b in enumerate(BIOMES):
      if b in ref.lower():mask|=1<<i
    if name.startswith('data/special/randomactors/'):
     for i,b in enumerate(BIOMES):
      if b in id[1].lower():mask|=1<<i
    if mask:masks[id[1]]=masks.get(id[1],0)|mask
  # Native actor aliases are the only mode-specific additions; no AW paths.
  assert masks and all(0<x<8 for x in masks.values());assert not any('/aw_' in n for n in result)
  key='data/templates/template_rmc_k2.tgi';text=decode(native[key]);_,end,_=block(text,'[Template K2AllRMC');extra=''
  for size in range(1280,2049,128):
   assert not re.search(r'\bwidth\s*=\s*'+str(size)+r'\b',text)
   extra+=f'\n[MapSize]\nwidth = {size}\nheight = {size}\nrecommended_kingdoms_min = 2\nrecommended_kingdoms_max = 16\n'
  put(key,text[:end-1]+extra+text[end-1:])
  # Reuse the accepted native WorldRules transform in memory, with no fixture
  # copying or localization-table replacement from Arcane.
  world_source=(REPO/'game/world-options/prepare.py').read_text();begin=world_source.index(" rel='data/Game/world_rules_k2.tgi'");end=world_source.index(' languages=json.loads',begin);transform=world_source[begin:end]
  class MemoryPath:
   def __init__(self,name=''):self.name=name.lower().strip('/')
   def __truediv__(self,part):return MemoryPath(self.name+'/'+part)
   def __lt__(self,other):return self.name<other.name
   def exists(self):return self.name in native or self.name in result
   def glob(self,pattern):return [MemoryPath(n)for n in sorted(set(native)|set(result))if n.startswith(self.name+'/') and n.endswith('.tgi') and n.count('/')==self.name.count('/')+1]
   def relative_to(self,_):return self
   def as_posix(self):return self.name
  def dec(path):return decode(result.get(path.name,native.get(path.name)))
  def write_world(rel,text):put(rel.lower(),text)
  exec('if True:\n'+transform,dict(re=re,game=MemoryPath(),dec=dec,write=write_world))
  for name,raw in list(result.items()):
   if not name.startswith('data/randommap/'):continue
   text=decode(raw);pattern=r'(\[Rules\]\s*\{\s*\[Rule\]\s*ids = PawsBiomes\s*default = paws_all\s*show_ui = (?:true|false))'
   text,n=re.subn(pattern,lambda m:m[1]+'\n  [Rule]\n  ids = PawsDayPhase\n  default = 0\n  show_ui = false',text);assert n>=1,name;put(name,text)
  for name,data in result.items():target=out/mode/'payload'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
  write(out/mode/'spawn-index.json',masks);write(out/mode/'native-groups.json',groups)
  audits[mode]=dict(nativeBiomes=list(BIOMES),files=len(result),aliases=alias_files,spawnMasks=len(masks),visibleClimateControls=visible,sourceHashes={n:hashlib.sha256(original[n]).hexdigest().upper()for n in result if n in original},changedHashes={n:hashlib.sha256(b).hexdigest().upper()for n,b in result.items()})
  print('PURE_NATIVE_WORLD_DATA',mode,len(result),len(masks),flush=True)
 write(out/'preparation.json',audits)
if __name__=='__main__':main()
