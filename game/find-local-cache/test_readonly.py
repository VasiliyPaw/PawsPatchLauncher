"""Check real native eligibility and getter purity on valid synthetic NI data.

Native shader/texture getters, RTTI traversal, property lookup and matcher run
unchanged. Only vtable type-query leaves return controlled native type IDs.
"""
import argparse,json,random,struct
from test_native import Uc,UC_ARCH_X86,UC_MODE_32,Ks,KS_ARCH_X86,KS_MODE_32,PROJECT
from unicorn.x86_const import *
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();raw=(PROJECT/'work/kohan-ii-decompilation/inputs/k2_runtime_1372_20260904.bin').read_bytes();base=0x460000;heap=0x30000000;stack=0x20000000;stop=0x40000000;code=0x55000000
 u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(base,(len(raw)+4095)&~4095);u.mem_write(base,raw)
 for at in [heap,stack,stop,code]:u.mem_map(at,0x10000)
 ks=Ks(KS_ARCH_X86,KS_MODE_32);u.mem_write(code,bytes(ks.asm(f'mov eax,{base+0x603724};ret',code)[0]));u.mem_write(code+32,bytes(ks.asm('mov eax,8;ret',code+32)[0]));rng=random.Random(118903);checks=0
 obj=heap+0x1000;vt=heap+0x2000;data=heap+0x3000;render=heap+0x4000;array=heap+0x5000;buffer=heap+0x6000;skin=heap+0x7000;prop=heap+0x8000;propvt=heap+0x9000;node=heap+0xa000;texture=heap+0xb000
 def put(blob,at,v):struct.pack_into('<I',blob,at-heap,v)
 def call(target,ecx,args):
  sp=stack+0x8000;u.mem_write(sp,struct.pack('<'+'I'*(len(args)+1),stop,*args));u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,ecx);u.reg_write(UC_X86_REG_EFLAGS,0x202);u.emu_start(target,stop,count=3000);assert u.reg_read(UC_X86_REG_EIP)==stop;return u.reg_read(UC_X86_REG_EAX),u.reg_read(UC_X86_REG_ESP)
 for i in range(600):
  b=bytearray(0x10000);isSkin=rng.randrange(2);shader=rng.choice([0,1,7,0xffffffff]);tex=rng.choice([0,1,19,0xffffffff]);present=rng.randrange(2)
  for addr,value in [(obj,vt),(vt+4,code),(obj+0xcc,data),(obj+0xd0,skin if isSkin else 0),(data+0x38,render),(render+0x14,1),(render+0x1c,array),(array,buffer),(buffer+8,shader),(skin+0xc,skin+0x100),(skin+0x10c,skin+0x200),(skin+0x210,skin+0x300),(skin+0x328,render),(obj+0xa4,node if present else 0),(node+8,prop),(prop,propvt),(propvt+0x34,code+32),(prop+0x2c,texture),(texture,texture+0x100),(texture+0x104,tex)]:put(b,addr,value)
  prefix=rng.choice([None,(1,1),(1,2),(2,1),(2,2)]);conditions=[]
  if prefix:conditions.append([prefix[0],prefix[1],0,rng.randrange(9)])
  conditions.extend([[1,3,0,rng.choice([1,7,0xffffffff])],[1,5,0,rng.choice([1,19,0xffffffff])]])
  tail=[(2,27),(2,11),(2,9),(2,13),(2,17),(2,21)][:i%7]
  if i%9==0:tail.append((rng.choice([1,2]),rng.choice([7,8,15,16,19,20,22,23,24,25,26,28])))
  conditions.extend([[polarity,kind,0,rng.randrange(9)]for polarity,kind in tail])
  for j,c in enumerate(conditions):c[2]=heap+(j+1)*16 if j+1<len(conditions)else 0;struct.pack_into('<4I',b,j*16,*c)
  u.mem_write(heap,bytes(b));value,esp=call(base+0x18e184,0,(obj,));assert value==shader and esp==stack+0x8008;assert bytes(u.mem_read(heap,len(b)))==b;checks+=1
  value,esp=call(base+0x18e1f5,0,(obj,0));assert value==(tex if present else 0)and esp==stack+0x800c;assert bytes(u.mem_read(heap,len(b)))==b;checks+=1
  expected=shader!=0
  if prefix:
   positive=bool(isSkin)if prefix[1]==1 else not isSkin;expected=expected and(positive if prefix[0]==1 else not positive)
  value,esp=call(base+0x18de67,heap,(obj,0));assert esp==stack+0x800c;assert bytes(u.mem_read(heap,len(b)))==b;checks+=1
  if not tail:assert bool(value&255)==expected
  again,esp=call(base+0x18de67,heap,(obj,0));assert bool(again&255)==bool(value&255)and esp==stack+0x800c;assert bytes(u.mem_read(heap,len(b)))==b;checks+=1
  value,esp=call(base+0x18de67,heap,(obj,1));assert not(value&255)and esp==stack+0x800c;assert bytes(u.mem_read(heap,len(b)))==b;checks+=1
 result=dict(accepted=True,cases=600,checks=checks,nativeGetters=True,nativeRttiAndPropertyTraversal=True,allHeapBytesUnchanged=True,controlledLeaves=['geometry RTTI type getter','property type ID getter'],coverage=['skinned and unskinned renderer-data paths','zero and high-bit keys','present and absent texture property','both skin kinds and polarities','readonly eligibility','occupied strict rejection'])
 from pathlib import Path
 Path(a.out).write_text(json.dumps(result,indent=2));print('LOCAL_FIND_NATIVE_READONLY_PASS',checks,'checks')
if __name__=='__main__':main()
