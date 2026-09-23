"""Region-only defense and candidate ranking, compiled x86 at three ASLR bases.
Uses the real native winning-comparison instructions; game services stubbed.
"""
from pathlib import Path
exec(compile(Path(__file__).with_name('test_clearing_priority.py').read_text().split('\nfor image,cave in ')[0], 'test_clearing_priority.py:fixtures','exec'))

def region(f,goal=None,x=16,y=64):
 g=f.source if goal is None else goal
 p=f.node+0xe00;f.w(g+0x4c,0);f.w(g+0x48,p);f.f(p+0x54,x);f.f(p+0x58,y)
 return p

for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 for case in ['quiet','wounded','moving','combat','damage','near-enemy','anchor-enemy','anchor-damage','invalid-region','stale-target','five-scouts','disabled']:
  f=DefenseFixture(image,cave);p=region(f,x=100,y=64)
  if case=='wounded':f.f(f.leader+0x910,99)
  if case in ['moving','combat']:f.w(f.state,image+(0x4f4df0 if case=='moving' else 0x4f4e20))
  if case=='invalid-region':f.w(f.source+0x48,0)
  if case=='stale-target':f.w(f.source+0x4c,0x10004)
  if case=='five-scouts':f.scouts(5)
  if case=='disabled':f.w(f.data+4,7)
  f.tick(0)
  if case in ['damage','anchor-damage']:
   f.f(f.world+0xe8,5)
   if case=='anchor-damage':f.f(f.city+0x20,100)
   f.damage()
  if case in ['near-enemy','anchor-enemy']:
   f.enemy()
   if case=='anchor-enemy':f.f(f.lair+0x20,100)
  f.tick(10)
  check(f.transfer()==(case=='quiet'),('region release safety',case,image))
  if case=='quiet':
   check(f.admission()==1,'region quiet-return cooldown')
   f.enemy();f.f(f.lair+0x20,100)
   check(f.admission()==0,'region-anchor threat overrides cooldown')
 f=DefenseFixture(image,cave);p=region(f);f.tick(0)
 f.w(f.source+0x48,p+0x100);f.f(p+0x154,16);f.f(p+0x158,64);f.tick(10)
 check(not f.transfer(),'new region restarts quiet time')
 f.tick(20);check(f.transfer(),'new region releases after full quiet interval')
 # Both additional recruitment paths must work with targetless defense.
 f=PriorityFixture(image,cave);f.army();region(f);f.warm()
 check(f.plan()==2,'targetless regional defenders join complete clearing group')
 f=PriorityFixture(image,cave);f.w(f.lair+8,1);region(f);f.warm();f.recruit()
 check(f.r(f.sa+0x10)==f.explore,'targetless defense can fill pending exploration')
 f=PriorityFixture(image,cave);f.army();region(f);f.w(f.target+8,1);f.warm()
 f.recruit();check(all(f.r(sa+0x10)==f.source for sa,*_ in f.armies),'regional force reserved for pending clearing')
 f.recruit(f.target);check(all(f.r(sa+0x10)==f.target for sa,*_ in f.armies),'regional force staged in own pending activation')
 # Candidate callback preserves unchanged scores and native ABI. Failed
 # native eligibility never reaches this call site in the actual selector.
 for case in ['camp','foundation','hidden','dead','ally','insufficient','disabled','zero','negative','nan','infinite','overflow']:
  f=PriorityFixture(image,cave);f.army();score=10
  if case=='foundation':f.w(f.ldef+0x4e0,0)
  if case=='hidden':f.w(f.stats+16,0)
  if case=='dead':f.w(f.lair+8,1)
  if case=='ally':f.w(f.stats+12,1)
  if case=='insufficient':f.f(f.den+0x10,1000)
  if case=='disabled':f.w(f.data+4,7)
  if case in ['zero','negative','nan','infinite','overflow']:score={'zero':0,'negative':-10,'nan':float('nan'),'infinite':float('inf'),'overflow':1e38}[case]
  result=f.call(f.hook(24),obj=f.player,args=[f.lair],fp=score)
  expected=40 if case=='camp' else struct.unpack('<f',struct.pack('<f',score))[0]
  check((math.isnan(result) and math.isnan(expected)) or result==expected,('candidate ranking gate',case,result))
 # Real original 1F77B3..1F77DD comparison, with only its already-admitted
 # candidate score callee stubbed. Previous goal-level multiplier would
 # leave the ordinary target (score20) ahead of settlement camp(score10).
 for enabled in (True,False):
  for order in [(False,True),(True,False)]:
   f=PriorityFixture(image,cave);f.army();f.w(f.data+4,15 if enabled else 7)
   start,end=0x1f77b3,0x1f77dd;code=bytearray(game[start:end]);h=f.hook(24)
   struct.pack_into('<i',code,h['site']+1-start,cave+h['offset']-image-h['site']-5)
   struct.pack_into('<I',code,0x1f77c9-start,image+0x451244)
   f.u.mem_write(image+start,bytes(code));f.f(image+0x451244,0.0001)
   ctx=f.node+0xf00;winner=ctx+16;f.w(ctx,f.player);f.w(winner,0);f.f(f.sp+0x10,0)
   for camp in order:
    candidate=f.lair if camp else f.city
    f.f(f.stats+20,10 if camp else 20)
    f.asm(image+h['target'],f'fld dword ptr [{f.stats+20}];ret 4')
    for reg,val in [(UC_X86_REG_ESP,f.sp),(UC_X86_REG_ESI,ctx),(UC_X86_REG_EDI,candidate),(UC_X86_REG_EBP,winner)]:f.u.reg_write(reg,val)
    f.u.emu_start(image+start,image+end,count=40000000)
    check(f.u.reg_read(UC_X86_REG_EIP)==image+end and f.u.reg_read(UC_X86_REG_ESP)==f.sp,'original comparison ABI')
   check(f.r(winner)==(f.lair if enabled else f.city),('native selector winner',enabled,order))

print('AI_REGION_CLEARING_PASS',checks,'checks; 3 ASLR bases; original native winning comparison; other engine services stubbed')
