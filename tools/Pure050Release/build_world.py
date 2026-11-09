"""Emit a three-climate Pure world payload without company-cap balance hooks."""
import ast,re,shutil,subprocess
from context import *
def main():
 out=OUT/'world-native-r2';native=out/'native';native.mkdir(parents=True,exist_ok=False);src=out/'source';src.mkdir()
 masks=read(OUT/'world-data-r1/vanilla/spawn-index.json');assert masks==read(OUT/'world-data-r1/immortals/spawn-index.json')
 (native/'spawn-index.h').write_text('#define SPAWN_COUNT '+str(len(masks))+'\nstatic char*spawn_ids[]={'+','.join(json.dumps(n)for n in sorted(masks))+'};\nstatic U spawn_masks[]={'+','.join(str(masks[n])for n in sorted(masks))+'};\n')
 for name in ['world_rules.h','day_cycle.h']:shutil.copy2(REPO/'game/world-options'/name,src/name)
 regions=(REPO/'game/mixed-biomes/regions.h').read_text();regions=regions.replace('U ids[4]={0,1,2,3},i,j,t,count=1+hash(seed^0xB10C0A17u)%4;','U ids[3]={0,1,2},i,j,t,count=1+hash(seed^0xB10C0A17u)%3;').replace('for(i=3;i;i--)','for(i=2;i;i--)');assert 'ids[3]={0,1,2}' in regions;(src/'regions.h').write_text(regions)
 text=(REPO/'game/mixed-biomes/biomes.c').read_text().replace('../world-options/world_rules.h','world_rules.h').replace('../world-options/day_cycle.h','day_cycle.h').replace('"sun_default"','"sun_afternoon"')
 old='for(b=0;b<4;b++)for(k=0;k<9;k++){table[b][k]=find';assert text.count(old)==1;text=text.replace(old,'for(b=0;b<3;b++)for(k=0;k<9;k++){table[b][k]=find')
 start=text.index(' if(rule_enum(world,"PawsBiomes","paws_random")){');end=text.index(' grid=R(map,0x28);',start)
 text=text[:start]+''' { U mapping[4]={0,1,2,0};mapping[3]=hash(s->seed^0x33b10beu)%3;
  if(rule_enum(world,"PawsBiomes","paws_random"))biome_selection(s->seed,mapping);
  for(k=0;k<4;k++)s->regions[k]=0;
  for(k=0;k<w*h;k++){s->cells[k]=(unsigned char)mapping[s->cells[k]];s->regions[s->cells[k]]++;}
 }
'''+text[end:]
 text=text.replace('arctic_snowswamp01','arctic_tundra01').replace('desert_quicksand01','desert_scrub01')
 # Native modes have no Arcane snow-swamp/quicksand resources.
 from rwd import entries,decode
 native_ids=set()
 for name,raw in entries(OUT/'stable-fixtures/vanilla/game/Data.rwd').items():
  if name.startswith('data/terrain/'):native_ids.update(re.findall(r'(?im)^\s*ids\s*=\s*(\w+)',decode(raw)))
 required=set(re.findall(r'"((?:temperate|arctic|desert)_[a-z]+\d\d)"',text));assert required<=native_ids,required-native_ids
 (src/'biomes.c').write_text(text)
 source=REPO/'game/mixed-biomes/build.py';code=source.read_text();code=code[:code.index('# Generate centered pause and save menus')]
 code=code.replace("OUT=WS/'outputs/mixed-biomes-r2-20261106'",'OUT=Path('+repr(str(out))+')').replace("str(HERE/'biomes.c')",'str(Path('+repr(str(src/'biomes.c'))+'))')
 tree=ast.parse((REPO/'game/world-options/build_native.py').read_text());insertion=next(ast.literal_eval(n.value)for n in ast.walk(tree)if isinstance(n,ast.Assign)and any(isinstance(x,ast.Name)and x.id=='insertion' for x in n.targets))
 code=code.replace('hooks=[dict(site=0x25697a',insertion+'hooks=[dict(site=0x25697a',1)
 code=code.replace('for h in hooks:\n','hooks=[h for h in hooks if h["site"] not in (0x235c4c,0x5c138,0xbf32d)]\nhooks += [dict(site=0x246a40,entry=tick,n=5,op=0xe8),dict(site=0x2462bc,entry=sunstart,n=5,op=0xe8)]\nfor h in hooks:\n',1)
 code=code.replace('MixedBiomesTestPatch','PureWorldOptionsPatch').replace('LOCAL_MIXED_BIOMES r2;','PURE_WORLD_OPTIONS r1;').replace('companies25 minWidth=1200 minHeight=1200','nativeBiomes=3 dynamicCycle=600 kingdomCapsUnchanged=true')
 exec(compile(code,str(source),'exec'),{'__file__':str(source)})
 meta=read(native/'payload.json');assert len(meta['hooks'])==5;assert not {h['site']for h in meta['hooks']}&{0x235c4c,0x5c138,0xbf32d};meta.update(nativeBiomes=3,dynamicDayCycleSeconds=600,spawnMasks=len(masks));write(native/'payload.json',meta)
 generated=native/'PureWorldOptionsPatch.cs';assert generated.is_file()
 validate=' internal static void Validate(IMemory m,uint image){\n'
 for h in meta['hooks']:
  b='TerrainPatch.Hex("'+h['before']+'")'
  if h['site']==0x2566b9:validate+=' {byte[]b='+b+';Buffer.BlockCopy(BitConverter.GetBytes(image+0x43ff0d),0,b,1,4);TerrainPatch.Expect(m,image+0x2566b9,b);}\n'
  else:validate+=' TerrainPatch.Expect(m,image+0x'+format(h['site'],'x')+','+b+');\n'
 validate+=' }\n';s=generated.read_text().replace('internal static class PureWorldOptionsPatch {','internal static class PureWorldOptionsPatch {\n'+validate);generated.write_text(s)
 write(out/'build-inputs.json',{str(p):sha(p)for p in src.glob('*')})
 print('PURE_WORLD_NATIVE_READY',len(meta['hooks']),len(masks),'spawn ids; native company caps retained')
if __name__=='__main__':main()
