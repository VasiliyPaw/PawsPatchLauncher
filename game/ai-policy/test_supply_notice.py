"""Compiled supply cap and UI-only warning throttle at three ASLR bases.
Native services are explicit stubs; the complete original warning call site runs.
"""
from pathlib import Path
fixtures=Path(__file__).with_name('test_limits.py').read_text().split('\nfor image,cave in ')[0]
fixtures=fixtures.replace('count=100000','count=3000000')
# A PRE rejection skips the native stub that sets CF. Its return flags are
# governed by the existing budget wrapper, not by the skipped stub.
fixtures=fixtures.replace("if h['mode']!=9:assert", "if h['mode']!=9 and self.r(self.stats+12):assert")
exec(compile(fixtures,'test_limits.py:fixtures','exec'))
game=(a.legacy/'k2_runtime_1372_20260904.bin').read_bytes()
names=['human_company_supply','drauga_company_supply','gauri_company_supply','haroun_company_supply']
checks=0
def check(value,msg):
 global checks
 assert value,msg
 checks+=1
class SupplyFixture(Fixture):
 def __init__(self,image,cave):
  super().__init__(image,cave);self.u.mem_map(0x51090000,0x1000);self.w(self.data+4,8);self.w(self.pl+4,1);self.w(image+0x5f9218,2)
  self.u.mem_write(self.df+0x800,(names[0]+'\0').encode('utf-16le'))
 def company(self,index,owner=None,dead=False,name=None):
  at=self.obj+0x10000+index*0x1000;definition=at+0x500;ident=1000+index
  self.w(at,self.image+0x4e5c58);self.w(at+4,definition);self.w(at+8,1 if dead else 0);self.w(at+0x14,ident);self.w(at+0xe8,self.k if owner is None else owner)
  self.w(definition+8,at+0x800);self.u.mem_write(at+0x800,((name or names[index%4])+'\0').encode('utf-16le'));self.w(self.reg+0x20004+ident*4,at)
  return at
for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 for mode in (4,):
  for h in [h for h in meta['wrappers'] if h['mode']==mode]:
   for n in range(5):
    f=SupplyFixture(image,cave)
    for i in range(n):f.company(i)
    ret,_=f.run(h);check(bool(ret&255)==(n<2),('cap',mode,n))
    check(ret&0xffffff00==0xc0ff00,'native upper return bits')
   for case in ['human','disabled','soldier','dead','foreign','recycled','native-refusal']:
    f=SupplyFixture(image,cave);f.company(0);actor=f.company(1)
    if case=='human':f.w(f.pl+4,0)
    if case=='disabled':f.w(f.data+4,0)
    if case=='soldier':f.u.mem_write(f.df+0x800,'supplier\0'.encode('utf-16le'))
    if case=='dead':f.w(actor+8,1)
    if case=='foreign':f.w(actor+0xe8,f.k+16)
    if case=='recycled':f.w(actor+0x14,666)
    ret,_=f.run(h,native=0xc0ff00 if case=='native-refusal' else 0xc0ff01)
    check(bool(ret&255)==(case!='native-refusal'),('exemption',mode,case))
   # Independent city validations in one simulation tick count newly
   # registered companies even before the strategic actor list refreshes.
   f=SupplyFixture(image,cave)
   for i in range(4):
    ret,_=f.run(h);check(bool(ret&255)==(i<2),'same-tick city validation')
    if ret&255:f.company(i)
   f.w(f.obj+0x10000+8,1);check(f.run(h)[0]&255,'loss allows replacement')
 # Final budget rejection must happen before native budget reservations.
 f=SupplyFixture(image,cave);f.company(0);f.company(1)
 h=next(h for h in meta['wrappers'] if h['mode']==5)
 check(f.run(h)[0]&255==1 and f.r(f.stats+12)==0,'no native budget mutation beyond supply cap')
 # Mode 10 is a post-creation observer: never fake failure after creation.
 f=SupplyFixture(image,cave);f.company(0);f.company(1)
 h=next(h for h in meta['wrappers'] if h['mode']==10)
 check(f.run(h)[0]==0xc0ff01,'successful creation return is untouched')
 h=next(h for h in meta['wrappers'] if h['mode']==39)
 f=Fixture(image,cave);f.w(f.data+4,8);f.w(image+0x5f9218,2)
 start,end=0x1e15a6,0x1e15e5;code=bytearray(game[start:end])
 for offset in (0x1e15a8,0x1e15ae,0x1e15b8,0x1e15bd,0x1e15d9):
  struct.pack_into('<I',code,offset-start,(struct.unpack_from('<I',code,offset-start)[0]+image-0x460000)&0xffffffff)
 struct.pack_into('<i',code,h['site']+1-start,cave+h['offset']-image-h['site']-5)
 f.u.mem_write(image+start,bytes(code))
 # Every warning reaches the unchanged six-argument diagnostic logger.
 f.asm(image+0x135740,f'inc dword ptr [{f.stats}];mov eax,[esp+24];mov [{f.stats+32}],eax;mov eax,0xc0ffee;stc;ret')
 f.asm(image+0x29c19a,f'mov eax,[{f.stats+16}];ret')
 f.asm(image+0x2fe35d,f'inc dword ptr [{f.stats+4}];mov eax,[esp+4];mov dword ptr [eax],0x123456;ret')
 f.asm(image+0x1378e2,f'inc dword ptr [{f.stats+8}];ret')
 shown=0
 for index,(now,world,mask,expected) in enumerate([(0,f.world,8,True),(1,f.world,8,False),(30000,f.world,8,False),(299999,f.world,8,False),(300000,f.world,8,True),(300001,f.world,8,False),(600000,f.world,8,True),(10,f.world,8,True),(11,f.world+4,8,True),(12,f.world+4,0,True),(13,f.world+4,0,True)]):
  f.w(f.stats+16,now);f.w(image+0x5f3fb8,world);f.w(f.data+4,mask)
  registers={UC_X86_REG_ESP:f.sp,UC_X86_REG_EBP:0xabcdef01,UC_X86_REG_ESI:0xabcdef02,UC_X86_REG_EDI:59}
  for reg,v in registers.items():f.u.reg_write(reg,v)
  for i in range(8):f.u.reg_write(UC_X86_REG_XMM0+i,0x12340000000000001234+i)
  f.u.emu_start(image+start,image+end,count=100000)
  shown+=int(expected)
  check(f.r(f.stats)==index+1 and f.r(f.stats+32)==59,'full native logging')
  check(f.r(f.stats+4)==shown and f.r(f.stats+8)==shown,'rate limit precedes formatting and UI')
  for reg,v in registers.items():check(f.u.reg_read(reg)==v,('caller stack/nonvolatile',reg))
  for i in range(8):check(f.u.reg_read(UC_X86_REG_XMM0+i)==0x12340000000000001234+i,'SSE preservation')
 # Relocated guard includes the complete native absolute logging pointer.
 guard=bytearray.fromhex(h['guard'])
 for offset in h['guardRelocations']:struct.pack_into('<I',guard,offset,(struct.unpack_from('<I',guard,offset)[0]+image-0x460000)&0xffffffff)
 check(struct.unpack_from('<I',guard,1)[0]==image+0x5f8720,'warning call guard is ASLR safe')
print('AI_SUPPLY_NOTICE_PASS',checks,'checks; native game callees stubbed; original warning caller executed')
