"""Compiled count hook: restored/outdated values, integer totals, ABI and writes.
Native area scaling is an explicit stub; this is not a generated game map.
"""
import argparse,json,math,struct,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--native',type=Path,required=True);a=p.parse_args()
sys.path[:0]=[str(a.legacy/'lobby_colors_1372/deps_r15')]
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_MEM_WRITE
from unicorn.x86_const import *
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
m=json.loads((a.native/'counts.json').read_text());raw=(a.native/'counts.bin').read_bytes();ks=Ks(KS_ARCH_X86,KS_MODE_32);checks=0
def check(ok,name):
 global checks
 checks+=1
 assert ok,name
def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
class Fixture:
 def __init__(self,image,cave):
  self.image=image;self.cave=cave;self.u=u=Uc(UC_ARCH_X86,UC_MODE_32)
  for at,size in [(image,0x690000),(cave,m['allocation']),(0x51000000,0x20000),(0x61000000,0x10000)]:u.mem_map(at,size)
  b=bytearray(raw)
  for off,im,cv in m['fixups']:struct.pack_into('<I',b,off,(struct.unpack_from('<I',b,off)[0]+im*(image-m['image'])+cv*(cave-m['cave']))&0xffffffff)
  u.mem_write(cave,bytes(b));self.bal=0x51000000;self.ctx=0x51001000;self.creator=0x51002000;self.profile=0x51003000
  self.sg=0x51004000;self.fg=0x51005000;self.og=0x51006000;self.arr=0x51007000;self.values=0x51008000;self.strings=0x51009000;self.sp=0x6100e000
  self.w(self.bal+4,self.ctx);self.w(self.ctx,self.creator);self.w(self.creator,image+0x4fdf7c);self.w(self.creator+0x50,self.profile)
  self.w(self.profile+0x74,self.arr);self.w(self.profile+0x78,2);self.w(self.arr,self.sg);self.w(self.arr+4,self.fg)
  self.w(self.creator+0x64,self.values);self.w(self.creator+0x68,2)
  for i,(g,text) in enumerate([(self.sg,'random_settlementcamps'),(self.fg,'random_foundationcamps'),(self.og,'random_settlements')]):
   string=self.strings+i*256;u.mem_write(string,(text+'\0').encode('utf-16le'));self.w(g+8,string);self.w(g+0x58,0xcdcdcd01);self.f(g+0x20,1.4);self.w(g+0x28,7)
   if i<2:self.w(self.values+i*8,string)
  self.asm(image+0x255e1c,f'fld dword ptr [{self.ctx+32}]; ret 4')
  self.asm(image+m['hook']+8,'nop')
 def w(self,p,v):self.u.mem_write(p,struct.pack('<I',v&0xffffffff))
 def f(self,p,v):self.u.mem_write(p,struct.pack('<f',v))
 def r(self,p):return struct.unpack('<I',self.u.mem_read(p,4))[0]
 def asm(self,p,code):self.u.mem_write(p,bytes(ks.asm(code,p)[0]))
 def run(self,kind,sv,fv,scale,original=123):
  u=self.u;group={'s':self.sg,'f':self.fg,'o':self.og}[kind];self.w(self.bal+8,group)
  self.f(self.values+4,sv);self.f(self.values+12,fv);self.f(self.ctx+32,scale)
  regs={UC_X86_REG_EBX:group,UC_X86_REG_ESI:self.bal,UC_X86_REG_EDI:0x11223344,UC_X86_REG_EBP:self.sp+1024,UC_X86_REG_ECX:0x12345678,UC_X86_REG_EDX:0x23456789}
  for reg,v in regs.items():u.reg_write(reg,v)
  for i in range(8):u.reg_write(UC_X86_REG_XMM0+i,0x12345678123456781234567812345678+i)
  u.reg_write(UC_X86_REG_ESP,self.sp);u.reg_write(UC_X86_REG_EAX,original);u.reg_write(UC_X86_REG_EFLAGS,0x247)
  writes=[];h=u.hook_add(UC_HOOK_MEM_WRITE,lambda u,access,p,n,v,d:writes.append((p,n)))
  u.emu_start(self.cave+m['entry'],self.image+m['hook']+8,count=300000);u.hook_del(h)
  result=self.r(self.bal+0x30)
  check(u.reg_read(UC_X86_REG_EAX)==result,'EAX result');check(u.reg_read(UC_X86_REG_ESP)==self.sp,'stack preserved')
  check(all(u.reg_read(reg)==v for reg,v in regs.items()),'registers preserved')
  check(u.reg_read(UC_X86_REG_EFLAGS)==0x247,'flags preserved')
  check(u.reg_read(UC_X86_REG_XMM0)==7,'displaced movd preserved')
  check(all(u.reg_read(UC_X86_REG_XMM0+i)==0x12345678123456781234567812345678+i for i in range(1,8)),'other SSE registers preserved')
  check(all(0x61000000<=p and p+n<=self.sp or p==self.bal+0x30 and n==4 for p,n in writes),'only stack and native count written')
  return result
for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 f=Fixture(image,cave)
 for total in range(0,101):
  for sv in [0,total/3,total]:
   fv=total-sv;actual_total=int(f32(sv))+int(f32(fv));want=(actual_total+2)//5
   s=f.run('s',sv,fv,1);fd=f.run('f',sv,fv,1)
   check((s,fd)==(actual_total-want,want),'integer total and nearest 20 percent')
 for sv,fv in [(19,15),(4,2),(3.2,.8),(6.4,1.6),(3.2,1.6),(6.4,.8),(0,0)]:
  for width in [256,384,512,768,960,1024,1536]:
   scale=f32((width/256)**f32(1.4));total=int(f32(f32(sv)*scale))+int(f32(f32(fv)*scale));want=(total+2)//5
   pair=(f.run('f',sv,fv,scale),f.run('s',sv,fv,scale))
   check(pair==(want,total-want),'restored values, native truncation, reverse order')
 for case in ['other','missing-group','missing-value','mismatched-scale','unbalanced','unknown-creator','negative','nan','huge','zero-scale','foreign-group']:
  f=Fixture(image,cave);sv,fv,scale=4,2,1;kind='s'
  if case=='other':kind='o'
  if case=='missing-group':f.w(f.profile+0x78,1)
  if case=='missing-value':f.w(f.creator+0x68,1)
  if case=='mismatched-scale':f.f(f.fg+0x20,2)
  if case=='unbalanced':f.w(f.fg+0x58,0xcdcdcd00)
  if case=='unknown-creator':f.w(f.creator,image+0x4fdf80)
  if case=='negative':sv=-1
  if case=='nan':fv=float('nan')
  if case=='huge':sv=10000
  if case=='zero-scale':scale=0
  if case=='foreign-group':f.w(f.profile+0x74,f.arr+4);f.w(f.arr+8,f.og)
  check(f.run(kind,sv,fv,scale)==123,('native fallback',case))
result=dict(passed=True,checks=checks,bases=3,nativeScaleStub=True,playedMap=False)
(a.native/'test-results.json').write_text(json.dumps(result,indent=2));print('FOUNDATION_COUNTS_PASS',checks)
