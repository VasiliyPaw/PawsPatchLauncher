"""Compiled UI-hook ABI, relocation and generated profile/locale validation."""
import argparse,json,struct,sys,re
from pathlib import Path
from localization import TEXT,LANGUAGES,CLIMATES,SHAPES,profile_id
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'terrain-prototype'))
from audit import RAW,BASE
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
m=json.loads((a.out/'native/prototype.json').read_text());blob=(a.out/'native/prototype.bin').read_bytes();checks=0
for image in [BASE,0x210000]:
 for cave in [0x1600000,0x10000000]:
  u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(image,(len(RAW)+4095)&~4095);u.mem_write(image,RAW)
  code=bytearray(blob)
  for off,im,cv in m['fixups']:struct.pack_into('<I',code,off,(struct.unpack_from('<I',code,off)[0]+im*(image-BASE)+cv*(cave-0x10000000))&0xffffffff)
  u.mem_map(cave,m['size']);u.mem_write(cave,bytes(code));u.mem_map(0x30000000,0x20000)
  calls=[];target_self=0x30010000
  def w(at,v):u.mem_write(at,struct.pack('<I',v))
  def r(at):return struct.unpack('<I',u.mem_read(at,4))[0]
  def intercepted(uc,addr,size,data):
   sp=uc.reg_read(UC_X86_REG_ESP)
   if addr in [image+0x11a7b4,image+0x119f91,image+0x11ba60]:
    assert uc.reg_read(UC_X86_REG_ECX)==target_self;calls.append('original')
   else:
    assert r(sp+4)==cave+m['uiState'] and r(sp+8)==target_self;calls.append('extension')
   for reg in [UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_EDX]:uc.reg_write(reg,0x12345678)
   uc.reg_write(UC_X86_REG_EIP,r(sp));uc.reg_write(UC_X86_REG_ESP,sp+4)
  for at in [image+0x11a7b4,image+0x119f91,image+0x11ba60]+[cave+m['exports'][s] for s in ['menu_create','menu_populate','menu_destroy','menu_rivers_refresh']]:u.hook_add(UC_HOOK_CODE,intercepted,begin=at,end=at)
  for hook,expected in zip(m['hooks'][1:7],[['original','extension'],['extension'],['extension','original']]+[['original','extension']]*3):
   calls.clear();sp=0x3000f000;w(sp,0x3001f000);u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,target_self)
   regs=[UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP]
   for i,reg in enumerate(regs):u.reg_write(reg,0x88880000+i)
   u.emu_start(cave+hook['entry'],0x3001f000,count=10000)
   assert calls==expected;checks+=1
   assert u.reg_read(UC_X86_REG_ESP)==sp+4;checks+=1
   assert [u.reg_read(reg) for reg in regs]==[0x88880000+i for i in range(4)];checks+=1
for language in LANGUAGES:
 base=a.out/'locales'/language;text=TEXT[language];ui=(base/'UI/Shared/random_map_dialog.tgi').read_text(encoding='utf-16')
 for label in text['shapes']+text['climates']:
  assert (label+'\0').encode('utf-16-le') in blob,(language,label);checks+=1
 assert ui.count('[PawClimate Template=')==1 and all(v in ui for v in text['labels']);checks+=1
 assert ui.count('[PawRivers Template=')==1 and ui.index('[PawRivers Template=')>ui.index('[ObjectsSlidersPanel');checks+=1
 rules=(base/'Game/world_rules_k2.tgi').read_text(encoding='utf-16');assert rules.count('ids = PawsRivers')==1 and rules.count('ids = paws_rivers_random')==1;checks+=1
 # The label's entire hit area ends before the dropdown starts.
 label=ui[ui.index('[PawClimateLabel'):ui.index('[PawShapeLabel')]
 assert 'R = +110' in label and 57+110<177;checks+=1
 assert len(list((base/'RandomMap').glob('*.tgi')))==9;checks+=1
 for si,s in enumerate(SHAPES[1:],1):
  for ci,c in enumerate(CLIMATES):
   rmc=(base/'RandomMap'/('rmc_'+profile_id(s,c)+'.tgi')).read_text(encoding='utf-16')
   assert 'IDS = '+profile_id(s,c) in rmc and 'biome = '+c in rmc;checks+=1
   assert text['shapes'][si]+' — '+text['climates'][ci] in rmc and text['descriptions'][si] in rmc;checks+=1
   assert not re.search(r'TerrainNoise|Template=\w*(?:MountainTerrainBlob\d*|Lake(?:Frozen)?TerrainBlob)',rmc);checks+=1
   assert rmc.count('width = 1024')==1 and rmc.count('width = 768')==1;checks+=1
print(checks,'PASS: UI wrappers at four relocations, climate profiles, six locales and hit areas')
