"""Compiled SelectGoals group planner; native list mutations and admission are
explicit stubs. Tests do not claim a live match or network verification."""
from pathlib import Path
exec(compile(Path(__file__).with_name('test_defense.py').read_text().split('\nfor image,cave in ')[0], 'test_defense.py:fixtures','exec'))

class GroupFixture(DefenseFixture):
 instruction_limit=40000000
 def __init__(self,image=0x460000,cave=0x10000000):
  super().__init__(image,cave)
  self.w(self.lair+8,0);self.w(self.lair+0xe8,self.kingdom+0x800);self.w(self.ldef+0x4e0,self.markerdef)
  self.w(self.kingdom+0x2dc,self.city+0x800);self.w(self.kingdom+0x2e0,1);self.w(self.city+0x800,self.city)
  self.w(self.target,image+0x4da480);self.w(self.target+0x4c,2);self.f(self.target+0x40,100)
  self.w(self.target+0x14,0);self.f(self.target+0x34,5.458358e-13);self.f(self.target+0x38,10024)
  for off in (0x28,0x64,0x6c):self.w(image+0x4da480+off,self.r(image+0x4d79e8+off))
  self.ego=self.layout+0x800;self.w(self.player+0x1c,self.ego);self.f(self.stats+100,1)
  self.asm(image+0x5ca80,f'mov eax,[esp+4];mov eax,[eax+8];and eax,65535;mov eax,[eax*4+{self.reg+0x20004}];mov eax,[eax+0x7c];fld dword ptr [eax+0x68];ret 4')
  self.asm(image+0x5cb59,f'fld dword ptr [{self.stats+100}];ret 16')
  # Same ABI as native ref destructor: pointer to one held SA reference.
  self.asm(image+0x42fca,'mov eax,[ecx];dec dword ptr [eax+4];ret')
  self.w(self.sa+4,1);self.f(self.org+0x68,100)
  self.w(image+0x4da510+0x64,image+0x2500)
  self.asm(image+0x2500,'mov eax,[esp+4];mov [eax+0x10],ecx;inc dword ptr [ecx+0x14];ret 16')
  self.w(image+0x4da480+0x68,image+0x2200)
  self.armies=[(self.sa,self.actor,self.org,self.leader,self.state)]
 def army(self,cv=100,x=20):
  i=len(self.armies);p=0x510d0000+i*0x1800;actor=p;org=p+0x300;unit=p+0x600;sa=p+0x900;state=p+0xa00;idx=100+i*2
  for obj,id in [(actor,idx),(unit,idx+1)]:self.w(obj,self.image+0x4e5c58);self.w(obj+0x14,id);self.w(obj+0xe8,self.kingdom);self.w(self.reg+0x20004+4*id,obj)
  self.w(actor+4,self.ldef+0x600);self.w(actor+0x7c,org);self.f(actor+0x20,x);self.f(actor+0x24,64)
  self.w(org,self.image+0x4e1ae0);self.w(org+4,actor);self.f(org+0x5c,78);self.f(org+0x60,78);self.f(org+0x68,cv)
  self.w(org+0x18,self.layout);self.w(org+0x1c,self.layout+0x200);self.w(org+0x20,2);self.w(org+0x28,org+0x180);self.w(org+0x2c,2);self.w(org+0x180,unit)
  self.w(unit+0x80,unit+0x180);self.w(unit+0x184,unit);self.w(unit+0x190,actor);self.w(unit+0x60,unit+0x200);self.w(unit+0x204,unit);self.f(unit+0x210,100);self.f(unit+0x214,100)
  self.w(actor+0x70,actor+0x200);self.w(actor+0x214,actor+0x240);self.w(actor+0x240,state);self.w(state,self.image+0x4f4f28)
  self.w(sa+4,1);self.w(sa+8,idx);self.w(sa+0xc,self.player);self.w(sa+0x10,self.source)
  node=p+0xb00;self.w(node,self.sa if i==1 else self.armies[-1][0]);self.w(node+4,self.r(self.player+0x2c));self.w(self.player+0x2c,node)
  # Native owned-list with each SA exactly once.
  for j,t in enumerate(self.armies+[(sa,actor,org,unit,state)]):
   nd=0x510cf000+j*16;self.w(nd,t[0]);self.w(nd+4,nd+16 if j<i else 0)
  self.w(self.player+0x2c,0x510cf000)
  self.armies.append((sa,actor,org,unit,state));self.w(self.source+0x14,len(self.armies));return self.armies[-1]
 def plan(self):
  allowed=[self.source+0x14,self.target+0x14]
  for sa,*_ in self.armies:allowed += [sa+4,sa+0x10]
  self.call(self.hook(22),obj=self.source,args=[self.budget,self.engine+0x14,0],allowed=allowed)
  return sum(self.r(t[0]+0x10)==self.target for t in self.armies)
 def events(self,kind):
  n=self.r(self.data);return [struct.unpack('<8I',self.u.mem_read(self.data+128+((i-1)&2047)*128,32)) for i in range(1,n+1) if self.r(self.data+128+((i-1)&2047)*128+12)==kind]

for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 f=GroupFixture(image,cave);f.army();f.warm();check(f.plan()==2,'two individually insufficient companies committed together')
 check(all(f.r(sa+4)==1 for sa,*_ in f.armies),'temporary actor references balanced')
 check(len(f.events(35))==2 and f.events(33)[-1][-1]==1,'each real assignment and full plan recorded')
 for case in ['insufficient','wound','morale','kill','danger','damage','native-refusal','hidden','dead-target','allied-target','foundation','disabled','unknown-goal','inactive-goal','far','builder','zero-cv','matchup','mine','zero-gain','one-strong','extra','gap','world-reset']:
  f=GroupFixture(image,cave);sa,act,org,unit,state=f.army()
  if case=='insufficient':f.f(org+0x68,30)
  if case=='wound':f.f(unit+0x210,69)
  if case=='morale':f.f(org+0x5c,46)
  if case=='kill':f.w(state,image+0x4f4e20)
  if case=='danger':f.enemy()
  if case=='native-refusal':f.w(f.stats+28,1)
  if case=='hidden':f.w(f.stats+16,0)
  if case=='dead-target':f.f(f.den+0x210,0)
  if case=='allied-target':f.w(f.stats+12,1)
  if case=='foundation':f.w(f.ldef+0x4e0,0)
  if case=='disabled':f.w(f.data+4,7)
  if case=='unknown-goal':f.w(f.engine+0x18,1)
  if case=='inactive-goal':f.w(f.target+8,1)
  if case=='far':f.f(act+0x20,400)
  if case=='builder':f.w(act+0xa8,f.actor+0xa00);f.w(f.actor+0xa00,image+0x4df830);f.w(f.actor+0xa04,act)
  if case=='zero-cv':f.f(org+0x68,0)
  if case=='matchup':f.f(f.stats+100,.5)
  if case=='mine':
   mine=0x510ec000;f.u.mem_write(mine,bytes(f.u.mem_read(f.city,0x800)));f.w(mine+0x14,91);f.w(f.reg+0x20004+4*91,mine);f.w(mine+0x98,0)
   f.w(mine+0x94,mine+0x600);f.w(mine+0x604,mine);f.w(mine+0x60,mine+0x500);f.w(mine+0x504,mine);f.w(f.source+0x4c,91)
  if case=='zero-gain':f.f(f.stats+32,0)
  if case=='one-strong':f.f(org+0x68,200)
  if case=='extra':f.army(100,24)
  f.warm()
  if case=='damage':f.damage()
  if case=='gap':f.f(f.world+0xe8,70)
  if case=='world-reset':f.w(f.data+meta['routingOffset']+meta['routingSize'],0)
  expected=case in ['mine','zero-gain','one-strong','extra','world-reset','gap','damage']
  got=f.plan();check((got>0)==expected,('group gate',case,got))
  if not expected:check(all(f.r(t[0]+0x10)==f.source for t in f.armies),('no partial force',case))
  if case=='extra':check(got==2,'only enough nearest defenders, spare company retained')
 # A successful old pair fallback must never send one fighter before the group.
 f=GroupFixture(image,cave);f.warm();check(not f.transfer(),'old offensive singleton transfer disabled')
 f=GroupFixture(image,cave);f.army();f.warm();f.f(f.stats+32,0);check(f.plan()==2,'low singleton marginal gain does not hide a feasible group')
 f=GroupFixture(image,cave);f.army();f.warm();f.w(f.engine+0x18,4097);check(f.plan()==0,'oversized vector rejected')
 f=GroupFixture(image,cave);f.army();f.warm();f.w(f.target+0x4c,0x10002);check(f.plan()==0,'recycled camp full id rejected')
 f=GroupFixture(image,cave);f.army();f.warm();f.f(f.den+0x10,1000);check(f.plan()==0,'whole army insufficient even before assembling')
 f=GroupFixture(image,cave);f.army();f.warm();f.asm(image+0x2300,'ret 16')
 check(f.plan()==0 and not f.events(35),'unexpected native assignment failure is not reported as assignment')
 check(f.events(33)[-1][-1]==8,'incomplete native commit is explicitly diagnosed')
 check(all(f.r(sa+4)==1 for sa,*_ in f.armies),'references balanced even on native assignment failure')

print('AI_CLEARING_PASS',checks,'checks; 3 relocated bases; native assignment/diplomacy are stubs, not a played match')
