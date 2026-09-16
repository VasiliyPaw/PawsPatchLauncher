"""Probe stock 1.3.72 Denizen health/count/resupply code, without starting a game.

Only owner lookup and output-map containers are fixtures. The return-health,
count threshold, weighted bar and resupply calculations are original x86.
This establishes possible states, not the cause of the reported live match.
"""
import argparse, hashlib, struct, sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.legacy/'lobby_colors_1372/pydeps_r3'))
sys.path.insert(0,str(a.legacy/'lobby_colors_1372/deps_r15'))
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
from unicorn.x86_const import *
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
raw=(a.legacy/'k2_runtime_1372_20260904.bin').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='b865d8206990c4f055c51de857f0b09b88ab5ee3b6ae74ee5232134001aa591c'
u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(0x460000,0x700000);u.mem_write(0x460000,raw)
u.mem_map(0x30000000,0x200000);ks=Ks(KS_ARCH_X86,KS_MODE_32)
def w(addr,val):u.mem_write(addr,struct.pack('<I',val))
def f(addr,val):u.mem_write(addr,struct.pack('<f',val))
def ri(addr):return struct.unpack('<I',u.mem_read(addr,4))[0]
def rf(addr):return struct.unpack('<f',u.mem_read(addr,4))[0]
def stub(addr,code):u.mem_write(addr,bytes(ks.asm(code,addr)[0]))
component,home,group,data,owner,vt,healthout,countout=[0x30000000+i*0x1000 for i in range(1,9)]
registry=0x30010000
w(0xA4F72C,registry);w(component+4,home);w(component+0x18,group)
w(group+4,data);w(data+0x174,0x121);f(data+0x284,6000);f(data+0x2CC,.01);f(data+0x1E4,100)
w(home,vt);w(vt+0x108,0x30009000);stub(0x30009000,f'mov eax,{owner}; ret')
# Single group: no prior entry in either UI output map. Caller-provided defaults
# stay zero. Insertion returns the corresponding fixture pair (value,total).
stub(0x63B214,'ret 8');stub(0x66C333,'mov eax,ecx; ret 4')
def run(addr,args=()):
    sp=0x301FF000;w(sp,0x30000000)
    for i,value in enumerate(args):w(sp+4+i*4,value)
    u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,component)
    u.reg_write(UC_X86_REG_EBP,0);u.reg_write(UC_X86_REG_FPCW,0x37F)
    u.emu_start(addr,0x30000000,count=100000)
    assert u.reg_read(UC_X86_REG_EIP)==0x30000000
    assert u.reg_read(UC_X86_REG_ESP)==sp+4+4*len(args)
checks=0
for hp,expected in [(0,0),(3000,0),(4800,0),(5999,0),(6000,1)]:
    f(group+8,hp);w(group,0);w(healthout,0);w(healthout+4,0);w(countout,0);w(countout+4,0)
    run(0x66A12E,(healthout,countout))
    assert ri(countout)==expected and ri(countout+4)==1,(hp,ri(countout),ri(countout+4))
    run(0x6690FA)
    assert abs(rf(component+0x10)-hp/6000*100)<.001
    assert rf(component+0x14)==100
    checks+=2
for penalty,delta in [(0,60),(.5,30),(1,0)]:
    f(owner+0x1FC,penalty);f(group+8,4800)
    run(0x66AE2A,(group,struct.unpack('<I',struct.pack('<f',1))[0]))
    assert abs(rf(group+8)-(4800+delta))<.001,(penalty,rf(group+8))
    checks+=1
print(f'PASS {checks} stock x86 probes: partial bar / zero ready count; owner penalty can suppress resupply. Live cause remains unconfirmed.')
