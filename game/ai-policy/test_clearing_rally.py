"""Safe existing native region staging; no generated attack or movement state."""
from pathlib import Path
exec(compile(Path(__file__).with_name('test_clearing_priority.py').read_text().split('\nfor image,cave in ')[0],'test_clearing_priority.py:fixtures','exec'))
class RallyFixture(PriorityFixture):
 def __init__(self,image,cave):
  super().__init__(image,cave)
  # Total army can clear the camp, but one company still needs recovery.
  self.army();self.warm();self.f(self.leader+0x910,50)
  self.f(self.lair+0x20,112);self.f(self.lair+0x24,32)
  self.rally=self.node+0xe00;self.region=self.node+0xf00
  self.w(self.rally,image+0x4da510);self.w(self.rally+4,self.engine);self.w(self.rally+8,1);self.f(self.rally+0x38,300)
  self.w(self.rally+0x48,self.region);self.f(self.region+0x54,80);self.f(self.region+0x58,120)
  self.w(self.engine+0x18,4);self.w(self.node+0x80c,self.rally)
  self.w(image+0x4da510+0x6c,image+0x2000);self.w(image+0x4da510+0x28,image+0x2100)
 def stage(self):
  self.call(self.hook(23),obj=self.rally,args=[self.budget,self.engine+0x14,3],allowed=self.allowed()+[self.rally+0x14])
  return self.r(self.armies[1][0]+0x10)==self.rally
for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 for case in ('safe','inside-guard-radius','city','hidden','no-force','foundation','zero-gain','native-refusal','disabled','failed-add'):
  f=RallyFixture(image,cave)
  if case=='inside-guard-radius':f.f(f.region+0x54,110);f.f(f.region+0x58,45)
  if case=='city':f.f(f.region+0x54,16);f.f(f.region+0x58,64)
  if case=='hidden':f.w(f.stats+16,0)
  if case=='no-force':f.f(f.den+0x10,200)
  if case=='foundation':f.w(f.ldef+0x4e0,0)
  if case=='zero-gain':f.f(f.stats+32,0)
  if case=='native-refusal':f.w(f.stats+28,1)
  if case=='disabled':f.w(f.data+4,7)
  if case=='failed-add':f.asm(image+0x2500,f'cmp ecx,{f.rally};je refused;mov eax,[esp+4];mov [eax+0x10],ecx;inc dword ptr [ecx+0x14];refused:ret 16')
  check(f.stage()==(case=='safe'),('safe existing rally',case))
  check(f.r(f.sa+0x10)==f.source,'injured company remains with its recovery/native task')
  check(f.r(f.rally+8)==1,'native parent owns rally activation')
  check(all(f.r(sa+4)==1 for sa,*_ in f.armies),'rally ref balance')
  check(not f.events(35),'insufficient force was not sent to attack')
  if case=='failed-add':check(f.r(f.armies[1][0]+0x10)==f.source,'failed staging restores original membership')
 # After native activation and recovery, join the camp assault directly.
 f=RallyFixture(image,cave);check(f.stage(),'staged ready reinforcement')
 f.w(f.rally+8,2);f.f(f.world+0xe8,40);f.f(f.leader+0x910,100)
 # Test the loaded-save case as well: no sidecar rally metadata retained.
 for preserve in (True,False):
  if not preserve:
   tail=meta['allocation']-meta['dataOffset']-96*28
   f.u.mem_write(f.data+tail,bytes(96*28))
  f.tick(40);f.tick(50)
  f.call(f.hook(22),obj=f.source,args=[f.budget,f.engine+0x14,0],allowed=f.allowed()+[f.rally+0x14])
  check(all(f.r(sa+0x10)==f.target for sa,*_ in f.armies),'rally joins once recovering company ready')
  if preserve:
   # Fresh equivalent staging for reconstruction case.
   f=RallyFixture(image,cave);check(f.stage(),'second staging');f.w(f.rally+8,2);f.f(f.leader+0x910,100)
print('AI_CLEARING_RALLY_PASS',checks,'checks; 3 ASLR bases; native activation/services stubbed')
