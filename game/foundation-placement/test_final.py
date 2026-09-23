"""Run the compiled final-pool planner and both new wrappers in x86.
Definition lookup and the weighted choice boundary are explicit engine stubs.
This tests ABI, classification and writes, not game rendering or multiplayer.
"""
import argparse,json,struct,sys,random
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--native',type=Path,required=True);a=p.parse_args()
sys.path[:0]=[str(a.legacy/'lobby_colors_1372/deps_r15')]
from unicorn import Uc,UcError,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_PROT_READ,UC_PROT_WRITE,UC_PROT_EXEC,UC_ERR_WRITE_PROT
from unicorn.x86_const import *
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
m=json.loads((a.native/'counts.json').read_text());raw=(a.native/'counts.bin').read_bytes();ks=Ks(KS_ARCH_X86,KS_MODE_32);checks=0
def check(ok,why):
 global checks
 checks+=1
 assert ok,why
for image,cave in [(0x460000,0x10000000),(0x18000000,0x38000000)]:
 u=Uc(UC_ARCH_X86,UC_MODE_32)
 for at,n in [(image,0x690000),(cave,m['allocation']),(0x51000000,0x200000),(0x61000000,0x10000)]:u.mem_map(at,n)
 code=bytearray(raw)
 for off,im,cv in m['fixups']:struct.pack_into('<I',code,off,(struct.unpack_from('<I',code,off)[0]+im*(image-m['image'])+cv*(cave-m['cave']))&0xffffffff)
 u.mem_write(cave,bytes(code));data=cave+m['dataOffset'];reg=0x51000000;db=0x51070000;world=0x51080000;sd=0x51090000;fd=0x51091000;other=0x51092000;sp=0x6100e000;done=0x6100fff0
 def w(p,v):u.mem_write(p,struct.pack('<I',v&0xffffffff))
 def r(p):return struct.unpack('<I',u.mem_read(p,4))[0]
 def f(p,v):u.mem_write(p,struct.pack('<f',v))
 def asm(p,s):u.mem_write(p,bytes(ks.asm(s,p)[0]))
 for j,(d,name) in enumerate([(sd,'random_settlement_camps'),(fd,'random_foundation_camps'),(other,'random_enclave_camps')]):
  w(d+8,d+0x700);u.mem_write(d+0x700,(name+'\0').encode('utf-16le'));w(d+0x18,d+0x800);w(d+0x80c,0x23)
 w(image+0x5ef72c,reg);w(image+0x5f3fb8,world);w(image+0x5f3fb4,db);w(db+0xc,db+0x100)
 asm(image+0x2edb9,'ret 4')
 def lookup(uc,at,size,unused):
  s=r(u.reg_read(UC_X86_REG_ESP)+4);text=bytes(u.mem_read(s,100)).decode('utf-16le').split('\0')[0]
  u.reg_write(UC_X86_REG_EAX,sd if text=='random_settlement_camps' else fd)
 u.hook_add(UC_HOOK_CODE,lookup,begin=image+0x2edb9,end=image+0x2edb9)
 def call(name,args):
  w(sp,done)
  for i,v in enumerate(args):w(sp+4+i*4,v)
  u.reg_write(UC_X86_REG_ESP,sp);u.emu_start(cave+m['exports'][name],done,count=20000000)
  check(u.reg_read(UC_X86_REG_ESP)==sp+4,'cdecl stack');return u.reg_read(UC_X86_REG_EAX)
 def setup(points,source_foundations=0):
  u.mem_write(reg,bytes(0x70000));u.mem_write(data,bytes(m['dataSize']));actors=[]
  for i,(x,y) in enumerate(points):
   ptr=0x51100000+i*0x100;id=1000+i;w(reg+0x20004+4*id,ptr);w(ptr+0x14,id);w(ptr+4,fd if i<source_foundations else sd);w(ptr+8,0);f(ptr+0x20,x);f(ptr+0x24,y);actors.append(ptr)
  # Ready-made enclaves and cities are excluded even when in the same registry.
  ptr=0x511f0000;w(reg+0x20004+4*9000,ptr);w(ptr+0x14,9000);w(ptr+4,other);w(ptr+8,0)
  return actors
 # Reproduce log-375: first FinalPlan write faults when the installer makes
 # the entire allocation RX. Then exercise all cases with RX code / RW data.
 setup([(20.,20.),(80.,80.)],1)
 u.mem_protect(cave,m['allocation'],UC_PROT_READ|UC_PROT_EXEC)
 fault=None
 try:call('plan_map',[image,data,1])
 except UcError as error:fault=error
 check(fault is not None and fault.errno==UC_ERR_WRITE_PROT,'old all-RX layout reproduces crash')
 check(u.reg_read(UC_X86_REG_EIP)==cave+0x17f2 and u.reg_read(UC_X86_REG_EAX)==data+4,'same instruction and state field as log-375')
 u.mem_protect(data,m['allocation']-m['dataOffset'],UC_PROT_READ|UC_PROT_WRITE)
 for n in [0,1,2,3,4,5,7,9,16,27,34,36,47,64,101,256]:
  points=[(float((i%16)*45+20),float((i//16)*45+20)) for i in range(n)]
  actors=setup(points,n//3);before=bytes(u.mem_read(reg,0x200000));call('plan_map',[image,data,1])
  check(r(data+8)==n and r(data+12)==(n+2)//5,('placed pool quota',n))
  check(bytes(u.mem_read(reg,0x200000))==before,'engine memory untouched by planner')
  selected=[]
  for ptr in actors:
   original=r(ptr+4)+0x5c0;table=call('select_table',[image,data,ptr,original]);selected.append(table)
   check(call('select_table',[image,data,ptr,original])==original,'consumed ID not reused')
  check(selected.count(fd+0x5c0)==(n+2)//5,'exact final quota')
  check(not r(data+4) and r(data+16)==0,'plan exhausted')
  check(bytes(u.mem_read(reg,0x200000))==before,'selector never edits game data')
  call('plan_map',[image,data,1]);check([r(data+28+i*32+12) for i in range(n)]==[v-0x5c0 for v in selected],'deterministic plan')
  call('plan_map',[image,data,0]);check(r(data+4)==0 and r(data+8)==0,'failed generation resets stale plan')
 actors=setup([(20.,20.),(980.,20.),(20.,980.),(980.,980.),(500.,500.)]*5,9)
 call('plan_map',[image,data,1]);chosen={(r(data+28+i*32+20),r(data+28+i*32+24)) for i in range(25) if r(data+28+i*32+12)==fd}
 check(len(chosen)==5,'foundations cover center and all corners')
 w(image+0x5f3fb8,world+4);check(call('select_table',[image,data,actors[0],fd+0x5c0])==fd+0x5c0,'different world untouched');w(image+0x5f3fb8,world)
 # Wrapper arguments, displaced epilogue, nonvolatile registers and FPU/SSE.
 actors=setup([(20.,20.),(80.,80.),(140.,140.)],0)
 h=m['hooks'][1];ebp=0x6100e800;w(ebp-12,0x12345678);w(sp,0xabcdef01)
 preserved={UC_X86_REG_ESI:0x11112222,UC_X86_REG_EBX:0xaabb0001,UC_X86_REG_EBP:ebp}
 for regid,value in preserved.items():u.reg_write(regid,value)
 u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_EFLAGS,0x246);u.reg_write(UC_X86_REG_XMM3,0x123456789abcdef)
 u.emu_start(cave+h['offset'],image+h['site']+6,count=20000000)
 check(r(data+8)==3,'wrapper passes original BL success');check(u.reg_read(UC_X86_REG_ECX)==0x12345678 and u.reg_read(UC_X86_REG_EDI)==0xabcdef01,'displaced epilogue')
 check(u.reg_read(UC_X86_REG_ESP)==sp+4 and all(u.reg_read(k)==v for k,v in preserved.items()),'planner wrapper ABI')
 check(u.reg_read(UC_X86_REG_XMM3)==0x123456789abcdef and u.reg_read(UC_X86_REG_EFLAGS)==0x246,'planner SSE and flags')
 # Native weighted choice boundary still sees one RNG argument and one call.
 chosen_calls=[];asm(image+0x6f3e1,'mov eax,0x1234abcd; ret 4')
 u.hook_add(UC_HOOK_CODE,lambda uc,at,size,d:chosen_calls.append((u.reg_read(UC_X86_REG_ECX),r(u.reg_read(UC_X86_REG_ESP)+4))),begin=image+0x6f3e1,end=image+0x6f3e1)
 ptr=actors[1];expected=r(data+28+32+12)+0x5c0;w(sp,done);w(sp+4,0xabcdef12)
 u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ESI,ptr);u.reg_write(UC_X86_REG_ECX,sd+0x5c0)
 u.emu_start(cave+m['hooks'][2]['offset'],done,count=20000000)
 check(chosen_calls==[(expected,0xabcdef12)],'one native weighted choice with same RNG');check(u.reg_read(UC_X86_REG_EAX)==0x1234abcd and u.reg_read(UC_X86_REG_ESP)==sp+8,'weighted return ABI')
result=dict(passed=True,checks=checks,bases=2,engineLookupAndWeightedChoiceStub=True,playedMap=False,oldWriteProtectionCrashReproduced=True,codeRX=True,dataRW=True)
(a.native/'final-test-results.json').write_text(json.dumps(result,indent=2));print('FOUNDATION_FINAL_PASS',checks)
