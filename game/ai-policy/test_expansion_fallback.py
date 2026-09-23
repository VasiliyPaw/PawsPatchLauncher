"""Compiled settlement fallback and native region-scoring hook, three ASLRs.
Native fog, diplomacy, bookkeeping and region queries are controlled services."""
from pathlib import Path
exec(compile(Path(__file__).with_name('test_clearing_priority.py').read_text().split('\nfor image,cave in ')[0],'test_clearing_priority.py:fixtures','exec'))

def second_camp(f):
 c=0x510e8000;d=c+0x400;g=c+0x1000
 f.u.mem_write(c,bytes(f.u.mem_read(f.lair,0x180)));f.w(c+0x14,335);f.w(f.reg+0x20004+335*4,c);f.f(c+0x20,100)
 f.w(c+0x88,d);f.w(d,f.image+0x4e0434);f.w(d+4,c);f.f(d+0x10,100)
 f.w(c+0x60,d+0x100);f.w(d+0x104,c);f.f(d+0x110,1000)
 f.w(c+0x94,d+0x200);f.w(d+0x204,c);f.w(c+0xc4,0)
 f.u.mem_write(g,bytes(f.u.mem_read(f.target,0x80)));f.w(g+0x4c,335)
 f.w(f.node+0x80c,g);f.w(f.engine+0x18,4)
 return c,g

for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 for case in ('missing-best-goal','rejected-best','fully-staffed-best','no-second','foundation','dead','hidden','disabled','stale-id'):
  f=PriorityFixture(image,cave);f.army();c,g=second_camp(f);f.warm()
  if case=='rejected-best':f.asm(image+0x2000,f'cmp ecx,{f.target};sete al;movzx eax,al;ret 4')
  elif case=='fully-staffed-best':
   existing=f.army(200);f.w(existing[0]+0x10,f.target);f.w(f.target+0xc,f.node+0xe00);f.w(f.node+0xe00,existing[0]);f.w(f.target+0x14,1)
  else:f.w(f.target+0x4c,0)
  if case=='no-second':f.w(f.engine+0x18,3)
  if case=='foundation':
   otherdef=c+0x1800;f.u.mem_write(otherdef,bytes(f.u.mem_read(f.ldef,0x600)));f.w(otherdef+0x4e0,0);f.w(c+4,otherdef)
  if case=='dead':f.w(c+8,1)
  if case=='hidden':f.w(f.stats+16,0)
  if case=='disabled':f.w(f.data+4,7)
  if case=='stale-id':f.w(g+0x4c,0x10000+335)
  f.call(f.hook(22),obj=f.source,args=[f.budget,f.engine+0x14,0],allowed=f.allowed()+[g+0x14])
  got=sum(f.r(sa+0x10)==g for sa,*_ in f.armies)
  check((got==2)==(case in ('missing-best-goal','rejected-best','fully-staffed-best')),('next feasible goal',case,got))
  check(all(f.r(sa+4)==1 for sa,*_ in f.armies),('balanced fallback refs',case))
 # Keep native region admissibility: positive score only, same ego/player,
 # native camp region and no existing positive attack goal.
 for case in ('missing-goal','zero-goal','has-goal','different-region','hidden','foundation','dead','no-army','disabled','native-zero','native-negative','native-nan'):
  f=PriorityFixture(image,cave);f.army();r=f.node+0xe00
  f.asm(image+0x2273c2,f'mov eax,{r};ret')
  if case in ('has-goal','zero-goal'):
   f.w(f.engine+0xc,f.node+0xf00);f.w(f.node+0xf00,f.target)
   if case=='zero-goal':f.f(f.target+0x38,0)
  if case=='hidden':f.w(f.stats+16,0)
  if case=='foundation':f.w(f.ldef+0x4e0,0)
  if case=='dead':f.w(f.lair+8,1)
  if case=='no-army':f.w(f.player+0x2c,0)
  if case=='disabled':f.w(f.data+4,7)
  score={'native-zero':0,'native-negative':-10,'native-nan':float('nan')}.get(case,10)
  args=[bits(1),f.kingdom,r+4 if case=='different-region' else r,0,f.explore+0xc,bits(16),bits(64),0,0]
  got=f.call(f.hook(33),obj=f.ego,args=args,fp=score)
  expected=40 if case in ('missing-goal','zero-goal') else score
  check((math.isnan(got) and math.isnan(expected)) or got==expected,('scouting completion score',case,got))

print('AI_EXPANSION_FALLBACK_PASS',checks,'checks; 3 ASLR bases; missing/rejected/staffed camps skipped; exploration completes only native eligible regions')
