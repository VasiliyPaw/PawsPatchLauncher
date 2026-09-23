"""Pending Explore recruitment through compiled x86 hook and original activation
caller. Native diplomacy/gain/list bookkeeping are explicit stubs, not a match.
"""
from pathlib import Path
exec(compile(Path(__file__).with_name('test_defense.py').read_text().split('\nfor image,cave in ')[0], 'test_defense.py:fixtures','exec'))

class ScoutFixture(DefenseFixture):
 def __init__(self,image=0x460000,cave=0x10000000):
  super().__init__(image,cave)
  self.w(self.target+8,1);self.w(self.engine+0x14,self.node+0x800)
  self.w(self.node+0x800,self.source);self.w(self.node+0x804,self.target)
  self.w(self.sa+4,10)
  self.asm(image+0x42fca,'mov eax,[ecx]; dec dword ptr [eax+4]; ret')
  self.w(image+0x4da510+0x64,image+0x2500)
  self.asm(image+0x2500,'mov eax,[esp+4]; mov [eax+0x10],ecx; inc dword ptr [ecx+0x14]; ret 16')
 def seed(self,vector=None,index=1):
  self.call(self.hook(23),obj=self.target,args=[self.budget,self.engine+0x14 if vector is None else vector,index],allowed=[self.sa+4,self.sa+0x10,self.source+0x14,self.target+0x14])
  return self.r(self.sa+0x10)==self.target

for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 f=ScoutFixture(image,cave);f.warm();check(f.seed(),'ready defender seeds pending Explore')
 check(f.r(f.target+8)==1,'hook leaves native goal activation to caller')
 check(f.r(f.sa+4)==10,'temporary SA reference balanced')
 check([f.r(f.stats+44+4*i) for i in range(5)]==[f.sa,f.budget,1,1,0],'native removal budget/flags')
 check([f.r(f.stats+72+4*i) for i in range(4)]==[f.sa,0,0,0],'pending native add has no duplicate budget/recalculation')
 check(f.r(f.stats+36)==1 and f.r(f.stats+64)==1,'one removal and one addition')
 for scenario in ['not-quiet','wounded','morale','missing-member','moving','combat','enemy','recent-damage','wrong-owner','dead-city','reserved','native-refusal','zero-gain','nan-gain','disabled','active-target','dead-target','non-explore','filled-target','filled-head','zero-priority','nan-priority','bad-vector','bad-index','other-player','recent-dispatch','construction']:
  f=ScoutFixture(image,cave);f.warm()
  if scenario=='not-quiet':f.tick(5)
  if scenario=='wounded':f.f(f.leader+0x910,99)
  if scenario=='morale':f.f(f.org+0x5c,77)
  if scenario=='missing-member':f.w(f.org+0x200,0)
  if scenario=='moving':f.w(f.state,image+0x4f503c)
  if scenario=='combat':f.w(f.state,image+0x4f4e20)
  if scenario=='enemy':f.enemy()
  if scenario=='recent-damage':f.damage()
  if scenario=='wrong-owner':f.w(f.actor+0xe8,f.kingdom+0x800)
  if scenario=='dead-city':f.f(f.city+0x510,0)
  if scenario=='reserved':f.f(f.stats+88,.75)
  if scenario=='native-refusal':f.w(f.stats+28,1)
  if scenario=='zero-gain':f.f(f.stats+32,0)
  if scenario=='nan-gain':f.f(f.stats+32,float('nan'))
  if scenario=='disabled':f.w(f.data+4,7)
  if scenario=='active-target':f.w(f.target+8,2)
  if scenario=='dead-target':f.w(f.target+8,0)
  if scenario=='non-explore':f.w(f.target,image+0x4da480)
  if scenario=='filled-target':f.w(f.target+0x14,1)
  if scenario=='filled-head':f.w(f.target+0xc,f.node)
  if scenario=='zero-priority':f.f(f.target+0x38,0)
  if scenario=='nan-priority':f.f(f.target+0x38,float('nan'))
  if scenario=='other-player':f.w(f.target+4,f.engine+0x80)
  if scenario=='recent-dispatch':f.f(f.data+meta['routingOffset']+meta['routingSize']+96*24+4096*32+12,25)
  if scenario=='construction':
   g=f.node+0xa00;f.w(g,image+0x4da6b0);f.w(g+4,f.engine);f.w(g+8,2);f.f(g+0x38,100)
   for o in (0x28,0x6c):f.w(image+0x4da6b0+o,f.r(image+0x4d79e8+o))
   f.w(f.engine+0x18,3);f.w(f.node+0x808,g)
  check(not f.seed(vector=f.node if scenario=='bad-vector' else None,index=2 if scenario=='bad-index' else 1),('gate',scenario,image))
  check(f.r(f.sa+0x10)==f.source,'rejected candidate keeps original assignment')
  check(f.r(f.stats+36)==0 and f.r(f.stats+64)==0,'no mutation on rejection')
 for count in range(7):
  for state in (1,2):
   f=ScoutFixture(image,cave);f.scouts(count);f.warm()
   g=f.node+0xa00;f.w(g,image+0x4d79e8);f.w(g+8,state)
   node=f.r(f.node+0x204)
   while node:f.w(f.r(node)+0x10,g);node=f.r(node+4)
   check(f.seed()==(count<5),('five-scout cap including staged assignments',count,state))
 f=ScoutFixture(image,cave);f.warm();f.asm(image+0x2300,'ret 16')
 check(not f.seed(),'failed native add does not claim assignment')
 check(f.r(f.sa+0x10)==f.source and f.r(f.source+0x14)==1,'native add refusal restores source')
 check(f.r(f.sa+4)==10,'failed native add balances temporary reference')
 # Execute the exact original activation parent, with only external game
 # services mocked. Verifies this hook is reached while pending, returns to
 # real recalculation/activation branches and consumes exactly three args.
 for accepts in (True,False):
  f=ScoutFixture(image,cave);f.warm()
  original=bytearray(game[0x1e4736:0x1e47be])
  struct.pack_into('<I',original,0x1e47ae-0x1e4736,image+0x5f3fc8)
  f.u.mem_write(image+0x1e4736,bytes(original))
  h=f.hook(23);f.u.mem_write(image+h['site'],b'\xe8'+struct.pack('<i',cave+h['offset']-image-h['site']-5))
  f.asm(image+h['target'],'ret 12')
  for off,addr,code in [(0x14,0x2600,'xor eax,eax; ret'),(0x38,0x2700,'xor eax,eax; ret'),(0x8,0x2800,'mov eax,3; ret'),(0x80,0x2900,'mov dword ptr [ecx+8],0; ret')]:
   f.w(image+0x4d79e8+off,image+addr);f.asm(image+addr,code)
  score=bits(10 if accepts else 0)
  f.asm(image+0x1e54b1,f'mov dword ptr [ecx+0x34],{score}; ret 20')
  f.asm(image+0x1e156b,'ret 4')
  f.w(f.sp,0x62000000)
  for i,v in enumerate([f.budget,f.engine+0x14,1]):f.w(f.sp+4+i*4,v)
  f.u.reg_write(UC_X86_REG_ESP,f.sp);f.u.reg_write(UC_X86_REG_ECX,f.target)
  f.u.emu_start(image+0x1e4736,0x62000000,count=6000000)
  check(f.u.reg_read(UC_X86_REG_EIP)==0x62000000,'native parent returns')
  check(f.u.reg_read(UC_X86_REG_ESP)==f.sp+16,'native parent ABI')
  check(f.r(f.target+8)==(2 if accepts else 0),'native parent retains final activation/rejection decision')
  check(f.r(f.stats+36)==1 and f.r(f.stats+64)==1,'parent used recruitment hook exactly once')
print('AI_SCOUTING_PASS',checks,'checks; three ASLR bases; original activation caller, explicit engine-service stubs')
