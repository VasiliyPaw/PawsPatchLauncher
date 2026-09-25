"""Compiled fast-expansion/siege gates and original activation parent.
Native selection/list ownership, priority and path services are explicit stubs;
this is not a played-match or multiplayer acceptance test.
"""
from pathlib import Path
exec(compile(Path(__file__).with_name('test_builder_clearing.py').read_text().split('\nfor image,cave in ')[0], 'test_builder_clearing.py:fixtures','exec'))

BASES=[(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]
def region_stub(f):
 regions=0x510ed000;f.region=regions+0x200
 f.w(f.image+0x5f3fcc,regions);f.w(regions+0x14,regions+0x100);f.w(regions+0x18,2)
 f.w(regions+0x104,f.region);f.w(f.region,1)
 f.w(f.target+(0x40 if f.r(f.target)==f.image+0x4da6b0 else 0x48),f.region)
 f.asm(f.image+0x2273c2,f'mov eax,{f.region};ret')

def execution_stub(f):
 # Native ExecuteGoals owns a fresh budget and flushes its command queue.
 # Here only that service is stubbed: exercise compiled gate38 for each goal
 # and record actual allowed commands after its native affordability check.
 image=f.image;cave=f.cave;f.commands=0x510ef000
 f.asm(image+0x1e3e34,f'inc dword ptr [{f.commands}];mov eax,1;ret 4')
 code=f'inc dword ptr [{f.commands+12}];'
 for goal,counter in ((f.target,4),(f.explore,8)):
  code+=f'push {f.budget};mov ecx,{goal};call {cave+f.hook(38)["offset"]};test al,al;jz next{counter};inc dword ptr [{f.commands+counter}];next{counter}:;'
 code+='ret';f.asm(image+0x1e8925,code)
 return [f.engine+0x20]+list(range(f.commands,f.commands+16,4))

for image,cave in BASES:
 for case in ('quiet','nearby-enemy','city-damage','company-damage','member-damage','siege-city','siege-center','kill','member-kill','recovery','hp69','morale59','mine-enemy'):
  f=GroupFixture(image,cave);army=f.army();f.warm()
  if case in ('nearby-enemy','mine-enemy'):
   enemy=0x510ec000;f.w(enemy,image+0x4e5c58);f.w(enemy+0x14,335);f.w(f.reg+0x20004+335*4,enemy)
   f.w(enemy+0xe8,f.kingdom+0x800);f.f(enemy+0x20,25);f.f(enemy+0x24,64);f.w(enemy+0x7c,enemy+0x300);f.f(enemy+0x368,100)
  if case=='mine-enemy':f.w(f.city+0x98,0)
  if case in ('city-damage','company-damage','member-damage'):f.damage({'city-damage':f.city,'company-damage':f.actor,'member-damage':f.leader}[case])
  if case=='siege-city':f.w(f.city+0x100,0x00100000)
  if case=='siege-center':
   center=0x510ec000;f.u.mem_write(center,bytes(f.u.mem_read(f.city,0x800)));f.w(center+0x14,336);f.w(f.reg+0x20004+336*4,center)
   f.w(center+0x98,0);f.w(center+0x100,0x00100000);f.w(center+0x60,center+0x500);f.w(center+0x504,center);f.w(f.city+0x414,center)
  if case=='kill':f.w(f.state,image+0x4f4e20)
  if case=='member-kill':
   f.w(f.leader+0x70,f.leader+0xa00);f.w(f.leader+0xa14,f.leader+0xa40);f.w(f.leader+0xa40,f.leader+0xa80);f.w(f.leader+0xa80,image+0x4f4e20)
  if case=='recovery':f.w(f.actor+0x100,0x2000)
  if case=='hp69':f.f(f.leader+0x910,69)
  if case=='morale59':f.f(f.org+0x5c,46)
  check((f.plan()==2)==(case in ('quiet','nearby-enemy','city-damage')),('siege donor gate',case))
 for case in ('nearby-fight','siege','damage','hp69','morale59','recovery','expired','disabled'):
  f=GroupFixture(image,cave);f.army();f.warm();check(f.plan()==2,'prepare dispatched clearing force')
  f.f(f.leader+0x910,70);f.f(f.org+0x5c,60);f.f(f.org+0x60,100);f.w(f.state,image+0x4f4df0)
  f.damage(f.city) # City damage alone must not cancel the new assignment.
  if case=='siege':f.w(f.city+0x100,0x00100000)
  if case=='damage':f.damage(f.actor)
  if case=='hp69':f.f(f.leader+0x910,69)
  if case=='morale59':f.f(f.org+0x5c,59)
  if case=='recovery':f.w(f.actor+0x100,0x2000)
  if case=='expired':f.f(f.world+0xe8,75)
  if case=='disabled':f.w(f.data+4,7)
  check(bool(f.admission(f.source))==(case=='nearby-fight'),('clearing return cooldown uses the same siege/readiness policy',case))
 # Optional new members are capped by actual assigned force, not headcount.
 for case in ('enough','insufficient','existing','recovering','ordinary','foundation','native-refusal','disabled'):
  f=GroupFixture(image,cave);f.army(200);f.warm();sa,actor,*_=f.armies[1]
  f.w(sa+0x10,f.target);f.w(f.target+0xc,f.node+0x600);f.w(f.node+0x600,sa)
  if case=='insufficient':f.f(f.armies[1][2]+0x68,149)
  if case=='recovering':f.w(actor+0x100,0x2000)
  if case=='ordinary':f.w(f.target,image+0x4da510)
  if case=='foundation':f.w(f.ldef+0x4e0,0)
  if case=='disabled':f.w(f.data+4,7)
  native=0xabcdef02 if case=='native-refusal' else 0xabcdef00
  got=f.call(f.hook(18),obj=actor if case=='existing' else f.actor,begin=[f.target,0],native=native)
  check(got==(native|1 if case=='enough' else native),('enough force admission',case,hex(got)))
 for accepts in (True,False):
  f=BuilderFixture(image,cave);f.w(f.sa+0x10,0)
  if not accepts:f.asm(image+0x2300,'ret 16')
  check(f.reclaim()==accepts,'unassigned builder can be recruited')
  check(f.r(f.sa+4)==1 and (accepts or not f.r(f.sa+0x10)),'unassigned failure has balanced reference and no bogus restoration')

class PulseFixture(PriorityFixture):
 def __init__(self,image,cave,state=1):
  super().__init__(image,cave);self.army();self.warm();self.w(self.target+8,state)
  self.w(self.player+4,1);self.w(self.player+0x12c,1);self.w(self.player+0x168,1)
  self.table=0x510e0000;self.w(self.engine+8,self.table);self.w(self.engine+0x18,0)
  for i in range(23):self.w(self.table+4*i,self.table+0x100+i*32)
  self.list=self.table+0x100;self.link=self.table+0x800
  self.w(self.list+state*8,self.link);self.w(self.link,self.target)
  self.w(image+0x4da480+0x14,image+0x2600);self.asm(image+0x2600,'xor eax,eax;ret')
  self.w(image+0x4da480+0x60,image+0x2700);self.asm(image+0x2700,f'inc dword ptr [{self.stats+104}];ret 4')
  self.asm(image+0x1e481e,f'inc dword ptr [{self.stats+108}];mov eax,[esp+4];mov [ecx+8],eax;ret 8')
  self.asm(image+0x1e838a,f'inc dword ptr [{self.stats+112}];ret')
  self.execution_writes=execution_stub(self)
  region_stub(self)
  self.f(self.world+0xe8,30)
 def pulse(self,t):
  self.f(self.world+0xe8,t);self.call(self.hook(34),obj=self.player,allowed=[self.target+8])
 def call(self,h,*args,allowed=(),**kwargs):
  if h['mode']==34:allowed=list(allowed)+[self.player+0x178,self.player+0x181]
  return super().call(h,*args,allowed=allowed,**kwargs)

for image,cave in BASES:
 f=PulseFixture(image,cave)
 for t,expected in ((30,1),(31,1),(33.99,1),(34,2),(38,3),(5,4)):
  f.pulse(t);check(f.r(f.stats+112)==expected,('4 game seconds cadence and time rollback',t))
 check(len(f.events(52))==3,'completed pulse diagnostic obeys the existing five-second sampling window')
 for case in ('disabled','paused','human','dead-kingdom','ai-stopped','selection-busy','unknown-player','invalid-list','invalid-goal','cyclic-list','nan-time'):
  f=PulseFixture(image,cave)
  if case=='disabled':f.w(f.data+4,7)
  if case=='paused':f.w(image+0x5f9218,1)
  if case=='human':f.w(f.player+4,0)
  if case=='dead-kingdom':f.w(f.kingdom+8,32)
  if case=='ai-stopped':f.w(f.player+0x12c,0)
  if case=='selection-busy':f.w(f.engine+0x18,3)
  if case=='unknown-player':f.w(f.player+0x170,0)
  if case=='invalid-list':f.w(f.table+4,0)
  if case=='invalid-goal':f.w(f.target+4,0)
  if case=='cyclic-list':f.w(f.link+4,f.link)
  f.pulse(float('nan') if case=='nan-time' else 30)
  check(not f.r(f.stats+112),('pulse guard',case))
 f=PulseFixture(image,cave,0);f.pulse(30);check(f.r(f.target+8)==1 and f.r(f.stats+108)==1,'newly feasible dormant goal promoted using native state method')
 f=PulseFixture(image,cave,2);f.w(f.target+0xc,f.node+0x100);f.pulse(30)
 check(not f.r(f.stats+104),'occupied active goal keeps its target and priority')
 f=PulseFixture(image,cave);f.w(f.target,image+0x4d84d4);f.w(f.target+0x48,0xdeadbeef)
 f.w(image+0x4d84d4+0x14,image+0x2600);f.w(image+0x4d84d4+0x60,image+0x2700);f.pulse(30)
 check(f.r(f.stats+104)==1,'direct structure goals do not treat their tail as a regional pointer')
 for case in ('unexplored','other-region','no-site','no-region-table'):
  f=PulseFixture(image,cave,0)
  if case=='unexplored':f.w(f.stats+16,0)
  if case=='other-region':f.w(f.target+0x48,f.region+0x100)
  if case=='no-site':f.w(f.lair+8,1)
  if case=='no-region-table':f.w(image+0x5f3fcc,0)
  f.pulse(30);check(not f.r(f.stats+104) and not f.r(f.stats+112),('only known settlement regions refreshed',case))
 # Exercise the real activation parent, with its native recruitment skipped
 # only during a fast pass. SelectGoals list/budget ownership is stubbed.
 for accepts in (True,False):
  f=PulseFixture(image,cave)
  original=bytearray(game[0x1e4736:0x1e47be]);struct.pack_into('<I',original,0x1e47ae-0x1e4736,image+0x5f3fc8)
  f.u.mem_write(image+0x1e4736,bytes(original));h=f.hook(23)
  f.u.mem_write(image+h['site'],b'\xe8'+struct.pack('<i',cave+h['offset']-image-h['site']-5))
  f.asm(image+h['target'],f'inc dword ptr [{f.stats+116}];ret 12')
  for off,addr,code in [(0x38,0x2800,'xor eax,eax;ret'),(0x8,0x2900,'mov eax,3;ret'),(0x80,0x2a00,'mov dword ptr [ecx+8],0;ret')]:
   f.w(image+0x4da480+off,image+addr);f.asm(image+addr,code)
  f.asm(image+0x1e54b1,f'mov dword ptr [ecx+0x34],{bits(10 if accepts else 0)};ret 20');f.asm(image+0x1e156b,'ret 4')
  f.asm(image+0x1e47be,f'inc dword ptr [{f.stats+120}];ret 12')
  # Native selector calls wrappers for the target, an unrelated Explore goal
  # and active exchange. Unrelated goals must remain completely untouched.
  code=f'push ebx;mov ebx,ecx;mov dword ptr [ebx+0x18],3;'
  for goal in (f.explore,f.target):
   index=2 if goal==f.explore else 1
   code+=f'push {index};push {f.engine+0x14};push {f.budget};mov ecx,{goal};call {cave+f.hook(35)["offset"]};'
  code+=f'push 2;push {f.engine+0x14};push {f.budget};mov ecx,{f.explore};call {cave+f.hook(36)["offset"]};'
  code+='mov dword ptr [ebx+0x18],0;pop ebx;ret'
  f.asm(image+0x1e838a,code)
  # Writes by the explicit native selection/activation stubs and transfers.
  f.w(f.engine+0x20,1)
  f.call(f.hook(34),obj=f.player,allowed=f.allowed()+[f.engine+0x18,f.target+8,f.target+0x34]+f.execution_writes)
  check(not f.r(f.stats+116),'fast pending pass skips stock optional recruitment')
  check(not f.r(f.stats+120),'fast pass skips unrelated active exchange')
  check(f.r(f.explore+8)==1 and f.r(f.explore+0x14)==0,'unrelated exploration unchanged')
  check(f.r(f.target+8)==(2 if accepts else 0),'original activation decides acceptance')
  check(all(f.r(sa+0x10)==f.target for sa,*_ in f.armies),'whole force handed to original activation directly from defense')
  check(all(f.r(sa+4)==1 for sa,*_ in f.armies),'pulse transfers balance native references')
  check(f.r(f.commands)==int(accepts) and f.r(f.commands+4)==int(accepts) and not f.r(f.commands+8),'only activated changed goal passes native command affordability')
  check(f.r(f.engine+0x20)==1,'temporary native execution budget scope restored')
  # No fast-player state leaks into the next normal strategic pass.
  f.call(f.hook(35),obj=f.explore,args=[f.budget,f.engine+0x14,2])

 # Active clearing receives idle defenders through the restricted exchange;
 # the stock exchange cannot pull unrelated units into the extra pass.
 f=PulseFixture(image,cave,2)
 f.asm(image+0x1e4736,f'inc dword ptr [{f.stats+116}];ret 12')
 f.asm(image+0x1e47be,f'inc dword ptr [{f.stats+120}];ret 12')
 f.asm(image+0x1e838a,f'mov dword ptr [{f.engine+0x18}],3;push 1;push {f.engine+0x14};push {f.budget};mov ecx,{f.target};call {cave+f.hook(35)["offset"]};push 1;push {f.engine+0x14};push {f.budget};mov ecx,{f.target};call {cave+f.hook(36)["offset"]};mov dword ptr [{f.engine+0x18}],0;ret')
 f.call(f.hook(34),obj=f.player,allowed=f.allowed()+[f.engine+0x18]+f.execution_writes)
 check(all(f.r(sa+0x10)==f.target for sa,*_ in f.armies) and not f.r(f.stats+120),'active clearing uses complete group without optional stock exchange')
 check(f.r(f.commands+4)==1 and not f.r(f.commands+8),'active new assignment executed once, no unrelated command')
 check(not f.r(f.stats+116),'already active goal is not reactivated')
 f.f(f.world+0xe8,34)
 f.call(f.hook(34),obj=f.player,allowed=f.allowed()+[f.engine+0x18]+f.execution_writes)
 check(f.r(f.commands+4)==1,'unchanged active order is not reissued on next pulse')

 # A free builder is assigned in the fast active construction pass, with
 # native marker/capability/score checks still enforced.
 for case in ('ready','no-score','no-marker','wounded','fighting','recovery'):
  f=BuilderFixture(image,cave);f.w(f.sa+0x10,0);f.w(f.construct+8,2)
  f.w(f.player+4,1);f.w(f.player+0x12c,1);f.w(f.player+0x168,1);f.w(f.engine+0x18,0)
  table=0x510e8000;f.w(f.engine+8,table)
  for i in range(23):f.w(table+4*i,table+0x100+i*32)
  f.w(table+0x110,table+0x800);f.w(table+0x800,f.construct)
  f.w(image+0x4da6b0+0x14,image+0x2600);f.asm(image+0x2600,'xor eax,eax;ret')
  f.w(image+0x4da6b0+0x60,image+0x2800);f.asm(image+0x2800,'ret 4')
  f.asm(image+0x1e47be,f'inc dword ptr [{f.stats+108}];ret 12')
  f.asm(image+0x1e838a,f'mov dword ptr [{f.engine+0x18}],3;push 1;push {f.engine+0x14};push {f.budget};mov ecx,{f.construct};call {cave+f.hook(36)["offset"]};mov dword ptr [{f.engine+0x18}],0;ret')
  execution_writes=execution_stub(f)
  region_stub(f)
  if case=='no-score':f.f(f.stats+116,0)
  if case=='no-marker':f.w(f.marker+8,1)
  if case=='wounded':f.f(f.leader+0x910,69)
  if case=='fighting':f.w(f.state,image+0x4f4e20)
  if case=='recovery':f.w(f.actor+0x100,0x2000)
  f.call(f.hook(34),obj=f.player,allowed=f.allowed()+[f.engine+0x18,f.player+0x178,f.player+0x181]+execution_writes)
  check((f.r(f.sa+0x10)==f.construct)==(case=='ready'),('fast builder checks',case))
  check(not f.r(f.stats+108),'fast builder pass skips stock exchange')
  check(f.r(f.commands+4)==int(case=='ready') and not f.r(f.commands+8),'builder command follows fast assignment only when feasible')

print('AI_EXPANSION_PULSE_PASS',checks,'checks; three relocated bases; native selection and engine services stubbed, original pending activation executed')
