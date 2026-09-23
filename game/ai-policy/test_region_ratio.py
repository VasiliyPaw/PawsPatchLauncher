"""Original 5B686 with relocated policy; only region services/pow controlled.
Includes a saturated x87 caller stack and 80-bit return preservation."""
import argparse,sys,struct,json,math
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--native',type=Path,required=True);a=p.parse_args()
sys.path[:0]=[str(a.legacy/'lobby_colors_1372/deps_r15')]
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
ks=Ks(KS_ARCH_X86,KS_MODE_32);native=(a.legacy/'k2_runtime_1372_20260904.bin').read_bytes();meta=json.loads((a.native/'ai-policy.json').read_text());payload=(a.native/'ai-policy.bin').read_bytes();h=next(x for x in meta['wrappers'] if x['mode']==25)
checks=0
def fixture(image,cave):
 uc=Uc(UC_ARCH_X86,UC_MODE_32);uc.mem_map(image,(len(native)+4095)&~4095);copy=bytearray(native)
 pe=struct.unpack_from('<I',copy,60)[0];rv,sz=struct.unpack_from('<II',copy,pe+24+96+5*8);end=rv+sz
 while rv<end:
  page,n=struct.unpack_from('<II',copy,rv)
  for at in range(rv+8,rv+n,2):
   e=struct.unpack_from('<H',copy,at)[0]
   if e>>12==3:
    off=page+(e&4095);struct.pack_into('<I',copy,off,(struct.unpack_from('<I',copy,off)[0]+image-0x460000)&0xffffffff)
  rv+=n
 uc.mem_write(image,bytes(copy));uc.mem_map(cave,(meta['allocation']+4095)&~4095);code=bytearray(payload)
 for off,im,cv in meta['fixups']:struct.pack_into('<I',code,off,(struct.unpack_from('<I',code,off)[0]+im*(image-meta['image'])+cv*(cave-meta['cave']))&0xffffffff)
 uc.mem_write(cave,bytes(code));uc.mem_write(image+h['site'],b'\xe8'+struct.pack('<i',cave+h['offset']-image-h['site']-5))
 for at,size in ((0x51000000,0x10000),(0x61000000,0x10000),(0x62000000,0x1000)):uc.mem_map(at,size)
 return uc
for image,cave in ((0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)):
 for enabled in (False,True):
  for own,enemy in ((0,0),(100,0),(100,50),(0,50)):
   uc=fixture(image,cave)
   ego,definition,world,terrain,pl,region,summary,storage=range(0x51000000,0x51008000,0x1000)
   def w(at,v):uc.mem_write(at,struct.pack('<I',v&0xffffffff))
   def fl(at,v):uc.mem_write(at,struct.pack('<f',v))
   def asm(at,t):uc.mem_write(at,bytes(ks.asm(t,at)[0]))
   w(cave+meta['dataOffset']+4,8 if enabled else 0);w(image+0x5f3fb8,world);w(world+0x30,terrain);fl(terrain+0xc,960);fl(terrain+0x10,960)
   w(definition+0x174,(1<<5)|(1<<10));fl(definition+0x1e4,100);fl(definition+0x364,60)
   for o,v in ((0x2e4,1),(0x2e8,0),(0x2ec,2),(0x2f0,1),(0x2f4,1),(0x2f8,0),(0x2fc,0),(0x300,100)):fl(ego+o,v)
   w(pl+0x60,storage+0x100);w(storage+0x100,storage+0x104);w(region+0x4c,storage+0x200);w(storage+0x200,storage+0x300);w(region+0x6c,1);fl(storage+0x320,754);fl(storage+0x324,549);fl(storage,own);fl(storage+4,enemy)
   for off,t in ((0x1e947f,f'mov eax,{region};ret 8'),(0x1f539b,f'mov eax,{summary};ret 4'),(0x1f7454,f'fld dword ptr [{storage+4}];ret 4'),(0x1f731b,f'fld dword ptr [{storage}];ret 4'),(0x1f8322,'xor eax,eax;ret'),(0x21117,'xor eax,eax;ret 4'),(0x3f42e0,'ret')):asm(image+off,t)
   def power(u,at,n,data):
    x=struct.unpack('<d',struct.pack('<Q',u.reg_read(UC_X86_REG_XMM0)&((1<<64)-1)))[0];y=struct.unpack('<d',struct.pack('<Q',u.reg_read(UC_X86_REG_XMM1)&((1<<64)-1)))[0]
    try:z=math.pow(x,y)
    except ValueError:z=float('nan')
    u.reg_write(UC_X86_REG_XMM0,struct.unpack('<Q',struct.pack('<d',z))[0])
   uc.hook_add(UC_HOOK_CODE,power,begin=image+0x3f42e0,end=image+0x3f42e0)
   uc.reg_write(UC_X86_REG_ESP,0x6100f000);args=[definition,pl,0,pl,struct.unpack('<I',struct.pack('<f',753))[0],struct.unpack('<I',struct.pack('<f',549))[0]]
   driver='fninit;'+''.join(f'push {v};' for v in reversed(args))+f'mov ecx,{ego};call {image+0x5b686};fstp dword ptr [{storage+16}];nop';blob=bytes(ks.asm(driver,0x62000000)[0]);uc.mem_write(0x62000000,blob);uc.emu_start(0x62000000,0x62000000+len(blob),count=200000)
   score=struct.unpack('<f',uc.mem_read(storage+16,4))[0]
   assert (math.isnan(score) if not enabled and own==enemy==0 else score==(50 if own==100 and enemy==50 else 0)),(enabled,own,enemy,score)
   assert uc.reg_read(UC_X86_REG_ESP)==0x6100f000;checks+=2
 # Native callers may already have seven FP temporaries. All remain exact.
 for enabled in (False,True):
  uc=fixture(image,cave);storage=0x51007000;data=cave+meta['dataOffset']
  def w(at,v):uc.mem_write(at,struct.pack('<I',v&0xffffffff))
  extended=struct.pack('<QH',(1<<63)+(1<<13),16383);uc.mem_write(storage,extended);uc.mem_write(storage+16,struct.pack('<H',0x027f));w(data+4,8 if enabled else 0)
  uc.mem_write(image+h['target'],bytes(ks.asm(f'fld tbyte ptr [{storage}];ret 4',image+h['target'])[0]))
  # args[5] is a saved numerator in the native parent's stack. An unchanged
  # denominator does not inspect unrelated memory even with a full FP stack.
  driver=f'fninit;fldcw word ptr [{storage+16}];'+f'fld tbyte ptr [{storage}];'*7+'push 0;'+f'call {cave+h["offset"]};'+''.join(f'fstp tbyte ptr [{storage+64+i*16}];' for i in range(8))+f'fnstcw word ptr [{storage+32}];nop'
  blob=bytes(ks.asm(driver,0x62000000)[0]);uc.mem_write(0x62000000,blob);uc.reg_write(UC_X86_REG_ESP,0x6100f000);uc.emu_start(0x62000000,0x62000000+len(blob),count=200000)
  assert all(bytes(uc.mem_read(storage+64+i*16,10))==extended for i in range(8));assert bytes(uc.mem_read(storage+32,2))==struct.pack('<H',0x027f);assert uc.reg_read(UC_X86_REG_ESP)==0x6100f000;checks+=10
print('AI_REGION_RATIO_PASS',checks,'checks; original 5B686; 3 ASLR bases; empty-region NaN fixed, nonempty ratios and live 80-bit FP stack retained')
