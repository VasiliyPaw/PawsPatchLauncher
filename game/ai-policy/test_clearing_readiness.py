"""Regression for reported returning attacker and partial 70/60 scout donors.
Executes compiled callbacks; list/AI engine services are explicit stubs.
"""
from pathlib import Path
exec(compile(Path(__file__).with_name('test_clearing_priority.py').read_text().split('\nfor image,cave in ')[0], 'priority:fixtures', 'exec'))

for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 for source in ['scout','defender']:
  for case,hp,morale,expected in [('boundary',70,60,True),('hp-below',69.99,60,False),('morale-below',70,59.99,False),('nan-hp',float('nan'),100,False),('nan-morale',100,float('nan'),False),('partial',70,60,True),('empty',100,100,False),('injured-member',70,60,True),('recovering-move',100,100,False)]:
   f=PriorityFixture(image,cave);army=f.army();f.warm()
   if source=='scout':f.as_scout(army)
   sa,a,org,unit,st=army
   f.f(org+0x60,100);f.f(org+0x5c,morale);f.f(unit+0x210,hp)
   if case=='partial':f.w(f.layout+0x204,f.ldef) # selected flank absent
   if case=='empty':f.w(org+0x180,0)
   if case=='recovering-move':f.w(st,image+0x4f4df0);f.w(a+0x100,0x2000)
   if case=='injured-member':
    # Two living units total 140/200 HP, although one is only 40% healthy.
    extra=a+0xc00;body=extra+0x200;element=extra+0x180
    f.w(extra,image+0x4e5c58);f.w(extra+0x14,400);f.w(extra+0xe8,f.kingdom);f.w(f.reg+0x20004+400*4,extra)
    f.w(extra+0x60,body);f.w(body+4,extra);f.f(body+0x10,40);f.f(body+0x14,100)
    f.w(extra+0x80,element);f.w(element+4,extra);f.w(element+0x10,a)
    f.w(org+0x184,extra);f.f(unit+0x210,100);f.w(f.layout+0x204,f.ldef)
   check((f.plan()==2)==expected,('70/60 donor',source,case))
 # A retreating company stays assigned, but must not satisfy the whole attack.
 for state,flags,available in [(0x4f4df0,0x2000,False),(0x4f4df0,0x4000,False),(0x4f4fe0,0,False),(0x4f500c,0,False),(0x4f50a0,0,False),(0x4f4efc,0,False),(0x4f4ed0,0,False),(0x4f4df0,0,True),(0x4f4e78,0,True),(0x4f4fb4,0,True)]:
  f=PriorityFixture(image,cave);donor=f.army();old=f.army(500,32);f.warm()
  sa,a,org,unit,st=old;f.w(sa+0x10,f.target);f.w(f.target+0x14,1);f.w(f.source+0x14,2)
  node=0x510ee000;f.w(node,sa);f.w(node+4,0);f.w(f.target+0xc,node)
  f.w(st,image+state);f.w(a+0x100,flags)
  got=f.plan()
  check(got==(1 if available else 3),('existing attacker availability',hex(state),hex(flags),got))
  check(f.r(sa+0x10)==f.target and f.r(a+0x100)==flags and f.r(st)==image+state,'existing native recovery/attack untouched')
  check(bool(f.events(48))==(not available),'unavailable existing force diagnosed')
  check(all(f.r(x[0]+4)==1 for x in f.armies),'balanced references with pre-existing attacker')

print('AI_CLEARING_READINESS_PASS',checks,'checks; 3 ASLR bases; actual compiled callback, mocked native assignment services')
