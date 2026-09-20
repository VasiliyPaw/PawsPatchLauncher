"""Execute native control policy with mocked engine orders, in relocated x86."""
import argparse,json,struct,sys
from pathlib import Path
sys.dont_write_bytecode=True
p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--native',type=Path,required=True);a=p.parse_args()
sys.path[:0]=[str(a.legacy/'pydeps_readable'),str(a.legacy/'lobby_colors_1372/deps_r15')]
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
meta=json.loads((a.native/'controls.json').read_text());raw=(a.native/'controls.bin').read_bytes();ks=Ks(KS_ARCH_X86,KS_MODE_32);cases=0
for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
 u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(image,0x690000);u.mem_map(cave,(meta['allocation']+4095)&~4095);u.mem_map(0x51000000,0x40000);u.mem_map(0x61000000,0x10000);u.mem_map(0x62000000,0x1000)
 def w(p,v):u.mem_write(p,struct.pack('<I',v))
 def r(p):return struct.unpack('<I',bytes(u.mem_read(p,4)))[0]
 code=bytearray(raw)
 for off,im,cv in meta['fixups']:struct.pack_into('<I',code,off,(struct.unpack_from('<I',code,off)[0]+im*(image-meta['image'])+cv*(cave-meta['cave']))&0xffffffff)
 u.mem_write(cave,bytes(code));data=cave+meta['dataOffset'];session=0x51000000;conn=session+0x1000;row=session+0x2000;pl=session+0x3000;entry=session+0x4000;race=session+0x5000;faction=session+0x6000;difficulty=session+0x7000;orders=[]
 def stub(rva,argc,handler):
  address=image+rva;u.mem_write(address,bytes(ks.asm('ret '+str(argc*4),address)[0]))
  def hook(uc,at,size,unused):
   sp=u.reg_read(UC_X86_REG_ESP);args=[r(sp+4+i*4) for i in range(argc)];handler(u.reg_read(UC_X86_REG_ECX),args)
  u.hook_add(UC_HOOK_CODE,hook,begin=address,end=address)
 stub(0x1490d5,0,lambda self,args:u.reg_write(UC_X86_REG_EAX,r(conn)))
 stub(0x205de,1,lambda self,args:(w(self,args[0]),u.reg_write(UC_X86_REG_EAX,self)))
 def order(kind,self,args):
  orders.append((kind,self,args[0]))
  if kind==0:w(entry+0x18,race)
 for kind,rva in enumerate([0x1286cd,0x1287c1,0x128871]):stub(rva,1,lambda self,args,k=kind:order(k,self,args))
 def setup():
  u.mem_write(data,bytes(16384));u.mem_write(session,bytes(0x10000));orders.clear()
  w(data,image);w(data+8,0x123456);w(image+0x5f3fe4,session);w(image+0x5f3fec,conn);w(conn,1);w(session+0x60,1);w(session+0x6c,2)
  w(row+0xec,pl);w(row+0xf0,entry);w(row+0xf4,entry+128);w(pl+4,conn);u.mem_write(pl+0xc,b'\x01');w(pl+0x20,17)
  w(race+8,race+256);w(faction+8,faction+256);w(difficulty+8,difficulty+256);w(race+0x4c,1);w(race+0x48,race+512);w(race+512,faction)
  for i,choice in enumerate([race,faction,difficulty]):
   at=data+32+i*36;w(at,data);w(at+4,i);w(at+12,choice);w(at+16,1)
 def tick():
  sp=0x6100f000;w(sp,0x62000000)
  for i,arg in enumerate([image,data,row]):w(sp+4+4*i,arg)
  u.reg_write(UC_X86_REG_ESP,sp);u.emu_start(cave+meta['exports']['row_tick'],0x62000000,count=100000)
 for scenario,expected in [('new bot',3),('custom all',0),('human',0),('remote bot',0),('client',0),('AL host false',0),('saved game',0),('campaign',0),('observer',0),('unbound',0),('only difficulty',1)]:
  setup()
  if scenario=='custom all':
   for i in range(3):w(data+32+i*36+12,0)
  if scenario=='human':u.mem_write(pl+0xc,b'\x00')
  if scenario=='remote bot':w(pl+4,conn+4)
  if scenario=='client':w(conn,0)
  if scenario=='AL host false':w(conn,0x123400)
  if scenario=='saved game':w(session+0x64,2)
  if scenario=='campaign':w(session+0x6c,3)
  if scenario=='observer':w(row+0xf8,5)
  if scenario=='unbound':w(row+0xf0,0)
  if scenario=='only difficulty':w(data+44,0);w(data+80,0)
  tick();assert len(orders)==expected,(scenario,orders);tick();assert len(orders)==expected,'No repeated forcing'
  if expected==3:
   w(data+48,2);tick();assert len(orders)==4 and orders[-1][0]==0,'Only edited property reapplied'
   w(pl+0x20,18);tick();assert len(orders)==7,'New participant inherits all defaults'
  cases+=1
 # Execute every call-site wrapper too: the constructor uses ESI for the
 # menu, while its original callee receives ECX (a temporary string).
 for h in meta['hooks']:
  original_calls=[];probe_calls=[]
  original=image+h['target'];probe=cave+meta['exports'][h['name']]
  u.mem_write(original,bytes(ks.asm('mov eax,0x12345678; mov ecx,0x34567890; mov edx,0x45678901; stc; ret',original)[0]))
  u.mem_write(probe,bytes(ks.asm('mov eax,0xdeadbeef; mov ebx,0xbad; mov ecx,0xbad; mov edx,0xbad; mov esi,0xbad; mov edi,0xbad; pxor xmm0,xmm0; clc; ret',probe)[0]))
  u.ctl_remove_cache(probe,probe+256);u.ctl_remove_cache(original,original+256)
  def observe_original(uc,at,size,unused):original_calls.append(u.reg_read(UC_X86_REG_ECX))
  def observe_probe(uc,at,size,unused):
   sp=u.reg_read(UC_X86_REG_ESP);probe_calls.append([r(sp+4+i*4) for i in range(3)])
  ho=u.hook_add(UC_HOOK_CODE,observe_original,begin=original,end=original)
  hp=u.hook_add(UC_HOOK_CODE,observe_probe,begin=probe,end=probe)
  sp=0x6100f000;w(sp,0x62000000)
  preserved={UC_X86_REG_EBX:0x11111111,UC_X86_REG_ESI:0x22222222,UC_X86_REG_EDI:0x33333333,UC_X86_REG_EBP:0x44444444}
  for reg,value in preserved.items():u.reg_write(reg,value)
  u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,0x55555555);u.reg_write(UC_X86_REG_EFLAGS,0x246)
  u.reg_write(UC_X86_REG_XMM0,0x112233445566778899aabbccddeeff00)
  try:u.emu_start(cave+h['offset'],0x62000000,count=100000)
  except Exception:
   print('WRAPPER_FAILED',h['name'],hex(u.reg_read(UC_X86_REG_EIP)),hex(u.reg_read(UC_X86_REG_ESP)),original_calls,probe_calls);raise
  assert original_calls==[0x55555555],(h['name'],'original self/once',original_calls)
  assert probe_calls==[[image,data,0x22222222 if h['name']=='menu_create' else 0x55555555]],(h['name'],'probe self',probe_calls)
  assert u.reg_read(UC_X86_REG_ESP)==sp+4
  assert u.reg_read(UC_X86_REG_EAX)==0x12345678 and u.reg_read(UC_X86_REG_ECX)==0x34567890 and u.reg_read(UC_X86_REG_EDX)==0x45678901
  assert all(u.reg_read(reg)==value for reg,value in preserved.items())
  assert u.reg_read(UC_X86_REG_EFLAGS)&1 and u.reg_read(UC_X86_REG_XMM0)==0x112233445566778899aabbccddeeff00
  u.hook_del(ho);u.hook_del(hp);cases+=1
print('BOT_LOBBY_NATIVE_PASS',cases,'policy and relocated wrapper ABI cases; native engine mocked')
