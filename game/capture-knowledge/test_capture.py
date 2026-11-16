"""Compiled callback + original native ownership-only ghost updater.
Native ChangeKingdom is stubbed at its state-changing boundary; this does not
claim to reproduce a player's full match or the visibility race in vivo.
"""
from pathlib import Path
import argparse,sys,struct,json,hashlib
parser=argparse.ArgumentParser();parser.add_argument('--runtime',type=Path,required=True);parser.add_argument('--dll',type=Path,required=True);parser.add_argument('--deps',type=Path,action='append',required=True);parser.add_argument('--report',type=Path,required=True);args=parser.parse_args()
sys.path[:0]=list(map(str,args.deps))
def write(p,value):p.write_text(json.dumps(value,indent=2))
assert hashlib.sha256(args.runtime.read_bytes()).hexdigest()=='b865d8206990c4f055c51de857f0b09b88ab5ee3b6ae74ee5232134001aa591c'

import pefile
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
checks=0;cases=[]
def check(v,why):
 global checks
 assert v,why;checks+=1
class Fixture:
 def __init__(self,dll):
  self.u=Uc(UC_ARCH_X86,UC_MODE_32);self.base=0x460000;self.dll=dll;self.heap=0x30000000;self.stop=self.heap+0x1e0000;self.stack=self.heap+0x1f0000;self.ks=Ks(KS_ARCH_X86,KS_MODE_32);self.native_calls=[]
  self.u.mem_map(self.base,0x700000);self.u.mem_write(self.base,args.runtime.read_bytes());self.u.mem_map(self.heap,0x200000)
  pe=pefile.PE(str(args.dll));b=bytearray(pe.get_memory_mapped_image());self.u.mem_map(dll,(len(b)+4095)&~4095)
  for block in pe.DIRECTORY_ENTRY_BASERELOC:
   for e in block.entries:
    if e.type==3:struct.pack_into('<I',b,e.rva,(struct.unpack_from('<I',b,e.rva)[0]+dll-pe.OPTIONAL_HEADER.ImageBase)&0xffffffff)
  self.u.mem_write(dll,bytes(b));self.exports={x.name.decode():dll+x.address for x in pe.DIRECTORY_ENTRY_EXPORT.symbols};self.imports={}
  for block in pe.DIRECTORY_ENTRY_IMPORT:
   for x in block.imports:
    at=self.heap+0x1d0000+len(self.imports)*16;self.w(dll+x.address-pe.OPTIONAL_HEADER.ImageBase,at);self.imports[at]=x.name.decode()
  self.u.hook_add(UC_HOOK_CODE,self.hook)
  self.a=self.heap+0x1000;self.old=self.heap+0x2000;self.next=self.heap+0x3000;self.third=self.heap+0x4000;self.reg=self.heap+0x10000;self.vt=self.heap+0x8000;self.array=self.heap+0x9000;self.record=self.heap+0xa000;self.other_record=self.heap+0xb000;self.stub=self.heap+0xc000
  self.world=self.heap+0x6000;self.list=self.heap+0x7000;self.w(self.base+0x5f3fb8,self.world);self.w(self.world+0x150,self.list);self.w(self.world+0x154,3);self.w(self.list,self.old);self.w(self.list+4,self.next);self.w(self.list+8,self.third);self.w(self.base+0x5ef72c,self.reg);self.w(self.base+0x5f3fc8,0);self.w(self.a,self.vt);self.w(self.a+0x14,83);self.w(self.reg+0x20004+83*4,self.a);self.w(self.a+0xe8,self.old);self.w(self.a+0x94,1);self.w(self.a+0x58,32);self.w(self.a+0x5c,self.array);self.w(self.vt+0x70,self.base+0x22adbb);self.w(self.base+0x5f95f0,self.heap+0xd000);self.w(self.heap+0xd000+0x108,self.heap+0xe000);self.w(self.heap+0xe000,2);self.w(self.vt+0x8c,self.base+0x23bb57);self.w(self.vt+0x108,self.base+0x22f1f7)
  self.w(self.old+0x194,0);self.w(self.next+0x194,1);self.w(self.third+0x194,2);self.w(self.old+0x234,0x10001);self.w(self.next+0x234,0x20002);self.w(self.third+0x234,0x40004);self.third_record=self.heap+0xf000;self.u.mem_write(self.third_record,bytes(range(56)));self.w(self.third_record+0x14,self.old);self.w(self.array+8,self.third_record)
  self.u.mem_write(self.record,bytes(range(56)));self.w(self.record+0x14,self.old);self.w(self.array,self.record);self.u.mem_write(self.other_record,bytes(range(56)));self.w(self.other_record+0x14,self.old);self.w(self.array+4,self.other_record)
  self.asm(self.stub,'mov eax,[esp+4];mov [ecx+0xe8],eax;mov eax,0x1234abcd;ret 4');self.call('TestBind',[self.base,self.stub])
 def w(self,p,v):self.u.mem_write(p,struct.pack('<I',v&0xffffffff))
 def r(self,p):return struct.unpack('<I',self.u.mem_read(p,4))[0]
 def asm(self,p,s):self.u.mem_write(p,bytes(self.ks.asm(s,p)[0]))
 def hook(self,u,at,size,data):
  if at in (self.base+0x1e062b,self.base+0x1e05d3):
   sp=u.reg_read(UC_X86_REG_ESP);self.native_calls.append((at-self.base,self.r(sp+4),self.r(sp+8)));u.reg_write(UC_X86_REG_EIP,self.r(sp));u.reg_write(UC_X86_REG_ESP,sp+12);return
  if at not in self.imports:return
  name=self.imports[at];sp=u.reg_read(UC_X86_REG_ESP)
  if name=='VirtualQuery':
   out=self.r(sp+8);u.mem_write(out,struct.pack('<7I',self.heap,self.heap,4,0x200000,0x1000,4,0x20000));u.reg_write(UC_X86_REG_EAX,28);ret=16
  else:raise AssertionError('unexpected import '+name)
  u.reg_write(UC_X86_REG_EIP,self.r(sp));u.reg_write(UC_X86_REG_ESP,sp+ret)
 def call(self,name,args):
  self.u.mem_write(self.stack,struct.pack('<'+'I'*(len(args)+1),self.stop,*args));self.u.reg_write(UC_X86_REG_ESP,self.stack);self.u.emu_start(self.exports[name],self.stop,count=100000);check(self.u.reg_read(UC_X86_REG_EIP)==self.stop,'returned');check(self.u.reg_read(UC_X86_REG_ESP)==self.stack+4,'cdecl stack preserved');return self.u.reg_read(UC_X86_REG_EAX)
 def capture(self):return self.call('TestChange',[self.a,self.next])
for dll in (0x10000000,0x14000000,0x20000000):
 # The old all-participant candidate MUST fail this regression.
 f=Fixture(dll);before=bytes(f.u.mem_read(f.third_record,56));check(f.capture()==0x1234abcd,'original result preserved');check(bytes(f.u.mem_read(f.third_record,56))==before,'hidden third player keeps the last observed owner');check(f.r(f.record+0x14)==f.next,'former owner learns own loss even without sight');check(f.r(f.other_record+0x14)==f.next,'new owner learns acquisition even without sight');cases.append(dict(dll=hex(dll),hiddenThirdPreserved=True))
 # Execute ORIGINAL visibility code; the original change then removes sight.
 f=Fixture(dll);f.w(f.a+0x54,0x40000);f.asm(f.stub,'mov eax,[esp+4];mov [ecx+0xe8],eax;mov dword ptr [ecx+0x54],0;mov eax,0x1234abcd;ret 4');before=bytes(f.u.mem_read(f.third_record,56));f.capture();check(f.r(f.third_record+0x14)==f.next,'pre-change viewer learns capture after sight disappears');after=bytes(f.u.mem_read(f.third_record,56));check(after[:20]+after[24:]==before[:20]+before[24:],'only ownership refreshed');cases.append(dict(dll=hex(dll),preChangeVisibility=True))
 f=Fixture(dll);f.asm(f.stub,'mov eax,[esp+4];mov [ecx+0xe8],eax;mov dword ptr [ecx+0x54],0x40000;ret 4');f.capture();check(f.r(f.third_record+0x14)==f.old,'becoming visible after the event is not mistaken for observing it')
 f=Fixture(dll);f.w(f.heap+0xe000,0);f.capture();check(f.r(f.third_record+0x14)==f.next,'no-fog mode informs all native viewers')
 for index in (0,1,15,31):
  f=Fixture(dll);f.w(f.array,0);f.w(f.array+4,0);f.w(f.array+8,0);f.w(f.array+index*4,f.record);f.w(f.old+0x194,index);f.w(f.world+0x154,1);f.capture();check(f.r(f.record+0x14)==f.next,'former-owner index '+str(index));cases.append(dict(dll=hex(dll),formerIndex=index))
 for case in ('unit','observer','invalid-index','missing-record','destroyed','registry-replaced','same-owner','null-new','rejected-change'):
  f=Fixture(dll)
  if case=='unit':f.w(f.a+0x94,0)
  if case=='observer':f.w(f.old+0x198,1)
  if case=='invalid-index':f.w(f.old+0x194,32)
  if case=='missing-record':f.w(f.array,0)
  if case=='destroyed':f.w(f.a+8,1)
  if case=='registry-replaced':f.w(f.reg+0x20004+83*4,0)
  if case=='same-owner':f.next=f.old
  if case=='null-new':f.next=0
  if case=='rejected-change':f.asm(f.stub,'mov eax,0x1234abcd;ret 4')
  before=bytes(f.u.mem_read(f.record,56));f.capture();check(bytes(f.u.mem_read(f.record,56))==before,case+' excluded record unchanged');cases.append(dict(dll=hex(dll),case=case))
 f=Fixture(dll);f.w(f.base+0x5f3fc8,f.heap+0xd800);f.w(f.heap+0xd800+0x2c,1);f.capture();check(f.native_calls==[(0x1e062b,f.record,f.old),(0x1e05d3,f.record,f.old),(0x1e062b,f.other_record,f.next),(0x1e05d3,f.other_record,f.next)],'native AI bookkeeping limited to entitled records')
 f=Fixture(dll);f.capture();f.next=f.third;f.capture();check(f.r(f.record+0x14)==f.heap+0x3000,'first former owner does not learn a later unseen capture');check(f.r(f.other_record+0x14)==f.third and f.r(f.third_record+0x14)==f.third,'current victim and attacker learn the later capture')
 f=Fixture(dll);f.w(f.array+8,0);f.w(f.a+0x54,0x40000);f.capture();check(f.r(f.array+8)==0,'no new ghost records or terrain revelation')
 f=Fixture(dll);f.w(f.a+0x94,0);f.w(f.a+0x98,1);f.capture();check(f.r(f.record+0x14)==f.next,'settlement outer actor covered')
 # The installed runtime extends GetThingByID; never assume its old table layout.
 f=Fixture(dll);full_id=0x12340053;f.w(f.a+0x14,full_id);f.w(f.reg+0x20004+83*4,0);captured=f.heap+0x18000;f.asm(f.base+0x21117,f'mov eax,[esp+4];mov [{captured}],eax;mov eax,{f.a};ret 4');f.capture();check(f.r(captured)==full_id,'complete ID forwarded to native extended registry');check(f.r(f.record+0x14)==f.next,'extended-registry actor receives capture knowledge')
 f=Fixture(dll);f.w(f.reg+4+83*2,1);f.capture();check(f.r(f.record+0x14)==f.old,'native generation mismatch rejects stale actor')
 # Sixteen native vision bits plus all 32 valid ownership-record indices.
 f=Fixture(dll);f.w(f.world+0x154,34)
 for i in range(34):
  k=f.heap+0x80000+i*0x400;g=f.heap+0x90000+i*0x100;f.w(f.list+i*4,k);f.w(k+0x194,i if i<32 else 0xffffffff);f.w(k+0x198,int(i==33));f.w(k+0x234,1<<(16+i)if i<16 else 0)
  if i<32:f.w(f.array+i*4,g);f.u.mem_write(g,bytes(range(56)));f.w(g+0x14,f.old)
 f.w(f.a+0x54,sum(1<<(16+i)for i in range(16)if i%2));f.capture()
 for i in range(32):
  g=f.heap+0x90000+i*0x100;check(f.r(g+0x14)==(f.next if i<16 and i%2 else f.old),('only native visible participants updated',i))
 cases.append(dict(dll=hex(dll),all32Indices=True,nativeVisibilityPredicate=True))
write(args.report,dict(passed=True,checks=checks,cases=cases,nativeGhostUpdater=True,nativeVisibilityPredicate=True));print('CAPTURE_FOG_PASS',checks,'checks',len(cases),'cases')
