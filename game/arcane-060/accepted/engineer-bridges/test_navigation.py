"""Compiled bridge connectivity: transitive links, island 0, removal, approach."""
from pathlib import Path
import argparse,json,struct,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'terrain-prototype'))
from audit import RAW,BASE
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn.x86_const import *
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args()
m=json.loads((args.out/'native/prototype.json').read_text());blob=(args.out/'native/prototype.bin').read_bytes();checks=0
for image,cave in [(BASE,0x10000000),(0x210000,0x1600000)]:
 u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(image,(len(RAW)+4095)&~4095);u.mem_write(image,RAW)
 code=bytearray(blob)
 for off,im,cv in m['fixups']:struct.pack_into('<I',code,off,(struct.unpack_from('<I',code,off)[0]+im*(image-BASE)+cv*(cave-0x10000000))&0xffffffff)
 u.mem_map(cave,m['size']);u.mem_write(cave,bytes(code));u.mem_map(0x20000000,0x200000);u.mem_map(0x30000000,0x20000)
 state=cave+m['roadState'];world=0x20000000;session=world+0x1000;grid=world+0x2000;tiles=world+0x10000;registry=world+0x100000
 def w(at,v):u.mem_write(at,struct.pack('<I',v&0xffffffff))
 def f(at,v):u.mem_write(at,struct.pack('<f',v))
 def r(at):return struct.unpack('<I',u.mem_read(at,4))[0]
 def run(name,values=None,self=0,extra=0):
  values=[] if values is None else values;sp=0x3000f000
  u.mem_write(sp,struct.pack('<'+'I'*(len(values)+1),0x3001f000,*values));u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,self)
  u.reg_write(UC_X86_REG_EDX,extra)
  u.emu_start(cave+m['exports'][name] if isinstance(name,str) else name,0x3001f000,count=200000)
  assert u.reg_read(UC_X86_REG_EIP)==0x3001f000
  assert u.reg_read(UC_X86_REG_ESP)==sp+4
  return u.reg_read(UC_X86_REG_EAX)
 w(state,image);w(image+0x5f3fc0,0)
 run('roads_tick',[state,0]) # Bind the real installed dispatcher while inactive.
 w(state+12,world);w(image+0x5f3fb8,world);w(image+0x5f3fe4,session);w(image+0x5f9218,2);w(image+0x5ef72c,registry)
 w(session+0xf0,2);w(world+0x30,grid);w(grid+4,1);w(grid+0x1c,64);w(grid+0x20,64);w(grid+0x28,tiles)
 def cell(x,y):return tiles+(y*64+x)*48
 for i in range(4096):w(tiles+i*48+32,0x200)
 world_off=run('bridge_field',[0]);count_off=run('bridge_field',[1]);span_off=run('bridge_field',[2])
 w(state+world_off,world);w(state+count_off,4)
 bridge_def=world+0x90000;w(bridge_def+8,bridge_def+0x100);u.mem_write(bridge_def+0x100,'paws_engineer_bridge01\0'.encode('utf-16le'))
 def island(x,y,value):
  rect=world+0xa0000+(y*64+x)*16;w(rect+8,value);w(cell(x,y)+16,rect)
 for i,(left,right) in enumerate([(2,5),(4,5),(0,9),(4,0)]):
  y=8+i*8;a=world+0x80000+i*0x400;s=state+span_off+i*2092
  w(a,image+0x4e5c58);w(a+0x14,100+i);w(registry+0x20004+(100+i)*4,a);w(s,100+i)
  for off,v in [(4,9),(8,23),(12,y*2+1-3.2),(16,y*2+1+3.2),(20,1.08),(2080,1),(2084,0),(2088,7)]:f(s+off,v)
  w(s+24,1);w(a+0x100,0x200000 if i==3 else 0)
  for x in [4,5]:island(x,y,left)
  for x in [11,12]:island(x,y,right)
  island(8,y,21);w(cell(8,y),bridge_def)
 def lookup(x,y):return run('bridge_walk_island',self=cell(x,y))
 run('bridge_navigation_refresh',[state])
 assert lookup(5,8)==lookup(12,8)==lookup(5,16)==lookup(12,16)==2;checks+=4
 assert lookup(5,24)==lookup(12,24)==0;checks+=2
 assert lookup(8,8)==2 and lookup(8,24)==0;checks+=2
 assert lookup(8,32)==21 and lookup(5,32)==2;checks+=2 # Unfinished edge cannot join 0 to 2.
 company=world+0x88000;points=world+0x89000
 ctx=world+0xc0000;mind=ctx+0x100;region=ctx+0x200;rectlist=ctx+0x300;rect=ctx+0x400
 w(ctx+4,mind);w(mind+4,company);w(region+4,rectlist);w(rectlist,rect);w(rect+8,5);w(ctx+0x8c,5);w(ctx+0x3c,0x100)
 assert run('bridge_company_region',self=region,extra=ctx)==2;checks+=1
 assert run('bridge_company_island',self=cell(8,8),extra=ctx)==2;checks+=1
 assert run('bridge_path_island',self=cell(8,8),extra=ctx)==5;checks+=1
 w(company+8,0x1000)
 assert run('bridge_company_region',self=region,extra=ctx)==5;checks+=1
 assert run('bridge_company_island',self=cell(8,8),extra=ctx)==21;checks+=1
 w(company+8,0)
 # Getter replacements retain live native vector temporaries and registers.
 for site,self,expected in [(0x244727,cell(8,8),2),(0x2238cf,cell(8,8),2),(0x273e6c,region,2),(0x273f13,cell(8,8),2),(0x278e8a,cell(8,8),5)]:
  wrapper=cave+next(h['entry'] for h in m['hooks'] if h['site']==site)
  saved={UC_X86_REG_EBX:ctx,UC_X86_REG_ESI:ctx,UC_X86_REG_EDI:0x789000,UC_X86_REG_EBP:ctx}
  for reg,v in saved.items():u.reg_write(reg,v)
  xmm=0x112233445566778899aabbccddeeff00;u.reg_write(UC_X86_REG_XMM3,xmm);w(0x3000f000+0x34,ctx)
  assert run(wrapper,self=self,extra=0x12345678)==expected
  assert all(u.reg_read(reg)==v for reg,v in saved.items()) and u.reg_read(UC_X86_REG_ECX)==self and u.reg_read(UC_X86_REG_EDX)==0x12345678
  assert u.reg_read(UC_X86_REG_XMM3)==xmm;checks+=3
 for i in range(8):w(points+i*4,(4+i)|(8<<16))
 f(company+0x20,10);f(company+0x24,17)
 assert run('bridge_approach_check',[state,company,points,8])==1;checks+=1
 f(company+0x20,24)
 assert run('bridge_approach_check',[state,company,points,8])==2;checks+=1
 island(12,8,7);run('bridge_navigation_refresh',[state]);island(11,8,7)
 island(13,8,19);f(company+0x20,27)
 assert run('bridge_approach_check',[state,company,points,8])==0;checks+=1
 # Remove the second completed edge: island 4 must immediately separate.
 w(world+0x80000+0x400+8,2);run('bridge_navigation_refresh',[state])
 assert lookup(5,16)==4;checks+=1
 w(session+0x100,1);assert lookup(8,8)==(2 if m.get('multiplayer')else 21);checks+=1
print('NAVIGATION_PASS',checks,'compiled checks across two relocations')
