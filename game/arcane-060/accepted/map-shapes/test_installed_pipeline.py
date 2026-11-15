"""Compiled terrain/noise hook ordering, native chaining and relocated ABI."""
from pathlib import Path
import argparse,json,struct,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'terrain-prototype'))
from audit import RAW,BASE
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
meta=json.loads((a.out/'native/prototype.json').read_text());blob=(a.out/'native/prototype.bin').read_bytes();checks=0
assert meta['installed']
for image,cave in [(BASE,0x10000000),(0x230000,0x19000000)]:
 u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(image,(len(RAW)+4095)&~4095);u.mem_write(image,RAW)
 code=bytearray(blob)
 for off,im,cv in meta['fixups']:struct.pack_into('<I',code,off,(struct.unpack_from('<I',code,off)[0]+im*(image-BASE)+cv*(cave-0x10000000))&0xffffffff)
 u.mem_map(cave,meta['size']);u.mem_write(cave,bytes(code));u.mem_map(0x20000000,0x20000);u.mem_map(0x30000000,0x20000)
 state=cave+meta['state'];generator=0x20000000;creator=generator+0x1000;profile=generator+0x2000;world=generator+0x3000;session=generator+0x4000;grid=generator+0x5000
 calls=[];noiseOk=1
 def w(p,v):u.mem_write(p,struct.pack('<I',v))
 def r(p):return struct.unpack('<I',u.mem_read(p,4))[0]
 def reset():
  u.mem_write(state,bytes(100));w(state,image);w(state+4,cave+meta['adapter']);w(state+72,0x30010000)
  w(generator,creator);w(creator+0x50,profile);w(profile+8,profile+0x100);u.mem_write(profile+0x100,'paws_mixed_biomes\0'.encode('utf-16le'))
  w(image+0x5f3fb8,world);w(image+0x5f3fe4,session);w(session+0x100,0);w(world+0x30,grid);w(grid+0x1c,192);w(grid+0x20,192);calls.clear()
 def native(uc,at,size,_):
  assert uc.reg_read(UC_X86_REG_ECX)==generator
  calls.append(at);sp=uc.reg_read(UC_X86_REG_ESP);uc.reg_write(UC_X86_REG_EAX,noiseOk if at==image+0x256f58 else 0xbeef0001);uc.reg_write(UC_X86_REG_EIP,r(sp));uc.reg_write(UC_X86_REG_ESP,sp+4)
 for at in (0x30010000,image+0x256f58):u.hook_add(UC_HOOK_CODE,native,begin=at,end=at)
 def run(site):
  sp=0x3000f000;w(sp,0x3001f000);u.reg_write(UC_X86_REG_ESP,sp)
  regs=[UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP]
  values=[generator if reg==UC_X86_REG_ECX else 0x77770000+i for i,reg in enumerate(regs)]
  for reg,value in zip(regs,values):u.reg_write(reg,value)
  for i in range(8):u.reg_write(UC_X86_REG_XMM0+i,0x123456789abc+i)
  entry=next(h['entry'] for h in meta['hooks'] if h['site']==site)
  u.emu_start(cave+entry,0x3001f000,count=200000)
  assert u.reg_read(UC_X86_REG_ESP)==sp+4
  assert [u.reg_read(reg) for reg in regs]==values
  assert all(u.reg_read(UC_X86_REG_XMM0+i)==0x123456789abc+i for i in range(8))
 reset();run(0x25697a);assert calls==[0x30010000] and u.reg_read(UC_X86_REG_EAX)==0xbeef0001 and not r(state+84);checks+=4
 reset();noiseOk=1;run(0x2569b9);assert calls==[image+0x256f58] and u.reg_read(UC_X86_REG_EAX)==1 and not r(state+84);checks+=4
 reset();noiseOk=0;w(state+52,123);run(0x2569b9);assert calls==[image+0x256f58] and not u.reg_read(UC_X86_REG_EAX) and r(state+52)==123 and not r(state+84);checks+=4
 # Only the RMG island gate is relaxed; wet/blocked cells and classic
 # maps without rivers retain their original island ID at both relocations.
 cell=grid+0x100;analysis=grid+0x1000;primary=analysis+0x100
 def direct(name,args):
  sp=0x3000f000;u.mem_write(sp,struct.pack('<'+'I'*(len(args)+1),0x3001f000,*args));u.reg_write(UC_X86_REG_ESP,sp);u.emu_start(cave+meta['exports'][name],0x3001f000,count=200000);assert u.reg_read(UC_X86_REG_ESP)==sp+4;return u.reg_read(UC_X86_REG_EAX)
 reset();w(state+8,world);w(state+52,5);w(state+64,1);w(cell+0x10,cell+0x100);w(cell+0x20,0x200);w(image+0x5f3fcc,analysis);w(analysis+0x2c,primary);w(primary,77)
 assert direct('placement_island',[state,cell,22])==77 and r(state+96)==1;checks+=1
 for flags in [0x120,0x100]:
  w(cell+0x20,flags);assert direct('placement_island',[state,cell,22])==22;checks+=1
 w(cell+0x20,0x200);w(state+64,0);assert direct('placement_island',[state,cell,22])==22;checks+=1
 w(state+16,2);assert direct('placement_island',[state,cell,22])==77;checks+=1
 w(state+52,4);assert direct('placement_island',[state,cell,22])==22;checks+=1
 # Four quad corners are lowered even when the adjacent dry cell owns the
 # vertex. Adjacent dry banks blend gradually; remote terrain is preserved.
 reset();w(state+8,world);w(state+52,5);w(state+64,1);w(grid+0x1c,4);w(grid+0x20,4)
 cells=grid+0x2000;plan=cells+0x1000;hm=plan+0x100;base=hm+0x100;heights=base+0x100;baseheights=heights+0x100
 w(grid+0x28,cells);w(state+88,plan);w(state+92,16);u.mem_write(plan,bytes([0]*5+[1]+[0]*10))
 for i in range(16):w(cells+i*0x30+0x20,0x120 if i==5 else 0x200)
 w(world+0x38,hm);w(world+0x34,base)
 for ptr,data in [(hm,heights),(base,baseheights)]:
  w(ptr+0xc,5);w(ptr+0x10,5);w(ptr+0x14,1);w(ptr+0x1c,0);w(ptr+0x40,data)
 for i in range(25):w(heights+i*4,0);w(baseheights+i*4,0x40000000)
 writes=[]
 def height_native(uc,at,size,_):
  sp=uc.reg_read(UC_X86_REG_ESP);assert uc.reg_read(UC_X86_REG_ECX)==hm;x=r(sp+4);y=r(sp+8);writes.append((x,y));w(heights+(y*5+x)*4,r(sp+12));uc.reg_write(UC_X86_REG_ESP,sp+20);uc.reg_write(UC_X86_REG_EIP,r(sp))
 u.hook_add(UC_HOOK_CODE,height_native,begin=image+0x2f95f8,end=image+0x2f95f8)
 assert direct('finish_river_bed',[state])>=4 and {(1,1),(2,1),(1,2),(2,2)}<=set(writes);checks+=1
 def final_height(x,y):return struct.unpack('<f',u.mem_read(heights+(y*5+x)*4,4))[0]+2
 assert all(final_height(x,y)<-.1 for x,y in [(1,1),(2,1),(1,2),(2,2)]);checks+=1
 assert 0<final_height(0,0)<final_height(4,4)==2;checks+=1
 assert direct('finish_river_bed',[state])==0;checks+=1
 for i in range(25):w(heights+i*4,0)
 w(hm+0x1c,1);w(base+0x1c,1);writes.clear()
 assert direct('finish_river_bed',[state])>=9 and {(x,y) for x in range(1,4) for y in range(1,4)}<=set(writes);checks+=1
 assert all(final_height(x,y)<-.1 for x in range(1,4) for y in range(1,4));checks+=1
print('INSTALLED_PIPELINE_PASS',checks,'checks: original mixed stage, noise first, failure propagation, native ABI at two relocations')
