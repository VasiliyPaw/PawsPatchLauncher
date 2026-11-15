"""Compiled x86 call-site ABI and isolation guards, at two relocation bases."""
import argparse,json,struct,sys
from localization import profile_id,CLIMATES,SHAPES
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'terrain-prototype'))
from audit import RAW,BASE
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);a=p.parse_args()
m=json.loads((a.native/'prototype.json').read_text());blob=(a.native/'prototype.bin').read_bytes();checks=0
for cave in (0x10000000,0x17000000):
 u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(BASE,(len(RAW)+4095)&~4095);u.mem_write(BASE,RAW)
 code=bytearray(blob)
 for off,im,cv in m['fixups']:struct.pack_into('<I',code,off,(struct.unpack_from('<I',code,off)[0]+cv*(cave-0x10000000))&0xffffffff)
 u.mem_map(cave,m['size']);u.mem_write(cave,bytes(code));u.mem_map(0x20000000,0x20000);u.mem_map(0x30000000,0x10000);u.mem_map(0x31000000,4096)
 state=cave+m['state'];gen=0x20000000;creator=gen+0x1000;rmc=gen+0x2000;session=gen+0x3000;world=gen+0x4000;map_=gen+0x5000
 def w(at,v):u.mem_write(at,struct.pack('<I',v))
 def r(at):return struct.unpack('<I',u.mem_read(at,4))[0]
 def reset(name):
  u.mem_write(state,bytes(64));w(state,BASE);w(state+4,cave+m['adapter']);w(gen,creator);w(creator+0x50,rmc);w(rmc+8,gen+0x6000)
  u.mem_write(gen+0x6000,(name+'\0').encode('utf-16-le'));w(BASE+0x5f3fe4,session);w(session+0x100,0);w(BASE+0x5f3fb8,world);w(world+0x30,map_);w(map_+0x1c,192);w(map_+0x20,192);w(BASE+0x5f0030,0)
 calls=[]
 def native(uc,addr,size,data):
  calls.append(addr);sp=uc.reg_read(UC_X86_REG_ESP);assert uc.reg_read(UC_X86_REG_ECX)==gen
  uc.reg_write(UC_X86_REG_EAX,0xabcd0001);uc.reg_write(UC_X86_REG_EIP,r(sp));uc.reg_write(UC_X86_REG_ESP,sp+4)
 u.hook_add(UC_HOOK_CODE,native,begin=BASE+0x256f19,end=BASE+0x256f19)
 def run():
  sp=0x3000f000;w(sp,0x31000000);u.reg_write(UC_X86_REG_ESP,sp)
  regs=[UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP]
  for i,reg in enumerate(regs):u.reg_write(reg,gen if reg==UC_X86_REG_ECX else 0x77770000+i)
  saved=[u.reg_read(reg) for reg in regs]
  for i in range(8):u.reg_write(UC_X86_REG_XMM0+i,0x123456789abc+i)
  u.emu_start(cave+m['entry'],0x31000000,count=200000)
  assert u.reg_read(UC_X86_REG_EIP)==0x31000000 and u.reg_read(UC_X86_REG_ESP)==sp+4
  assert [u.reg_read(reg) for reg in regs]==saved
  assert all(u.reg_read(UC_X86_REG_XMM0+i)==0x123456789abc+i for i in range(8))
 for name in ['rmc_temperate03','rmc_arctic03','rmc_desert03','paws_shape_unknown','paws_shape_rivers_desert_extra']:
  calls.clear();reset(name);run();assert len(calls)==1 and u.reg_read(UC_X86_REG_EAX)==0xabcd0001 and r(state+48)==0;checks+=4
 for name in [profile_id(s,c) for s in SHAPES[1:] for c in CLIMATES]:
  reset(name);calls.clear();w(session+0x100,1);run();assert not calls and r(state+32)==2 and u.reg_read(UC_X86_REG_EAX)==0;checks+=4
  reset(name);w(map_+0x1c,1024);run();assert not calls and r(state+32)==1 and u.reg_read(UC_X86_REG_EAX)==0;checks+=4
  reset(name);run();assert not calls and r(state+32)==3 and u.reg_read(UC_X86_REG_EAX)==0;checks+=4
print(checks,'PASS: native passthrough, MP/size/palette guards, stack/register/SIMD preservation')
