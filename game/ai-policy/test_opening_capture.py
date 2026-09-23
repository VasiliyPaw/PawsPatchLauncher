"""Execute compiled opening veto through existing x86 wrappers.
Native diplomacy/goal scoring are explicit stubs; no live gameplay claimed.
"""
from pathlib import Path
fixture_source=Path(__file__).with_name('test_routing.py').read_text().split('\nfor image,cave in ')[0]
exec(compile(fixture_source,'test_routing.py:fixtures','exec'))

class OpeningFixture(Fixture):
 def __init__(self,image,cave,cities=1,vt=0x4da480):
  super().__init__(image,cave)
  self.goal=0x510b0000;self.engine=0x510b1000;self.citylist=0x510b2000
  self.w(self.player+0xc,self.engine);self.w(self.engine+4,self.player)
  self.w(self.goal,image+vt);self.w(self.goal+4,self.engine);self.w(self.goal+8,2);self.w(self.goal+0x4c,2)
  self.w(self.lair+0xe8,self.kingdom+0x800);self.w(self.ldef+0x290,1)
  self.w(self.ldef+0x4e0,0);self.w(self.lair+0xc4,0)
  self.w(self.kingdom+0x2dc,self.citylist);self.w(self.kingdom+0x2e0,cities)
  for j in range(max(3,cities)):
   city=0x510c0000+j*0x2000;oid=100+j;con=city+0x400;body=city+0x600;definition=city+0x800
   self.w(self.citylist+j*4,city);self.w(city,image+0x4e5c58);self.w(city+0x14,oid);self.w(self.reg+0x20004+oid*4,city)
   self.w(city+0xe8,self.kingdom);self.w(city+4,definition);self.w(city+0x94,city+0x300);self.w(city+0x304,city)
   self.w(city+0x98,con);self.w(con+4,city);self.w(con+0x14,city);self.w(city+0x60,body);self.w(body+4,city);self.f(body+0x10,1000)
   self.w(definition+0x4e0,self.markerdef);self.w(definition+0x430,definition+0x600)
 def score(self,before=1000):
  self.f(self.goal+0x38,before)
  self.call(self.hook(0),obj=self.goal,args=[0,0],allowed=[self.goal+0x38])
  return struct.unpack('<f',self.u.mem_read(self.goal+0x38,4))[0]
 def admission(self,native=0):
  return self.call(self.hook(18),obj=self.actor,begin=[self.goal,0],native=native)

cases=['zero','one','two','three','disabled','no_sai','unowned_second','dead_second','stale_second','duplicate_second','enclave_second','sovereign_second',
 'removed_target','recycled_target','dead_target','allied_target','self_target','unguarded','destructible_lair','settlement_camp','enemy_city',
 'foundation_enclave','no_structure','area_only','defense','explore','native_zero','native_negative','inactive_goal','bad_city_list']
blocked={'zero','one','unowned_second','dead_second','stale_second','duplicate_second','enclave_second','unguarded','foundation_enclave','inactive_goal'}
for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 for vt in [0x4da480,0x4d84d4]:
  for case in cases:
   count=0 if case=='zero' else 3 if case=='three' else 2 if case in {'two','unowned_second','dead_second','stale_second','duplicate_second','enclave_second','sovereign_second'} else 1
   f=OpeningFixture(image,cave,count,vt);second=f.r(f.citylist+4)
   if case=='disabled':f.w(f.data+4,7)
   if case=='no_sai':f.w(f.player+0x170,0)
   if case=='unowned_second':f.w(second+0xe8,f.kingdom+0x800)
   if case=='dead_second':f.f(second+0x610,0)
   if case=='stale_second':f.w(second+0x14,0x10065)
   if case=='duplicate_second':f.w(f.citylist+4,f.r(f.citylist))
   if case=='enclave_second':f.w(second+0x800+0x4e0,0)
   if case=='removed_target':f.w(f.lair+8,1)
   if case=='recycled_target':f.w(f.goal+0x4c,0x10002)
   if case=='dead_target':f.f(f.den+0x210,0)
   if case=='allied_target':f.w(f.stats+12,1)
   if case=='self_target':f.w(f.lair+0xe8,f.kingdom)
   if case=='unguarded':f.w(f.lair+0x88,0)
   if case=='destructible_lair':f.w(f.ldef+0x290,0)
   if case in {'settlement_camp','enemy_city'}:f.w(f.ldef+0x4e0,f.markerdef)
   if case=='foundation_enclave':f.w(f.lair+0x98,f.den+0x700);f.w(f.den+0x714,f.lair)
   if case=='no_structure':f.w(f.lair+0x94,0)
   if case=='area_only':f.w(f.goal+0x4c,0)
   if case=='defense':f.w(f.goal,image+0x4da510)
   if case=='explore':f.w(f.goal,image+0x4d79e8)
   if case=='inactive_goal':f.w(f.goal+8,1)
   if case=='bad_city_list':f.w(f.kingdom+0x2e0,257)
   before=0 if case=='native_zero' else -1 if case=='native_negative' else 1000
   check(f.score(before)==(0 if case in blocked else before),('score',case,hex(vt)))
   # Existing native refusals and EAX's unrelated upper bits must survive.
   check(f.admission(0xaabbcc00)==(0xaabbcc01 if case in blocked or case in {'native_zero','native_negative'} else 0xaabbcc00),('admission',case,hex(vt)))
   check(f.admission(0xaabbcc02)==0xaabbcc02,('native refusal',case))
  f=OpeningFixture(image,cave,1,vt)
  check(f.score()==0 and f.admission()==1,'one city rejects')
  f.w(f.kingdom+0x2e0,2)
  check(f.score()==1000 and f.admission()==0,'second city unlocks without timer')
  f.w(f.kingdom+0x2e0,1)
  check(f.score()==0 and f.admission()==1,'losing second city rechecks immediately')
  # Fresh transient state, as on save load, derives the rule from owned cities.
  f.u.mem_write(f.data,bytes(meta['allocation']-meta['dataOffset']));f.w(f.data+4,15)
  check(f.score()==0 and f.admission()==1,'no saved timer/state needed')
result=dict(passed=True,checks=checks,bases=3,goalTypes=2,nativeEngineBoundariesStubbed=True,liveMatch=False)
(a.native/'opening-capture-tests.json').write_text(json.dumps(result,indent=2))
print('AI_OPENING_CAPTURE_PASS',checks,'checks; score/admission; 3 bases; no game launched')
