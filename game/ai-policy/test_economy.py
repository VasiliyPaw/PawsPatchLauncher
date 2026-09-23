"""r22 compiled hooks, strict mutation/ABI checks with controlled native services.
No game launch; does not replace live multiplayer/save acceptance."""
from pathlib import Path
exec(compile(Path(__file__).with_name('test_builder_clearing.py').read_text().split('\nfor image,cave in ')[0],'test_builder_clearing.py:fixtures','exec'))

class EconomyFixture(BuilderFixture):
 def __init__(self,image,cave):
  super().__init__(image,cave)
  self.military=0x510f0000;self.builder=0x510f1000;self.recruit=0x510f2000;self.rs=0x510f4000;self.prod=self.rs+0x900;self.up=self.prod+0x100;self.stock=self.up+0x100
  self.w(self.actor+4,self.military);self.w(self.leader+4,self.military);self.w(self.actor+0xa8,0)
  self.w(self.military+0x174,128);self.w(self.builder+0x174,128);self.w(self.builder+0x2f0,self.layout);self.w(self.military+0x2f0,self.layout)
  self.w(self.builder+0x504,self.buildnode);self.w(self.builder+8,self.builder+0x600);self.u.mem_write(self.builder+0x600,'company_pioneer\0'.encode('utf-16le'))
  self.w(self.source,image+0x4da510);self.w(self.target,image+0x4da738);self.w(self.target+8,1);self.w(self.target+0x40,self.military)
  self.w(self.recruit,image+0x4d9274);self.w(self.recruit+4,self.engine);self.w(self.recruit+8,1);self.w(self.recruit+0x44,self.builder);self.w(self.recruit+0x48,self.layout)
  self.w(self.recruit+0x4c,self.recruit+0x100);self.w(self.recruit+0x108,4);self.w(self.recruit+0x10c,self.player)
  self.w(self.city+0xa0,self.city+0x900);self.asm(image+0x1df308,f'mov eax,[{self.city+0xa0}];ret');self.asm(image+0x21c6ec,'mov eax,1;ret')
  self.w(self.recruit+0x1c,self.recruit+0x300);self.w(self.recruit+0x20,9);self.f(self.recruit+0x300,100)
  self.w(image+0x5efa8c,self.rs);self.w(self.rs+0x24,self.rs+0x80);self.w(self.rs+0x28,9)
  names=['gold','stone','wood','iron','mana','unit_limit_provided','unit_limit_consumed','kingdom_points_provided','kingdom_points_consumed']
  for i,name in enumerate(names):
   rd=self.rs+0x100+i*0x80;self.w(self.rs+0x80+4*i,rd);self.w(rd+8,rd+0x38);self.w(rd+0xc,i);self.w(rd+0x18,2 if i in (6,8) else 0 if i==0 else 1)
   self.u.mem_write(rd+0x38,(name+'\0').encode('utf-16le'))
   if i in (6,8):self.w(rd+0x30,rd-0x80)
  for off,ptr in ((0x1a8,self.prod),(0x1c0,self.up),(0x1cc,self.stock)):self.w(self.kingdom+off,ptr)
  self.w(self.kingdom+0x1d0,9);self.f(self.prod+5*4,2);self.f(self.up+6*4,2);self.f(self.prod+7*4,20);self.f(self.stock,100)
  self.w(self.budget,self.stock);self.w(self.budget+4,9);self.w(self.budget+8,9)
  self.prvec=self.budget+0x100;self.upvec=self.prvec+0x40;self.w(self.prvec+4,self.prod);self.w(self.upvec+4,self.up)
  self.f(self.rs+0xc00,1);self.f(self.rs+0xc04,0)
  self.asm(image+0x2400,'mov eax,[esp+16];'+''.join(f'mov dword ptr [eax+{4*i}],0;' for i in range(9))+f'mov edx,[{self.rs+0xc00}];mov [eax+24],edx;mov edx,[esp+8];cmp edx,{self.builder};jne done;mov edx,[{self.rs+0xc04}];mov [eax+32],edx;done:mov eax,9;ret')
  self.w(image+0x4e5c58+0x34,image+0x2800);self.w(self.rs+0xc10,1);self.asm(image+0x2800,f'mov eax,[{self.rs+0xc10}];ret 4')
  self.asm(image+0x227526,'mov eax,[ecx+0x7c];fld dword ptr [eax+0x68];ret 4')
  self.asm(image+0x6a62a,'mov eax,[ecx];test eax,eax;je newref;dec dword ptr [eax+4];newref:mov eax,[esp+4];mov [ecx],eax;test eax,eax;je done;inc dword ptr [eax+4];done:ret 4')
  self.w(image+0x4d9274+0x64,image+0x2300)
  self.asm(image+0x2277b6,f'mov eax,{self.rs+0xd00};ret')
  self.w(self.centerdef+0x328,9);self.f(self.rs+0xd00,200)
  self.asm(image+0x29eaa,f'mov eax,[esp+4];cmp dword ptr [eax+4],9;jne bad;mov eax,[eax];mov edx,[{self.rs+0xd00}];mov [eax],edx;ret 8;bad:ud2')
 def military_army(self,cv=50):
  army=self.army(cv);self.w(army[1]+4,self.military);self.w(army[3]+4,self.military);return army
 def sovereign(self):
  self.w(self.centerdef+8,self.centerdef+0x800);self.u.mem_write(self.centerdef+0x800,'human_center_sovereign\0'.encode('utf-16le'))
 def builder_alive(self):
  self.w(self.actor+4,self.builder);self.w(self.actor+0xa8,self.org+0x100)
 def invoke(self,mode,obj,args,native=1,fp=10,allowed=()):
  h=self.hook(mode);self.f(self.stats+20,fp)
  self.asm(self.image+h['target'],f'inc dword ptr [{self.stats}];'+(f'fld dword ptr [{self.stats+20}];' if h['fp'] else '')+f'mov eax,{native};stc;ret {4*h["argc"]}')
  driver='fninit;stc;'+''.join(f'push {v};' for v in reversed(args))+f'mov ecx,{obj};call {self.cave+h["offset"]};'+(f'fstp dword ptr [{self.stats+24}];' if h['fp'] else '')+'nop'
  blob=bytes(ks.asm(driver,0x62000000)[0]);self.u.mem_write(0x62000000,blob);self.u.ctl_remove_cache(0x62000000,0x62001000)
  regs={UC_X86_REG_EBP:self.frame,UC_X86_REG_EBX:111,UC_X86_REG_ESI:222,UC_X86_REG_EDI:333}
  for k,v in regs.items():self.u.reg_write(k,v)
  for i in range(8):self.u.reg_write(UC_X86_REG_XMM0+i,0x987654321+i)
  self.u.reg_write(UC_X86_REG_ESP,self.sp);writes=[]
  wh=self.u.hook_add(UC_HOOK_MEM_WRITE,lambda u,ac,at,size,val,data:writes.append(at))
  self.u.emu_start(0x62000000,0x62000000+len(blob),count=40000000);self.u.hook_del(wh)
  check(self.u.reg_read(UC_X86_REG_EIP)==0x62000000+len(blob),('instruction budget',mode))
  check(self.u.reg_read(UC_X86_REG_ESP)==self.sp,('stack',mode))
  check(all(self.u.reg_read(k)==v for k,v in regs.items()),('nonvolatile registers',mode))
  check(all(self.u.reg_read(UC_X86_REG_XMM0+i)==0x987654321+i for i in range(8)),('XMM',mode))
  bad=[hex(at) for at in writes if not(self.data<=at<self.cave+meta['allocation'] or self.stats<=at<self.stats+128 or 0x61000000<=at<0x61010000 or at in allowed)]
  check(not bad,('unexpected game writes',mode,bad[:10]))
  return struct.unpack('<f',self.u.mem_read(self.stats+24,4))[0] if h['fp'] else self.u.reg_read(UC_X86_REG_EAX)&255
 def replace(self):
  return self.invoke(31,self.player,[self.recruit],allowed=self.allowed()+[self.recruit+0x14,self.recruit+0x50])
 def validate(self):return self.invoke(32,self.recruit+0xc,[self.recruit+0x50])

for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 for case in ('normal','funds','full','no-site','hidden','nan-site','no-capacity-need','other-limit','builder-alive','combat','hero','attacking','last-army','native-refusal','disabled','failed-add','pending-city','no-gold-borrow','no-factory','city-quota'):
  f=EconomyFixture(image,cave);army=f.military_army(40)
  if case=='funds':f.f(f.stock,99)
  if case=='full':f.f(f.stock,200)
  if case=='no-site':f.w(f.marker+8,1)
  if case=='hidden':f.w(f.stats+16,0)
  if case=='nan-site':f.f(f.stats+116,float('nan'))
  if case=='no-capacity-need':f.f(f.prod+20,3)
  if case=='other-limit':f.f(f.rs+0xc04,11);f.f(f.prod+28,10)
  if case=='builder-alive':f.builder_alive()
  if case in ('combat','attacking'):
   f.w(f.state,image+0x4f4e20);f.w(army[4],image+0x4f4e20)
   if case=='attacking':f.w(f.source,image+0x4da480)
  if case=='hero':
   for sa,act,org,unit,state in f.armies:f.w(org+0x34,f.rs+0xe00);f.w(org+0x38,2);f.w(f.rs+0xe00,0x123)
  if case=='last-army':f.w(0x510cf000+4,0)
  if case=='native-refusal':f.w(f.rs+0xc10,0)
  if case=='disabled':f.w(f.data+4,7)
  if case=='failed-add':f.asm(image+0x2300,'ret 16')
  if case=='pending-city':f.w(f.city+0x414,0)
  if case=='no-gold-borrow':f.f(f.stock,0)
  if case=='no-factory':f.w(f.city+0xa0,0)
  if case=='city-quota':
   f.w(f.ego+0x398,1);f.w(f.engine+0x28,f.rs+0xe00);f.w(f.engine+0x2c,1);f.w(f.rs+0xe00,f.rs+0xe10);f.w(f.rs+0xe10,f.city);f.w(f.rs+0xe14,1)
  before=f.r(f.stats);got=f.replace();expected=case in ('normal','full','hero','disabled')
  check(bool(got)==expected,('replacement conditions',case,got))
  staged=f.r(f.recruit+0x50)
  check(staged==(army[0] if case in ('normal','full','hero') else 0),('only weakest eligible staged',case,hex(staged)))
  check(f.r(f.stats)-before==int(case=='disabled'),('native bypass count',case))
  check(all(f.r(sa+4)==1+int(sa==staged) for sa,*_ in f.armies),('references',case))
  if case in ('normal','full','hero'):
   check(f.validate()==1,'fresh replacement accepted')
   f.f(f.stock,0);check(f.validate()==0,'funds disappeared before native execution')
   f.f(f.stock,100);f.w(army[4],image+0x4f4e20);check(f.validate()==0,'combat began before native execution')
   f.w(army[4],image+0x4f4f28);f.w(f.marker+8,1);check(f.validate()==0,'site occupied before native execution')
 # A hero-bearing travelling scout can supply the needed slot. Source goal
 # membership is changed with native methods, and restored on failed Add.
 for case in ('guard','move','explore','hero-move','hero-explore','kill','rout','recovering-move','recovering-explore','member-kill','failed-add','moving-defender'):
  f=EconomyFixture(image,cave);army=f.military_army(40);sa,a,org,unit,state=army
  f.w(f.source,image+0x4d79e8)
  tactical=0x4f4f28 if case=='guard' else 0x4f5038 if 'explore' in case else 0x4f4df0
  for other_sa,other_a,other_org,other_unit,other_state in f.armies:
   f.w(other_state,image+tactical)
   if case.startswith('hero'):
    f.w(other_org+0x34,f.rs+0xe00);f.w(other_org+0x38,2);f.w(f.rs+0xe00,0x123)
   if case in ('kill','rout'):f.w(other_state,image+(0x4f4e20 if case=='kill' else 0x4f500c))
   if case.startswith('recovering'):f.w(other_a+0x100,0x2000 if case=='recovering-move' else 0x4000)
   if case=='member-kill':
    f.w(other_unit+0x70,other_unit+0xa00);f.w(other_unit+0xa14,other_unit+0xa40);f.w(other_unit+0xa40,other_unit+0xa80);f.w(other_unit+0xa80,image+0x4f4e20)
  if case=='moving-defender':f.w(f.source,image+0x4da510)
  if case=='failed-add':f.asm(image+0x2300,f'cmp ecx,{f.recruit};je done;mov eax,[esp+4];mov [eax+0x10],ecx;inc dword ptr [ecx+0x14];done:ret 16')
  expected=case in ('guard','move','explore','hero-move','hero-explore')
  check(bool(f.replace())==expected,('scout replacement',case))
  check(f.r(f.recruit+0x50)==(sa if expected else 0),('scout weakest selected',case))
  check(all(f.r(x+4)==1+int(expected and x==sa) for x,*_ in f.armies),('scout balanced refs',case))
  if expected:
   check(f.validate()==1,'reserved scout still travelling passes native revalidation')
   for change in ('kill','rout','recovery','member-kill'):
    f.w(state,image+tactical);f.w(a+0x100,0);f.w(unit+0x70,0)
    if change in ('kill','rout'):f.w(state,image+(0x4f4e20 if change=='kill' else 0x4f500c))
    if change=='recovery':f.w(a+0x100,0x2000)
    if change=='member-kill':
     f.w(unit+0x70,unit+0xa00);f.w(unit+0xa14,unit+0xa40);f.w(unit+0xa40,unit+0xa80);f.w(unit+0xa80,image+0x4f4e20)
    check(f.validate()==0,('scout revalidation rejects new danger',change))
  else:
   check(all(f.r(x+0x10)==f.source for x,*_ in f.armies),('scout tasks preserved/restored',case))
 # Reserve only while a usable site and an absent builder were observed.
 for case in ('reserve','no-site','builder-present','expired','room','disabled','own-builder','last-slot','late-budget','other-capacity'):
  f=EconomyFixture(image,cave);f.military_army();f.f(f.prod+20,3)
  check(f.invoke(4,f.recruit,[f.builder])==1,'needed builder remains eligible')
  if case=='no-site':f.w(f.marker+8,1)
  if case=='builder-present':
   f.builder_alive()
   # Simulate the native registration notification after this new company.
   f.invoke(46,f.player,[f.builder])
  if case=='expired':f.f(f.world+0xe8,80)
  if case=='room':f.f(f.prod+20,4)
  if case=='disabled':f.w(f.data+4,7)
  if case=='other-capacity':f.f(f.rs+0xc04,11);f.f(f.prod+28,10)
  f.w(f.recruit+0x44,f.military if case!='own-builder' else f.builder)
  if case=='late-budget':
   before=f.r(f.stats);got=f.invoke(5,f.recruit,[f.prvec,f.upvec],native=0)
   check(got==1 and f.r(f.stats)==before,'capacity rejection occurs before native budget mutation')
  else:
   got=f.invoke(4,f.recruit,[f.military if case!='own-builder' else f.builder])
   check(bool(got)==(case not in ('reserve','last-slot')),('slot reserve',case,got))
 # First-kingdom reserve uses current native cost including discounts.
 for case in ('reserve','surplus','builder-hp70','builder-hp69','builder-morale-zero','builder-partial','combat','no-site','occupied','already-kingdom','not-sovereign','construction-itself','builder-recruit','started-upgrade','native-reject','disabled','discount'):
  f=EconomyFixture(image,cave);f.builder_alive();f.sovereign();f.f(f.stock,250)
  g=f.target;f.w(g+0x1c,f.recruit+0x400);f.w(g+0x20,9);f.f(f.recruit+0x400,100)
  if case=='surplus':f.f(f.stock,300)
  if case=='builder-hp70':f.f(f.leader+0x910,70)
  if case=='builder-hp69':f.f(f.leader+0x910,69)
  if case in ('builder-morale-zero','builder-partial'):f.f(f.leader+0x910,70);f.f(f.org+0x5c,0)
  if case=='builder-partial':f.w(f.layout+0x204,f.ldef)
  if case=='combat':f.w(f.state,image+0x4f4e20)
  if case=='no-site':f.w(f.marker+8,1)
  if case=='occupied':f.w(f.marker+0x88,f.den)
  if case=='already-kingdom':f.w(f.city+4,f.centerdef)
  if case=='not-sovereign':f.w(f.centerdef+8,0)
  if case=='construction-itself':f.w(g,image+0x4da6b0);f.w(g+0x44,f.centerdef)
  if case=='builder-recruit':g=f.recruit
  if case=='started-upgrade':f.w(g+8,2)
  if case=='disabled':f.w(f.data+4,7)
  if case=='discount':f.f(f.rs+0xd00,20)
  got=f.invoke(30,g,[f.budget,0],native=int(case!='native-reject'))
  check(bool(got)==(case not in ('reserve','builder-hp70','builder-morale-zero','builder-partial','native-reject')),('kingdom gold reserve',case,got))

# Run the real Recruit::Execute disband branch, including the new revalidation
# call site. Constructors and simulation transport are explicit ABI stubs.
for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 for cancel,scout in ((False,False),(True,False),(False,True),(True,True)):
  # Both cases below pass through the original game's Disband command path.
  # Hero lifecycle is owned by the engine, not simulated by this fixture.
  f=EconomyFixture(image,cave);army=f.military_army(40)
  if scout:
   f.w(f.source,image+0x4d79e8);f.w(army[4],image+0x4f4df0)
   f.w(army[2]+0x34,f.rs+0xe00);f.w(army[2]+0x38,2);f.w(f.rs+0xe00,0x123)
  check(f.replace()==1,'staging for native execution')
  start,end=0x1dc3c2,0x1dc48e;code=bytearray(game[start:end]);h=f.hook(32)
  struct.pack_into('<i',code,h['site']+1-start,cave+h['offset']-image-h['site']-5);f.u.mem_write(image+start,bytes(code))
  f.asm(image+0x1dc53d,f'jmp {image+end}')
  f.asm(image+0x2f397,'mov eax,1;ret 4')
  f.asm(image+0x1e2321,f'mov eax,[ecx+8];and eax,65535;mov eax,[eax*4+{f.reg+0x20004}];ret 4')
  f.asm(image+0x1e3cb8,f'mov eax,{f.player};ret')
  command=f.recruit+0x800;f.asm(image+0x2ef03c,f'mov eax,{command};ret')
  f.asm(image+0x22f4e9,'mov eax,[esp+4];mov [ecx],eax;mov eax,ecx;ret 4')
  f.asm(image+0x1f384d,'mov eax,[esp+4];mov eax,[eax];mov [ecx],eax;mov eax,[esp+8];mov [ecx+4],eax;mov eax,[esp+12];mov [ecx+8],eax;mov eax,ecx;ret 12')
  f.asm(image+0x1f2c03,f'mov eax,[esp+4];mov edx,[eax];mov edx,[edx];mov [{f.rs+0xf00}],edx;mov edx,[eax+4];mov [{f.rs+0xf04}],edx;inc dword ptr [{f.rs+0xf08}];ret 4')
  f.asm(image+0x1f397b,'ret')
  if cancel:f.f(f.stock,0)
  for reg,val in ((UC_X86_REG_EBX,f.recruit),(UC_X86_REG_ESI,f.recruit+0x50),(UC_X86_REG_EBP,f.frame),(UC_X86_REG_ESP,f.sp)):f.u.reg_write(reg,val)
  f.u.emu_start(image+start,image+end,count=40000000)
  check(f.u.reg_read(UC_X86_REG_EIP)==image+end and f.u.reg_read(UC_X86_REG_ESP)==f.sp,'original native disband branch ABI')
  check(f.r(f.rs+0xf08)==int(not cancel),'native command transport only when revalidation succeeds')
  if not cancel:check(f.r(f.rs+0xf00)==10 and f.r(f.rs+0xf04)==f.r(army[1]+0x14),'original Disband command targets only selected weak company')

print('AI_ECONOMY_PASS',checks,'checks; 3 ASLR bases; native Disband branch, revalidation, conditional slot and first-kingdom gold; engine transport/services stubbed')
