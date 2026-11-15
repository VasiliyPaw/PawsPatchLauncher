"""Execute the compiled planner against explicit native ABI fixtures.
These are synthetic policy/route/ownership checks, not live-match acceptance.
"""
from pathlib import Path
import argparse,json,struct,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'terrain-prototype'))
from audit import RAW,BASE
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *

p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args()
m=json.loads((args.out/'native/prototype.json').read_text());blob=(args.out/'native/prototype.bin').read_bytes()
checks=0
class Fixture:
 def __init__(self,image,cave):
  self.image=image;self.cave=cave;self.u=Uc(UC_ARCH_X86,UC_MODE_32);u=self.u
  u.mem_map(image,(len(RAW)+4095)&~4095);u.mem_write(image,RAW);code=bytearray(blob)
  for off,im,cv in m['fixups']:struct.pack_into('<I',code,off,(struct.unpack_from('<I',code,off)[0]+im*(image-BASE)+cv*(cave-0x10000000))&0xffffffff)
  u.mem_map(cave,m['size']);u.mem_write(cave,bytes(code));u.mem_map(0x20000000,0x1000000);u.mem_map(0x30000000,0x20000)
  self.state=cave+m['roadState'];self.world=0x20000000;self.session=0x20001000;self.grid=0x20002000;self.tiles=0x20010000;self.reg=0x20100000
  self.human=0x20200000;self.kingdom=0x20201000;self.ally=0x20202000;self.enemy=0x20203000;self.sai=0x20204000;self.pl=0x20205000;self.engine=0x20206000
  self.builder=0x20210000;self.unit=0x20211000;self.army=0x20212000;self.other=0x20213000;self.danger=0x20214000
  self.strings=0x20300000;self.nextString=self.strings;self.db=0x20400000;self.defs={};self.nextDef=self.db+0x1000;self.heap=0x20800000
  self.upkeepOverride=None;self.visible=True;self.known=True;self.nativeQueues=0;self.clock=0
  self.jobLayout=self.constants('bridge_ai_job_layout',6);self.aiLayout=self.constants('bridge_ai_layout',5)
  self.w(self.state,image);self.w(self.state+4,cave+m['adapter']);self.w(self.state+12,self.world)
  self.call('roads_bind',[self.state])
  self.w(image+0x5f3fb8,self.world);self.w(image+0x5f3fe4,self.session);self.w(image+0x5f9218,2);self.w(image+0x5ef72c,self.reg);self.w(image+0x5f3fc0,0)
  self.w(self.session+0xf0,2);self.w(self.world+0x30,self.grid);self.w(self.grid+4,1);self.w(self.grid+0x1c,96);self.w(self.grid+0x20,96);self.w(self.grid+0x28,self.tiles)
  self.w(image+0x5f3fc8,self.sai);self.w(self.sai+0x6c,self.sai+0x100);self.w(self.sai+0x70,1);self.w(self.sai+0x100,self.pl);self.w(self.pl+8,self.kingdom);self.w(self.pl+0xc,self.engine)
  self.w(self.world+0x150,self.world+0x100);self.w(self.world+0x154,4)
  for i,k in enumerate([self.human,self.kingdom,self.ally,self.enemy]):self.w(self.world+0x100+i*4,k);self.w(k+0x14,i+1)
  self.w(self.kingdom+0x1f8,7);self.w(self.ally+0x1f8,7)
  self.grass=self.definition('temperate_grass01');self.water=self.definition('temperate_river01')
  for y in range(96):
   for x in range(96):
    c=self.cell(x,y);wet=46<=x<=50;self.w(c,self.water if wet else self.grass);self.w(c+32,0x120 if wet else 0x200);rect=0x20500000+(y*96+x)*16;self.w(c+16,rect);self.w(rect+8,1 if x<46 else 2)
  for off in [0x34,0x38]:
   hm=self.world+0x3000+off*16;self.w(self.world+off,hm);self.w(hm+0xc,97);self.w(hm+0x10,97);self.w(hm+0x14,1);self.w(hm+0x1c,1);self.w(hm+0x40,0x20600000+(off-0x34)*0x10000)
   for y in range(97):
    for x in range(97):self.f(self.r(hm+0x40)+(y*97+x)*4,(-1 if 46<=x<=50 else 1) if off==0x34 else 0)
  self.w(self.state+self.call('bridge_field',[0]),self.world)
  self.make_actor(self.builder,100,self.kingdom,31,81);self.make_actor(self.unit,101,self.kingdom,31,81);self.make_actor(self.army,102,self.kingdom,25,97);self.make_actor(self.other,200,self.ally,31,101)
  self.w(self.unit+4,self.definition('Human_Engineer'));self.w(self.unit+0xa8,self.unit+0x400);self.w(self.unit+0x400,image+0x4df830);self.w(self.unit+0x404,self.unit)
  self.w(self.unit+0x60,self.unit+0x500);self.w(self.unit+0x504,self.unit);self.f(self.unit+0x510,100);self.f(self.unit+0x514,100)
  self.w(self.builder+0x7c,self.builder+0x400);self.w(self.builder+0x404,self.builder);self.w(self.builder+0x42c,1);self.w(self.builder+0x428,self.builder+0x700);self.w(self.builder+0x700,self.unit)
  self.w(self.unit+0x80,self.unit+0x600);self.w(self.unit+0x604,self.unit);self.w(self.unit+0x610,self.builder)
  builddef=self.r(self.unit+4);self.w(builddef+0x504,builddef+0x600);self.w(builddef+0x600,self.definition('paws_bridge_human_wood_site'));self.w(builddef+0x604,builddef+0x610);self.w(builddef+0x610,self.definition('paws_bridge_human_stone_site'))
  self.w(self.army+0x7c,self.army+0x400)
  self.idle(self.builder);self.move(self.army,167,97)
  for i,a in enumerate([self.builder,self.army]):
   node=self.pl+0x400+i*0x100;sa=node+0x30;self.w(node,sa);self.w(node+4,node+0x100 if i==0 else 0);self.w(sa+8,self.r(a+0x14));self.w(sa+0xc,self.pl)
  self.w(self.pl+0x2c,self.pl+0x400)
  self.w(image+0x5f3fb4,self.db);self.w(self.db+0xc,self.db+0x800)
  table=self.db+0x50000;self.w(image+0x5efa8c,table);self.w(table+0x24,table+0x100);self.w(table+0x28,3)
  for i,name in enumerate(['gold','stone','wood']):
   rd=self.definition(name);self.w(rd+0x18,0 if i==0 else 1);self.w(rd+0xc,i);self.w(table+0x100+i*4,rd)
  self.w(self.kingdom+0x1d0,3)
  for off in [0x1a8,0x1c0,0x1cc]:self.w(self.kingdom+off,self.kingdom+0x1000+off*16)
  self.f(self.r(self.kingdom+0x1cc),2000)
  for i in [1,2]:self.f(self.r(self.kingdom+0x1a8)+i*4,30)
  self.w(image+0x5f0030,self.db+0x70000);self.w(self.db+0x70024,self.db+0x70100);self.w(self.db+0x70028,3)
  for i,v in enumerate([self.grass,self.water,self.definition('paws_engineer_bridge01')]):self.w(self.db+0x70100+i*4,v)
  for off in [0x2be624,0x24a845,0x24a86a,0x2ef03c,0x3e1285,0x205de,0x21375,0x2edb9,0x2277b6,0x29eaa,0x2351d7,0x1f2c29,0x300000]:
   u.hook_add(UC_HOOK_CODE,self.native,begin=image+off,end=image+off)
 def constants(self,name,n):return struct.unpack('<'+'I'*n,self.u.mem_read(self.cave+m['exports'][name],n*4))
 def w(self,a,v):self.u.mem_write(a,struct.pack('<I',int(v)&0xffffffff))
 def f(self,a,v):self.u.mem_write(a,struct.pack('<f',v))
 def r(self,a):return struct.unpack('<I',self.u.mem_read(a,4))[0]
 def string(self,text):a=self.nextString;raw=(text+'\0').encode('utf-16le');self.nextString+=len(raw)+32;self.u.mem_write(a,raw);return a
 def text(self,a):
  b=bytearray()
  while a and len(b)<1024:
   c=bytes(self.u.mem_read(a,2));a+=2
   if c==b'\0\0':break
   b.extend(c)
  return b.decode('utf-16le')
 def definition(self,name):
  if name not in self.defs:
   d=self.nextDef;self.nextDef+=0x1000;self.defs[name]=d;self.w(d+8,self.string(name));self.w(d+0x328,3);self.w(d+0x330,d+0x900);self.w(d+0x334,3);self.f(d+0x900+(2 if 'wood' in name else 1)*4,10)
  return self.defs[name]
 def make_actor(self,a,id,k,x,y):self.w(a,self.image+0x4e5c58);self.w(a+0x14,id);self.w(a+0xe8,k);self.f(a+0x20,x);self.f(a+0x24,y);self.w(self.reg+0x20004+(id&65535)*4,a)
 def cell(self,x,y):return self.tiles+(y*96+x)*48
 def idle(self,a):self.w(a+0x70,a+0x800);self.w(a+0x814,a+0x900);self.w(a+0x900,a+0xa00);self.w(a+0xa00,self.image+0x4f4d98)
 def move(self,a,x,y):
  self.idle(a);cmd=a+0xb00;self.w(a+0x820,cmd);self.w(cmd+8,self.definition('move'));self.w(self.r(cmd+8)+0xc,5);self.w(cmd+0xc,4);self.f(cmd+0x18,x);self.f(cmd+0x1c,y)
 def call(self,name,values=(),selfptr=0,ecx2=0,limit=60000000):
  u=self.u;sp=0x3000f000;u.mem_write(sp,struct.pack('<'+'I'*(len(values)+1),0x3001f000,*values));u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,selfptr);u.reg_write(UC_X86_REG_EDX,ecx2)
  u.emu_start(self.cave+m['exports'][name] if isinstance(name,str) else name,0x3001f000,count=limit)
  assert u.reg_read(UC_X86_REG_EIP)==0x3001f000,(name,hex(u.reg_read(UC_X86_REG_EIP)))
  return u.reg_read(UC_X86_REG_EAX)
 def native(self,u,addr,size,_):
  off=addr-self.image;sp=u.reg_read(UC_X86_REG_ESP);obj=u.reg_read(UC_X86_REG_ECX);ret=0;clean=0
  if off==0x2be624:ret=self.human
  elif off==0x24a845:ret=int(self.known);clean=4
  elif off==0x24a86a:ret=int(self.visible);clean=4
  elif off==0x2ef03c:ret=self.heap
  elif off==0x3e1285:pass
  elif off==0x205de:self.w(obj,self.r(sp+4));clean=4
  elif off==0x21375:pass
  elif off==0x2edb9:ret=self.definition(self.text(self.r(sp+4)));clean=4
  elif off==0x2277b6:ret=0
  elif off==0x29eaa:
   
   if self.upkeepOverride is not None:
    for i in range(3):self.f(self.r(obj+0x330)+i*4,self.upkeepOverride.get(i,0))
   dest=self.r(self.r(sp+4));cost=160 if 'wood' in self.text(self.r(obj+8)) else 320;self.f(dest,cost);self.f(dest+4,0);self.f(dest+8,0);clean=8
  elif off==0x2351d7:ret=1;clean=4
  elif off==0x1f2c29:self.nativeQueues+=1;clean=8
  elif off==0x300000:ret=3;clean=4
  else:return
  u.reg_write(UC_X86_REG_EAX,ret);u.reg_write(UC_X86_REG_ESP,sp+4+clean);u.reg_write(UC_X86_REG_EIP,self.r(sp))
 def tick(self,t):self.f(self.world+0xe8,t);self.call('bridge_ai_check_tick',[self.state,fb(t)])
 def count(self,index):return self.r(self.state+self.aiLayout[0]+self.aiLayout[4]+4*index)
 def run(self,end=30):
  while self.clock<end:self.tick(self.clock);self.clock+=.2
 def intent(self):
  off,size,tools,*_=self.jobLayout;q=self.state+off+size;self.w(q,200);self.w(q+4,3);pts=[x|(48<<16)for x in range(42,56)];self.w(q+32,len(pts))
  for i,v in enumerate(pts):self.w(q+44+i*4,v)
  self.w(self.state+tools+4,1)

def fb(x):return struct.unpack('<I',struct.pack('<f',x))[0]
for image,cave in [(BASE,0x10000000),(0x210000,0x1600000)]:
 f=Fixture(image,cave)
 assert f.call('bridge_layout_size')+0x300<=m['size']-m['state'];checks+=1
 for before,after,want in [(200,150,1),(200,151,0),(100,60,0),(300,200,1),(1e28,100,1),(1e29,100,0),(200,1e29,0),(float('nan'),100,0)]:assert f.call('bridge_ai_useful_check',[fb(before),fb(after)])==want;checks+=1
 f.run();assert f.count(2)==1,('no useful project',f.count(0),f.count(1),f.count(2),f.count(8),f.count(6));checks+=1
 job,jobsize,tools,construction,*_=f.jobLayout;assert f.r(f.state+job)==100 and f.r(f.state+job+4)==2;checks+=2
 assert all(f.r(f.cell(x,48)+32)==0x120 for x in range(46,51));checks+=1
 f.run(50);assert f.count(2)==1;checks+=1
 # Reserved single-company SAI move is held; a mixed command releases it.
 envelope=0x20700000;container=envelope+0x100;node=container+0x100;cmd=envelope+0x400
 f.w(envelope,image+0x4dc574);f.w(envelope+4,container);f.w(container+8,node);f.w(node,100);f.w(envelope+0x10,cmd);f.w(cmd+8,f.definition('move'))
 hook=cave+next(h['entry']for h in m['hooks']if h['site']==0x1f2c0e)
 saved={UC_X86_REG_EBX:0x12345678,UC_X86_REG_ESI:0x34567890,UC_X86_REG_EDI:0x45678901,UC_X86_REG_EBP:0x56789012}
 for reg,v in saved.items():f.u.reg_write(reg,v)
 xmm=0x112233445566778899aabbccddeeff00;f.u.reg_write(UC_X86_REG_XMM3,xmm)
 f.call(hook,[f.pl+0x180,envelope],selfptr=f.pl);assert f.u.reg_read(UC_X86_REG_ESP)==0x3000f00c and f.nativeQueues==0 and f.count(9)==1;checks+=3
 f.w(cmd+8,f.definition('construct'));f.call(hook,[f.pl+0x180,envelope],selfptr=f.pl);assert f.nativeQueues==0 and f.count(9)==2;checks+=1
 assert all(f.u.reg_read(reg)==v for reg,v in saved.items())and f.u.reg_read(UC_X86_REG_XMM3)==xmm;checks+=1
 f.w(node+4,node+16);f.w(node+16,102);f.call(hook,[f.pl+0x180,envelope],selfptr=f.pl);assert f.nativeQueues==1 and f.r(f.state+job)==0;checks+=2
 f=Fixture(image,cave);f.run(30);assert f.count(2)==1
 f.move(f.army,167,15);f.tick(32);assert f.count(4)==1 and f.r(f.state+f.jobLayout[0])==0;checks+=2
 # A saved paid bridge with its native repair command is restored immediately.
 f=Fixture(image,cave);site=f.danger;f.make_actor(site,300,f.kingdom,97,97);f.w(site+4,f.definition('paws_bridge_wood_y_12'));f.f(site+0x2c,1);f.w(site+0x100,0x200000)
 f.w(site+0x60,site+0x500);f.f(site+0x510,100);f.f(site+0x514,2000)
 f.f(f.builder+0x20,85);f.f(f.builder+0x24,97);f.move(f.builder,85,97);cmd=f.builder+0xb00;f.w(cmd+8,f.definition('repair'));f.w(f.r(cmd+8)+0xc,3);f.w(cmd+0xc,1);f.w(cmd+0x10,300)
 f.w(f.state+f.call('bridge_field',[1]),1);f.w(f.state+f.call('bridge_field',[2]),300)
 f.tick(0);assert f.count(10)==1 and f.count(2)==0 and f.r(f.state+f.jobLayout[3])==300;checks+=3
 f.w(site+0x100,0);f.tick(21);assert f.count(3)==1 and f.r(f.state+f.jobLayout[0])==0;checks+=2
 for scenario in ['no-money','no-income','unknown-land','danger','existing-bridge','allied-intent','human-only','dead-builder','currency-supported','rich-bankrupt','native-upkeep-precharged','native-goal','cancelled-goal','blocked-bank','race-upkeep-vector','multiple-upkeep-shortage']:
  f=Fixture(image,cave)
  if scenario=='race-upkeep-vector':
   f.upkeepOverride={1:5};f.f(f.r(f.kingdom+0x1a8)+4,20);f.f(f.r(f.kingdom+0x1a8)+8,-5)
  if scenario=='multiple-upkeep-shortage':
   f.upkeepOverride={1:5,2:7};f.f(f.r(f.kingdom+0x1a8)+4,4);f.f(f.r(f.kingdom+0x1a8)+8,8)
  if scenario=='no-money':f.f(f.r(f.kingdom+0x1cc),200)
  if scenario=='no-income':
   for i in [1,2]:f.f(f.r(f.kingdom+0x1a8)+i*4,-5 if scenario=='native-upkeep-precharged'else 9)
  if scenario=='unknown-land':f.known=False
  if scenario=='danger':f.make_actor(f.danger,300,f.enemy,97,97);f.w(f.danger+0x7c,f.danger+0x400);f.w(image+0x4e5c58+0x144,image+0x300000)
  if scenario=='blocked-bank':
   f.make_actor(f.danger,300,f.kingdom,111,97);f.w(f.danger+4,f.definition('bank_building'))
  if scenario=='existing-bridge':
   for y in range(46,51):
    for x in range(46,51):f.w(f.cell(x,y)+32,0x200)
   # Native completed bridge connectivity is already mapped on its dry banks.
   for y in range(96):
    for x in range(96):f.w(f.r(f.cell(x,y)+16)+8,1)
  if scenario=='allied-intent':f.intent()
  if scenario=='human-only':f.w(f.pl+8,f.human)
  if scenario=='dead-builder':f.w(f.builder+8,1)
  if scenario in ['currency-supported','rich-bankrupt','native-upkeep-precharged','native-goal','cancelled-goal']:
   f.f(f.r(f.kingdom+0x1a8),45 if scenario=='native-upkeep-precharged'else 100 if scenario in ['currency-supported','native-goal','cancelled-goal']else 10)
   f.f(f.r(f.kingdom+0x1cc),20000)
   for i,name in enumerate(['stone','wood'],1):
    rd=f.definition(name);f.w(rd+0x1c,rd+0x800);f.w(rd+0x20,3);f.f(rd+0x800,i+1);f.f(f.r(f.kingdom+0x1a8)+i*4,-5 if scenario=='native-upkeep-precharged'else 9)
  if scenario in ['native-goal','cancelled-goal']:
   f.w(f.army+0x820,0);f.make_actor(f.danger,300,f.enemy,167,97)
   table=f.engine+0x400;lists=table+0x100;node=lists+0x100;goal=node+0x100
   f.w(f.engine+8,table);f.w(table,lists);f.w(lists+8,node);f.w(node,goal)
   f.w(goal,image+0x4da480);f.w(goal+4,f.engine);f.w(goal+8,1);f.f(goal+0x38,100);f.w(goal+0x4c,300)
   if scenario=='cancelled-goal':
    f.run(20.3);f.w(lists+8,0)
  try:f.run()
  except Exception:
   print('FAILED_SCENARIO',scenario,hex(image),'eip',hex(f.u.reg_read(UC_X86_REG_EIP)),flush=True);raise
  assert f.count(2)==(1 if scenario in ['currency-supported','native-upkeep-precharged','native-goal','blocked-bank','race-upkeep-vector']else 0),(scenario,'unexpected bridge',f.count(2));checks+=1
print('BRIDGE_AI_PASS',checks,'compiled policy/paths/ownership/ABI checks at two relocations')
