"""Run compiled x86 guards/ABI and original terrain blocking code in emulation.

This does not prove live pathfinding, visuals, save/load or movement speed.
"""
import argparse, json, struct
from pathlib import Path
from audit import RAW, BASE
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import *

p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);a=p.parse_args()
m=json.loads((a.native/'prototype.json').read_text());blob=(a.native/'prototype.bin').read_bytes()
checks=0
for cave in [0x10000000,0x15000000]:
 u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(BASE,(len(RAW)+4095)&~4095);u.mem_write(BASE,RAW)
 code=bytearray(blob)
 for off,im,cv in m['fixups']:
  struct.pack_into('<I',code,off,(struct.unpack_from('<I',code,off)[0]+cv*(cave-0x10000000))&0xffffffff)
 u.mem_map(cave,m['size']);u.mem_write(cave,bytes(code))
 heap=0x20000000;stack=0x30000000;stop=0x31000000
 u.mem_map(heap,0x40000);u.mem_map(stack,0x10000);u.mem_map(stop,0x1000)
 s=cave+m['state'];world=heap;session=heap+0x1000;map_=heap+0x2000;manager=heap+0x3000;variants=heap+0x4000;tiles=heap+0x10000
 def w(addr,value):u.mem_write(addr,struct.pack('<I',value&0xffffffff))
 def r(addr):return struct.unpack('<I',u.mem_read(addr,4))[0]
 def call(addr,self=0,args=(),clean=0):
  sp=stack+0xf000;u.mem_write(sp,struct.pack('<'+'I'*(len(args)+1),stop,*args));u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,self)
  preserved=[UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP]
  for n,reg in enumerate(preserved):u.reg_write(reg,0x77700000+n)
  u.emu_start(addr,stop,count=200000)
  assert u.reg_read(UC_X86_REG_EIP)==stop
  assert u.reg_read(UC_X86_REG_ESP)==sp+4+clean
  assert all(u.reg_read(reg)==0x77700000+n for n,reg in enumerate(preserved))
 def reset():
  u.mem_write(s,bytes(92));w(s,BASE);w(s+4,cave+m['adapter']);w(s+20,world)
  w(world+0x30,map_);w(world+0xd8,0);w(map_+0x1c,16);w(map_+0x20,16);w(map_+0x28,tiles)
  w(BASE+0x5f3fe4,session);w(session+0xf0,2);w(session+0x100,0)
  w(BASE+0x5f0030,manager);w(manager+0x24,variants);w(manager+0x28,3)
  for i,name in enumerate(['temperate_grass01','temperate_river01','temperate_road01']):
   v=heap+0x5000+i*0x100;t=v+0x40;w(variants+i*4,v);w(v,BASE+0x4741e8);w(v+8,heap+0x6000+i*0x100);u.mem_write(heap+0x6000+i*0x100,(name+'\0').encode('utf-16-le'));w(v+0x1c,t);w(t+0x4c,2 if i==1 else 1);w(t+0x1c,2 if i==1 else 0)
  for i in range(256):w(tiles+i*0x30,heap+0x5000);w(tiles+i*0x30+0x20,0x200)
  for i,val in enumerate([2,3,5,6,2]):w(s+24+i*4,val)
 def run():call(cave+m['exports']['tick'],args=[s,world])
 invoked=[];queue=[]
 def native(uc,addr,size,_):
  sp=uc.reg_read(UC_X86_REG_ESP);self=uc.reg_read(UC_X86_REG_ECX);invoked.append(addr)
  if addr==BASE+0x2517a3:queue.clear();clean=0
  elif addr==BASE+0x2517f9:
   xy=r(sp+4);queue.append((r(xy),r(xy+4),r(sp+8)));clean=8
  elif addr==BASE+0x25185b:
   assert r(sp+4)==0
   for x,y,v in queue:w(tiles+(y*16+x)*0x30,v)
   clean=4
  elif addr==BASE+0x20d4b:clean=0
  elif addr==BASE+0x242159:
   uc.reg_write(UC_X86_REG_EAX,0x12345655);uc.reg_write(UC_X86_REG_EFLAGS,0x247);clean=0
  else:assert addr==BASE+0x2424b2 and self==world and r(sp+4)==0;clean=4
  uc.reg_write(UC_X86_REG_EIP,r(sp));uc.reg_write(UC_X86_REG_ESP,sp+4+clean)
 for rva in [0x2517a3,0x2517f9,0x25185b,0x20d4b,0x2424b2,0x242159]:u.hook_add(UC_HOOK_CODE,native,begin=BASE+rva,end=BASE+rva)
 reset();run();assert not invoked and r(s+60)==1;checks+=1
 # Active command executes once, through the ABI adapter, at the requested coordinates.
 for kind in range(3):
  reset();invoked.clear();w(s+8,1);w(s+40,kind);run()
  assert r(s+12)==1 and r(s+16)==0 and r(s+64)==16 and len(queue)==16, ([r(s+i*4) for i in range(23)],queue,invoked)
  assert all(v==heap+0x5000+kind*0x100 for x,y,v in queue)
  n=len(invoked);run();assert len(invoked)==n;checks+=3
 for addr,value in [(session+0x100,1),(session+0xf0,1),(world+0xd8,6),(s+20,world+4),(map_+0x1c,129),(s+32,16),(s+24,8),(s+40,3)]:
  reset();invoked.clear();w(s+8,1);w(addr,value);run()
  assert not invoked and r(s+12)==1 and r(s+16)==1;checks+=1
 reset();invoked.clear();w(s+8,1);w(manager+0x28,0);run();assert not invoked and r(s+16)==2;checks+=1
 # The actual unmodified native cell routine toggles LAND/WATER masks.
 reset();cell=tiles;variant=heap+0x5000;terrain=variant+0x40
 for allowed,hard,expected in [(1,0,0x200),(2,0,0x100),(3,0,0),(0,0,0x300),(3,1,0x300)]:
  w(terrain+0x4c,allowed);w(cell+0x20,hard|0x88);call(BASE+0x24abf3,self=cell)
  assert r(cell+0x20)&0x300==expected and r(cell+0x20)&0x89==hard|0x88;checks+=1
 # Native variation switch, no doodads/actors: water -> road really clears land blocking.
 w(BASE+0x5f3fb8,world);w(map_+0x2c,0);w(cell,heap+0x5100);w(cell+0x20,0x120)
 w(terrain+0x4c,1);call(BASE+0x24a522,self=cell,args=[variant,0,heap+0x9000],clean=12)
 assert r(cell)==variant and r(cell+0x20)&0x370==0x200;checks+=1
 # The installed trampoline must preserve the original call's result, flags,
 # integer registers, stack, and SIMD state across the compiled C callback.
 reset();regs=[UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP]
 for i,reg in enumerate(regs):u.reg_write(reg,world if reg==UC_X86_REG_ESI else 0x45600000+i)
 saved={reg:u.reg_read(reg) for reg in regs};sp=stack+0xf000;u.reg_write(UC_X86_REG_ESP,sp)
 for i in range(8):u.reg_write(UC_X86_REG_XMM0+i,0x123456789abcdef+i)
 u.emu_start(cave+m['entry'],BASE+m['hook']+5,count=200000)
 assert u.reg_read(UC_X86_REG_EIP)==BASE+m['hook']+5 and u.reg_read(UC_X86_REG_ESP)==sp
 assert u.reg_read(UC_X86_REG_EAX)==0x12345655 and u.reg_read(UC_X86_REG_EFLAGS)==0x247
 assert all(u.reg_read(reg)==value for reg,value in saved.items())
 assert all(u.reg_read(UC_X86_REG_XMM0+i)==0x123456789abcdef+i for i in range(8));checks+=4
print(f'{checks} PASS: compiled guards/ABI and native blocking; live movement is not covered')
