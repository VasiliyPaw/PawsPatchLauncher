"""Readiness requires an actual living builder, not merely a living captain."""
from pathlib import Path
exec(compile(Path(__file__).with_name('test_builder_fleet.py').read_text().split('\nfor image,cave in ')[0],'fleet fixtures','exec'))
for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 for race in ('Undead','haroun'):
  for case in ('one-worker','captain-only','dead-worker','no-hp','wrong-company','wrong-owner','recycled-id','nan-hp'):
   f=FleetFixture(image,cave);f.race(race);f.builder_alive();f.build_goal();f.f(f.leader+0x910,0.001);f.f(f.org+0x5c,0)
   if case=='captain-only':f.w(f.leader+0xa8,0)
   if case=='dead-worker':f.w(f.leader+8,1)
   if case=='no-hp':f.f(f.leader+0x910,0)
   if case=='wrong-company':f.w(f.element+0x10,0)
   if case=='wrong-owner':f.w(f.leader+0xe8,f.kingdom+0x800)
   if case=='recycled-id':f.w(f.reg+4+2*3,1)
   if case=='nan-hp':f.f(f.leader+0x910,float('nan'))
   check(f.reclaim()==(case=='one-worker'),('living worker identity',race,case))
 f=FleetFixture(image,cave);f.race('haroun');f.builder_alive();f.pulse_setup();f.w(f.marker+8,1)
 for t in (30,34,62,94):f.pulse(t)
 check(f.r(f.commandlog)==0,'keep reusable Haroun company between sites')
 f=FleetFixture(image,cave);f.race('haroun');f.site(1);f.queued(1)
 check(f.eligible()==0,'one queued Haroun is enough for multiple sites')
print('AI_WORKER_SURVIVAL_PASS',checks,'checks; three ASLR bases')
