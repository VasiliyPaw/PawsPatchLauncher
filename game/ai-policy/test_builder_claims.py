"""Independent allied workers through compiled recruitment/admission callbacks.
Native visibility, terrain and order services are mocked, not a network test.
"""
from pathlib import Path
exec(compile(Path(__file__).with_name('test_builder_fleet.py').read_text().split('\nfor image,cave in ')[0],'test_builder_fleet.py:fixtures','exec'))

class TeamFixture(FleetFixture):
 def __init__(self,image,cave,queued=False):
  super().__init__(image,cave)
  self.ally=0x510f8000;self.ak=0x510f9000;self.ac=0x510fa000;self.ae=0x510fb000;self.ag=0x510fc000
  for dst,src,n in ((self.ally,self.player,0x100),(self.ak,self.kingdom,0x400),(self.ac,self.city,0x1000),(self.ae,self.engine,0x100)):
   self.u.mem_write(dst,bytes(self.u.mem_read(src,n)))
  self.w(self.player+0x170,2);self.w(self.player+0x204,self.ally)
  self.w(self.kingdom+0x1f8,0x1234);self.w(self.ak+0x1f8,0x1234)
  self.w(self.ally+8,self.ak);self.w(self.ally+0xc,self.ae);self.w(self.ally+0x2c,0);self.w(self.ae+4,self.ally);self.w(self.ae+0xc,0)
  self.w(self.ac+0x14,500);self.w(self.ac+0xe8,self.ak);self.w(self.reg+0x20004+500*4,self.ac)
  self.w(self.ac+0xa0,self.ac+0x900);self.w(self.ac+0x904,self.ac)
  if queued:
   self.queued(1);self.w(self.city+0x918,0)
   self.w(self.ac+0x914,self.rs+0x1300);self.w(self.ac+0x918,1)
   self.aa=0
  else:
   sa,act,org,unit,state=self.army();self.aa=act;self.asa=sa
   self.w(act+4,self.builder);self.w(act+0xe8,self.ak);self.w(unit+0xe8,self.ak)
   self.w(sa+0xc,self.ally);self.w(sa+0x10,0)
   self.w(self.ally+0x2c,self.ag+0x200);self.w(self.ag+0x200,sa)
 def change(self):self.native_invalidation();self.advance()

for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 for queued in (False,True):
  for race in ('human','drauga','gauri','haroun','Undead','fallen'):
   f=TeamFixture(image,cave,queued);f.race(race)
   check(f.eligible()==1,('ally worker does not reserve sole site',queued,race))
   f.builder_alive();f.change();check(f.eligible()==0,'own worker covers own demand')
   f.site(1);f.change();check(f.eligible()==int(race!='haroun'),'own multi-site demand, one reusable Haroun')
 f=TeamFixture(image,cave);f.builder_alive();f.build_goal()
 f.w(f.ag,image+0x4da6b0);f.w(f.ag+4,f.ae);f.w(f.ag+8,2);f.w(f.ag+0x44,f.centerdef)
 f.f(f.ag+0x48,80);f.f(f.ag+0x4c,64);f.w(f.asa+0x10,f.ag)
 check(f.admission(f.target)==0,'ally accepted Construct no longer reserves a free site')
 f=TeamFixture(image,cave);f.w(f.stats+16,0)
 check(f.eligible()==0,'unknown site still creates no demand')
print('AI_BUILDER_CLAIMS_PASS',checks,'checks; independent allied settlement recruitment')
