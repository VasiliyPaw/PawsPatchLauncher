"""r35: compiled reservation, initial hero filter and budgeted execution retry.
Real native affordability/debit and Disband branch; engine transport/selection
are explicit ABI stubs. Does not substitute for a played match.
"""
from pathlib import Path
exec(compile(Path(__file__).with_name('test_army_upgrade.py').read_text().split('\nfor image,cave in ')[0],'test_army_upgrade.py:fixtures','exec'))

BASES=[(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]
for image,cave in BASES:
 for case in ('hero','captain','unit','military','human-player','disabled','native-reject','sovereign','empty-live-layout'):
  f=ArmyFixture(image,cave);f.w(f.recruit+0x44,f.builder)
  candidate=f.rs+0x3000;f.w(candidate+0x174,0x42036d);f.w(f.frame-0x34,f.recruit)
  if case in ('captain','unit'):f.w(candidate+0x174,0x40036d)
  if case=='military':f.w(f.recruit+0x44,f.military)
  if case=='human-player':f.w(f.player+4,0)
  if case=='disabled':f.w(f.data+4,7)
  if case=='sovereign':f.sovereign()
  if case=='empty-live-layout':f.w(f.recruit+0x48,0)
  native=0xabcdef00 if case=='native-reject' else 0xabcdef01
  got=f.invoke(51,candidate,[123],native=native)
  check(got==int(case in ('captain','unit','military','human-player','disabled')),('initial hero eligibility',case,got))
  check(f.r(candidate+0x174)==(0x40036d if case in ('captain','unit') else 0x42036d),'immutable definition preserved')
 for case in ('hold','own-goal','funds','combat','hero','requirements','disabled','capacity','last-army'):
  f=ArmyFixture(image,cave);sa,actor,org,unit,state=f.military_army(40);check(f.replace()==1,'staged military upgrade')
  if case=='funds':f.f(f.stock,0)
  if case=='combat':f.w(state,image+0x4f4e20)
  if case=='hero':f.w(org+0x34,f.rs+0xf00);f.w(org+0x38,1);f.w(f.rs+0xf00,123)
  if case=='requirements':f.w(f.rs+0xe04,3)
  if case=='disabled':f.w(f.data+4,7)
  if case=='capacity':f.f(f.prod+20,4)
  if case=='last-army':f.w(f.actor+8,1)
  goal=f.recruit if case=='own-goal' else f.explore
  check(f.call(f.hook(18),obj=actor,begin=[goal,0],native=0)==int(case in ('hold','hero')),('reservation admission and immediate cancellation',case))

class CompletionFixture(ArmyFixture):
 def __init__(self,image,cave):
  super().__init__(image,cave);self.old=self.military_army(40);check(self.replace()==1,'prepare retry')
  self.w(self.recruit+8,2);self.w(self.player+0x12c,1);self.w(self.engine+0x18,0)
  self.table=self.rs+0x4000;self.w(self.engine+8,self.table)
  for i in range(23):self.w(self.table+4*i,self.table+0x100+i*32)
  self.w(self.table+0x110,self.table+0x800);self.w(self.table+0x800,self.recruit)
  regions=self.table+0x900;self.w(image+0x5f3fcc,regions);self.w(regions+0x14,regions+0x100);self.w(regions+0x18,1)
  self.w(regions+0x100,regions+0x200);self.asm(image+0x2273c2,f'mov eax,{regions+0x200};ret')
  self.w(image+0x4d9274+0x14,image+0x2a00);self.asm(image+0x2a00,'xor eax,eax;ret')
  self.asm(image+0x1e838a,'ret') # selected reservation is already active
  self.w(image+0x5f3fb4,self.table+0xb00);self.w(self.table+0xb34,self.rs+0x80)
  self.u.mem_write(image+0x1e3e34,game[0x1e3e34:0x1e3eb3])
  self.w(image+0x1e3e7f,image+0x5f3fb4) # rebase absolute data reference
  self.asm(image+0x1e3cda,'mov eax,[esp+4];mov eax,[eax];movss xmm0,[eax];mov eax,[ecx+0x1c];comiss xmm0,[eax];setae al;ret 8')
  self.asm(image+0x1e3dfc,'mov eax,1;ret')
  start,end=0x1dc3c2,0x1dc48e;code=bytearray(game[start:end]);h=self.hook(32)
  struct.pack_into('<i',code,h['site']+1-start,cave+h['offset']-image-h['site']-5);self.u.mem_write(image+start,bytes(code))
  self.asm(image+0x1dc53d,f'jmp {image+end}')
  self.asm(image+end,'ret')
  self.asm(image+0x2f397,'mov eax,1;ret 4')
  self.asm(image+0x1e2321,f'mov eax,[ecx+8];and eax,65535;mov eax,[eax*4+{self.reg+0x20004}];ret 4')
  self.asm(image+0x1e3cb8,f'mov eax,{self.player};ret')
  self.command=self.table+0xc00;self.log=self.table+0xd00
  self.asm(image+0x2ef03c,f'mov eax,{self.command};ret')
  self.asm(image+0x22f4e9,'mov eax,[esp+4];mov [ecx],eax;mov eax,ecx;ret 4')
  self.asm(image+0x1f384d,'mov eax,[esp+4];mov eax,[eax];mov [ecx],eax;mov eax,[esp+8];mov [ecx+4],eax;mov eax,[esp+12];mov [ecx+8],eax;mov eax,ecx;ret 12')
  self.asm(image+0x1f2c03,f'mov eax,[esp+4];mov edx,[eax];mov edx,[edx];mov [{self.log}],edx;mov edx,[eax+4];mov [{self.log+4}],edx;inc dword ptr [{self.log+8}];ret 4')
  self.asm(image+0x1f397b,'ret')
  # Fresh native budget is a copy of stock. No simulated army/resources are mutated.
  self.money=self.table+0xe00;self.vector=self.money+0x40;self.w(self.vector,self.money);self.w(self.vector+4,9)
  code=f'push ebp;push ebx;push esi;push edi;mov ebp,{self.frame};mov eax,[{self.stock}];mov [{self.money}],eax;push {self.vector};mov ecx,{self.recruit};call {cave+self.hook(38)["offset"]};test al,al;jz done;mov ebx,{self.recruit};mov esi,{self.recruit+0x50};call {image+start};done:pop edi;pop esi;pop ebx;pop ebp;ret'
  self.asm(image+0x1e8925,code)
 def pulse(self,t):
  self.f(self.world+0xe8,t)
  return self.invoke(34,self.player,[],allowed=[self.engine+0x20]+list(range(self.command,self.vector+12,4))+[self.old[0]+4])

for image,cave in BASES:
 for case in ('retry','funds','combat','hero','requirements','disabled','normal-recruit','replacement-gone','expansion-budget-flag'):
  f=CompletionFixture(image,cave)
  if case=='funds':f.f(f.stock,0)
  if case=='combat':f.w(f.old[4],image+0x4f4e20)
  if case=='hero':f.w(f.old[2]+0x34,f.rs+0xf00);f.w(f.old[2]+0x38,1);f.w(f.rs+0xf00,123)
  if case=='requirements':f.w(f.rs+0xe04,3)
  if case=='disabled':f.w(f.data+4,7)
  if case=='normal-recruit':f.w(f.recruit+0x50,0)
  if case=='replacement-gone':f.w(f.old[0]+0x10,f.source)
  if case=='expansion-budget-flag':f.w(f.engine+0x20,1)
  f.pulse(30);expect=case in ('retry','hero','expansion-budget-flag')
  check(f.r(f.log+8)==int(expect),('retry reaches actual native Disband only when eligible',case))
  if expect:
   check(f.r(f.log)==10 and f.r(f.log+4)==f.r(f.old[1]+0x14),'native Disband addresses selected weak company')
   check(struct.unpack('<f',f.u.mem_read(f.money,4))[0]==0,'native cost deducted from fresh pass budget')
   check(struct.unpack('<f',f.u.mem_read(f.stock,4))[0]==100,'real kingdom stock untouched by policy')
   f.pulse(33);check(f.r(f.log+8)==1,'no retry before four game seconds')
   f.w(f.old[1]+8,1);f.pulse(34);check(f.r(f.log+8)==1,'completed/disbanded company never commanded twice')
  check(f.r(f.engine+0x20)==int(case=='expansion-budget-flag'),'original execution cascade flag restored')
print('UPGRADE_COMPLETION_PASS',checks,'checks; 3 ASLR bases; compiled initial hero filter and native budget/Disband path')
