"""Real x86 payload + original engine regression, guarded preload/lifecycle cases."""
import argparse,json,struct,sys
from pathlib import Path
LEG=Path('G:/CodexData/projects/Codex/2026-08-11/kohan-ii-d-steamlibrary-steamapps-common/work')
sys.path[:0]=[str(LEG/'pydeps_readable'),str(LEG/'lobby_colors_1372/deps_r15')]
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
RAW=(LEG/'k2_runtime_1372_20260904.bin').read_bytes()
IMAGE=0x460000;CAVE=0x10000000;HEAP=0x20000000;STACK=0x28000000;STOP=0x30000000

class Rig:
 def __init__(self,meta,payload,image=IMAGE,cave=CAVE):
  self.image=image;self.cave=cave;self.meta=meta;self.calls=[];self.clock=1000;self.low=False;self.locks=0
  self.u=Uc(UC_ARCH_X86,UC_MODE_32)
  for at,n in [(image,0x700000),(cave,meta['size']),(HEAP,0x100000),(STACK,0x100000),(STOP,0x1000)]:self.u.mem_map(at,(n+4095)&~4095)
  if image==IMAGE:self.u.mem_write(image,RAW)
  code=bytearray(payload)
  for off,im,cv in meta['fixups']:
   struct.pack_into('<I',code,off,(struct.unpack_from('<I',code,off)[0]+im*(image-IMAGE)+cv*(cave-CAVE))&0xffffffff)
  self.u.mem_write(cave,bytes(code));self.state=cave+meta['state'];self.put(self.state,image,STOP+0x100,STOP+0x200,3)
  self.u.hook_add(UC_HOOK_CODE,self.hook)
 def put(self,p,*v):self.u.mem_write(p,struct.pack('<'+'I'*len(v),*v))
 def get(self,p):return struct.unpack('<I',self.u.mem_read(p,4))[0]
 def ret(self,value=0,args=0):
  sp=self.u.reg_read(UC_X86_REG_ESP);at=self.get(sp);self.u.reg_write(UC_X86_REG_EAX,value);self.u.reg_write(UC_X86_REG_ESP,sp+4+args);self.u.reg_write(UC_X86_REG_EIP,at)
 def hook(self,u,at,n,data):
  if at==STOP:u.emu_stop();return
  sp=u.reg_read(UC_X86_REG_ESP);ecx=u.reg_read(UC_X86_REG_ECX)
  if at==self.image+0x1b61c8:
   self.put(ecx+8,self.get(sp+4));self.put(ecx+0x18,self.get(sp+8));self.ret(args=8)
  elif at==self.image+0x64679:
   key=self.get(self.get(sp+4));table=self.get(ecx);node=self.get(table)
   while node and self.get(node)!=key:node=self.get(node+8)
   self.ret(node,args=4)
  elif at==self.image+0x49894:
   if not self.get(ecx+8) and not self.get(ecx+4):self.put(ecx+8,self.get(self.get(self.get(ecx))));self.put(ecx+4,1)
   self.ret()
  elif at==STOP+0x100:self.clock+=1;self.ret(self.clock)
  elif at==STOP+0x200:
   p=self.get(sp+4);b=struct.pack('<II7Q',64,95 if self.low else 30,8<<30,64<<20 if self.low else 6<<30,8<<30,6<<30,4<<30,2<<30,0);self.u.mem_write(p,b);self.ret(1,args=4)
  elif at==self.image+0x1c99f4:
   assert self.locks==1 and self.get(sp+4)==1 and self.get(sp+8)==1;self.calls.append(('request',ecx));self.put(ecx+4,1);self.put(ecx+8,self.get(ecx+8)|1);self.ret(args=8)
  elif at==self.image+0x1c6eb8:assert self.locks==0;self.ret()
  elif at==STOP+0x300:self.locks+=1;self.ret()
  elif at==STOP+0x400:self.locks-=1;assert self.locks==0;self.ret()
  elif at==self.image+0x18ac10:self.calls.append(('gpu',self.get(sp+4)));self.ret(args=4)
  elif at==self.image+0x1c9aea:
   assert self.get(sp+4)==1 and self.get(ecx+4)==1;self.calls.append(('release',ecx));self.put(ecx+4,0);self.put(ecx+8,self.get(ecx+8)|0x20);self.ret(args=4)
 def call(self,at,args=(),ecx=0):
  sp=STACK+0x80000;self.put(sp,STOP,*args)
  registers=[UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP]
  for i,r in enumerate(registers):self.u.reg_write(r,0x11220000+i*0x101)
  self.u.reg_write(UC_X86_REG_ECX,ecx);self.u.reg_write(UC_X86_REG_ESP,sp);self.u.reg_write(UC_X86_REG_MXCSR,0x1f80)
  self.u.reg_write(UC_X86_REG_XMM0,0x99887766554433221122334455667788)
  self.u.emu_start(at,STOP+1,count=2000000)
  assert [self.u.reg_read(r) for r in registers]==[0x11220000+i*0x101 for i in range(4)],'callee-saved register corruption'
  return self.u.reg_read(UC_X86_REG_ESP)-sp
 def caches(self):
  m=HEAP+0x100;table=HEAP+0x200;nodes=HEAP+0x300;cache=HEAP+0x1000
  self.put(m+0x20,table,1);self.put(table,nodes);self.put(m+0x30,0,510000000,51,0,180000000,90)
  for i,(rw,vw) in enumerate([(30,30),(20,20),(1,40)]):
   p=cache+i*0x100;self.put(nodes+i*12,101+i,p,nodes+(i+1)*12 if i<2 else 0);self.put(p+4,101+i);self.put(p+0x14,rw);self.put(p+0x24,vw)
  return m,[cache+i*0x100 for i in range(3)]

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--native',type=Path,required=True);a=ap.parse_args();meta=json.loads((a.native/'payload.json').read_text());payload=(a.native/'payload.bin').read_bytes();passed=[]
 # Execute the actual original SetWeights binary: the last class destroys the
 # other classes' VRAM quotas. The corrected wrapper must fail that regression.
 rig=Rig(meta,payload);m,c=rig.caches();rig.call(IMAGE+0x1b5c02,(c[2],1,0),m)
 assert len({rig.get(p+8) for p in c})==1 and all(rig.get(p+0x18)==0 for p in c);passed.append('original engine bug reproduced from retail instructions')
 for image,cave in [(IMAGE,CAVE),(0x1200000,0x41000000),(0x3100000,0x61000000)]:
  for ram,vram in [(1,0),(40,50),(0,0),(0xffffffff//1000,0xffffffff//2000)]:
   r=Rig(meta,payload,image,cave);m,c=r.caches();r.call(cave+meta['hooks'][1]['entry'],(c[2],ram,vram),m)
   tr=50+ram;tv=50+vram
   for p in c:
    assert r.get(p+8)==510000000*r.get(p+0x14)//tr
    assert r.get(p+0x18)==180000000*r.get(p+0x24)//tv
   assert sum(r.get(p+8) for p in c)<=510000000 and sum(r.get(p+0x18) for p in c)<=180000000
   assert r.u.reg_read(UC_X86_REG_XMM0)==0x99887766554433221122334455667788
   assert r.u.reg_read(UC_X86_REG_ESP)==STACK+0x80000+16
   passed.append('budgets and ABI at '+hex(image)+' '+str((ram,vram)))
 # Pending class construction, including the all-zero budget edge case.
 for zero in [False,True]:
  r=Rig(meta,payload);m,c=r.caches();p=HEAP+0x1500;r.put(p+4,199)
  if zero:
   r.put(m+0x30,0,0,0,0,0,0)
   for q in c:r.put(q+0x14,0);r.put(q+0x24,0)
  r.call(CAVE+meta['hooks'][1]['entry'],(p,0 if zero else 10,0),m)
  assert r.get(m+0x38)==(0 if zero else 61)
  assert r.get(p+8)==(0 if zero else 510000000*10//61);passed.append('pending cache construction zero='+str(zero))
 # Scope and memory/battle guards execute the same native rc_tick export.
 def preload(phase=6,paused=1,low=False,cache=True,full=True,in_use=False,pending=False,occupied=False):
  r=Rig(meta,payload);r.low=low;m,c=r.caches();manager=m-0x9c;r.put(IMAGE+0x5f3fd4,manager);r.put(r.state+100,1);r.put(r.state+12,3 if full else 1)
  r.put(IMAGE+0x5f3fb8,HEAP+0x50000);r.put(IMAGE+0x5f92f4,phase)
  uv=HEAP+0x60000;r.put(IMAGE+0x5f9480,uv);r.put(uv+0xfc,uv+0x400);r.put(uv+0x400,int(cache))
  sim=HEAP+0x61000;r.put(IMAGE+0x5f3fe8,sim);r.put(sim+0x28,paused)
  renderer=HEAP+0x62000;r.put(IMAGE+0x5f3f98,renderer);r.put(renderer+0x40,renderer+0x100)
  r.put(IMAGE+0x5fc910,101);r.put(IMAGE+0x5fc924,102)
  for q in c:r.put(q+8,100<<20);r.put(q+0x18,100<<20)
  mutex=HEAP+0x64000;r.put(manager+0x20,mutex);r.put(mutex+4,STOP+0x300,STOP+0x400)
  if occupied:
   for q in c:r.put(q+0xc,80<<20)
  t=HEAP+0x7000;node=HEAP+0x7100;r.put(manager+0x60,t,1);r.put(t,node)
  paths=['Units/Human/Soldier/Soldier.nif','Units/Human/Soldier/SoldierIdle.kf','Spells/Fire/Fire.nif','Units/Hero/HeroPortrait.nif','Special/MenuBackground/menu.nif']
  for i,name in enumerate(paths):
   p=HEAP+0x8000+i*0x100;w=HEAP+0x9000+i*0x200;r.put(node+i*8,p,node+(i+1)*8 if i<4 else 0);r.put(p,IMAGE+(0x4d3510 if i==1 else 0x4d34a4));r.put(p+0x14,1);r.put(p+0x38,w);r.put(p+0x40,HEAP+0xa000+i*0x100);r.u.mem_write(w,name.encode('utf-16le')+b'\0\0')
   if in_use:r.put(p+4,1)
   if pending:r.put(p+0x20,HEAP+0x65000);r.put(HEAP+0x65010,1)
  for _ in range(6):r.clock+=100;r.call(CAVE+meta['exports']['rc_tick'],(r.state,))
  return r
 for kw,expected in [({},3),({'phase':4,'paused':0},0),({'phase':4,'paused':1},3),({'phase':2},0),({'low':True},0),({'cache':False},0),({'full':False},0),({'in_use':True},0),({'pending':True},0),({'occupied':True},0)]:
  r=preload(**kw);req=[p for typ,p in r.calls if typ=='request'];rel=[p for typ,p in r.calls if typ=='release'];assert len(req)==expected and req==rel,(kw,r.calls)
  if expected:assert r.get(r.state+44)==2 and r.get(r.state+48)==1
  passed.append('prewarm policy '+str(kw))
 (a.native/'native-tests.json').write_text(json.dumps(dict(accepted=True,cases=len(passed),checks=passed),indent=2));print('RESOURCE_CACHE_NATIVE_TEST_PASS',len(passed))
if __name__=='__main__':main()
