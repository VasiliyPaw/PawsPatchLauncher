"""Compare the compiled candidate with actual 1.3.72 Find/matcher instructions.

Only allocation, handle construction and read-only object/RTTI getters are
controlled stubs. Native ordered search, condition cloning/reset and writes run.
"""
import argparse,ctypes,csv,json,random,struct,sys
from pathlib import Path
LEGACY=Path('G:/CodexData/projects/Codex/2026-08-11/kohan-ii-d-steamlibrary-steamapps-common/work');sys.path[:0]=[str(LEGACY/'pydeps_readable'),str(LEGACY/'lobby_colors_1372/deps_r15')]
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
class PE:
 def __init__(self,path):
  self.b=path.read_bytes();nt=struct.unpack_from('<I',self.b,60)[0];self.opt=nt+24;self.base=struct.unpack_from('<I',self.b,self.opt+28)[0];self.size=struct.unpack_from('<I',self.b,self.opt+56)[0];self.sections=[]
  for i in range(struct.unpack_from('<H',self.b,nt+6)[0]):
   s=self.opt+struct.unpack_from('<H',self.b,nt+20)[0]+i*40;vs,va,size,off=struct.unpack_from('<IIII',self.b,s+8);self.sections.append((va,max(vs,size),size,off))
 def at(self,rva):return next(off+rva-va for va,vs,size,off in self.sections if va<=rva<va+vs)
 def exports(self):
  er=struct.unpack_from('<I',self.b,self.opt+96)[0];e=struct.unpack_from('<IIHHIIIIIII',self.b,self.at(er));out={}
  for i in range(e[7]):
   name=self.at(struct.unpack_from('<I',self.b,self.at(e[9])+i*4)[0]);name=self.b[name:self.b.index(b'\0',name)].decode();ordinal=struct.unpack_from('<H',self.b,self.at(e[10])+i*2)[0];out[name]=self.base+struct.unpack_from('<I',self.b,self.at(e[8])+ordinal*4)[0]
  return out
 def load(self,u):
  u.mem_map(self.base,(self.size+4095)&~4095);u.mem_write(self.base,self.b[:struct.unpack_from('<I',self.b,self.opt+60)[0]])
  for va,vs,size,off in self.sections:
   if size:u.mem_write(self.base+va,self.b[off:off+size])
def main():
 p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--cases',type=int,default=1000);a=p.parse_args()
 ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
 raw=(PROJECT/'work/kohan-ii-decompilation/inputs/k2_runtime_1372_20260904.bin').read_bytes();base=0x460000;heap=0x30000000;stack=0x20000000;stop=0x40000000;cave=0x55000000
 u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(base,(len(raw)+4095)&~4095);u.mem_write(base,raw)
 for at,size in [(heap,0x400000),(stack,0x10000),(stop,0x1000),(cave,0x1000)]:u.mem_map(at,size)
 pe=PE(a.build/'test-local.dll');pe.load(u);exports=pe.exports();ks=Ks(KS_ARCH_X86,KS_MODE_32)
 def asm(at,s):u.mem_write(at,bytes(ks.asm(s,at)[0]))
 def d(p):return struct.unpack('<I',bytes(u.mem_read(p,4)))[0]
 asm(base+0x18e184,'mov eax,[esp+4];test eax,eax;jz shader_null;mov eax,[eax+0x10];ret 4;shader_null:xor eax,eax;ret 4')
 asm(base+0x18e1f5,'mov eax,[esp+4];test eax,eax;jz texture_null;mov eax,[eax+0x14];ret 8;texture_null:xor eax,eax;ret 8')
 asm(base+0x142c27,f'mov eax,[esp+4];cmp eax,{base+0x603724};setz al;movzx eax,al;ret 4')
 asm(base+0x384190,'xor eax,eax;ret 4')
 asm(base+0x20633,'mov dword ptr [ecx],0x12ab34cd;mov eax,ecx;ret')
 asm(base+0x2ef03c,'ret');asm(cave+0x100,f'mov eax,{base+0x603724};ret')
 cursor=heap+0x40000;allocations=[]
 def allocate(uc,address,size,data):
  nonlocal cursor
  size=d(uc.reg_read(UC_X86_REG_ESP)+4);assert size in [16,32];at=cursor;cursor+=(size+15)&~15;assert cursor<heap+0x400000;allocations.append((at,size));uc.mem_write(at,bytes(size));uc.reg_write(UC_X86_REG_EAX,at)
 u.hook_add(UC_HOOK_CODE,allocate,begin=base+0x2ef03c,end=base+0x2ef03c)
 original=raw[0x18e3c8:0x18e3cd];u.mem_write(cave,original+b'\xe9'+struct.pack('<I',(base+0x18e3cd-cave-10)&0xffffffff))
 registers=[UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP];sp=stack+0x8000
 def call(target,ecx=0,args=(),limit=400000):
  u.mem_write(sp,struct.pack('<'+'I'*(len(args)+1),stop,*args));u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,ecx);u.reg_write(UC_X86_REG_EDX,0);u.reg_write(UC_X86_REG_EFLAGS,0x202)
  for i,reg in enumerate(registers):u.reg_write(reg,0x11223340+i)
  u.emu_start(target,stop,count=limit)
  assert u.reg_read(UC_X86_REG_EIP)==stop,('Native call exceeded instruction limit',hex(u.reg_read(UC_X86_REG_EIP)))
  return u.reg_read(UC_X86_REG_EAX),u.reg_read(UC_X86_REG_ESP),tuple(u.reg_read(r)for r in registers)
 rng=random.Random(918743);skipTotal=0;allocationCases=0;calls=0;skippingCases=0
 for case in range(a.cases):
  n=rng.randrange(1,29);blob=bytearray(0x40000);obj=heap+0x18000;vt=heap+0x19000;struct.pack_into('<II',blob,vt-heap,0,cave+0x100)
  schema=rng.choice([[],[(1,1)],[(2,1)],[(1,2)],[(2,2)]])
  for i in range(n):
   suffix=[(2,27),(2,11),(2,9),(2,13),(2,17),(2,21)][:case%7]
   pattern=[*schema,(1,3),(1,5),*suffix];header=heap+i*32;cond=heap+0x10000+i*0x100
   if case%11==0 and i==n//2:pattern.append((1,7))
   if case%13==0 and i==n//2 and i+1<n:pattern[-1]=rng.choice([(1,6),(2,5),(1,11),(2,3)])
   if case%23==0 and i==n//2:pattern=[(1,7)]
   struct.pack_into('<8I',blob,header-heap,0,0,0,0,cond,0,header+32 if i+1<n else 0,0)
   for j,(polarity,kind)in enumerate(pattern):
    key=rng.randrange(1,5)if case%3 else rng.randrange(5)
    if case%17==0:key=0xffffffff
    struct.pack_into('<4I',blob,cond-heap+j*16,polarity,kind,cond+(j+1)*16 if j+1<len(pattern)else 0,key)
  if case%29==0:struct.pack_into('<I',blob,16,0)
  objects=[(rng.randrange(5),rng.randrange(5),rng.randrange(2))for _ in range(4)]
  mode=0 if case%31==0 else 1;actual=2 if case%37==0 else 1;outputs=[]
  for optimized in [False,True]:
   u.mem_write(heap,bytes(blob)+bytes(0x40000));cursor=heap+0x40000;allocations.clear();out=[]
   u.mem_write(base+0x18e3c8,original)
   u.ctl_remove_cache(base+0x18e3c8,base+0x18e3cd)
   call(exports['TestInit'],args=(cave,base+0x18de9d,1,actual,mode))
   if optimized:
    u.mem_write(base+0x18e3c8,b'\xe9'+struct.pack('<I',(exports['TestFind']-base-0x18e3cd)&0xffffffff));u.ctl_remove_cache(base+0x18e3c8,base+0x18e3cd)
   for shader,texture,skin in objects:
    u.mem_write(obj,bytes(0x100));u.mem_write(obj,struct.pack('<I',vt));u.mem_write(obj+0x10,struct.pack('<II',shader,texture));u.mem_write(obj+0xd0,struct.pack('<I',skin))
    try:pointer,esp,regs=call(base+0x18e3c8,ecx=heap,args=(0 if case%41==0 else obj,))
    except Exception as error:raise AssertionError((case,n,schema,optimized,objects,mode,actual))from error
    assert esp==sp+8;assert regs==tuple(0x11223340+i for i in range(4))
    out.append(pointer);calls+=1
   if optimized:
    skipped=call(exports['TestSkipped'])[0];skipTotal+=skipped;skippingCases+=skipped>0
   outputs.append((out,list(allocations),bytes(u.mem_read(heap,0x80000))))
  assert outputs[0]==outputs[1],(case,n,schema,objects,mode,actual)
  allocationCases+=bool(outputs[0][1])
 assert skipTotal>10000 and skippingCases>100 and allocationCases>100,(skipTotal,skippingCases,allocationCases)
 # A valid shared immutable occupied prefix longer than the optimisation cap.
 # Only the final native bin may allocate. Compare its actual cloned conditions.
 long=bytearray(0x400000);count=16390;cond=heap+0x110000;obj=heap+0x120000
 for i in range(count):struct.pack_into('<8I',long,i*32,0,0,0,0,cond,0,heap+(i+1)*32 if i+1<count else 0,0)
 struct.pack_into('<8I',long,cond-heap,1,3,cond+16,1,1,5,0,1);struct.pack_into('<2I',long,obj-heap+0x10,1,2);results=[]
 for optimized in [False,True]:
  u.mem_write(heap,bytes(long));cursor=heap+0x200000;allocations.clear();u.mem_write(base+0x18e3c8,original);u.ctl_remove_cache(base+0x18e3c8,base+0x18e3cd);call(exports['TestInit'],args=(cave,base+0x18de9d,1,1,1))
  if optimized:u.mem_write(base+0x18e3c8,b'\xe9'+struct.pack('<I',(exports['TestFind']-base-0x18e3cd)&0xffffffff));u.ctl_remove_cache(base+0x18e3c8,base+0x18e3cd)
  value=call(base+0x18e3c8,ecx=heap,args=(obj,),limit=6000000);results.append((value,list(allocations),bytes(u.mem_read(heap,0x400000))))
  if optimized:assert call(exports['TestSkipped'])[0]==16384
 assert results[0]==results[1]and len(results[0][1])==3
 result=dict(accepted=True,cases=a.cases,nativeCallsCompared=calls//2+1,skippedGroups=skipTotal,skippingCases=skippingCases,allocationCases=allocationCases,longChainCap=dict(nodes=count,skipped=16384,nativeAllocations=3),compared=['selected pointer','all heap bytes including condition keys and cloned nodes','allocation order and sizes','callee-saved registers','ret4 stack balance'],nativeCode=['Find','AND matcher','predicate dispatcher','group constructor except handle leaf','condition clone/link/reset'],controlledStubs=['allocation','reference-handle leaf construction','shader/texture getters','RTTI/property getters'],limitations=['native DLL installer and actual rendering require separate live checks','object getters are controlled read-only stubs'])
 a.out.write_text(json.dumps(result,indent=2));print('LOCAL_FIND_NATIVE_EQUIVALENCE_PASS',json.dumps(result))
if __name__=='__main__':main()
