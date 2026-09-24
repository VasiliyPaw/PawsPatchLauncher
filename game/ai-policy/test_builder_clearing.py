"""r21 compiled policy: aggregate HP, exact camp guards and builder precedence.
Native engine queries/assignment are ABI stubs, not evidence of played AI."""
from pathlib import Path
exec(compile(Path(__file__).with_name('test_clearing_priority.py').read_text().split('\nfor image,cave in ')[0],'test_clearing_priority.py:fixtures','exec'))

class BuilderFixture(PriorityFixture):
 def __init__(self,image,cave):
  super().__init__(image,cave)
  self.w(self.lair+8,1)
  self.w(self.actor+0xa8,self.org+0x100);self.w(self.org+0x100,image+0x4df830);self.w(self.org+0x104,self.actor)
  self.construct=self.target;self.w(self.construct,image+0x4da6b0);self.w(self.construct+8,1);self.w(self.construct+0x14,0)
  self.w(self.construct+0x44,self.centerdef);self.f(self.construct+0x48,80);self.f(self.construct+0x4c,64)
  self.marker=0x510e0000;self.w(self.marker,image+0x4e5c58);self.w(self.marker+0x14,333);self.w(self.marker+4,self.markerdef)
  self.f(self.marker+0x20,80);self.f(self.marker+0x24,64);self.w(self.reg+0x20004+333*4,self.marker)
  self.cell=self.cells+(16*32+20)*0x30;self.w(self.cell+8,self.marker+0x300);self.w(self.marker+0x300,self.marker)
  self.w(self.sa,image+0x4800);self.w(image+0x4820,image+0x2700)
  self.asm(image+0x2700,f'mov eax,[{self.stats+120}];ret 8');self.w(self.stats+120,1)
  self.asm(image+0x1d13d4,f'mov eax,[{self.stats+112}];ret 4');self.w(self.stats+112,1)
  self.asm(image+0x1ee5b3,f'fld dword ptr [{self.stats+116}];ret 20');self.f(self.stats+116,100)
  self.w(image+0x4da6b0+0x64,image+0x2300)
  self.w(self.source,image+0x4da480)
  self.f(self.world+0xe8,30)
 def reclaim(self):
  self.recruit(self.construct)
  return self.r(self.sa+0x10)==self.construct

for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 for hp in (0,1,69,69.99,70,71,99,100):
  f=PriorityFixture(image,cave);army=f.army();f.warm();f.as_scout(army);f.f(army[3]+0x210,hp)
  check((f.plan()==2)==(hp>=70),('scout aggregate threshold',hp))
 # Unequal bodies: a badly hurt soldier is allowed when total HP is 90%.
 f=PriorityFixture(image,cave);army=f.army();f.warm();f.as_scout(army)
 sa,actor,org,unit,state=army;u=unit+0x500
 f.w(u,image+0x4e5c58);f.w(u+0x14,334);f.w(f.reg+0x20004+334*4,u);f.w(u+0xe8,f.kingdom)
 f.w(u+0x80,u+0x180);f.w(u+0x184,u);f.w(u+0x190,actor);f.w(u+0x60,u+0x200);f.w(u+0x204,u)
 f.w(org+0x184,u);f.w(f.layout+0x204,f.ldef);f.f(unit+0x210,900);f.f(unit+0x214,900);f.f(u+0x210,1);f.f(u+0x214,100)
 # The shared layout now also requires the defender's second slot: switch it
 # to an independent otherwise identical layout with an empty optional flank.
 dl=f.layout+0xb00;f.u.mem_write(dl,bytes(f.u.mem_read(f.layout,0x40)));f.w(f.org+0x18,dl)
 f.w(f.org+0x1c,dl+0x100);f.w(dl+0x100,f.ldef);f.w(dl+0x104,0)
 check(f.plan()==2,'90.1% aggregate with a member at 1% HP has no individual veto')
 for belongs in (True,False):
  f=PriorityFixture(image,cave);army=f.army();f.warm();f.as_scout(army)
  # Keep a guard near the scout but outside the defender city radius.
  f.f(army[1]+0x20,100);f.f(f.lair+0x20,110)
  enemy=0x510ec000;f.w(enemy,image+0x4e5c58);f.w(enemy+0x14,335);f.w(enemy+0xe8,f.kingdom+0x800);f.w(f.reg+0x20004+335*4,enemy)
  f.f(enemy+0x20,112);f.f(enemy+0x24,64);f.w(enemy+0x7c,enemy+0x300);f.f(enemy+0x368,100)
  if belongs:
   f.w(f.den+0x40,f.den+0x700);f.w(f.den+0x700,f.den+0x740);f.w(f.den+0x74c,f.den+0x780);f.w(f.den+0x780,335)
  check((f.plan()==2)==belongs,('same neutral owner is not enough to classify camp guard',belongs))
 for case in ('attack','explore','defense','wound','hp70','hp69','hp-below','morale-zero','morale-low','partial','empty','nan-hp','recovering-move','kill','rout','construct','repair','member-kill','missing-marker','foundation','wrong-capability','no-score','invalid-score','native-refusal','disabled','occupied','failed-add'):
  f=BuilderFixture(image,cave)
  if case in ('explore','defense'):f.w(f.source,image+(0x4d79e8 if case=='explore' else 0x4da510))
  if case=='wound':f.f(f.leader+0x910,99)
  if case in ('hp70','hp69'):f.f(f.leader+0x910,int(case[2:]))
  if case=='hp-below':f.f(f.leader+0x910,69.99)
  if case in ('morale-zero','morale-low','partial'):
   f.f(f.leader+0x910,70);f.f(f.org+0x5c,0 if case=='morale-zero' else 1)
  if case=='partial':f.w(f.layout+0x204,f.ldef)
  if case=='empty':f.w(f.r(f.org+0x28),0)
  if case=='nan-hp':f.f(f.leader+0x910,float('nan'))
  if case=='recovering-move':f.w(f.state,image+0x4f4df0);f.w(f.actor+0x100,0x2000)
  if case in ('kill','rout'):f.w(f.state,image+(0x4f4e20 if case=='kill' else 0x4f500c))
  if case in ('construct','repair'):f.w(f.state,image+(0x4f4ed0 if case=='construct' else 0x4f4efc))
  if case=='member-kill':
   f.w(f.leader+0x70,f.leader+0xa00);f.w(f.leader+0xa14,f.leader+0xa40);f.w(f.leader+0xa40,f.leader+0xa80);f.w(f.leader+0xa80,image+0x4f4e20)
  if case=='missing-marker':f.w(f.marker+8,1)
  if case=='foundation':f.w(f.centerdef+0x4e0,0)
  if case=='wrong-capability':f.w(f.stats+112,0)
  if case in ('no-score','invalid-score'):f.f(f.stats+116,0 if case=='no-score' else float('nan'))
  if case=='native-refusal':f.w(f.stats+120,0)
  if case=='disabled':f.w(f.data+4,7)
  if case=='occupied':f.w(f.construct+0xc,f.node)
  if case=='failed-add':f.asm(image+0x2300,f'cmp ecx,{f.construct};je refused;mov eax,[esp+4];mov [eax+0x10],ecx;inc dword ptr [ecx+0x14];refused:ret 16')
  check(f.reclaim()==(case in ('attack','explore','defense','wound','hp70','morale-zero','morale-low','partial')),('builder reclaim',case))
  check(f.r(f.sa+4)==1,('builder ref balanced',case))
  if case=='failed-add':check(f.r(f.sa+0x10)==f.source,'failed native construction add restores old task')
 # A ready builder with a live free site cannot be taken by attack/explore/
 # calm defense. Retreat/recovery are outside the new admission veto.
 for vt,blocked in ((0x4da480,True),(0x4d84d4,True),(0x4d79e8,True),(0x4da510,True),(0x4da6b0,True),(0x4da3f8,True),(0x4d0000,False)):
  f=BuilderFixture(image,cave);f.w(f.construct+8,2);f.w(f.sa+0x10,f.construct);f.w(f.source,image+vt)
  check(bool(f.admission(f.source))==blocked,('construction admission',hex(vt)))
 f=BuilderFixture(image,cave);f.w(f.construct+8,2);f.w(f.sa+0x10,f.construct);f.w(f.marker+8,1)
 check(not f.admission(f.source),'invalidated site releases old construction reservation')
 # The same threshold protects already assigned construction; low morale or
 # casualties alone do not expose the builder to optional attack selection.
 for hp,morale,flags,protected in ((70,0,0,True),(70,59,0,True),(69.99,100,0,False),(70,0,0x2000,False),(70,0,0x4000,False)):
  f=BuilderFixture(image,cave);f.w(f.construct+8,2);f.w(f.sa+0x10,f.construct)
  f.f(f.leader+0x910,hp);f.f(f.org+0x5c,morale);f.w(f.layout+0x204,f.ldef);f.w(f.actor+0x100,flags)
  check(bool(f.admission(f.source))==protected,('partial builder protection',hp,morale,flags))
 # Recorded 51:08/51:57 regression: a builder walking to a live free marker
 # was in Construct, so quiet mine/city Defense could repeatedly steal it.
 for goalvt in (0x4da480,0x4d84d4,0x4d79e8,0x4da510,0x4da6b0,0x4da3f8):
  for case in ('travel','hp70','hp69','low-morale','partial','member-combat','enemy','damage','retreat','recover','marker-gone','native-refusal','disabled','source-pending','repair','kill','unknown-state'):
   f=BuilderFixture(image,cave);f.w(f.construct+8,2);f.w(f.sa+0x10,f.construct)
   f.w(f.source,image+goalvt);f.w(f.state,image+0x4f4ed0)
   if case in ('hp70','hp69'):f.f(f.leader+0x910,int(case[2:]))
   if case=='low-morale':f.f(f.org+0x5c,0)
   if case=='partial':f.w(f.layout+0x204,f.ldef)
   if case=='member-combat':
    f.w(f.leader+0x70,f.leader+0xa00);f.w(f.leader+0xa14,f.leader+0xa40);f.w(f.leader+0xa40,f.leader+0xa80);f.w(f.leader+0xa80,image+0x4f4e20)
   if case=='enemy':f.enemy()
   if case=='damage':f.damage(f.actor)
   if case in ('retreat','recover'):f.w(f.actor+0x100,0x4000 if case=='retreat' else 0x2000)
   if case=='marker-gone':f.w(f.marker+8,1)
   if case=='disabled':f.w(f.data+4,7)
   if case=='source-pending':f.w(f.construct+8,1)
   if case in ('repair','kill','unknown-state'):f.w(f.state,image+{'repair':0x4f4efc,'kill':0x4f4e20,'unknown-state':0x400000}[case])
   native=0xaabbcc02 if case=='native-refusal' else 0xaabbcc00
   expected=0xaabbcc01 if case in ('travel','hp70','low-morale','partial','source-pending') else native
   actual=f.call(f.hook(18),obj=f.actor,begin=[f.source,0],native=native)
   check(actual==expected,('Construct travel protection',hex(goalvt),case,hex(actual)))
 # r29, live company 49488: native Construct-to-Construct exchanges bypassed
 # the old optional-goal filter. A stable site must survive repeated passes,
 # including its pending stage, without blocking queries for its own goal.
 for active in (1,2):
  f=BuilderFixture(image,cave);f.w(f.construct+8,active);f.w(f.sa+0x10,f.construct)
  f.w(f.source,image+0x4da6b0);f.w(f.state,image+0x4f4ed0)
  f.w(f.source+0x44,f.centerdef);f.f(f.source+0x48,100);f.f(f.source+0x4c,80)
  for t in (30,34,50,90):
   f.f(f.world+0xe8,t)
   check(bool(f.admission(f.source)),'another construction cannot steal a committed builder')
   check(not f.admission(f.construct),'same construction capability query is allowed')
  f.f(f.stats+116,0);check(not f.admission(f.source),'ineligible current site permits retarget')
  f.f(f.stats+116,100);f.w(f.marker+8,1)
  check(not f.admission(f.source),'occupied current site permits retarget')

print('AI_BUILDER_CLEARING_PASS',checks,'checks; 3 ASLR bases; native services stubbed')
