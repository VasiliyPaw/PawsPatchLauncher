"""Execute emitted x86 floor ABI, x87 return and SSE/register preservation."""
from pathlib import Path
import argparse,json,struct,sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'terrain-prototype'))
from audit import RAW,BASE
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn.x86_const import *
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
m=json.loads((a.out/'native/prototype.json').read_text());blob=(a.out/'native/prototype.bin').read_bytes();checks=0
ks=Ks(KS_ARCH_X86,KS_MODE_32)
for image,cave in [(BASE,0x10000000),(0x210000,0x1600000)]:
 u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(image,(len(RAW)+4095)&~4095);u.mem_write(image,RAW)
 code=bytearray(blob)
 for off,im,cv in m['fixups']:struct.pack_into('<I',code,off,(struct.unpack_from('<I',code,off)[0]+im*(image-BASE)+cv*(cave-0x10000000))&0xffffffff)
 u.mem_map(cave,m['size']);u.mem_write(cave,bytes(code));u.mem_map(0x20000000,0x200000);u.mem_map(0x30000000,0x20000)
 state=cave+m['roadState'];world=0x20000000;reg=world+0x10000;actor=world+0x90000;xy=world+0xa0000;value=xy+0x100
 def w(p,v):u.mem_write(p,struct.pack('<I',v))
 def f(p,v):u.mem_write(p,struct.pack('<f',v))
 def invoke(at,values,self=0,clean=0):
  sp=0x3000f000;u.mem_write(sp,struct.pack('<'+'I'*(len(values)+1),0x3001f000,*values));u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,self)
  u.emu_start(at,0x3001f000,count=100000)
  assert u.reg_read(UC_X86_REG_EIP)==0x3001f000 and u.reg_read(UC_X86_REG_ESP)==sp+4+clean
 for key in (0,1,2):
  invoke(cave+m['exports']['bridge_field'],[key])
  if key==0:world_off=u.reg_read(UC_X86_REG_EAX)
  elif key==1:count_off=u.reg_read(UC_X86_REG_EAX)
  else:span_off=u.reg_read(UC_X86_REG_EAX)
 w(state,image);w(state+12,world);w(state+world_off,world);w(state+count_off,1)
 session=world+0x1000;w(image+0x5f3fe4,session);w(image+0x5f3fb8,world);w(image+0x5f9218,2);w(session+0xf0,2)
 w(image+0x5f3fbc,world);w(image+0x5ef72c,reg);w(reg+0x20004+400,actor)
 w(actor,image+0x4e5c58);w(actor+0x14,100);w(state+span_off,100)
 definition=world+0xc0000;w(actor+4,definition);w(definition+8,definition+0x100)
 u.mem_write(definition+0x100,'paws_bridge_stone_x_13\0'.encode('utf-16le'))
 for off,v in [(4,10),(8,20),(12,5),(16,11),(20,3)]:f(state+span_off+off,v)
 marker_site=next(h['site'] for h in m['hooks'] if 0x2ec00c<=h['site']<0x2ec090)
 for site,target in [(0x23e0ed,0x2424d0),(0x2e6fca,0x2ea376),(0x2e24fd,0x2ea376),(marker_site,0x2ea376)]:
  wrapper=cave+next(h['entry'] for h in m['hooks'] if h['site']==site)
  guard='' if target==0x2ea376 else f'cmp ecx,{world};jne bad;'
  stub=bytes(ks.asm(f'{guard}fld dword ptr [{value}];mov eax,0x12345678;ret 8;bad:ud2;',image+target)[0]);u.mem_write(image+target,stub)
  # Pop the returned ST0 only after the real wrapper has returned to its caller.
  capture=0x3001e000
  u.mem_write(capture,bytes(ks.asm(f'fstp dword ptr [{value+4}];ret;',capture)[0]))
  for x,y,flags,native,expected in [(15,8,0x122,-1,3),(15,8,0x22,-1,3),(15,8,0x123,-1,-1),(15,8,0,-1,-1),(0,8,0x122,-1,-1),(15,8,0x122,6,6),(15,8,5,-1,-1)]:
   f(xy,x);f(xy+4,y);f(value,native)
   saved={UC_X86_REG_EBX:0x123400,UC_X86_REG_ESI:world+0xb0000,UC_X86_REG_EDI:0x789000,UC_X86_REG_EBP:0xabcdef}
   for register,v in saved.items():u.reg_write(register,v)
   xmm=0x112233445566778899aabbccddeeff00;u.reg_write(UC_X86_REG_XMM3,xmm)
   invoke(wrapper,[xy,flags],self=world+0x400 if site==marker_site else world,clean=8)
   assert all(u.reg_read(register)==v for register,v in saved.items())
   assert u.reg_read(UC_X86_REG_XMM3)==xmm and u.reg_read(UC_X86_REG_EAX)==0x12345678
   invoke(capture,[])
   actual=struct.unpack('<f',u.mem_read(value+4,4))[0];assert actual==expected,(actual,expected)
   checks+=4
 # The bridge's own native model uses its base height while it rises, but
 # unfinished bridges must never raise ordinary walkers or open a shortcut.
 view=world+0xb0000;w(view+0x10,definition);w(view+0x14,actor);w(actor+0xc,view)
 visual=cave+next(h['entry'] for h in m['hooks'] if h['site']==0x2e6fca)
 simulation=cave+next(h['entry'] for h in m['hooks'] if h['site']==0x23e0ed)
 f(xy,15);f(xy+4,8);f(value,-1);w(actor+0x100,0x200000)
 u.reg_write(UC_X86_REG_ESI,view)
 invoke(visual,[xy,0x122],self=world,clean=8);invoke(capture,[])
 assert struct.unpack('<f',u.mem_read(value+4,4))[0]==3;checks+=1
 # A bridge corpse uses flags 0x223. Its sinking starts at the old deck,
 # while dead spans no longer raise living movers onto the lost crossing.
 w(actor+8,2)
 invoke(visual,[xy,0x223],self=world,clean=8);invoke(capture,[])
 assert struct.unpack('<f',u.mem_read(value+4,4))[0]==3;checks+=1
 invoke(simulation,[xy,0x122],self=world,clean=8);invoke(capture,[])
 assert struct.unpack('<f',u.mem_read(value+4,4))[0]==-1;checks+=1
 w(actor+8,0)
 invoke(simulation,[xy,0x122],self=world,clean=8);invoke(capture,[])
 assert struct.unpack('<f',u.mem_read(value+4,4))[0]==-1;checks+=1
 # Wood has a 0.10-unit-thick deck. Feet use its top; the model stays at base.
 w(actor+0x100,0);u.mem_write(definition+0x100,'paws_bridge_wood_x_13\0'.encode('utf-16le'))
 invoke(simulation,[xy,0x122],self=world,clean=8);invoke(capture,[])
 assert abs(struct.unpack('<f',u.mem_read(value+4,4))[0]-3.1)<1e-6;checks+=1
 invoke(visual,[xy,0x122],self=world,clean=8);invoke(capture,[])
 assert struct.unpack('<f',u.mem_read(value+4,4))[0]==3;checks+=1
print('FLOOR_WRAPPER_PASS',checks,'ABI/x87/SSE/register checks across two relocations')
