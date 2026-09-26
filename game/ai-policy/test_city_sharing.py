"""Compiled city tribute policy plus original TeamCommand constructor.
Registry, validation and network dispatch are controlled ABI services.
"""
from pathlib import Path
exec(compile(Path(__file__).with_name('test_builder_fleet.py').read_text().split('\nfor image,cave in ')[0],'fleet fixtures','exec'))

class GiftFixture(FleetFixture):
 def __init__(self,image,cave,own=7,ally=2):
  super().__init__(image,cave);self.pulse_setup()
  self.extra=0x52000000;self.u.mem_map(self.extra,0x40000)
  self.other=self.extra;self.w(self.kingdom+0x1f8,0x1234);self.w(self.other+0x1f8,0x1234)
  self.w(self.kingdom+0x14,100);self.w(self.other+0x14,101)
  self.w(self.world+0x150,self.extra+0x800);self.w(self.world+0x154,2)
  self.w(self.extra+0x800,self.kingdom);self.w(self.extra+0x804,self.other)
  self.cities=[]
  for k,count,start in ((self.kingdom,own,0),(self.other,ally,16)):
   arr=self.extra+0x1000+start*0x100;self.w(k+0x2dc,arr);self.w(k+0x2e0,count)
   for i in range(count):
    a=self.extra+0x5000+(start+i)*0x1000;idx=600+start+i
    self.w(arr+4*i,a);self.w(a,image+0x4e5c58);self.w(a+0x14,idx);self.w(a+4,self.centerdef)
    self.w(self.reg+0x20004+4*idx,a);self.w(a+0xe8,k);self.w(a+0x94,a+0x600)
    center=a+0x800;cid=1600+start+i
    self.w(center,image+0x4e5c58);self.w(center+4,self.centerdef);self.w(center+8,0x4200)
    self.w(center+0x14,cid);self.w(self.reg+0x20004+4*cid,center);self.w(center+0xe8,k)
    self.w(a+0x98,a+0x400);self.w(a+0x404,a);self.w(a+0x414,center);self.w(a+0x41c,10-i)
    self.w(center+0x60,a+0x500);self.w(a+0x504,center);self.f(a+0x510,1000)
    if k==self.kingdom:self.cities.append(a)
  self.defs=self.extra+0x3000;self.w(image+0x5f3fb4,self.defs);self.w(self.defs+0x270,self.defs+0x300)
  self.w(self.defs+0x324,self.defs+0x400);self.w(self.defs+0x410,self.defs+0x500)
  # Execute the real constructor, rebasing its two image absolute addresses.
  code=game[0x287201:0x287257]
  for rva in (0x4f8604,0x5f3fb4):code=code.replace(struct.pack('<I',0x460000+rva),struct.pack('<I',image+rva))
  self.u.mem_write(image+0x287201,code)
  self.asm(image+0x287257,'mov eax,[esp+4];mov [ecx+16],eax;ret 4')
  self.w(self.stats+100,1)
  # Native validation requires target actor flag 0x4000: real settlement
  # containers lack it, while their central buildings have it. Keep distinct
  # IDs/objects so targeting the container cannot pass this regression.
  self.asm(image+0x287287,f'cmp dword ptr [ecx+8],{self.kingdom};jne bad;cmp dword ptr [ecx+12],{self.other};jne bad;cmp dword ptr [ecx+4],{self.defs+0x500};jne bad;mov eax,[ecx+16];mov eax,[eax*4+{self.reg+0x20004}];test dword ptr [eax+8],0x4000;jz refuse;mov eax,[{self.stats+100}];ret;refuse:xor eax,eax;ret;bad:ud2')
  self.asm(image+0xb8e65,f'cmp dword ptr [esp+4],0x55667788;jne bad;inc dword ptr [{self.stats+104}];mov eax,[ecx+16];mov [{self.stats+108}],eax;mov eax,[ecx+12];mov [{self.stats+112}],eax;ret 4;bad:ud2')

for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 for case in ('give','difference4','difference3','enemy','no-team','defeated','native-refusal','kingdom','siege','invalid-center','disabled','human-donor','bad-list','all-kingdoms'):
  f=GiftFixture(image,cave,6 if case=='difference4' else 5 if case=='difference3' else 7)
  if case=='enemy':f.w(f.other+0x1f8,0x7777)
  if case=='no-team':f.w(f.kingdom+0x1f8,0)
  if case=='defeated':f.w(f.other+0x1a4,2)
  if case=='native-refusal':f.w(f.stats+100,0)
  if case in ('kingdom','all-kingdoms'):
   definition=f.extra+0x3f000;f.w(definition+8,definition+0x600);f.u.mem_write(definition+0x600,'human_center_sovereign\0'.encode('utf-16le'))
   for city in f.cities if case=='all-kingdoms' else f.cities[-1:]:f.w(f.r(city+0x414)+4,definition)
  if case=='siege':f.w(f.cities[-1]+0x100,0x00100000)
  if case=='invalid-center':f.f(f.cities[-1]+0x510,0)
  if case=='disabled':f.w(f.data+4,0)
  if case=='human-donor':f.w(f.player+4,0)
  if case=='bad-list':f.w(f.other+0x2e0,257)
  before=bytes(f.u.mem_read(f.extra,0x40000));f.pulse(30)
  expected=case in ('give','kingdom','siege')
  check(f.r(f.stats+104)==int(expected),('city transfer eligibility',case))
  check(bytes(f.u.mem_read(f.extra,0x40000))==before,'no direct city/ownership mutations')
  if expected:
   selected=f.cities[-2 if case in ('kingdom','siege') else -1]
   check(f.r(f.stats+108)==f.r(f.r(selected+0x414)+0x14),'least developed city targets its current central building')
   check(f.r(f.stats+108)!=f.r(selected+0x14),'settlement container ID is never sent to GIVE_ACTOR')
   check(f.r(f.stats+112)==f.other,'human ally is eligible without an SAI player')
   f.pulse(34);f.pulse(90);check(f.r(f.stats+104)==1,'pending command not duplicated')
   f.w(selected+0xe8,f.other);f.pulse(94)
   check(f.r(f.stats+104)==1,'fresh city counts prevent over-giving')
 # Native refusal is retried on the next minute, with no persistent owner changes.
 f=GiftFixture(image,cave);f.w(f.stats+100,0);f.pulse(30);f.w(f.stats+100,1);f.pulse(34)
 check(f.r(f.stats+104)==0,'refusal throttle');f.pulse(90);check(f.r(f.stats+104)==1,'refusal eventually retries')

print('AI_CITY_SHARING_PASS',checks,'checks; native command constructor; three ASLR bases')
import hashlib
(a.native/'city-sharing.json').write_text(json.dumps(dict(passed=True,checks=checks,
 relocationBases=3,nativeSha256=hashlib.sha256(raw).hexdigest().upper(),
 distinctCenterActors=True,nativeDispatchStubbed=True,gameLaunched=False),indent=2)+'\n',encoding='utf-8')
