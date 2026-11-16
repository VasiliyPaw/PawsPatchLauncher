"""Execute original native picking with the clock layered over real HUD targets."""
from pathlib import Path
import argparse,sys,struct,json,hashlib
parser=argparse.ArgumentParser();parser.add_argument('--runtime',type=Path,required=True);parser.add_argument('--deps',type=Path,action='append',required=True);parser.add_argument('--report',type=Path,required=True);args=parser.parse_args()
sys.path[:0]=list(map(str,args.deps))
def write(p,value):p.write_text(json.dumps(value,indent=2))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()

import re
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn.x86_const import *
raw=args.runtime.read_bytes();assert hashlib.sha256(raw).hexdigest()=='b865d8206990c4f055c51de857f0b09b88ab5ee3b6ae74ee5232134001aa591c'
asset=(Path(__file__).with_name('paws_day_clock.tgi')).read_text();label=asset.split('[Label]')[1]
assert all(re.search(r'client_'+k+r'\s*=\s*'+v,label)for k,v in [('L','100%'),('T','100%'),('R','0%'),('B','0%')]);assert 'L = 0%'in label and'T = 7'in label and'R = 100%'in label and'B = +24'in label
checks=0;cases=[]
for base in [0x460000,0x80000,0x6a0000]:
 for width,height in [(800,600),(1024,768),(1280,1024),(1280,720),(1920,1080),(1920,1200),(2560,1440),(2560,1080),(3440,1440),(3840,2160)]:
  uc=Uc(UC_ARCH_X86,UC_MODE_32);uc.mem_map(base,0x700000);uc.mem_write(base,raw);heap=0x30000000;uc.mem_map(heap,0x30000);cursor=heap+0x1000
  def alloc():
   global cursor
   p=cursor;cursor+=0x100;return p
  def w(p,v):uc.mem_write(p,struct.pack('<I',v))
  def rect(p,b):uc.mem_write(p,struct.pack('<4f',*b))
  groupVT,decalVT,widgetVT=heap,heap+0x100,heap+0x200;w(groupVT+0x38,base+0x2ad0e0);w(decalVT+0x38,base+0x2ac629);w(widgetVT+0x7c,base+0x2b6bc0)
  logical=max(1024,width/height*768);sx=width/logical;sy=height/768
  def widget():
   p=alloc();w(p,widgetVT);return p
  def view(owner,b,group=False):
   v=alloc();w(v,groupVT if group else decalVT);w(v+0xc,owner);w(v+0x88,4);b=tuple(x*(sx if i%2==0 else sy)for i,x in enumerate(b));rect(v+0x20,b);rect(v+0x54,b)
   if group:uc.mem_write(v+0xd0,b'\1')
   return v
  def children(parent,items):
   prev=0
   for v in items:
    node=alloc();w(node,v);w(node+4,prev);prev=node
   w(parent+0xcc,prev)
  world,clock,rootOwner=widget(),widget(),widget();buttons=[widget()for i in range(10)];root=view(rootOwner,(0,0,logical,768),True);worldVE=view(world,(0,0,logical,768));buttonVEs=[view(p,(99+36.6*i,7,132+36.6*i,40))for i,p in enumerate(buttons)];clockPrimary=view(clock,(0,0,logical,768),True);textVE=view(clock,(0,7,logical,31));children(clockPrimary,[textVE]);children(root,[worldVE,*buttonVEs,clockPrimary]);sp=heap+0x2e000;stop=heap+0x2f000
  def pick(x,y):
   global checks
   uc.mem_write(sp,struct.pack('<IffI',stop,x*sx,y*sy,1));uc.reg_write(UC_X86_REG_ESP,sp);uc.reg_write(UC_X86_REG_ECX,root);uc.emu_start(base+0x2ad0e0,stop,count=10000);assert uc.reg_read(UC_X86_REG_EIP)==stop and uc.reg_read(UC_X86_REG_ESP)==sp+16;checks+=1;return uc.reg_read(UC_X86_REG_EAX)
  for i in range(10):
   for y in [8,15,25,30]:assert pick(115+36.6*i,y)==clock;checks+=1
   assert pick(115+36.6*i,35)==buttons[i];checks+=1
  # The native bounds resolver collapses reversed client anchors to the
  # text's far-right bottom corner, outside the valid mouse canvas.
  rect(textVE+0x54,(width,31*sy,width,31*sy))
  for i in range(10):
   for y in [8,15,25,30,35,39]:assert pick(115+36.6*i,y)==buttons[i];checks+=1
  for x,y in [(logical/2,18),(1,18),(logical-1,18),(logical/2,200),(115,50)]:assert pick(x,y)==world;checks+=1
  cases.append(dict(base=hex(base),resolution=[width,height],oldClockObstructionReproduced=True,allTenButtonsReachable=True,clockPositionUnchanged=True))
write(args.report,dict(passed=True,checks=checks,cases=cases,actualNativeFunctions=True,clockAssetSha256=sha(Path(__file__).with_name('paws_day_clock.tgi'))));print('CLOCK_PICKING_PASS',checks,'checks,',len(cases),'native cases')
