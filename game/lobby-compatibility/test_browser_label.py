"""Relocated x86 tests for Steam display-only map label; original map resolver
and engine string/Steam services are mocked, input identity is byte-audited."""
import sys,struct,argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--dll',type=Path,required=True);a=p.parse_args()
sys.path[:0]=[str(a.legacy/'pydeps_readable'),str(a.legacy/'lobby_colors_1372/deps_r15')]
import pefile
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
pe=pefile.PE(str(a.dll));original=pe.OPTIONAL_HEADER.ImageBase;raw=pe.get_memory_mapped_image();exports={s.name.decode().split('@')[0].lstrip('_'):s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols};ks=Ks(KS_ARCH_X86,KS_MODE_32);checks=0
for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(image,0x690000);u.mem_map(cave,(len(raw)+4095)&~4095);u.mem_map(0x51000000,0x20000);u.mem_map(0x61000000,0x10000);u.mem_map(0x62000000,0x1000)
 def w(p,v):u.mem_write(p,struct.pack('<I',v))
 def r(p):return struct.unpack('<I',bytes(u.mem_read(p,4)))[0]
 def wide(p):
  data=bytearray()
  while True:
   ch=bytes(u.mem_read(p,2));p+=2
   if ch==b'\0\0':return data.decode('utf-16le')
   data+=ch
 def put(p,s):u.mem_write(p,s.encode('utf-16le')+b'\0\0');return p
 code=bytearray(raw)
 for block in pe.DIRECTORY_ENTRY_BASERELOC:
  for e in block.entries:
   if e.type==3:struct.pack_into('<I',code,e.rva,(struct.unpack_from('<I',code,e.rva)[0]+cave-original)&0xffffffff)
 u.mem_write(cave,bytes(code));calls=[]
 def stub(at,n,fun):
  u.mem_write(at,bytes(ks.asm('ret '+str(n*4),at)[0]))
  def h(uc,pc,size,unused):
   sp=u.reg_read(UC_X86_REG_ESP);fun(u.reg_read(UC_X86_REG_ECX),[r(sp+4+i*4) for i in range(n)])
  u.hook_add(UC_HOOK_CODE,h,begin=at,end=at)
 def cmp(self,args):u.reg_write(UC_X86_REG_EAX,0 if wide(r(u.reg_read(UC_X86_REG_ESP)+4))==wide(r(u.reg_read(UC_X86_REG_ESP)+8)) else 1)
 stub(0x62000020,0,cmp)
 for module in pe.DIRECTORY_ENTRY_IMPORT:
  for e in module.imports:
   if e.name==b'wcscmp':w(cave+e.address-original,0x62000020)
 def convert(self,args):calls.append(('publish',wide(args[0])));w(self,0x51018000);u.reg_write(UC_X86_REG_EAX,self)
 def resolve(self,args):calls.append(('resolve',tuple(args)));w(self+0x50,put(0x51016000,'Translated map title'))
 def assign(self,args):calls.append(('label',wide(args[0])));w(self,args[0]);u.reg_write(UC_X86_REG_EAX,self)
 stub(image+0x23ee7,1,convert);stub(image+0x77fdc,3,resolve);stub(image+0x214d4,1,assign)
 def call(name,args,self=0,cleanup=0):
  sp=0x6100f000;w(sp,0x62000000)
  for i,arg in enumerate(args):w(sp+4+4*i,arg)
  u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,self);u.reg_write(UC_X86_REG_EDX,0)
  u.emu_start(cave+exports[name],0x62000000,count=100000)
  assert u.reg_read(UC_X86_REG_ESP)==sp+4+cleanup
 call('PawTestImage',[image]);room=0x51000000
 for title in ['Random Map','Saved match.rsg','Карта 123']:
  text=put(room+0x1000,title);before=bytes(u.mem_read(room+0x1000,100));calls.clear();call('PawTestAdvertisedMap',[text],room,4)
  assert calls==[('publish','Paws Launcher')];assert bytes(u.mem_read(room+0x1000,100))==before;checks+=3
 for mode in ['RMC','Map','Save']:
  for label in ['Paws Launcher','Vanilla save','Paws Launcher extra','']:
   u.mem_write(room,bytes(0x100));ptrs=[]
   for off,text in [(0x2000,mode),(0x3000,'real-map-id.rsg'),(0x4000,label)]:w(room+off,put(room+off+16,text));ptrs.append(room+off)
   before=[bytes(u.mem_read(x,128)) for x in ptrs];calls.clear();call('PawTestBrowserMap',ptrs,room,12)
   assert calls[0]==('resolve',tuple(ptrs));assert wide(r(room+0x50))==('Paws Launcher' if label=='Paws Launcher' else 'Translated map title')
   assert [bytes(u.mem_read(x,128)) for x in ptrs]==before;assert not any(bytes(u.mem_read(room,0x50)));checks+=4
print('LOBBY_BROWSER_LABEL_PASS',checks,'checks; three ASLR bases; native map IDs and source labels unchanged')
