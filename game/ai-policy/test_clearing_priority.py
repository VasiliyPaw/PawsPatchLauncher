"""Regression for r18 scouting starving a complete clearing group. Compiled
x86 and original pending activation parent; external engine services stubbed.
"""
from pathlib import Path
exec(compile(Path(__file__).with_name('test_clearing.py').read_text().split('\nfor image,cave in ')[0], 'test_clearing.py:fixtures','exec'))

class PriorityFixture(GroupFixture):
 def __init__(self,image=0x460000,cave=0x10000000):
  super().__init__(image,cave)
  self.explore=self.node+0xc00
  self.w(self.explore,image+0x4d79e8);self.w(self.explore+4,self.engine);self.w(self.explore+8,1);self.f(self.explore+0x38,300)
  self.w(self.engine+0x18,3);self.w(self.node+0x808,self.explore)
  self.w(image+0x4d79e8+0x68,image+0x2200)
 def allowed(self):
  return [self.source+0x14,self.target+0x14,self.explore+0x14]+[x for sa,*_ in self.armies for x in [sa+4,sa+0x10]]
 def plan(self):
  self.call(self.hook(22),obj=self.source,args=[self.budget,self.engine+0x14,0],allowed=self.allowed())
  return sum(self.r(t[0]+0x10)==self.target for t in self.armies)
 def recruit(self,goal=None):
  goal=self.explore if goal is None else goal
  self.call(self.hook(23),obj=goal,args=[self.budget,self.engine+0x14,1 if goal==self.target else 2],allowed=self.allowed())
 def as_scout(self,army):
  sa,a,org,unit,state=army
  self.w(self.sa+4,1);self.w(self.explore+8,2);self.w(self.explore+0x14,1)
  self.w(sa+0x10,self.explore);self.w(state,self.image+0x4f5038)
 def fallback(self,sa):
  self.w(self.explore+8,2)
  self.call(self.hook(20),obj=self.source,args=[self.explore,sa,self.budget],allowed=self.allowed())
  return self.r(sa+0x10)==self.explore

for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 # Exact reported failure: individually zero marginal gain but a viable pair.
 f=PriorityFixture(image,cave);f.army();f.warm();f.f(f.stats+32,0)
 f.recruit();check(all(f.r(sa+0x10)==f.target for sa,*_ in f.armies),'clearing commits before extra scouting despite zero singleton gain')
 check(f.r(f.explore+0x14)==0,'scouting did not consume the strike force')
 for state in (1,2):
  f=PriorityFixture(image,cave);f.army();spare=f.army(100,120);f.warm();f.w(f.target+8,state);f.f(f.stats+32,0)
  check(not f.fallback(f.sa),'complete group reserves selected defender for pending or active attack')
  f.f(f.stats+32,10);check(f.fallback(spare[0]),'unneeded spare can still explore')
  check(f.r(f.target+8)==state,'reservation never activates an attack')
 f=PriorityFixture(image,cave);f.army();f.warm();f.w(f.target+8,1)
 f.recruit();check(all(f.r(sa+0x10)==f.source for sa,*_ in f.armies),'pending force reserved until its own activation callback')
 # Previous active callback used this pass's throttle, but cannot consume the
 # only valid pending activation opportunity.
 f.recruit(f.target);check(all(f.r(sa+0x10)==f.target for sa,*_ in f.armies),'own pending callback fills complete reserved group')
 check(f.r(f.target+8)==1,'native parent remains responsible for activation')
 check([f.r(f.stats+72+4*i) for i in range(4)]==[f.sa,0,0,0],'pending AddActor uses null budget and no recalculation')
 check(all(e[-1]==2 for e in f.events(35)),'pending assignments explicitly distinguished in diagnostics')
 # A defender and an exploring company can form the pair. One missing/wounded
 # or engaged member must prevent the full group transfer, including Move
 # companies whose individual unit has already entered combat.
 for case in ['explore','move','guard','sleep','wound','morale','rout','kill','member-fighting','recent-damage','builder','far','wrong-owner']:
  f=PriorityFixture(image,cave);army=f.army();f.warm();f.as_scout(army);sa,a,org,unit,st=army
  if case in ['move','guard','sleep','rout','kill']:f.w(st,image+{'move':0x4f4df0,'guard':0x4f4f28,'sleep':0x4f4d98,'rout':0x4f500c,'kill':0x4f4e20}[case])
  if case=='wound':f.f(unit+0x210,69)
  if case=='morale':f.f(org+0x5c,46)
  if case=='member-fighting':
   f.w(unit+0x70,unit+0x300);f.w(unit+0x314,unit+0x340);f.w(unit+0x340,unit+0x380);f.w(unit+0x380,image+0x4f4e20)
  if case=='recent-damage':f.damage(a)
  if case=='builder':f.w(a+0xa8,a+0x280);f.w(a+0x280,image+0x4df830);f.w(a+0x284,a)
  if case=='far':f.f(a+0x20,400)
  if case=='wrong-owner':f.w(a+0xe8,f.kingdom+0x800)
  got=f.plan();check((got==2)==(case in ['explore','move','guard','sleep']),('scout donor readiness',case,got))
  if case not in ['explore','move','guard','sleep']:check(f.r(f.sa+0x10)==f.source and f.r(sa+0x10)==f.explore,'failed group does not transfer its other member')
 # No feasible group must not create a permanent reserve blocking all scouting.
 f=PriorityFixture(image,cave);f.warm();check(f.fallback(f.sa),'insufficient whole group leaves scouting available')
 # A partial native failure restores all original tasks and balances refs.
 for pending in (False,True):
  f=PriorityFixture(image,cave);f.army();f.warm();f.w(f.target+8,1 if pending else 2)
  f.asm(image+0x2300,f'mov eax,[esp+4];cmp eax,{f.sa};je refuse;mov [eax+0x10],ecx;inc dword ptr [ecx+0x14];refuse:ret 16')
  if pending:f.recruit(f.target)
  else:f.plan()
  check(all(f.r(sa+0x10)==f.source for sa,*_ in f.armies),'failed second addition rolls back first and restores second')
  check(f.r(f.target+0x14)==0,'partial failed group leaves target empty')
  check(all(f.r(sa+4)==1 for sa,*_ in f.armies),'failure balances all held references')
  check(not f.events(35),'rolled back group is not reported as assigned')
 # Original activation parent, not a replacement dispatcher, chooses state2.
 for accepts in (True,False):
  f=PriorityFixture(image,cave);f.army();f.warm();f.w(f.target+8,1)
  original=bytearray(game[0x1e4736:0x1e47be]);struct.pack_into('<I',original,0x1e47ae-0x1e4736,image+0x5f3fc8)
  f.u.mem_write(image+0x1e4736,bytes(original));h=f.hook(23)
  f.u.mem_write(image+h['site'],b'\xe8'+struct.pack('<i',cave+h['offset']-image-h['site']-5));f.asm(image+h['target'],'ret 12')
  for off,addr,code in [(0x14,0x2600,'xor eax,eax;ret'),(0x38,0x2700,'xor eax,eax;ret'),(0x8,0x2800,'mov eax,3;ret'),(0x80,0x2900,'mov dword ptr [ecx+8],0;ret')]:
   f.w(image+0x4da480+off,image+addr);f.asm(image+addr,code)
  f.asm(image+0x1e54b1,f'mov dword ptr [ecx+0x34],{bits(10 if accepts else 0)};ret 20');f.asm(image+0x1e156b,'ret 4')
  f.w(f.sp,0x62000000)
  for i,v in enumerate([f.budget,f.engine+0x14,1]):f.w(f.sp+4+i*4,v)
  f.u.reg_write(UC_X86_REG_ESP,f.sp);f.u.reg_write(UC_X86_REG_ECX,f.target)
  f.u.emu_start(image+0x1e4736,0x62000000,count=40000000)
  check(f.u.reg_read(UC_X86_REG_EIP)==0x62000000 and f.u.reg_read(UC_X86_REG_ESP)==f.sp+16,'original activation parent returns with correct ABI')
  check(f.r(f.target+8)==(2 if accepts else 0),'original activation or rejection retained')
  check(all(f.r(sa+0x10)==f.target for sa,*_ in f.armies),'whole pair reached original activation decision')

print('AI_CLEARING_PRIORITY_PASS',checks,'checks; 3 ASLR bases; full group reservations, scout donors, original activation parent; engine services partly stubbed')
