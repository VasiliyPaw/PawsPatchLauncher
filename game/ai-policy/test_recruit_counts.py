"""Compiled recruitment counts plus the original native actor/property scorer.
Lifecycle services are explicit stubs; three relocated game/payload bases.
No game process is attached or changed by this test.
"""
from pathlib import Path
exec(compile(Path(__file__).with_name('test_limits.py').read_text().split('\nfor image,cave in ')[0], 'test_limits.py:fixtures', 'exec'))
game=(a.legacy/'k2_runtime_1372_20260904.bin').read_bytes()
hooks={m:next(h for h in meta['wrappers'] if h['mode']==m) for m in (40,42,43,44,45,46,47,48)}
checks=0
def check(value,message):
 global checks
 assert value,message
 checks+=1

class CountsFixture(Fixture):
 def __init__(self,image,cave):
  super().__init__(image,cave)
  self.w(self.data+4,8);self.w(self.pl+4,1);self.w(image+0x5f9218,2)
  self.ego=self.obj+0x10000;self.cfg=self.ego+0x1000;self.prop=self.ego+0x2000;self.vt=self.prop+0x100
  self.alias1=self.ego+0x3000;self.alias2=self.ego+0x4000
  self.w(self.df+0x534,self.alias1);self.w(self.df+0x548,self.alias2)
  self.w(self.df+0x1d4,self.prop+0x200);self.w(self.prop+0x200,self.prop)
  self.w(self.prop,self.vt);self.w(self.vt+0x18,image+0x1000);self.asm(image+0x1000,'mov eax,1; ret')
  self.w(self.cfg+0x100+4,self.cfg);self.w(self.cfg,1);self.f(self.cfg+4,350);self.f(self.cfg+8,5000)
  self.w(self.stats+32,6);self.w(self.stats+36,1)
  for target in (0x1eeb0b,0x1eeb2b):self.asm(image+target,f'mov eax,[{self.stats+32}]; mov ecx,0x1234; mov edx,0x5678; stc; ret 4')
  for target in (0x1ee8a3,0x1ee978):self.asm(image+target,f'inc dword ptr [{self.stats+12}]; mov eax,0xabcdef01; stc; ret 4')
  for start,end in ((0x5c7b9,0x5c8ef),(0x29949,0x2995d)):
   self.u.mem_write(image+start,game[start:end])
  for h in meta['wrappers']:
   if h['mode'] in (42,43):self.asm(image+h['site'],f'call {cave+h["offset"]}')
  self.asm(image+0x64679,f'cmp ecx,{self.ego+0x374}; jne prop; cmp dword ptr [{self.stats+36}],1; jne missing; mov eax,{self.cfg+0x100}; ret 4; prop: cmp dword ptr [{self.stats+36}],2; jne missing; mov eax,{self.cfg+0x100}; ret 4; missing: xor eax,eax; ret 4')
 def call(self,mode,args,obj=None,actor=0,native=None):
  h=hooks[mode];u=self.u
  if mode==48:self.asm(self.image+h['target'],f'mov eax,{native or self.pl}; stc; ret 16')
  self.w(self.sp,0x62000000)
  for j,value in enumerate(args):self.w(self.sp+4+j*4,value)
  regs={UC_X86_REG_EBX:0xabcdef12,UC_X86_REG_ESI:0x12345678,UC_X86_REG_EDI:actor or 0x22334455,UC_X86_REG_EBP:0x33445566}
  for reg,value in regs.items():u.reg_write(reg,value)
  xmm=[0x12340000123400001234000012340000+i for i in range(8)]
  for i,value in enumerate(xmm):u.reg_write(UC_X86_REG_XMM0+i,value)
  u.reg_write(UC_X86_REG_ECX,obj or self.pl);u.reg_write(UC_X86_REG_ESP,self.sp)
  # The native priority function clobbers XMM0/1 legitimately; callbacks must
  # preserve all other registers and the older value on the x87 stack.
  self.asm(0x62000100,'fninit; fld1')
  u.emu_start(0x62000100,0x62000104)
  writes=[];wh=u.hook_add(UC_HOOK_MEM_WRITE,lambda u,access,at,size,value,data:writes.append(at))
  u.emu_start(self.cave+h['offset'],0x62000000,count=3000000);u.hook_del(wh)
  check(u.reg_read(UC_X86_REG_ESP)==self.sp+4+4*h['argc'],'stack cleanup')
  for reg,value in regs.items():check(u.reg_read(reg)==value,'nonvolatile registers')
  for i in range(2 if mode==40 else 0,8):check(u.reg_read(UC_X86_REG_XMM0+i)==xmm[i],'SSE preserved')
  check(all(self.data<=at<self.cave+meta['allocation'] or 0x61000000<=at<0x61010000 or self.stats<=at<self.stats+128 for at in writes),'only payload/stack/stub writes')
  if mode!=40:check(u.reg_read(UC_X86_REG_EFLAGS)&1,'native carry preserved')
  eax=u.reg_read(UC_X86_REG_EAX)
  self.asm(0x62000120,f'fstp qword ptr [{self.stats+64}];'+(f'fstp qword ptr [{self.stats+72}];' if mode==40 else '')+'nop')
  code=bytes(ks.asm(f'fstp qword ptr [{self.stats+64}];'+(f'fstp qword ptr [{self.stats+72}];' if mode==40 else ''),0x62000120)[0])
  u.emu_start(0x62000120,0x62000120+len(code))
  result=struct.unpack('<d',u.mem_read(self.stats+64,8))[0]
  check((struct.unpack('<d',u.mem_read(self.stats+72,8))[0] if mode==40 else result)==1,'older x87 value')
  return result if mode==40 else eax
 def reset(self,index=0,player=None):return self.call(48,[index,self.k,self.ego,0],native=player)
 def actor(self,index,kind=1,flags=0,definition=None):
  actor=self.obj+0x20000+index*0x200
  self.w(actor,self.image+0x4e5c58);self.w(actor+4,definition or self.df);self.w(actor+0x14,1000+index);self.w(actor+0x144,kind);self.w(actor+0x100,flags)
  return actor
 def add(self,actor,player=None):return self.call(46,[self.r(actor+4)],actor=actor,obj=player)
 def remove(self,actor,player=None):return self.call(47,[self.r(actor+4)],actor=actor,obj=player)
 def count(self,key=None,property=False,player=None):return self.call(45 if property else 44,[key or (self.prop if property else self.df)],obj=player)
 def score(self):return self.call(40,[self.df,self.pl,1],obj=self.ego)
 def unscoped(self,property=False):return self.call(43 if property else 42,[self.prop if property else self.df])

for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 # Shared admission rules do not depend on the actor/race's definition name.
 for race in ('human','drauga','gauri','haroun','undead','fallen'):
  f=CountsFixture(image,cave);f.u.mem_write(f.df+0x800,(race+'_worker\0').encode('utf-16le'));f.reset()
  # Live city boneweavers/berserker militia can have class 2 with bit 4 clear.
  for i in range(6):f.add(f.actor(i,kind=2,flags=4 if i%2 else 0))
  for i in range(6,10):f.add(f.actor(i,kind=1,flags=4)) # local militia
  f.add(f.actor(10,kind=3,flags=0)) # militia organization can lack denizen bit
  for key in (f.df,f.alias1,f.alias2):check(f.count(key)==0,('no local soldiers/workers',race))
  check(f.count(property=True)==0,'no local role_settler/role_melee counts')
  check(f.unscoped()==6 and f.unscoped(True)==6,'outside recruitment original counts intact')
  for priority_path in (1,2):
   f.w(f.stats+36,priority_path)
   for property_count in (0,1):
    f.w(f.cfg,property_count);check(f.score()==350,'real native scorer no local repeat penalty')
  check(f.unscoped()==6,'scope restored after native floating result')
  field=f.actor(12,kind=1);f.add(field)
  for key in (f.df,f.alias1,f.alias2):check(f.count(key)==1,'field definition and aliases counted')
  check(f.count(property=True)==1,'field properties counted')
  for path in (1,2):f.w(f.stats+36,path);check(f.score()==-4650,'existing field builder prevents duplicate demand')
  f.w(field+8,1);f.w(field+0x100,4);f.remove(field)
  check(f.count()==0 and f.count(property=True)==0,'death/conversion removes original recorded membership')
  # Excluded militia becoming a field unit must be removed then registered.
  actor=f.actor(13,kind=1,flags=4);f.add(actor);f.w(actor+0x100,0);f.remove(actor);f.add(actor)
  check(f.count()==1,'militia conversion re-registers field soldier')
  f.remove(actor);f.add(actor);check(f.count()==1,'recycled ID tombstones')
  # Same-world and same-player address on loading a save cannot reuse counts.
  f.reset();check(f.count()==0,'same-address save load reset')
  f.add(f.actor(14,kind=0));check(f.count()==1,'field company counted')
  # Native counter and stock defense code remain untouched throughout.
  check(f.unscoped()==6,'native defense count unaffected')
 f=CountsFixture(image,cave)
 check(f.count()==6,'no initialized mirror falls back to native')
 f.reset();actor=f.actor(0);f.add(actor)
 other=f.pl+0x400;f.w(other+4,1);f.reset(1,other)
 check(f.count(player=other)==0 and f.count()==1,'players isolated')
 f.remove(actor);f.add(actor,other)
 check(f.count()==0 and f.count(player=other)==1,'capture transfers ownership')
 f.w(f.pl+4,0);check(f.count()==6,'human native counts');f.w(f.pl+4,1)
 f.w(f.data+4,0);f.add(f.actor(1));check(f.count()==6,'disabled query unchanged')
 f.w(f.data+4,8);check(f.count()==1,'registration tracked while option disabled')
 f.w(image+0x5f9218,1);check(f.count()==6,'not in running phase unchanged');f.w(image+0x5f9218,2)
 f.add(f.actor(1));check(f.count()==6,'duplicate registration invalidates mirror safely')
 f.reset();f.remove(f.actor(0));check(f.count()==6,'missing removal invalidates mirror safely')
 f.reset();f.w(image+0x5f3fb8,f.world+0x100);check(f.count()==6,'world change falls back until reconstruction')
 f.reset();check(f.count()==0,'new world starts empty')
 # Use original native call-site instructions to deliver EDI at admission.
 start,end=0x1ecc83,0x1ecc93;native=bytearray(game[start:end]);h=hooks[46]
 struct.pack_into('<i',native,h['site']+1-start,cave+h['offset']-image-h['site']-5)
 f.u.mem_write(image+start,bytes(native));actor=f.actor(4);f.w(f.sp+8,actor)
 f.u.reg_write(UC_X86_REG_ESP,f.sp-64);f.u.reg_write(UC_X86_REG_EBP,f.sp);f.u.reg_write(UC_X86_REG_ECX,f.pl)
 f.u.emu_start(image+start,image+end,count=3000000)
 check(f.count()==1,'original registration caller supplies actor in EDI')
print('AI_RECRUIT_COUNTS_PASS',checks,'checks; six races, real native priority math, lifecycle/load/owner changes, recruitment-only scope, ABI and no engine table writes; lifecycle services mocked')
