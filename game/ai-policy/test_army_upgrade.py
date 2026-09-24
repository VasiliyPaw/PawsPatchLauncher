"""Compiled upgrade hooks: two capacities, meaningful gain, native ownership.
Engine services are controlled ABI stubs. This is not live-match acceptance.
"""
from pathlib import Path
exec(compile(Path(__file__).with_name('test_economy.py').read_text().split('\nfor image,cave in ')[0],'test_economy.py:fixtures','exec'))

class ArmyFixture(EconomyFixture):
 def __init__(self,image,cave):
  super().__init__(image,cave)
  self.w(self.player+4,1);self.w(self.recruit+0x44,self.military)
  self.w(self.layout+8,self.rs+0x1500);self.w(self.layout+0xc,self.rs+0x1580);self.w(self.rs+0x1520,1)
  self.f(self.rs+0xe00,150);self.f(self.org+0x68,100)
  self.asm(image+0x1dc172,f'fld dword ptr [{self.rs+0xe00}];ret 4')
  self.asm(image+0x21cc0e,f'mov eax,[{self.rs+0xe04}];ret 16')
  self.f(self.rs+0xe08,0);self.f(self.rs+0xe0c,0)
  self.asm(image+0x2400,'mov eax,[esp+16];'+''.join(f'mov dword ptr [eax+{4*i}],0;' for i in range(9))+f'mov dword ptr [eax+24],0x3f800000;mov edx,[esp+12];cmp edx,{self.layout};je new;mov edx,[{self.rs+0xe0c}];jmp value;new:mov edx,[{self.rs+0xe08}];value:mov [eax+32],edx;mov eax,9;ret')
 def eligible(self):return self.invoke(4,self.recruit,[self.military])

for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 for case in ('upgrade','equal','small-gain','funds','kingdom-blocked','kingdom-freed','no-shortage','combat','hero','militia','last-army','native-refusal','city-quota','requirements','failed-add','other-pending','disabled'):
  f=ArmyFixture(image,cave);sa,a,org,unit,state=f.military_army(40)
  if case=='equal':f.f(f.rs+0xe00,40)
  if case=='small-gain':f.f(f.rs+0xe00,53.99)
  if case=='funds':f.f(f.stock,99)
  if case.startswith('kingdom-'):
   f.f(f.prod+20,3);f.f(f.up+32,18.5);f.f(f.rs+0xe08,2.5)
   if case=='kingdom-freed':f.f(f.rs+0xe0c,1)
  if case=='no-shortage':f.f(f.prod+20,3)
  if case in ('combat','hero','militia'):
   for s,ac,o,u,st in f.armies:
    if case=='combat':f.w(st,image+0x4f4e20)
    if case=='hero':f.w(o+0x34,f.rs+0xf00);f.w(o+0x38,2);f.w(f.rs+0xf00,123)
    if case=='militia':f.w(ac+0x144,2)
  if case=='last-army':f.w(0x510cf000+4,0)
  if case=='native-refusal':f.w(f.rs+0xc10,0)
  if case=='requirements':f.w(f.rs+0xe04,3)
  if case=='city-quota':
   f.w(f.ego+0x398,1);f.w(f.engine+0x28,f.rs+0xf00);f.w(f.engine+0x2c,1);f.w(f.rs+0xf00,f.rs+0xf10);f.w(f.rs+0xf10,f.city);f.w(f.rs+0xf14,1)
  if case=='failed-add':f.asm(image+0x2300,'ret 16')
  if case=='other-pending':
   other=f.recruit+0x400;f.w(other,image+0x4d9274);f.w(other+0x50,f.sa);f.w(f.sa+0x10,other)
  if case=='disabled':f.w(f.data+4,7)
  got=f.replace();check(bool(got)==(case in ('upgrade','kingdom-freed','hero','disabled')),('upgrade selection',case,got))
  check(f.r(f.recruit+0x50)==(sa if case in ('upgrade','kingdom-freed','hero') else 0),('reservation',case))
  if case in ('upgrade','kingdom-freed','hero'):
   check(f.validate()==1,'valid final native disband')
   f.f(f.stock,0);check(f.validate()==0,'lost gold cancels disband');f.f(f.stock,100)
   f.w(f.rs+0xe04,3);check(f.validate()==0,'lost prerequisite cancels disband');f.w(f.rs+0xe04,0)
   f.f(f.rs+0xe00,40);check(f.validate()==0,'lost advantage cancels disband');f.f(f.rs+0xe00,150)
   f.w(state,image+0x4f4e20);check(f.validate()==0,'new combat cancels disband')
   f.w(state,image+0x4f4f28)
   for other_sa,other_a,*_ in f.armies:
    if other_a!=a:f.w(other_a+8,1)
   check(f.validate()==0,'loss of the other military company cancels disband')
  if case=='failed-add':check(f.r(sa+0x10)==f.source,'failed native assignment restores source')
 for freed,expected in ((0,0),(1,1)):
  f=ArmyFixture(image,cave);f.military_army(40);f.f(f.up+32,18.5);f.f(f.rs+0xe08,2.5);f.f(f.rs+0xe0c,freed)
  check(f.eligible()==expected,('early admission checks both limits',freed))
 f=ArmyFixture(image,cave);f.military_army(40);check(f.eligible()==1,'upgrade reaches final planner at full army cap')
 f.f(f.rs+0xe00,40);check(f.eligible()==0,'equal unit cannot bypass cap')
print('ARMY_UPGRADE_PASS',checks)
