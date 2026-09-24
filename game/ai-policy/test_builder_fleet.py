"""r30 compiled native callbacks: civilian fleet, thresholds, queue, heroes.
Native services are ABI stubs; no live-match/network acceptance is claimed.
"""
from pathlib import Path
exec(compile(Path(__file__).with_name('test_economy.py').read_text().split('\nfor image,cave in ')[0],'test_economy.py:fixtures','exec'))
count_namespace={'__file__':__file__}
exec(compile(Path(__file__).with_name('test_recruit_counts.py').read_text().split('\nfor image,cave in ')[0].replace('count=3000000','count=40000000'),'test_recruit_counts.py:fixtures','exec'),count_namespace)
native_count_call=count_namespace['CountsFixture'].call

class FleetFixture(EconomyFixture):
 def __init__(self,image,cave):
  super().__init__(image,cave)
  self.w(self.player+4,1);self.w(self.data+4,8)
  self.w(self.city+0x904,self.city)
  self.nation=self.rs+0x1000;self.w(self.kingdom+0x240,self.nation);self.w(self.nation+8,self.nation+0x100)
  self.race('human')
 def race(self,name):self.u.mem_write(self.nation+0x100,(name+'\0').encode('utf-16le'))
 def builder_alive(self):
  super().builder_alive()
  self.w(self.leader+4,self.builder);self.w(self.leader+0xa8,self.rs+0x1600)
  self.w(self.rs+0x1600,self.image+0x4df830);self.w(self.rs+0x1604,self.leader)
 def eligible(self):return self.invoke(4,self.recruit,[self.builder])
 def advance(self):self.f(self.world+0xe8,struct.unpack('<f',self.u.mem_read(self.world+0xe8,4))[0]+5)
 def site(self,i):
  marker=self.marker+i*0x400;idx=333+i;x=80+i*4;y=64
  self.w(marker,self.image+0x4e5c58);self.w(marker+4,self.markerdef);self.w(marker+0x14,idx)
  self.f(marker+0x20,x);self.f(marker+0x24,y);self.w(self.reg+0x20004+idx*4,marker)
  cell=self.cells+(16*32+int(x/4))*0x30;self.w(cell+8,marker+0x300);self.w(marker+0x300,marker)
  return marker
 def queued(self,count):
  factory=self.city+0x900;table=self.rs+0x1300;self.w(factory+0x14,table);self.w(factory+0x18,count)
  for i in range(count):
   job=table+0x100+i*0x30;self.w(table+4*i,job);self.w(job+4,0);self.w(job+8,self.builder);self.w(job+0xc,self.layout)
 def native_invalidation(self):
  self.invoke(6,self.city+0x900,[self.builder,self.layout,0,0,0])
 def build_goal(self):
  self.w(self.target,self.image+0x4da6b0);self.w(self.target+0x44,self.centerdef)
 def reclaim(self):
  self.call(self.hook(23),obj=self.target,args=[self.budget,self.engine+0x14,1],allowed=self.allowed())
  return self.r(self.sa+0x10)==self.target
 def pulse_setup(self):
  self.w(self.player+0x12c,1);self.w(self.engine+0x18,0);table=self.rs+0x1800;self.w(self.engine+8,table)
  for i in range(23):self.w(table+i*4,table+0x100+i*32)
  self.command=self.rs+0x2000;self.commandlog=self.command+0x100
  self.w(self.player+0x198,0x55667788)
  self.asm(self.image+0x2ef03c,f'cmp dword ptr [esp+4],0x40;jne bad;mov eax,{self.command};ret;bad:ud2')
  self.asm(self.image+0x22f4e9,'mov eax,[esp+4];cmp eax,10;jne bad;mov [ecx+8],eax;mov eax,ecx;ret 4;bad:ud2')
  self.asm(self.image+0x1f384d,'mov eax,[esp+4];mov eax,[eax];mov [ecx+16],eax;inc dword ptr [eax+4];mov eax,[esp+8];mov [ecx+24],eax;mov eax,[esp+12];mov [ecx+8],eax;ret 12')
  self.asm(self.image+0x1f2c03,f'cmp ecx,{self.player};jne bad;mov eax,[esp+4];mov edx,[eax+24];mov [{self.commandlog+4}],edx;cmp dword ptr [eax+8],0x55667788;jne bad;mov eax,[eax+16];cmp dword ptr [eax+8],10;jne bad;inc dword ptr [{self.commandlog}];ret 4;bad:ud2')
  self.asm(self.image+0x1f397b,'mov eax,[ecx+16];dec dword ptr [eax+4];ret')
 def pulse(self,t):
  self.f(self.world+0xe8,t)
  self.invoke(34,self.player,[],allowed=list(range(self.command,self.command+0x110,4)))
 def native_priority_setup(self):
  self.pl=self.player;self.k=self.kingdom;self.df=self.builder
  cfg=self.rs+0x2800;prop=cfg+0x300;self.prop=prop
  self.w(prop+8,prop+0x100);self.u.mem_write(prop+0x100,'role_settler\0'.encode('utf-16le'))
  self.w(self.df+0x1d4,prop+0x200);self.w(prop+0x200,prop);self.w(prop,prop+0x40);self.w(prop+0x58,image+0x1000)
  self.asm(image+0x1000,'mov eax,1;ret')
  self.w(cfg+0x104,cfg);self.w(cfg,1);self.f(cfg+4,350);self.f(cfg+8,5000)
  for target in (0x1eeb0b,0x1eeb2b):self.asm(image+target,'mov eax,7;stc;ret 4')
  self.asm(image+0x1ee8a3,'stc;ret 4')
  for start,end in ((0x5c7b9,0x5c8ef),(0x29949,0x2995d)):self.u.mem_write(image+start,game[start:end])
  for h in meta['wrappers']:
   if h['mode'] in (42,43):self.asm(image+h['site'],f'call {cave+h["offset"]}')
  self.w(self.stats+36,1)
  self.asm(image+0x64679,f'cmp ecx,{self.ego+0x374};jne prop;cmp dword ptr [{self.stats+36}],1;jne missing;mov eax,{cfg+0x100};ret 4;prop:cmp dword ptr [{self.stats+36}],2;jne missing;mov eax,{cfg+0x100};ret 4;missing:xor eax,eax;ret 4')
  native_count_call(self,48,[0,self.k,self.ego,0])
  native_count_call(self,46,[self.df],actor=self.actor)
 def native_priority(self,prop):
  self.w(self.stats+36,2 if prop else 1)
  return native_count_call(self,40,[self.df,self.pl,1],obj=self.ego)

class WaitingFixture(FleetFixture):
 def __init__(self,image,cave):
  super().__init__(image,cave);self.builder_alive();self.w(self.marker+8,1)
  sa,act,org,unit,state=self.army(300)
  self.w(self.lair+8,0);self.f(self.lair+0x20,112);self.f(self.lair+0x24,32)
  self.attack=self.explore;self.w(self.attack,image+0x4da480);self.w(self.attack+8,2);self.w(self.attack+0x4c,2)
  self.w(sa+0x10,self.attack);self.w(self.attack+0xc,self.attack+0x100);self.w(self.attack+0x100,sa)
  self.rally=self.node+0xe00;self.region=self.node+0xf00
  self.w(self.rally,image+0x4da510);self.w(self.rally+4,self.engine);self.w(self.rally+8,1);self.f(self.rally+0x38,300)
  self.w(self.rally+0x48,self.region);self.f(self.region+0x54,80);self.f(self.region+0x58,120)
  self.w(self.engine+0x18,4);self.w(self.node+0x80c,self.rally)
 def stage(self):
  self.call(self.hook(23),obj=self.rally,args=[self.budget,self.engine+0x14,3],allowed=self.allowed()+[self.rally+0x14])
  return self.r(self.sa+0x10)==self.rally

for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 # Capturable towns share marker_settlement but never turn into build sites.
 for race in ('human','drauga','gauri','haroun','Undead','fallen'):
  for attack in (0x4da480,0x4d84d4):
   f=WaitingFixture(image,cave);f.race(race);f.w(f.attack,image+attack)
   f.w(f.actor+8,1) # no existing worker: isolate the future-site demand
   check(f.eligible()==1,('destroyable camp needs worker',race,attack))
   f.w(f.ldef+0x290,1)
   check(f.eligible()==0,('cached capturable town no worker demand',race,attack))
   f.advance();check(f.eligible()==0,('fresh capturable town no worker demand',race,attack))
   f.w(f.actor+8,0)
   check(not f.stage(),('no builder staging outside capturable town',race,attack))
   f.w(f.marker+8,0);f.w(f.actor+8,1);f.advance()
   check(f.eligible()==1,('real vacancy still needs worker alongside capturable town',race,attack))
 f=FleetFixture(image,cave);f.builder_alive();f.site(1);f.native_priority_setup()
 for prop in (False,True):check(f.native_priority(prop)==350,'real native repeat penalty lifted while a site lacks worker')
 f.queued(1);f.native_invalidation()
 for prop in (False,True):check(f.native_priority(prop)==-4650,'real native repeat penalty restored when queue covers demand')
 for race in ('human','drauga','gauri','haroun','Undead','fallen'):
  f=FleetFixture(image,cave);f.race(race);f.site(1);f.site(2);f.builder_alive()
  check(f.eligible()==int(race!='haroun'),('reusable Haroun versus consumable workers',race))
  f.queued(1);f.native_invalidation();check(f.eligible()==int(race!='haroun'),'one queued still leaves a vacancy except Haroun')
  f.queued(2);f.native_invalidation();check(f.eligible()==0,'existing plus queued covers all sites')
  f.queued(0);f.native_invalidation();check(f.eligible()==int(race!='haroun'),'cancelled queue restores uncovered demand')
  f.w(f.marker+0x408,1);f.w(f.marker+0x808,1)
  check(f.eligible()==0,'occupied/disappeared sites reduce demand immediately')
  f.w(f.marker+8,1);check(f.eligible()==0,'no vacancy no extra workers')
 for case in ('militia','field','born-before-SA','captain-only','hidden','disabled','sovereign'):
  f=FleetFixture(image,cave);f.builder_alive()
  if case=='militia':f.w(f.actor+0x144,2)
  if case=='born-before-SA':f.w(f.player+0x2c,0)
  if case=='captain-only':
   f.w(f.actor+0xa8,0);f.w(f.leader+0xa8,0)
   f.w(f.org+0x28,f.org+0x180);f.w(f.org+0x2c,1);f.w(f.org+0x180,f.leader)
  if case=='hidden':f.w(f.stats+16,0);f.w(f.actor+8,1)
  if case=='disabled':f.w(f.data+4,0)
  if case=='sovereign':f.sovereign();f.site(1)
  check(f.eligible()==int(case in ('militia','disabled')),('field census/cap',case))
 # A living capable Haroun/Undead worker suffices, even below 1% HP.
 for race in ('human','Undead','haroun'):
  for hp in (0,0.01,1,19.99,20,69.99,70):
   for recovery in (False,True):
    f=FleetFixture(image,cave);f.race(race);f.builder_alive();f.build_goal()
    f.f(f.leader+0x910,hp);f.f(f.org+0x5c,0);f.w(f.layout+0x204,f.ldef)
    if recovery:
     f.w(f.source,image+0x4da5a0);f.w(image+0x4da5a0+0x68,image+0x2200)
     f.w(f.state,image+0x4f4df0);f.w(f.actor+0x100,0x2000);f.w(f.stats+120,0)
    check(f.reclaim()==((hp>0 if race!='human' else hp>=70) and (not recovery or race!='human')),('partial builder recovery',race,hp,recovery))
 # Recover must not reclaim a fit Undead worker after the construction handoff.
 for case in ('undead20','undead19','human70','danger','retreat','invalid-site','combat','disabled'):
  f=FleetFixture(image,cave);f.race('human' if case=='human70' else 'Undead');f.builder_alive();f.build_goal()
  f.w(f.sa+0x10,f.target);f.w(f.target+8,2);f.w(f.source,image+0x4da5a0)
  f.w(f.state,image+0x4f4ed0);f.f(f.org+0x5c,0);f.f(f.leader+0x910,70 if case=='human70' else 19 if case=='undead19' else 20)
  if case=='danger':f.enemy()
  if case=='retreat':f.w(f.actor+0x100,0x4000)
  if case=='invalid-site':f.w(f.marker+8,1)
  if case=='combat':f.w(f.state,image+0x4f4e20)
  if case=='disabled':f.w(f.data+4,0)
  check(f.admission(f.source)==int(case in ('undead20','undead19')),('no construction/recovery oscillation',case))
 for case in ('combat','retreat','danger','nan'):
  f=FleetFixture(image,cave);f.race('Undead');f.builder_alive();f.build_goal();f.f(f.leader+0x910,20)
  if case=='combat':f.w(f.state,image+0x4f4e20)
  if case=='retreat':f.w(f.actor+0x100,0x4000)
  if case=='danger':f.enemy()
  if case=='nan':f.f(f.leader+0x910,float('nan'))
  check(not f.reclaim(),('Undead retains danger/combat safety',case))
 for case in ('attack','attack-structure','defense','no-task','wounded','civilian','human-player','disabled','native-refusal'):
  f=FleetFixture(image,cave);f.builder_alive();f.w(f.target,image+(0x4d84d4 if case=='attack-structure' else 0x4da480))
  if case=='defense':f.w(f.target,image+0x4da510)
  if case=='no-task':f.w(f.sa+0x10,0)
  if case=='wounded':f.f(f.leader+0x910,1)
  if case=='civilian':f.w(f.target,image+0x4da5a0)
  if case=='human-player':f.w(f.player+4,0)
  if case=='disabled':f.w(f.data+4,0)
  native=2 if case=='native-refusal' else 0
  check(f.admission(f.target,native)==(2 if native else 0 if case in ('civilian','human-player','disabled') else 1),('civilian offensive ban',case))
 for case in ('builder','military','disabled','human'):
  f=FleetFixture(image,cave)
  if case!='military':f.builder_alive()
  if case=='disabled':f.w(f.data+4,0)
  if case=='human':f.w(f.player+4,0)
  check(f.invoke(49,f.player,[f.ldef,f.sa],fp=123)==(0 if case=='builder' else 123),('hero score',case))
  check(f.invoke(50,f.org,[0])==(0 if case=='builder' else 1),('hero final admission',case))
 # Another builder owns this coordinate, even through another Construct goal.
 f=FleetFixture(image,cave);f.builder_alive();f.build_goal();sa,a,org,unit,state=f.army()
 f.w(a+4,f.builder);f.w(a+0xa8,a+0x280);f.w(a+0x280,image+0x4df830);f.w(a+0x284,a)
 other=f.explore;f.w(other,image+0x4da6b0);f.w(other+8,1);f.w(other+0x44,f.centerdef)
 f.f(other+0x48,80);f.f(other+0x4c,64);f.w(sa+0x10,other)
 check(f.admission(f.target)==1 and not f.reclaim(),'separate goals cannot dispatch builders to same site')
 f.f(other+0x48,84);check(f.admission(f.target)==0 and f.reclaim(),'different sites get distinct builders')
 for case in ('safe','inside-guard','approach-crosses-guard','no-clearing-force','free-site','hurt','undead20','native-refusal','disabled','failed-add','kingdom-already-exists'):
  f=WaitingFixture(image,cave)
  if case=='inside-guard':f.f(f.region+0x54,110);f.f(f.region+0x58,45)
  if case=='approach-crosses-guard':
   f.f(f.lair+0x20,80);f.f(f.lair+0x24,64);f.f(f.actor+0x20,16);f.f(f.actor+0x24,0)
   f.f(f.region+0x54,124);f.f(f.region+0x58,124)
  if case=='no-clearing-force':f.w(f.attack+0xc,0)
  if case=='free-site':f.w(f.marker+8,0)
  if case in ('hurt','undead20'):f.f(f.leader+0x910,20);f.f(f.org+0x5c,0)
  if case=='undead20':f.race('Undead')
  if case=='native-refusal':f.w(f.stats+120,0)
  if case=='disabled':f.w(f.data+4,0)
  if case=='kingdom-already-exists':f.sovereign();f.w(f.city+4,f.centerdef)
  if case=='failed-add':f.asm(image+0x2500,f'cmp ecx,{f.rally};je refused;mov eax,[esp+4];mov [eax+0x10],ecx;inc dword ptr [ecx+0x14];refused:ret 16')
  check(f.stage()==(case in ('safe','undead20')),('safe builder staging',case))
  check(f.r(f.sa+4)==1,'staging balances native references')
  if case=='safe':
   f.w(f.rally+8,2)
   check(f.admission(f.rally)==0,'current safe staging remains admitted')
   f.w(f.source,image+0x4d79e8)
   check(f.admission(f.source)==1,'safe waiting worker retained')
   f.w(f.attack+0xc,0);check(f.admission(f.source)==0,'cancelled clearing frees waiting worker')
   check(f.admission(f.rally)==1,'cancelled staging cannot become military defense')
  if case=='failed-add':check(f.r(f.sa+0x10)==f.source,'failed staging restores native source goal')
 for case in ('surplus','still-needed','busy-building','combat','danger','native-refusal','site-temporarily-gone','disabled'):
  f=FleetFixture(image,cave);f.builder_alive();f.pulse_setup();f.w(f.marker+8,1)
  if case=='still-needed':f.w(f.marker+8,0)
  if case=='busy-building':f.build_goal();f.w(f.sa+0x10,f.target)
  if case=='combat':f.w(f.state,image+0x4f4e20)
  if case=='danger':f.enemy()
  if case=='native-refusal':f.w(f.rs+0xc10,0)
  if case=='disabled':f.w(f.data+4,0)
  f.pulse(30);f.pulse(34);f.pulse(58)
  check(f.r(f.commandlog)==0,'surplus grace interval preserves companies')
  if case=='site-temporarily-gone':f.w(f.marker+8,0)
  f.pulse(62)
  check(f.r(f.commandlog)==int(case=='surplus'),('native surplus disband conditions',case))
  if case=='surplus':
   check(f.r(f.commandlog+4)==1 and f.r(f.command+4)==0,'native disband ID and balanced command refs')
   f.pulse(66);f.pulse(70);check(f.r(f.commandlog)==1,'pending native command is not duplicated')

print('AI_BUILDER_FLEET_PASS',checks,'checks; three ASLR bases; native services mocked')
