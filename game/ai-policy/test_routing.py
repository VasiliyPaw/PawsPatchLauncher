"""Run the compiled routing wrappers in x86 emulation. Native diplomacy/fog,
lock and terrain callees are explicit stubs; native combat-value code is real.
Does not claim a played match or multiplayer verification.
"""
import argparse,json,struct,sys,heapq,math
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--native',type=Path,required=True);a=p.parse_args()
sys.path[:0]=[str(a.legacy/'lobby_colors_1372/deps_r15'),str(a.legacy/'pydeps_readable')]
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_MEM_WRITE
from unicorn.x86_const import *
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
meta=json.loads((a.native/'ai-policy.json').read_text());raw=(a.native/'ai-policy.bin').read_bytes();game=(a.legacy/'k2_runtime_1372_20260904.bin').read_bytes();ks=Ks(KS_ARCH_X86,KS_MODE_32)
checks=0
def check(ok,why):
 global checks
 checks+=1
 assert ok,why
def bits(f):return struct.unpack('<I',struct.pack('<f',f))[0]
class Fixture:
 def __init__(self,image=0x460000,cave=0x10000000):
  self.image=image;self.cave=cave;u=self.u=Uc(UC_ARCH_X86,UC_MODE_32)
  for at,size in [(0,4096),(image,0x690000),(cave,(meta['allocation']+4095)&~4095),(0x51000000,0x100000),(0x61000000,0x10000),(0x62000000,4096)]:u.mem_map(at,size)
  code=bytearray(raw)
  for off,im,cv in meta['fixups']:struct.pack_into('<I',code,off,(struct.unpack_from('<I',code,off)[0]+im*(image-meta['image'])+cv*(cave-meta['cave']))&0xffffffff)
  u.mem_write(cave,bytes(code));self.data=cave+meta['dataOffset'];self.route=self.data+meta['routingOffset'];self.w(self.data+4,15);self.w(0x24,77)
  self.world=0x51000000;self.actor=0x51001000;self.org=0x51002000;self.kingdom=0x51003000;self.player=0x51004000;self.query=0x51005000;self.grid=0x51006000
  self.lair=0x51008000;self.den=0x51009000;self.ldef=0x5100a000;self.stats=0x5100b000;self.reg=0x51020000;self.cells=0x51090000;self.sp=0x6100e000;self.frame=0x6100f000
  self.w(image+0x5f3fb8,self.world);self.w(image+0x5f9218,2);self.w(image+0x5ef72c,self.reg)
  self.f(self.world+0xe8,600);self.w(self.world+0x30,self.grid)
  self.w(image+0x5f3fc8,self.player+0x100);self.w(self.player+0x16c,self.player+0x200);self.w(self.player+0x170,1);self.w(self.player+0x200,self.player);self.w(self.player+8,self.kingdom)
  self.session=self.player+0x500;self.slot=self.player+0x700;self.slotnode=self.player+0x900
  self.w(image+0x5f3fe4,self.session);self.w(self.session+0xc8,self.slotnode);self.w(self.slotnode,self.slot)
  self.w(self.slot,image+0x4bd914);self.w(self.slot+0xc,1);self.w(self.slot+0x28,self.kingdom)
  for actor,idx in [(self.actor,1),(self.lair,2)]:self.w(actor,image+0x4e5c58);self.w(actor+0x14,idx);self.w(self.reg+0x20004+idx*4,actor)
  self.w(self.actor+0xe8,self.kingdom);self.w(self.actor+0x7c,self.org);self.f(self.org+0x68,10);self.w(self.query+0x1c,self.actor)
  self.leader=self.actor+0x300;self.element=self.actor+0x600
  self.w(self.org+4,self.actor);self.w(self.org+0x40,self.leader)
  self.w(self.leader,image+0x4e5c58);self.w(self.leader+0x14,3);self.w(self.reg+0x20004+3*4,self.leader);self.w(self.leader+0x80,self.element)
  self.w(self.element+4,self.leader);self.w(self.element+0x10,self.actor);self.w(self.leader+0xe8,self.kingdom)
  self.w(self.query+0x1c,self.leader)
  self.w(self.actor+4,self.ldef+0x600);self.w(self.actor+0xa8,self.org+0x100);self.w(self.org+0x100,image+0x4df830);self.w(self.org+0x104,self.actor)
  self.buildnode=0x5100c000;self.centerdef=0x5100e000;self.markerdef=0x5100f000
  self.w(self.ldef+0x600+0x504,self.buildnode);self.w(self.buildnode,self.centerdef)
  self.w(self.centerdef+0x430,self.centerdef+0x600);self.w(self.centerdef+0x4e0,self.markerdef)
  self.w(self.markerdef+8,self.markerdef+0x100);self.u.mem_write(self.markerdef+0x100,'marker_settlement\0'.encode('utf-16le'))
  self.w(self.leader+4,self.ldef+0x600)
  self.w(image+0x4e5c58+0x144,image+0x500);self.w(self.lair+0x88,self.den);self.w(self.den,image+0x4e0434);self.w(self.den+4,self.lair);self.f(self.den+0x10,100)
  self.w(self.lair+0xc4,self.den+0x100);self.w(self.den+0x100,image+0x4e17ac);self.w(self.den+0x104,self.lair)
  self.w(self.lair+0x60,self.den+0x200);self.f(self.den+0x210,1000);self.w(self.lair+4,self.ldef)
  self.w(self.den+0x204,self.lair);self.w(self.lair+0x94,self.den+0x300);self.w(self.den+0x304,self.lair)
  self.f(self.lair+0x20,64);self.f(self.lair+0x24,64);self.f(self.ldef+0x364,16);self.f(self.ldef+0x368,18)
  self.w(self.grid+4,2);self.f(self.grid+8,4);self.f(self.grid+0xc,128);self.f(self.grid+0x10,128);self.w(self.grid+0x1c,32);self.w(self.grid+0x28,self.cells)
  self.w(self.stats+12,3);self.w(self.stats+16,1);self.f(self.stats+20,5)
  self.asm(image+0x500,f'mov eax,[{self.stats+12}]; ret 4')
  self.asm(image+0x24a845,f'mov eax,[{self.stats+16}]; ret 4')
  u.mem_write(image+0x2274c1,game[0x2274c1:0x227526]) # exact native combat aggregation, relocates without absolute operands in exercised branches
  self.lock=True
 def w(self,at,v):self.u.mem_write(at,struct.pack('<I',v&0xffffffff))
 def f(self,at,v):self.w(at,bits(v))
 def r(self,at):return struct.unpack('<I',self.u.mem_read(at,4))[0]
 def asm(self,at,code):self.u.mem_write(at,bytes(ks.asm(code,at)[0]));self.u.ctl_remove_cache(at,at+256)
 def call(self,h,args=(),obj=None,native=0,fp=5,begin=None,allowed=()):
  obj=self.actor if obj is None else obj;u=self.u;self.f(self.stats+20,fp)
  mode=h['mode'];native_code=f'inc dword ptr [{self.stats}];'
  if mode==11:native_code+=f'mov dword ptr [{self.stats+4}],1;'
  if mode==12:native_code+=f'mov eax,[{self.route+36}]; mov [{self.stats+8}],eax; mov dword ptr [{self.stats+4}],0;'
  native_code+=f'fld dword ptr [{self.stats+20}];' if h['fp'] else ''
  native_code+=f'mov eax,{native}; mov ecx,0x11223344; mov edx,0x55667788; stc; ret {0 if h["cdecl"] else h["argc"]*4}'
  self.asm(self.image+h['target'],native_code)
  self.asm(0x62000000,('fstp dword ptr ['+str(self.stats+24)+'];' if h['fp'] else '')+'nop')
  end=0x62000000+len(bytes(ks.asm(('fstp dword ptr ['+str(self.stats+24)+'];' if h['fp'] else '')+'nop',0x62000000)[0]))
  self.w(self.sp,0x62000000)
  for i,v in enumerate(args):self.w(self.sp+4+i*4,v)
  if begin:
   for i,v in enumerate(begin):self.w(self.frame+8+i*4,v)
  regs={UC_X86_REG_EBP:self.frame,UC_X86_REG_ESI:123,UC_X86_REG_EDI:234,UC_X86_REG_EBX:345}
  for k,v in regs.items():u.reg_write(k,v)
  for i in range(8):u.reg_write(UC_X86_REG_XMM0+i,0xabcdefabcd+i)
  u.reg_write(UC_X86_REG_ESP,self.sp);u.reg_write(UC_X86_REG_ECX,obj)
  writes=[];hook=u.hook_add(UC_HOOK_MEM_WRITE,lambda u,ac,at,size,val,data:writes.append(at))
  calls=self.r(self.stats)
  u.emu_start(self.cave+h['offset'],end,count=getattr(self,'instruction_limit',12000000));u.hook_del(hook)
  check(u.reg_read(UC_X86_REG_EIP)==end,'wrapper returned within instruction budget')
  check(u.reg_read(UC_X86_REG_ESP)==self.sp+4+(0 if h['cdecl'] else h['argc']*4),'stack balanced')
  check(all(u.reg_read(k)==v for k,v in regs.items()),'callee-save registers')
  check(all(u.reg_read(UC_X86_REG_XMM0+i)==0xabcdefabcd+i for i in range(8)),'XMM preservation')
  check(u.reg_read(UC_X86_REG_EFLAGS)&1,'callee flags')
  check(self.r(self.stats)==calls+1,'native exactly once')
  check(all(self.data<=at<self.cave+meta['allocation'] or self.stats<=at<self.stats+128 or 0x61000000<=at<0x61010000 or at in allowed for at in writes),'no unexpected actor/gameplay writes')
  return struct.unpack('<f',u.mem_read(self.stats+24,4))[0] if h['fp'] else u.reg_read(UC_X86_REG_EAX)
 def hook(self,mode):return next(h for h in meta['wrappers'] if h['mode']==mode)
 def begin(self,x=8,y=64,tx=120,ty=64):
  self.call(self.hook(11),begin=[0,bits(x),bits(y),bits(tx),bits(ty),self.query,0]);return self.r(self.route+28)
 def end(self):self.call(self.hook(12));check(self.r(self.stats+8)==0,'context cleared before unlock')
 def blocked(self,x,y):return self.call(self.hook(14),[self.query],obj=self.cells+(y*32+x)*48)&255

for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 for scenario,expected in [('builder',1),('human',0),('member',0),('friend',0),('neutral',0),('hidden',0),('dead',0),('weak_lair',0),('attack_target',0),('builder_target',0),('disabled',0),('removed',0),('nonfinite',0),('strong_army',0),('weak_army',0),('capturable',1),('direct_org',1),('broken_backlink',0),('dead_leader',0),('removed_company',0),('actual_builder_member',1),('foundation_builder',0),('mine_builder',0),('empty_build_list',0),('cyclic_build_list',0)]:
  f=Fixture(image,cave)
  if scenario=='human':f.w(f.slot+0xc,0)
  if scenario=='member':f.w(f.actor+0x7c,0)
  if scenario=='capturable':f.w(f.lair+0xc4,0)
  if scenario=='direct_org':f.w(f.query+0x1c,f.actor)
  if scenario=='broken_backlink':f.w(f.element+4,0)
  if scenario=='dead_leader':f.w(f.leader+8,1)
  if scenario=='removed_company':f.w(f.actor+8,1)
  if scenario=='actual_builder_member':
   component=f.r(f.actor+0xa8);f.w(f.actor+0xa8,0);f.w(f.leader+0xa8,component);f.w(component+4,f.leader)
   f.w(f.org+0x28,f.org+0x200);f.w(f.org+0x2c,1);f.w(f.org+0x200,f.leader)
  if scenario in ('friend','neutral'):f.w(f.stats+12,1 if scenario=='friend' else 2)
  if scenario=='hidden':f.w(f.stats+16,0)
  if scenario=='dead':f.f(f.den+0x210,0)
  if scenario=='weak_lair':f.f(f.den+0x10,0)
  if scenario in ('attack_target','strong_army','weak_army'):f.w(f.actor+0xa8,0)
  if scenario in ('attack_target','builder_target'):f.w(f.query+0x20,f.lair)
  if scenario=='strong_army':f.f(f.org+0x68,1000)
  if scenario=='disabled':f.w(f.data+4,7)
  if scenario=='removed':f.w(f.lair+8,1)
  if scenario=='nonfinite':f.f(f.ldef+0x364,float('nan'))
  if scenario=='foundation_builder':f.u.mem_write(f.markerdef+0x100,'marker_foundation_spot\0'.encode('utf-16le'))
  if scenario=='mine_builder':f.w(f.centerdef+0x430,0)
  if scenario=='empty_build_list':f.w(f.buildnode,0)
  if scenario=='cyclic_build_list':f.w(f.buildnode,0);f.w(f.buildnode+4,f.buildnode)
  check(f.begin()==expected,scenario)
  for h in [h for h in meta['wrappers'] if h['mode']==13]:
   result=f.call(h,[bits(v) for v in (8,64,120,64)],native=0xcafe01)
   check(result==(0xcafe00 if expected else 0xcafe01),(scenario,'LOS'))
  for h in [h for h in meta['wrappers'] if h['mode']==14]:
   check(f.call(h,[f.query],obj=f.cells+(16*32+16)*48)==0,(scenario,'danger is not an impassable cell'))
   check(f.call(h,[f.query],obj=f.cells+(16*32+16)*48,native=0xabcd01)==0xabcd01,'native blocked remains blocked')
  f.end()
 # Even adjacent guard circles must not obstruct an attack. Exercise actual
 # compiled selection with strategic attack orders and member combat states.
 for state in [0x4f4dc4,0x4f4e20,0x4f4e4c,0x4f4e78,0x4f4ea4,0x4f4fb4]:
  for member in [False,True]:
   f=Fixture(image,cave);unit=f.leader if member else f.actor;cai=0x51012000;stack=cai+0x100;s=stack+0x100
   f.w(unit+0x70,cai);f.w(cai+0x14,stack);f.w(stack,s);f.w(s,image+state)
   f.w(f.org+0x28,f.org+0x200);f.w(f.org+0x2c,1);f.w(f.org+0x200,f.leader)
   check(f.begin()==0,('combat bypass',hex(state),member));f.end()
 for goalvt,active,expected in [(0x4da480,2,1),(0x4d84d4,2,1),(0x4da480,0,1),(0x4d79e8,2,1),(0x4da6b0,2,1),(0x4da510,2,1)]:
  f=Fixture(image,cave);node=0x51012000;sa=node+0x100;g=sa+0x100;eng=g+0x100
  f.w(f.player+0x2c,node);f.w(f.player+0xc,eng);f.w(node,sa);f.w(sa+8,1);f.w(sa+0xc,f.player);f.w(sa+0x10,g)
  f.w(g,image+goalvt);f.w(g+4,eng);f.w(g+8,active)
  check(f.begin()==expected,('local strategic order cannot affect shared routing',hex(goalvt),active));f.end()
 # Hostile explicit actor target bypasses unrelated lairs; allied construction
 # targets must still retain avoidance. Target itself need not have denizens.
 f=Fixture(image,cave);f.w(f.query+0x20,f.leader)
 check(f.begin()==0,'hostile query target bypasses all threats');f.end()
 # Crash log-363: the global registry contains non-GActor objects too.
 # A registered service object can have poison at the component offsets;
 # an even smaller one ends at a page boundary. Never read its actor tail.
 for case in ('poisoned_service','short_service','stale_generation'):
  f=Fixture(image,cave)
  if case=='short_service':
   fake=0x63000fe8;f.u.mem_map(0x63000000,4096)
  else:fake=f.actor+0xb00
  f.w(fake,image+0x4b0000);f.w(fake+0x14,20);f.w(f.reg+0x20004+20*4,fake)
  if case=='poisoned_service':
   for o,v in [(0x60,0xabababab),(0x88,0xefefefef),(0x94,8)]:f.w(fake+o,v)
  if case=='stale_generation':
   f.w(fake,image+0x4e5c58);f.w(fake+0x14,0x10014);f.w(fake+0x88,0xefefefef)
  check(f.begin()==1,('registered non-actor ignored',case));f.end()
 # No replacement admission hook: the original game's builder/army
 # eligibility runs unchanged for every goal and option combination.
 check(any(h['mode']==18 and h['site']==0x1e280f for h in meta['wrappers']), 'admission hook only used for peaceful defense cooldown; offense tested separately')
 check(game[0x1e280f:0x1e2814]==b'\xe8'+struct.pack('<i',0x2273b0-0x1e2814),'original admission call verified')
 f=Fixture(image,cave);f.begin(50,64,10,64)
 check(not f.blocked(11,16),'can leave danger')
 check(f.call(f.hook(13),[bits(v) for v in (50,64,8,64)],native=1)==1,'outward segment')
 check(not f.blocked(16,16),'danger uses movement cost even inside the radius')
 f.end()
 f=Fixture(image,cave);f.begin();node=f.actor+0x800;f.w(node,15);f.w(node+4,16)
 check(f.call(f.hook(15),[node,16,16],fp=5)>5,'grid cost increases')
 f.w(node,1);f.w(node+4,1);check(f.call(f.hook(15),[node,2,1],fp=5)==5,'safe grid cost unchanged')
 m=f.grid+0x100;regions=m+0x100;left=m+0x200;right=m+0x300;f.w(image+0x5f3fcc,m);f.w(m+0x14,regions);f.w(m+0x18,2);f.w(regions,left);f.w(regions+4,right)
 for o,x in [(left,8),(right,120)]:f.f(o+0x54,x);f.f(o+0x58,64)
 check(f.call(f.hook(16),[1],obj=left,fp=5)>5,'regional cost increases')
 f.end()

# Use the compiled movement-cost callback in a real search with a choice of
# routes, then a forced corridor and a goal inside danger. Terrain is modeled.
f=Fixture();f.begin(6,66,122,66);costs={};node=f.actor+0x800
def edge(p,n):
 key=tuple(sorted((p,n)))
 if key not in costs:
  f.w(node,p[0]);f.w(node+4,p[1]);costs[key]=f.call(f.hook(15),[node,n[0],n[1]],fp=1)
 return costs[key]
def astar(weighted=True,only_corridor=False,end=(30,16)):
 start=(1,16);q=[(0,start)];prev={start:None};dist={start:0}
 while q:
  _,p=heapq.heappop(q)
  if p==end:
   path=[]
   while p is not None:path.append(p);p=prev[p]
   return path[::-1]
  for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
   n=p[0]+dx,p[1]+dy
   if not(0<=n[0]<32 and 8<=n[1]<=24) or (only_corridor and n[1]!=16):continue
   d=dist[p]+(edge(p,n) if weighted else 1)
   if d<dist.get(n,1e9):dist[n]=d;prev[n]=p;heapq.heappush(q,(d+abs(n[0]-end[0])+abs(n[1]-end[1]),n))
 return []
normal=astar(False);detour=astar()
check(detour and len(detour)>len(normal),'builder path detours around actual guarded area')
check(all((x*4+2-64)**2+(y*4+2-64)**2>=24**2 for x,y in detour),'weighted route stays outside when possible')
forced=astar(only_corridor=True);check(forced==normal,'unavoidable corridor remains reachable')
inside=astar(end=(16,16));check(inside and inside[-1]==(16,16),'destination inside a radius remains reachable')
for h in [h for h in meta['wrappers'] if h['mode']==13]:
 check(f.call(h,[bits(v) for v in (62,66,66,66)],native=1)==1,'adjacent reconstruction steps stay legal in danger')
 check(f.call(h,[bits(v) for v in (62,66,66,66)],native=0)==0,'native wall cannot be bypassed')
f.end()
for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 for scenario,expected in [('camp',4000),('too_strong',1000),('hidden',1000),('allied',1000),('two_cities',4000),('three_cities',4000),('many_cities',4000),('no_cities',1000),('three_cities_hidden',1000),('three_cities_allied',1000),('three_cities_too_strong',1000),('three_cities_remote',1000),('three_cities_construction',1000),('disabled',1000),('inactive',0),('stale_id',1000),('ordinary_enemy_city',1000),('secondary',150),('no_available_camp',1000),('construction',3000),('remote',1000),('dead_camp',1000)]:
  f=Fixture(image,cave);city=0x5100d000;settlement=city+0x400;body=city+0x600;goal=0x51010000;engine=goal+0x100
  node=0x51011000;sa=node+0x100;marker=0x51012000
  f.w(city,image+0x4e5c58);f.w(city+0x14,4);f.w(f.reg+0x20004+4*4,city);f.w(city+0xe8,f.kingdom);f.w(city+0x94,city+0x300);f.w(city+0x98,settlement)
  f.w(settlement+4,city);f.w(settlement+0x14,city);f.w(city+0x60,body);f.w(body+4,city);f.f(body+0x10,1000)
  f.w(f.kingdom+0x2dc,city+0x800);f.w(city+0x800,city);f.w(f.kingdom+0x2e0,1);f.f(city+0x20,8);f.f(city+0x24,64)
  f.w(f.player+0x2c,node);f.w(node,sa);f.w(sa+8,1);f.w(f.actor+0xa8,0);f.f(f.org+0x68,300)
  f.w(f.ldef+0x4e0,marker);f.w(marker+8,marker+0x100);f.u.mem_write(marker+0x100,'marker_settlement\0'.encode('utf-16le'))
  f.w(goal,image+0x4da480);f.w(goal+4,engine);f.w(engine+4,f.player);f.w(goal+0x4c,2);f.f(goal+0x38,1000)
  if scenario in ('too_strong','three_cities_too_strong'):f.f(f.den+0x10,1000)
  if scenario in ('hidden','three_cities_hidden'):f.w(f.stats+16,0)
  if scenario in ('allied','three_cities_allied'):f.w(f.stats+12,1)
  if scenario=='disabled':f.w(f.data+4,7)
  if scenario=='inactive':f.f(goal+0x38,0)
  if scenario=='stale_id':f.w(goal+0x4c,0x10002)
  if scenario=='ordinary_enemy_city':f.w(f.lair+0x98,city+0x900);f.w(city+0x914,f.lair)
  city_count=0 if scenario=='no_cities' else 2 if scenario=='two_cities' else 8 if scenario=='many_cities' else 3 if scenario.startswith('three_cities') else 1
  for j in range(1,city_count):
   other=0x510b0000+j*0x1000;oid=100+j
   f.u.mem_write(other,bytes(f.u.mem_read(city,0x800)));f.w(other+0x14,oid);f.w(f.reg+0x20004+oid*4,other)
   f.w(other+0x94,other+0x300);f.w(other+0x304,other)
   f.w(other+0x98,other+0x400);f.w(other+0x404,other);f.w(other+0x414,other);f.w(other+0x60,other+0x600);f.w(other+0x604,other)
   f.w(city+0x800+j*4,other)
  f.w(f.kingdom+0x2e0,city_count)
  if scenario in ('secondary','no_available_camp'):
   other=0x51015000;odef=0x51017000;oden=0x51018000
   f.u.mem_write(other,bytes(f.u.mem_read(f.lair,0x180)));f.u.mem_write(odef,bytes(f.u.mem_read(f.ldef,0x600)));f.u.mem_write(oden,bytes(f.u.mem_read(f.den,0x400)))
   f.w(other+0x14,6);f.w(f.reg+0x20004+6*4,other);f.w(other+4,odef);f.w(odef+0x4e0,0)
   for off,part in [(0x88,oden),(0x94,oden+0x300),(0x60,oden+0x200)]:f.w(other+off,part);f.w(part+4,other)
   f.w(goal+0x4c,6)
   if scenario=='no_available_camp':f.w(f.ldef+0x4e0,0)
  if scenario in ('construction','three_cities_construction'):f.w(goal,image+0x4da6b0);f.w(goal+0x44,f.ldef)
  if scenario in ('remote','three_cities_remote'):
   for j in range(city_count):f.f(f.r(city+0x800+j*4)+0x20,1000)
  if scenario=='dead_camp':f.f(f.den+0x210,0)
  f.call(f.hook(0),obj=goal,args=[0,0],allowed=[goal+0x38])
  check(abs(struct.unpack('<f',f.u.mem_read(goal+0x38,4))[0]-expected)<0.01,('expansion score',scenario))
  if scenario=='camp':
   f.w(sa+0x10,goal);f.f(f.actor+0x20,64);f.f(f.actor+0x24,64)
   for time,want in [(602,4000),(676,4000),(678,4000),(1802,4000)]:
    f.f(f.world+0xe8,time);f.f(goal+0x38,1000);f.call(f.hook(0),obj=goal,args=[0,0],allowed=[goal+0x38])
    check(abs(struct.unpack('<f',f.u.mem_read(goal+0x38,4))[0]-want)<.01,('long siege retains priority',time))
   f.w(sa+0x10,0);f.f(f.world+0xe8,1804);f.f(goal+0x38,1000)
   f.call(f.hook(0),obj=goal,args=[0,0],allowed=[goal+0x38]);check(f.r(goal+0x38)==bits(4000),'unassignment does not change long siege priority')
   f.f(f.org+0x68,400);f.f(f.world+0xe8,1806);f.f(goal+0x38,1000)
   f.call(f.hook(0),obj=goal,args=[0,0],allowed=[goal+0x38]);check(f.r(goal+0x38)==bits(4000),'reinforcement keeps clearing priority')
print('AI_ROUTING_PASS',checks,'checks; 3 ASLR bases; native CV; guarded hooks; human/ally/fog/limits; exit; detour fixture; engine callees partly stubbed')
