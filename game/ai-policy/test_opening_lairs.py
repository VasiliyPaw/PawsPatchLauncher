"""Compiled strategic large-lair gates; native target comparison is exercised.
Engine diplomacy and city services are controlled fixtures, not a live match.
"""
from pathlib import Path
exec(compile(Path(__file__).with_name('test_opening_capture.py').read_text().split('\nfor image,cave in ')[0], 'test_opening_capture.py:fixtures','exec'))

LARGE=['active_ice_dragon_lair','active_lair_dragon_lair','lair_dark_rift','branch_thing_dwelling','wyvern_nest','active_storm_drake_crag']
def named(f,name):
 f.w(f.ldef+8,f.ldef+0x100);f.u.mem_write(f.ldef+0x100,(name+'\0').encode('utf-16le'))
 f.w(f.ldef+0x290,0)
def candidate(f,score=100):
 return f.call(f.hook(24),obj=f.player,args=[f.lair],fp=score)

for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 for vt in (0x4da480,0x4d84d4):
  for name in LARGE:
   for count in (0,1,2,3,4):
    f=OpeningFixture(image,cave,count,vt);named(f,name)
    check(f.score()==(0 if count<3 else 1000),('large score',name,count))
    check(f.admission(0xaabbcc00)==(0xaabbcc01 if count<3 else 0xaabbcc00),('large admission',name,count))
    check(f.admission(0xaabbcc02)==0xaabbcc02,'native rejection survives')
    check(candidate(f)==(0 if count<3 else 100),('large candidate',name,count))
 for case in ('sovereign-third','foundation-third','foreign-third','dead-third','removed-third','stale-third','duplicate-third','nonconsecutive-duplicate','no-list','bad-list','no-ai','disabled',
              'defense','explore','recovery','area-only','foreign-goal','own-lair','ally-lair','removed-lair','dead-lair','recycled-target','unguarded','roaming-monster','small-lair','settlement-camp','city','similar-id'):
  f=OpeningFixture(image,cave,3 if case in ('sovereign-third','foundation-third','foreign-third','dead-third','removed-third','stale-third','duplicate-third','nonconsecutive-duplicate') else 2)
  named(f,LARGE[0]);third=f.r(f.citylist+8)
  if case=='sovereign-third':
   f.w(third+0x808,third+0x1000);f.u.mem_write(third+0x1000,'human_center_sovereign\0'.encode('utf-16le'))
  if case=='foundation-third':f.w(third+0x800+0x4e0,0)
  if case=='foreign-third':f.w(third+0xe8,f.kingdom+0x800)
  if case=='dead-third':f.f(third+0x610,0)
  if case=='removed-third':f.w(third+8,1)
  if case=='stale-third':f.w(third+0x14,0x10066)
  if case=='duplicate-third':f.w(f.citylist+8,f.r(f.citylist+4))
  if case=='nonconsecutive-duplicate':f.w(f.citylist+8,f.r(f.citylist))
  if case=='no-list':f.w(f.kingdom+0x2dc,0)
  if case=='bad-list':f.w(f.kingdom+0x2e0,257)
  if case=='no-ai':f.w(f.player+0x170,0)
  if case=='disabled':f.w(f.data+4,7)
  if case in ('defense','explore','recovery'):f.w(f.goal,image+{'defense':0x4da510,'explore':0x4d79e8,'recovery':0x4d0000}[case])
  if case=='area-only':f.w(f.goal+0x4c,0)
  if case=='foreign-goal':f.w(f.goal+4,f.engine+0x100)
  if case=='own-lair':f.w(f.lair+0xe8,f.kingdom)
  if case=='ally-lair':f.w(f.stats+12,1)
  if case=='removed-lair':f.w(f.lair+8,1)
  if case=='dead-lair':f.f(f.den+0x210,0)
  if case=='recycled-target':f.w(f.goal+0x4c,0x10002)
  if case in ('unguarded','roaming-monster'):f.w(f.lair+0x88,0)
  if case=='roaming-monster':f.w(f.lair+0x94,0)
  if case in ('small-lair','settlement-camp','city','similar-id'):named(f,{'small-lair':'wolf_den','settlement-camp':'slaan_settlementcamp','city':'human_center_city','similar-id':LARGE[0]+'_extra'}[case])
  blocked=case in ('foundation-third','foreign-third','dead-third','removed-third','stale-third','duplicate-third','nonconsecutive-duplicate')
  check(f.score()==(0 if blocked else 1000),('scope/identity',case))
  check(bool(f.admission())==blocked,('scope/admission',case))
 # Existing/new/loaded assignments derive the threshold from real ownership.
 f=OpeningFixture(image,cave,2);named(f,LARGE[1])
 check(f.score()==0 and f.admission()==1,'before third city')
 f.w(f.kingdom+0x2e0,3)
 check(f.score()==1000 and f.admission()==0,'third city unlocks immediately')
 f.w(f.kingdom+0x2e0,2)
 check(f.score()==0 and f.admission()==1,'city lost rechecks')
 f.u.mem_write(f.data,bytes(meta['allocation']-meta['dataOffset']));f.w(f.data+4,15)
 check(f.score()==0 and f.admission()==1,'load needs no additional saved state')
 for score in (0,-10,float('nan'),float('inf')):
  result=candidate(f,score)
  check((math.isnan(result) and math.isnan(score)) or result==score,'nonpositive/nonfinite native score unchanged')
 # The rejected high-score lair must not win the region target selection and
 # hide a permitted alternative. Execute the original comparison instructions.
 for count in (2,3):
  for order in ((True,False),(False,True)):
   f=OpeningFixture(image,cave,count);named(f,LARGE[0]);h=f.hook(24)
   start,end=0x1f77b3,0x1f77dd;code=bytearray(game[start:end])
   struct.pack_into('<i',code,h['site']+1-start,cave+h['offset']-image-h['site']-5)
   struct.pack_into('<I',code,0x1f77c9-start,image+0x451244)
   f.u.mem_write(image+start,bytes(code));f.f(image+0x451244,0.0001)
   ctx=f.citylist+0x100;winner=ctx+16;f.w(ctx,f.player);f.w(winner,0);f.f(f.sp+0x10,0)
   for large in order:
    target=f.lair if large else f.r(f.citylist)
    f.f(f.stats+20,10000 if large else 10)
    f.asm(image+h['target'],f'fld dword ptr [{f.stats+20}];ret 4')
    for reg,val in [(UC_X86_REG_ESP,f.sp),(UC_X86_REG_ESI,ctx),(UC_X86_REG_EDI,target),(UC_X86_REG_EBP,winner)]:f.u.reg_write(reg,val)
    f.u.emu_start(image+start,image+end,count=12000000)
    check(f.u.reg_read(UC_X86_REG_EIP)==image+end and f.u.reg_read(UC_X86_REG_ESP)==f.sp,'original comparison ABI')
   check(f.r(winner)==(f.lair if count==3 else f.r(f.citylist)),('native target selection',count,order))

print('AI_OPENING_LAIRS_PASS',checks,'checks; six exact lair IDs; three ASLR bases; native services stubbed')
