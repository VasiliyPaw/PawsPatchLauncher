"""Compiled x86 callbacks: timers, complete native layout, real threat override,
and transfer ABI. Goal bookkeeping/path planning are explicit engine stubs;
this does not claim a played match or multiplayer verification.
"""
from pathlib import Path
# Reuse the routing suite's relocation/ABI/memory-write fixture setup only.
fixture_source=Path(__file__).with_name('test_routing.py').read_text().split('\nfor image,cave in ')[0]
exec(compile(fixture_source,'test_routing.py:fixtures','exec'))

class DefenseFixture(Fixture):
 def __init__(self,image=0x460000,cave=0x10000000):
  super().__init__(image,cave)
  self.city=0x510b0000;self.engine=0x510b1000;self.source=0x510b2000;self.target=0x510b3000;self.sa=0x510b4000;self.budget=0x510b5000;self.node=0x510b6000;self.layout=0x510b7000
  self.w(self.lair+8,1);self.w(self.actor+0xa8,0);self.f(self.actor+0x20,16);self.f(self.actor+0x24,64)
  self.w(self.org,image+0x4e1ae0);self.f(self.org+0x5c,78);self.f(self.org+0x60,78)
  self.w(self.org+0x18,self.layout);self.w(self.layout+0x28,self.layout+0x100);self.w(self.layout+0x2c,2)
  self.w(self.layout+0x100,0);self.w(self.layout+0x104,1)
  self.w(self.org+0x1c,self.layout+0x200);self.w(self.org+0x20,2);self.w(self.layout+0x200,self.ldef);self.w(self.layout+0x204,0)
  self.w(self.org+0x28,self.org+0x200);self.w(self.org+0x2c,2);self.w(self.org+0x200,self.leader);self.w(self.org+0x204,0)
  body=self.leader+0x900;self.w(self.leader+0x60,body);self.w(body+4,self.leader);self.f(body+0x10,100);self.f(body+0x14,100)
  self.cai=self.actor+0xd00;self.state=self.actor+0xe00
  self.w(self.actor+0x70,self.cai);self.w(self.cai+4,self.actor);self.w(self.cai+0x14,self.cai+0x80);self.w(self.cai+0x80,self.state);self.w(self.state,image+0x4f4f28)
  self.w(self.city,image+0x4e5c58);self.w(self.city+0x14,4);self.w(self.reg+0x20004+16,self.city);self.w(self.city+0xe8,self.kingdom)
  self.w(self.city+0x98,self.city+0x400);self.w(self.city+0x404,self.city);self.w(self.city+0x414,self.city);self.w(self.city+0x60,self.city+0x500);self.w(self.city+0x504,self.city);self.f(self.city+0x510,1000)
  self.w(self.city+4,self.ldef);self.f(self.city+0x20,16);self.f(self.city+0x24,64)
  self.w(self.city+0x94,self.city+0x600);self.w(self.city+0x604,self.city)
  self.w(self.player+0xc,self.engine);self.w(self.engine+4,self.player);self.w(self.engine+0xc,0)
  self.w(self.engine+0x14,self.node+0x800);self.w(self.engine+0x18,2);self.w(self.node+0x800,self.source);self.w(self.node+0x804,self.target)
  self.w(self.source,image+0x4da510);self.w(self.source+4,self.engine);self.w(self.source+8,2);self.w(self.source+0x4c,4);self.f(self.source+0x38,1000)
  self.w(self.source+0xc,self.node+0x100);self.w(self.source+0x14,1);self.w(self.node+0x100,self.sa)
  self.w(self.target,image+0x4d79e8);self.w(self.target+4,self.engine);self.w(self.target+8,2);self.f(self.target+0x38,100)
  self.w(self.player+0x2c,self.node+0x200);self.w(self.node+0x200,self.sa);self.w(self.sa+8,1);self.w(self.sa+0xc,self.player);self.w(self.sa+0x10,self.source)
  self.asm(image+0x24a86a,f'mov eax,[{self.stats+16}]; ret 4')
  self.w(image+0x4d79e8+0x6c,image+0x2000);self.w(image+0x4d79e8+0x28,image+0x2100);self.f(self.stats+32,1)
  self.asm(image+0x2000,f'mov eax,[{self.stats+28}]; ret 4')
  self.asm(image+0x2100,f'fld dword ptr [{self.stats+32}]; ret 8')
  self.w(image+0x4da510+0x68,image+0x2200);self.w(image+0x4d79e8+0x64,image+0x2300)
  # These stand in for engine bookkeeping only. Record every ABI argument.
  self.asm(image+0x2200,f'inc dword ptr [{self.stats+36}]; mov [{self.stats+40}],ecx;'+''.join(f'mov eax,[esp+{4+i*4}]; mov [{self.stats+44+i*4}],eax;' for i in range(5))+f'mov eax,[esp+4]; mov dword ptr [eax+0x10],0; dec dword ptr [ecx+0x14]; ret 20')
  self.asm(image+0x2300,f'inc dword ptr [{self.stats+64}]; mov [{self.stats+68}],ecx;'+''.join(f'mov eax,[esp+{4+i*4}]; mov [{self.stats+72+i*4}],eax;' for i in range(4))+f'mov eax,[esp+4]; mov [eax+0x10],ecx; inc dword ptr [ecx+0x14]; ret 16')
  self.resources=self.layout+0x400;rd=self.resources+0x100
  self.w(image+0x5efa8c,self.resources);self.w(self.resources+0x24,self.resources+0x80);self.w(self.resources+0x28,1);self.w(self.resources+0x80,rd);self.w(rd+8,rd+0x80);self.u.mem_write(rd+0x80,'kingdom_points_consumed\0'.encode('utf-16le'))
  self.w(self.data+meta['queryPointerOffset'],image+0x2400);self.f(self.stats+88,0)
  self.asm(image+0x2400,f'mov eax,[esp+16]; mov edx,[{self.stats+88}]; mov [eax],edx; mov eax,1; ret')
 def tick(self,time):
  self.f(self.world+0xe8,time);self.call(self.hook(17),obj=self.player)
 def warm(self):
  for t in (0,10,20,30):self.tick(t)
 def transfer(self):
  self.call(self.hook(20),obj=self.source,args=[self.target,self.sa,self.budget],allowed=[self.sa+0x10,self.source+0x14,self.target+0x14])
  return self.r(self.sa+0x10)==self.target
 def admission(self,goal=None,native=0):
  return self.call(self.hook(18),obj=self.actor,begin=[goal or self.source,0],native=native)&255
 def damage(self,a=None):
  ev=self.node+0x400;self.f(ev+0xc,10)
  self.call(self.hook(21),obj=self.player,args=[a or self.city,ev])
 def enemy(self,visible=True,building=False):
  self.w(self.lair+8,0);self.w(self.lair+0xe8,self.kingdom+0x800);self.f(self.lair+0x20,32);self.f(self.lair+0x24,64)
  self.w(self.stats+16,int(visible));self.w(self.lair+0x94,self.den+0x300 if building else 0);self.w(self.lair+0x6c,self.den+0x500)
 def scouts(self,count):
  previous=self.node+0x200
  for i in range(count):
   node=0x510c0000+i*0x40;sa=0x510c1000+i*0x40;actor=0x510c2000+i*0x200;id=10+i
   self.w(previous+4,node);self.w(node,sa);self.w(sa+8,id);self.w(sa+0x10,self.target);self.w(sa+0xc,self.player)
   self.w(actor,self.image+0x4e5c58);self.w(actor+0x14,id);self.w(actor+0xe8,self.kingdom);self.w(self.reg+0x20004+4*id,actor)
   previous=node

for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 f=DefenseFixture(image,cave)
 for time in (0,5,9.99):f.tick(time);check(not f.transfer(),('quiet period not elapsed',time))
 f.tick(10);check(f.transfer(),'full guarded company transfers after 10 game seconds')
 check([f.r(f.stats+x) for x in (36,40,44,48,52,56,60)]==[1,f.source,f.sa,f.budget,1,1,0],'native remove ABI')
 check([f.r(f.stats+x) for x in (64,68,72,76,80,84)]==[1,f.target,f.sa,f.budget,1,1],'native assign ABI')
 check(f.admission()==1,'peaceful defense cooldown')
 check(f.admission(native=7)==7,'native refusal preserved')
 f.f(f.world+0xe8,54.9);check(f.admission()==1,'45 game seconds cooldown')
 f.f(f.world+0xe8,55);check(f.admission()==0,'cooldown expires')
 f.f(f.world+0xe8,40);f.enemy();check(f.admission()==0,'real visible threat overrides cooldown immediately')
 # Attack, repair, construction and builder combat never pass this calm-defense filter.
 for vt in (0x4da480,0x4d84d4,0x4da6b0,0x4d79e8):
  f.w(f.target,image+vt);check(f.admission(f.target)==0,'non-defense admission stays native')

cases=[('wounded',False),('missing-member',False),('dead-hero',False),('empty-flank',True),('low-morale',False),('nan-hp',False),('bad-layout',False),('dead-company',False),('recycled-id',False),('kill',False),('move',False),('rout',False),('sleep',True),('danger',False),('unseen',True),('stationary-lair',True),('damage',False),('late-threat',False),('late-damage',False),('late-wound',False),('reserved',False),('native-refusal',False),('native-zero-gain',False),('inactive-target',False),('five-scouts',False),('non-defense',False),('disabled',False),('rollback',False),('changed-owner',False),('invalid-city',False),('stale-city',False)]
for name,expected in cases:
 f=DefenseFixture();body=f.leader+0x900
 if name=='wounded':f.f(body+0x10,99.99)
 if name=='missing-member':f.w(f.layout+0x204,f.ldef)
 if name=='dead-hero':f.w(f.org+0x34,f.layout+0x700);f.w(f.org+0x38,2);f.w(f.layout+0x704,0x510bab00)
 if name=='low-morale':f.f(f.org+0x5c,77)
 if name=='nan-hp':f.f(body+0x10,float('nan'))
 if name=='bad-layout':f.w(f.layout+0x2c,1)
 if name=='dead-company':f.w(f.actor+8,1)
 if name=='recycled-id':f.w(f.reg+4+2,1)
 if name in ('kill','move','rout','sleep'):f.w(f.state,f.image+{'kill':0x4f4e20,'move':0x4f4df0,'rout':0x4f500c,'sleep':0x4f4d98}[name])
 if name in ('danger','unseen','stationary-lair'):f.enemy(name!='unseen',name=='stationary-lair')
 if name=='reserved':f.f(f.stats+88,11)
 if name=='native-refusal':f.w(f.stats+28,1)
 if name=='native-zero-gain':f.f(f.stats+32,0)
 if name=='inactive-target':f.w(f.target+8,1)
 if name=='non-defense':f.w(f.source,f.image+0x4da480)
 if name=='disabled':f.w(f.data+4,7)
 if name=='invalid-city':f.f(f.city+0x510,0)
 if name=='stale-city':f.w(f.source+0x4c,0x10004)
 if name=='five-scouts':f.scouts(5)
 for t in (0,10,20,30):
  f.f(f.world+0xe8,t)
  if name=='damage' and t==30:f.damage()
  f.tick(t)
 if name=='rollback':f.tick(5)
 if name=='changed-owner':f.w(f.actor+0xe8,f.kingdom+0x800)
 if name=='late-threat':f.enemy()
 if name=='late-wound':f.f(body+0x10,99)
 if name=='late-damage':f.damage()
 check(f.transfer()==expected,('release gate',name))

for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 for count in (0,1,2,3,4,5,6):
  f=DefenseFixture(image,cave);f.scouts(count);f.warm()
  check(f.transfer()==(count<5),('scout cap permits fifth but blocks sixth',count,image))

f=DefenseFixture();f.w(f.target,f.image+0x4da6b0)
for offset in (0x28,0x64,0x6c):f.w(f.image+0x4da6b0+offset,f.r(f.image+0x4d79e8+offset))
f.f(f.stats+88,11);f.w(f.actor+0xa8,f.org+0x100);f.w(f.org+0x100,f.image+0x4df830);f.w(f.org+0x104,f.actor)
f.w(f.node+4,f.node+0x800);f.w(f.node+0x800,f.target)
f.warm();check(f.transfer(),'kingdom-point builder may take valid construction')
f=DefenseFixture();f.warm();f.damage();check(not f.transfer(),'damage blocks recovered company');f.tick(60);check(not f.transfer(),'quiet period starts after sampling gap');f.tick(70);check(f.transfer(),'release resumes after 10 continuously sampled quiet seconds')
f=DefenseFixture();f.tick(0);f.f(f.world+0xe8,5);f.damage();f.tick(10);check(not f.transfer(),'recent damage resets quiet time');f.f(f.world+0xe8,14.99);check(not f.transfer(),'ten seconds since damage not yet elapsed');f.f(f.world+0xe8,15);check(f.transfer(),'ten quiet seconds since last damage suffice between samples')
class ClearingFixture(DefenseFixture):
 instruction_limit=40000000
 def __init__(self,image=0x460000,cave=0x10000000,vt=0x4da480):
  super().__init__(image,cave)
  self.w(self.lair+8,0);self.w(self.lair+0xe8,self.kingdom+0x800)
  self.w(self.ldef+0x4e0,self.markerdef);self.f(self.org+0x68,300)
  self.w(self.kingdom+0x2dc,self.city+0x800);self.w(self.kingdom+0x2e0,1);self.w(self.city+0x800,self.city)
  self.w(self.target,image+vt);self.w(self.target+0x4c,2)
  for off in (0x28,0x64,0x6c):self.w(image+vt+off,self.r(image+0x4d79e8+off))
  self.w(self.player+0x1c,self.layout+0x800)
  self.asm(image+0x5ca80,f'fld dword ptr [{self.org+0x68}];ret 4')
  self.asm(image+0x5cb59,'fld1;ret 16')
 def explore(self):
  self.clear=self.target;self.target=self.node+0xa00
  self.w(self.target,self.image+0x4d79e8);self.w(self.target+4,self.engine);self.w(self.target+8,2);self.f(self.target+0x38,100)
  self.w(self.engine+0x18,3);self.w(self.node+0x808,self.target)

for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 for vt in (0x4da480,0x4d84d4):
  f=ClearingFixture(image,cave,vt);f.warm();check(not f.transfer(),'offense waits for complete group planner')
 for case in ['strong-guard','hidden','allied','dead','foundation','invalid-city','native-refusal','native-zero-gain','inactive','wounded','damage','disabled','builder']:
  f=ClearingFixture(image,cave)
  if case=='strong-guard':f.f(f.den+0x10,1000)
  if case=='hidden':f.w(f.stats+16,0)
  if case=='allied':f.w(f.stats+12,1)
  if case=='dead':f.f(f.den+0x210,0)
  if case=='foundation':f.w(f.ldef+0x4e0,0)
  if case=='invalid-city':f.f(f.city+0x510,0)
  if case=='native-refusal':f.w(f.stats+28,1)
  if case=='native-zero-gain':f.f(f.stats+32,0)
  if case=='inactive':f.w(f.target+8,1)
  if case=='wounded':f.f(f.leader+0x910,99)
  if case=='disabled':f.w(f.data+4,7)
  if case=='builder':f.w(f.actor+0xa8,f.org+0x100)
  f.warm()
  if case=='damage':f.damage()
  check(not f.transfer(),('clearing retains safety and native admission',case))
 f=ClearingFixture(image,cave);f.explore();f.warm();check(not f.transfer(),'existing feasible clearing takes precedence over extra scouting')
 f.target=f.clear;check(not f.transfer(),'offensive singleton must wait for group planner')
 for case in ('no-camp','unfeasible','inadmissible','builder'):
  f=ClearingFixture(image,cave);f.explore()
  if case=='no-camp':f.w(f.lair+8,1)
  if case=='unfeasible':f.f(f.den+0x10,1000)
  if case=='inadmissible':
   f.w(f.image+0x4da480+0x6c,f.image+0x2600);f.asm(f.image+0x2600,'mov eax,1;ret 4')
  if case=='builder':f.w(f.actor+0xa8,f.org+0x100)
  f.warm();check(f.transfer(),('scouting remains available when clearing cannot take this company',case))
print('AI_DEFENSE_PASS',checks,'checks; compiled native wrappers, 3 ASLR bases; engine goal bookkeeping is stubbed')
