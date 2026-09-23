"""Execute compiled x86 policy and wrappers; engine callees are explicit stubs.
Regression fixtures cover native resource pairing, limited capacity, selection
fallback, cdecl/thiscall preservation and stale child-building commands.
"""
import argparse,json,struct,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--native',type=Path,required=True);a=p.parse_args()
sys.path[:0]=[str(a.legacy/'lobby_colors_1372/deps_r15'),str(a.legacy/'pydeps_readable')]
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_MEM_WRITE
from unicorn.x86_const import *
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
meta=json.loads((a.native/'ai-policy.json').read_text());raw=(a.native/'ai-policy.bin').read_bytes();ks=Ks(KS_ARCH_X86,KS_MODE_32)
cases=0
class Fixture:
 def __init__(self,image,cave,count=9):
  self.image=image;self.cave=cave;self.n=count;u=self.u=Uc(UC_ARCH_X86,UC_MODE_32)
  u.mem_map(image,0x690000);u.mem_map(cave,(meta['allocation']+4095)&~4095);u.mem_map(0x51000000,0x90000);u.mem_map(0x61000000,0x10000);u.mem_map(0x62000000,0x1000)
  self.obj=0x51000000;self.pl=self.obj+0x1000;self.engine=self.obj+0x2000;self.k=self.obj+0x3000;self.world=self.obj+0x4000;self.df=self.obj+0x5000
  self.pr=self.obj+0x6000;self.up=self.pr+128;self.cost=self.pr+512;self.table=self.obj+0x7000;self.city=self.obj+0x9000;self.center=self.obj+0xa000;self.body=self.obj+0xb000;self.reg=self.obj+0x30000;self.sp=0x6100f000
  self.data=cave+meta['dataOffset'];self.stats=self.obj+0x8000;self.calls=0
  code=bytearray(raw)
  for off,im,cv in meta['fixups']:struct.pack_into('<I',code,off,(struct.unpack_from('<I',code,off)[0]+im*(image-meta['image'])+cv*(cave-meta['cave']))&0xffffffff)
  u.mem_write(cave,bytes(code));self.w(self.data+4,7);self.w(self.data+meta['queryPointerOffset'],cave+meta['queryOffset'])
  self.w(image+0x5f3fb8,self.world);self.f(self.world+0xe8,600);self.w(self.obj+4,self.engine);self.w(self.engine+4,self.pl);self.w(self.pl+8,self.k);self.w(self.obj+0x44,self.df)
  self.w(image+0x5f3fc8,self.table+128);self.w(self.table+128+0x6c,self.table+256);self.w(self.table+128+0x70,1);self.w(self.table+256,self.pl)
  self.w(self.df+8,self.df+0x800);u.mem_write(self.df+0x800,'company_expensive\0'.encode('utf-16le'));self.w(self.df+0x174,128);self.w(self.df+0x2f0,self.df+0x400)
  self.w(self.k+0x1a8,self.pr);self.w(self.k+0x1c0,self.up);self.w(self.k+0x1cc,self.pr+256);self.w(self.k+0x1d0,count)
  self.f(self.pr,900);self.f(self.up,300);self.f(self.pr+256,12000)
  self.w(image+0x5efa8c,self.table);self.w(self.table+0x24,self.table+0x300);self.w(self.table+0x28,count)
  for i in range(count):
   rd=self.table+0x400+64*i;self.w(self.table+0x300+4*i,rd);self.w(rd+0xc,i);self.w(rd+0x18,1)
  for used,provided in [(5,6),(7,8)]:
   rd=self.table+0x400+64*used;self.w(rd+0x18,2);self.w(rd+0x30,self.table+0x400+64*provided);self.f(self.pr+4*provided,20);self.f(self.up+4*used,19)
  # Native ResourceVector bridge really executes; only engine vector allocation,
  # aggregate cost calculation and destruction are mocked here.
  self.asm(image+0x22607d,f'inc dword ptr [{self.stats}]; mov dword ptr [ecx+4],{self.cost}; mov dword ptr [ecx+8],{count}; mov eax,ecx; ret')
  self.asm(image+0x20dae6,f'inc dword ptr [{self.stats+4}]; mov eax,[esp+12]; mov [{self.stats+16}],eax; ret')
  self.asm(image+0x226166,f'inc dword ptr [{self.stats+8}]; ret')
  self.w(image+0x5ef72c,self.reg);self.w(self.city,image+0x4e5c58);self.w(self.center,image+0x4e5c58);self.w(self.city+0x14,123);self.w(self.center+0x14,456);self.w(self.reg+0x20004+4*123,self.city);self.w(self.reg+0x20004+4*456,self.center)
  self.w(self.city+0x98,self.obj);self.w(self.city+0xe8,self.k);self.w(self.center+0xe8,self.k);self.w(self.center+0x60,self.body);self.w(self.body+4,self.center);self.f(self.body+0x10,15000);self.f(self.body+0x14,15000)
  self.w(self.obj+0x14,self.center)
 def w(self,p,v):self.u.mem_write(p,struct.pack('<I',v))
 def f(self,p,v):self.u.mem_write(p,struct.pack('<f',v))
 def r(self,p):return struct.unpack('<I',self.u.mem_read(p,4))[0]
 def asm(self,p,s):self.u.mem_write(p,bytes(ks.asm(s,p)[0]));self.u.ctl_remove_cache(p,p+256)
 def run(self,h,args=None,native=0xc0ff01,blocked=0):
  global cases
  u=self.u;obj=self.obj;args=args or [self.df]*h['argc'];self.calls+=1
  if h['mode'] in (6,7,9,10):self.w(obj+4,self.city)
  if h['mode']==8:args=[self.city,self.df,self.cost,0,self.stats+64]
  if h['mode']==5:
   self.w(self.table+0x1000+4,self.pr);self.w(self.table+0x1010+4,self.up);args=[self.table+0x1000,self.table+0x1010];self.w(obj+0x48,self.df+0x444)
  stub=f'inc dword ptr [{self.stats+12}];'
  if h['mode']==8:stub+=f'mov edx,[esp+20]; mov dword ptr [edx],{blocked};'
  stub+=f'mov eax,{native}; mov ecx,0x1234; mov edx,0x5678; stc; ret {0 if h["cdecl"] else h["argc"]*4};'
  self.asm(self.image+h['target'],stub)
  self.w(self.sp,0x62000000)
  for j,v in enumerate(args):self.w(self.sp+4+j*4,v)
  regs={UC_X86_REG_EBX:0xabcdef12,UC_X86_REG_ESI:0x12345678,UC_X86_REG_EDI:0x22334455,UC_X86_REG_EBP:0x33445566}
  for reg,v in regs.items():u.reg_write(reg,v)
  for i in range(8):u.reg_write(UC_X86_REG_XMM0+i,0x12340000123400001234000012340000+i)
  u.reg_write(UC_X86_REG_ECX,obj);u.reg_write(UC_X86_REG_ESP,self.sp)
  old=bytes(u.mem_read(obj,0x90000));writes=[]
  hook=u.hook_add(UC_HOOK_MEM_WRITE,lambda u,access,at,size,value,data:writes.append(at))
  u.emu_start(self.cave+h['offset'],0x62000000,count=100000);u.hook_del(hook)
  assert u.reg_read(UC_X86_REG_ESP)==self.sp+4+(0 if h['cdecl'] else h['argc']*4),(h,'stack')
  for reg,v in regs.items():assert u.reg_read(reg)==v,(h,'nonvolatile register')
  for i in range(8):assert u.reg_read(UC_X86_REG_XMM0+i)==0x12340000123400001234000012340000+i
  assert all(self.data<=at<self.cave+meta['allocation'] or 0x61000000<=at<0x61010000 or self.stats<=at<self.stats+128 for at in writes),(h,'unexpected game write')
  if h['mode']!=9:assert u.reg_read(UC_X86_REG_EFLAGS)&1
  cases+=1
  n=self.r(self.data);ev=bytes(u.mem_read(self.data+128+((n-1)&2047)*128,128))
  return u.reg_read(UC_X86_REG_EAX),struct.unpack_from('<I',ev,28)[0]

for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 for h in [x for x in meta['wrappers'] if x['mode']==4]:
  for scenario,expected,resource in [('full_kingdom',False,8),('exact_fit',True,0),('ordinary',True,0),('full_army',False,6),('negative_resource',True,0),('native_rejected',False,0xffffffff),('disabled',True,0),('shards',False,8),('no_table',True,0)]:
   f=Fixture(image,cave,10 if scenario=='shards' else 9);f.f(f.cost+28,4);f.f(f.cost+20,1)
   if scenario in ('exact_fit','negative_resource'):f.f(f.up+28,16)
   if scenario=='ordinary':f.f(f.cost+28,0)
   if scenario=='full_army':f.f(f.up+20,20)
   if scenario=='negative_resource':f.f(f.up+4,50);f.f(f.cost+4,100);f.f(f.pr+4,0)
   if scenario=='disabled':f.w(f.data+4,1)
   if scenario=='no_table':f.w(image+0x5efa8c,0)
   ret,result=f.run(h,native=0xc0ff00 if scenario=='native_rejected' else 0xc0ff01)
   assert bool(ret&255)==expected and ret&0xffffff00==0xc0ff00,(scenario,hex(ret))
   assert result==resource,(scenario,result,resource)
   assert f.r(f.stats)==f.r(f.stats+4)==f.r(f.stats+8),'vector lifetime'
   if f.r(f.stats):assert f.r(f.stats+16)==f.df+0x400,'default company layout forwarded'
  # A previously blocked expensive candidate becomes eligible immediately once
  # the real capacity changes; recorded-event dedup must never cache decisions.
  f=Fixture(image,cave);f.f(f.cost+28,4)
  assert f.run(h)[0]&255==0
  f.f(f.cost+28,0);assert f.run(h)[0]&255==1 # next ordinary candidate remains selectable
  f.f(f.cost+28,4);f.f(f.up+28,16);assert f.run(h)[0]&255==1
 for h in [x for x in meta['wrappers'] if 5<=x['mode']<=8 or x['mode']==10]:
  for accepted in (False,True):
   f=Fixture(image,cave);f.f(f.cost+28,4)
   if h['mode']==5:
    # Late pass already reserved the cost: remove exactly this reservation for
    # diagnostic comparison, never mutate the real budget vector.
    f.f(f.up+28,20 if accepted else 19)
    ret,result=f.run(h,native=0xc0ff00 if accepted else 0xc0ff01)
    assert result==(0 if accepted else 8)
    assert f.r(f.stats+16)==f.df+0x444,'actual goal layout forwarded'
   else:
    ret,result=f.run(h,native=0xc0ff01 if accepted else 0xc0ff00,blocked=0 if accepted else f.table+0x400+7*64)
    if h['mode']==8:assert result==(0 if accepted else 8)
    elif h['mode'] in (7,10):assert result==int(accepted)
    else:assert result==1 # reached enqueue; opaque EAX has no boolean meaning
   assert ret==(0xc0ff00 if (h['mode']==5)==accepted else 0xc0ff01)
 h=next(x for x in meta['wrappers'] if x['mode']==9)
 for scenario,reason in [('healthy',0),('sovereign',0),('wounded',0),('siege',0),('dead',4),('missing_center',2),('removed_center',2),('removed_city',1),('wrong_owner',3),('no_owner',3),('wrong_body',4),('nan_health',4),('disabled',0)]:
  f=Fixture(image,cave)
  if scenario=='wounded':f.f(f.body+0x10,1)
  if scenario=='siege':f.w(f.city+0x100,0xffffffff) # wrapper doesn't bypass native siege validation
  if scenario=='dead':f.f(f.body+0x10,0)
  if scenario=='missing_center':f.w(f.obj+0x14,0)
  if scenario=='removed_center':f.w(f.reg+0x20004+456*4,0)
  if scenario=='removed_city':f.w(f.reg+0x20004+123*4,0)
  if scenario=='wrong_owner':f.w(f.center+0xe8,f.k+256)
  if scenario=='no_owner':f.w(f.city+0xe8,0);f.w(f.center+0xe8,0)
  if scenario=='wrong_body':f.w(f.body+4,0)
  if scenario=='nan_health':f.f(f.body+0x10,float('nan'))
  if scenario=='disabled':f.w(f.data+4,3);f.f(f.body+0x10,0)
  ret,result=f.run(h)
  assert result==reason,(scenario,result,reason)
  assert f.r(f.stats+12)==(0 if reason else 1),(scenario,'native child creation call count')
print('AI_LIMIT_LIFECYCLE_PASS',cases,'relocated x86 cases; native resource-vector bridge; capacity fallback, ABI, city lifecycle; engine callees mocked')
