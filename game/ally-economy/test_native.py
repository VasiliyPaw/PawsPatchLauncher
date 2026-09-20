"""Execute the compiled x86 UI payload, not a Python copy of the policy.
Native UI services are instrumented; selection traversal executes stock code.
"""
import argparse,json,struct,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--native',type=Path,required=True);a=p.parse_args()
sys.path[:0]=[str(a.legacy/'lobby_colors_1372/deps_r15'),str(a.legacy/'pydeps_readable')]
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
meta=json.loads((a.native/'panel.json').read_text());raw=(a.legacy/'k2_runtime_1372_20260904.bin').read_bytes();checks=0
def check(value):
 global checks
 checks+=1
 assert value,checks
class Fixture:
 def __init__(self,image,cave):
  self.i=image;self.c=cave;self.d=cave+meta['dataOffset'];self.u=Uc(UC_ARCH_X86,UC_MODE_32)
  for addr,size in [(image,0x700000),(cave,meta['allocation']),(0x20000000,0x400000),(0x30000000,0x100000),(0x40000000,0x1000)]:self.u.mem_map(addr,size)
  # Only selection's tiny native routines are needed in this fixture.
  for lo,hi in [(0x2e1071,0x2e1085),(0x2e6289,0x2e62a8)]:self.u.mem_write(image+lo,raw[lo:hi])
  b=bytearray((a.native/'panel.bin').read_bytes())
  for off,im,cv in meta['fixups']:struct.pack_into('<I',b,off,(struct.unpack_from('<I',b,off)[0]+im*(image-meta['image'])+cv*(cave-meta['cave']))&0xffffffff)
  self.u.mem_write(cave,bytes(b));self.alloc=0x20001000;self.calls=[];self.labels=[];self.formats=[];self.releases=[];self.color_args=[]
  self.manager=self.new(0x300);self.ui=self.new(0x200);self.selectionManager=self.new(0x40);self.selectionList=self.new(4);self.selection=self.new(0x180)
  self.bar=self.new(0x100);self.widgets=[self.new(0x100) for _ in range(3)];self.resources=self.new(12)
  self.reg=self.new(0x70000);self.world=self.new(0x100);self.local=self.kingdom(1,[1,1,1]);self.other=self.kingdom(2,[0.2,0.8,0.4]);self.other2=self.kingdom(3,[0.8,0.3,0.9]);self.enemy=self.kingdom(4,[1,0,0]);self.neutral=self.kingdom(5,[0.6,0.6,0.6]);self.local_result=self.local
  self.actor=self.new(0x200);self.actorvt=self.new(0x200);self.p(self.actor,self.actorvt);self.p(self.actorvt+0xb4,image+0x601010);self.p(self.actorvt+0x108,image+0x601020);self.actorlive=True;self.owner=self.other
  for r,val in [(0x5f3fc0,self.manager),(0x5f3fbc,self.ui),(0x5f3fb8,self.world),(0x5ef72c,self.reg),(0x5f9218,2)]:self.p(image+r,val)
  self.p(self.ui+0x13c,self.selectionManager);self.p(self.selectionManager+8,self.selectionList);self.p(self.selectionList,self.selection);self.p(self.selection+0x14,self.actor)
  self.p(self.bar+0x74,self.resources);self.p(self.bar+0x78,len(self.widgets));self.p(self.bar+0x24,0);self.p(self.bar+0xa8,0x3e800000)
  for idx,w in enumerate(self.widgets):
   self.p(self.resources+4*idx,w);definition=self.new(0x50);label=self.new(0x100);vt=self.new(0x100)
   self.p(w+0x78,definition);self.p(w+0x74,label);self.p(label,vt);self.p(vt+0xc8,image+0x601030);self.p(definition+0x18,2 if idx==2 else 0 if idx==0 else 1);self.b(w+0x88,idx==0)
   self.p(w+0x7c,struct.unpack('<I',struct.pack('<f',-10.0 if idx==1 else 0.75))[0]);self.p(w+0x80,0x447a0000);self.p(w+0x84,0x41a00000)
  self.u.hook_add(UC_HOOK_CODE,self.hook)
 def new(self,n):r=self.alloc;self.alloc+=(n+15)&~15;return r
 def p(self,addr,val=None):
  if val is None:return struct.unpack('<I',self.u.mem_read(addr,4))[0]
  self.u.mem_write(addr,struct.pack('<I',val&0xffffffff))
 def b(self,addr,val=None):
  if val is None:return self.u.mem_read(addr,1)[0]
  self.u.mem_write(addr,bytes([int(val)]))
 def kingdom(self,id,rgb):
  k=self.new(0x400);vt=self.new(0x200);col=self.new(0x30);self.p(k,vt);self.p(k+0x14,id);self.p(k+0x1f4,col);self.p(self.reg+0x20004+4*id,k);self.p(vt+0x144,self.i+0x601000)
  self.u.mem_write(col+0x18,struct.pack('<fff',*rgb));return k
 def string(self,s):
  addr=self.new(16+2*(len(s)+1))+16;self.p(addr-12,len(s));self.u.mem_write(addr,s.encode('utf-16le')+b'\0\0');return addr
 def ret(self,n=0,value=0):
  sp=self.u.reg_read(UC_X86_REG_ESP);addr=self.p(sp);self.u.reg_write(UC_X86_REG_EAX,value);self.u.reg_write(UC_X86_REG_ESP,sp+4+n);self.u.reg_write(UC_X86_REG_EIP,addr)
 def hook(self,u,addr,size,data):
  if addr==0x40000000:u.emu_stop();return
  if not self.i<=addr<self.i+0x700000:return
  r=addr-self.i;s=u.reg_read(UC_X86_REG_ECX);sp=u.reg_read(UC_X86_REG_ESP);arg=lambda n:self.p(sp+4+4*n)
  if r in (0x2e1071,0x2e6289) or 0x2e1071<r<0x2e1085 or 0x2e6289<r<0x2e62a8:return
  self.calls.append((r,s))
  if r==0x2be624:self.ret(value=self.local_result)
  elif r==0x601010:self.ret(value=int(self.actorlive))
  elif r==0x601020:self.ret(value=self.owner)
  elif r==0x601000:self.ret(4,1 if s in (self.other,self.other2) else 3 if s==self.enemy else 2)
  elif r==0xbf01f:self.p(self.bar+0x24,self.p(self.bar+0x24)|1);self.ret()
  elif r in (0xbfbf0,0x2b61c8,0xbf939,0xbf010):self.ret()
  elif r in (0xbf6ea,0xbf7cf):self.b(s+(0x9c if r==0xbf6ea else 0x9d),0);self.ret()
  elif r==0xbfd31:
   if self.b(s+0xa4)!=arg(0):self.b(s+0xa4,arg(0));self.p(s+0x24,self.p(s+0x24)|0x20000)
   self.ret(4)
  elif r==0x2b7271:self.p(s+0x24,(self.p(s+0x24)&~1)|arg(0));self.ret(4)
  elif r in (0x2bcd9f,0x2bcd63):
   args=[arg(n) for n in range(5 if r==0x2bcd9f else 6)];self.formats.append((r,args));self.p(args[0],self.string('\ue0010.75/20' if r==0x2bcd9f else '\ue0011000(+1)' if args[4] else '\ue001-10'));self.ret()
  elif r==0x1ada8c:
   self.color_args.append((arg(2),arg(3),bytes(self.u.mem_read(arg(4),12))));self.p(arg(0),self.string('colored'));self.ret()
  elif r==0x601030:self.labels.append((s,self.p(arg(0))));self.ret(4)
  elif r==0x21375:self.releases.append(s);self.ret()
  elif r==0xc0575:self.ret(4)
  else:raise AssertionError(hex(r))
 def call(self,name,obj=None,wrapper=None,extra=()):
  if obj is None:obj=self.bar
  sp=0x300f0000;args=(self.i,self.d,obj) if wrapper is None else extra
  self.u.mem_write(sp,struct.pack('<'+'I'*(len(args)+1),0x40000000,*args));self.u.reg_write(UC_X86_REG_ESP,sp);self.u.reg_write(UC_X86_REG_ECX,obj)
  for reg,val in [(UC_X86_REG_EBX,0x12345678),(UC_X86_REG_ESI,0x23456789),(UC_X86_REG_EDI,0x3456789a),(UC_X86_REG_EBP,0x456789ab)]:self.u.reg_write(reg,val)
  entry=self.c+(meta['exports'][name] if wrapper is None else meta['hooks'][wrapper]['offset']);self.u.emu_start(entry,0x40000000,count=150000)
  check(self.u.reg_read(UC_X86_REG_EIP)==0x40000000)
  for reg,val in [(UC_X86_REG_EBX,0x12345678),(UC_X86_REG_ESI,0x23456789),(UC_X86_REG_EDI,0x3456789a),(UC_X86_REG_EBP,0x456789ab)]:check(self.u.reg_read(reg)==val)
  check(self.u.reg_read(UC_X86_REG_ESP)==sp+4+(len(extra)*4 if wrapper==3 else 0))
 def active(self):check(self.p(self.d+12)==1 and self.p(self.bar+0xa0)==self.p(self.owner+0x14) and self.b(self.bar+0x80)==1)
for image,cave in [(0x460000,0x10000000),(0xf20000,0x11000000),(0x18000000,0x12000000)]:
 f=Fixture(image,cave);simulation=bytes(f.u.mem_read(f.local,0x400))+bytes(f.u.mem_read(f.other,0x400))
 f.call('tick',wrapper=0);f.active();check(f.b(f.bar+0xa4)==1 and f.p(f.bar+0xa8)==0x3e800000)
 for w in f.widgets:f.call('resource_tick',w,wrapper=1)
 check(len(f.labels)==3 and len(f.releases)==6);check(all(x[0]==1 for x in f.color_args));check(all(x[2]==struct.pack('<fff',1,1,1) for x in f.color_args))
 check(f.formats[0][1][3]==0 and f.formats[0][1][4]==1);check(f.formats[1][1][3]==0 and f.formats[1][1][4]==0);check(f.formats[2][1][4]==0 and f.formats[2][1][2]==0x3f400000)
 f.owner=f.other2;f.call('tick');f.active();check(bytes(f.u.mem_read(f.d+20,12))==struct.pack('<fff',1,1,1))
 # Changing kingdoms keeps white numbers; the normal top row is untouched.
 outsider=f.new(0x100);f.call('resource_tick',outsider);check(f.calls[-1][0]==0xbf939)
 source=f.new(0x100);f.p(source+0x24,8);f.p(f.bar+0xd0,source);f.b(f.bar+0xd8,1);f.b(f.bar+0x9c,1)
 f.call('tick');check(f.p(f.d+12)==0 and f.p(f.bar+0xa0)==0 and f.b(f.bar+0x80)==0 and f.b(f.bar+0x9c)==1 and f.calls[-1][0]==0xbfbf0)
 f.p(source+0x24,0);f.call('tick');f.active();check(f.b(f.bar+0x9c)==0 and f.b(f.bar+0xd8)==0)
 # Pinned recruitment forecast has priority even without a hover source.
 f.b(f.bar+0xd8,1);f.b(f.bar+0xd9,1);f.call('tick');check(f.p(f.d+12)==0);f.b(f.bar+0xd9,0);f.b(f.bar+0xd8,0)
 for reason in ('self','enemy','neutral','none','dead','observer','missing','inactive'):
  f.owner=f.other;f.actorlive=True;f.local_result=f.local;f.p(f.selection+0x14,f.actor);f.p(image+0x5f9218,2);f.p(f.reg+0x20004+8,f.other);f.call('tick');f.active()
  if reason in ('self','enemy','neutral'):f.owner={'self':f.local,'enemy':f.enemy,'neutral':f.neutral}[reason]
  elif reason=='none':f.p(f.selection+0x14,0)
  elif reason=='dead':f.actorlive=False
  elif reason=='observer':f.local_result=0
  elif reason=='missing':f.p(f.reg+0x20004+8,0)
  else:f.p(image+0x5f9218,0)
  f.calls=[];f.call('tick');check(f.p(f.d+12)==2 and all(r!=0xbf01f for r,s in f.calls));check(f.b(f.bar+0xa4)==0)
  f.p(f.bar+0x24,f.p(f.bar+0x24)&~0x20000);f.call('tick');check(f.p(f.d+12)==0 and f.p(f.bar+0xa0)==0 and not(f.p(f.bar+0x24)&1))
 f.p(image+0x5f9218,2);f.owner=f.other;f.call('tick');f.active()
 f.call('reset',wrapper=2);check(f.p(f.d+4)==0 and f.p(f.d+12)==0)
 f.call('tick');f.call('reset',wrapper=3,extra=(1,));check(f.p(f.d+4)==0)
 check(simulation==bytes(f.u.mem_read(f.local,0x400))+bytes(f.u.mem_read(f.other,0x400)))
print('ALLY_ECONOMY_NATIVE_PASS',checks,'checks; 3 ASLR layouts; selection/relations/forecast/color/lifecycle/ABI; simulation untouched')
