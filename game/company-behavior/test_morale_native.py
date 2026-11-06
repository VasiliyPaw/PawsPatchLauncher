"""Execute native morale classification and damage with the actual emitted r2 shim."""
import argparse,sys,struct,json,subprocess,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
sys.path[:0]=[str(a.legacy/'lobby_colors_1372/deps_r15'),str(a.legacy/'pydeps_readable')]
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.x86_const import *
raw=(a.legacy/'k2_runtime_1372_20260904.bin').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='b865d8206990c4f055c51de857f0b09b88ab5ee3b6ae74ee5232134001aa591c'
DECISION=0x2147ec;DAMAGE=0x2157f4;OBJ=0x30000000;ORG=OBJ+0x1000;AI=OBJ+0x2000;WORLD=OBJ+0x3000;STACK=0x70000000;END=STACK+0xf000
checks=0
def check(value,detail):
 global checks
 checks+=1
 if not value:raise AssertionError(detail)
regs=[UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP,UC_X86_REG_ESP,UC_X86_REG_EFLAGS]+[UC_X86_REG_XMM0+i for i in range(8)]+[UC_X86_REG_FPCW,UC_X86_REG_MXCSR]
def make(image,cave,patched,cur,maximum,threshold,query=False,option=''):
 u=Uc(UC_ARCH_X86,UC_MODE_32)
 for at,n in [(image,0x700000),(cave,4096),(OBJ,0x5000),(STACK,0x10000)]:u.mem_map(at,n)
 def put(at,n):u.mem_write(at,struct.pack('<I',n&0xffffffff))
 def fp(at,n):u.mem_write(at,struct.pack('<f',n))
 u.mem_write(image+DECISION,raw[DECISION:DECISION+78])
 if patched:
  u.mem_write(cave,(a.out/'morale.decision').read_bytes());u.mem_write(image+DECISION,(a.out/'morale.decision-jump').read_bytes())
 put(ORG+4,OBJ);put(OBJ+0x70,AI if option!='no-ai' else 0);put(OBJ+0x7c,ORG)
 put(AI,image+0x500000);put(image+0x50005c,image+0x1000)
 u.mem_write(image+0x1000,b'\xb0'+bytes([int(query)])+b'\xc3')
 if option=='command28':put(AI+0x28,1)
 if option=='command2c':put(AI+0x2c,1)
 fp(ORG+0x5c,cur);fp(ORG+0x60,maximum);fp(ORG+0xb8,threshold)
 for i,reg in enumerate(regs):u.reg_write(reg,0x11111111+i*0x01010101)
 u.reg_write(UC_X86_REG_ECX,ORG);u.reg_write(UC_X86_REG_ESP,STACK+0x8000);put(STACK+0x8000,END)
 u.reg_write(UC_X86_REG_EFLAGS,0x246);u.reg_write(UC_X86_REG_FPCW,0x37f);u.reg_write(UC_X86_REG_MXCSR,0x1f80)
 return u,put,fp

decisions=0;damage_rows=[];recovery_rows=[]
for image,cave in [(0x460000,0x60000000),(0xf20000,0x51000000),(0x18000000,0x28000000)]:
 subprocess.run([str(a.out/'ExhaustionTests.exe'),str(a.out/'morale'),f'{image:x}',f'{cave:x}'],check=True)
 cases=[]
 for threshold in (8,16,20,25,40,48):
  for maximum in (16,134):
   for cur in (0.,-0.,0.527,threshold-0.125,threshold,threshold+0.125,maximum):
    for query in (False,True):
     for option in ('','command28','command2c'):cases.append((cur,maximum,threshold,query,option))
 cases += [(0,134,20,False,'no-ai'),(0,0,20,False,'no-ai'),(0,-1,20,False,''),(float('nan'),134,20,False,''),(float('inf'),134,20,False,'')]
 for case in cases:
  outputs=[]
  for patched in (False,True):
   u,put,fp=make(image,cave,patched,*case);before=bytes(u.mem_read(OBJ,0x5000));calls=[]
   u.hook_add(UC_HOOK_CODE,lambda uc,ip,size,data:calls.append(ip) if ip==image+DECISION+8 else None)
   u.emu_start(image+DECISION,END,count=200)
   check(u.reg_read(UC_X86_REG_EIP)==END,('return',image,case,patched))
   check(u.reg_read(UC_X86_REG_ESP)==STACK+0x8004,('stack',case,patched))
   check(bytes(u.mem_read(OBJ,0x5000))==before,('object write',case,patched))
   check(len(calls)==1,('native decision count',case,patched))
   outputs.append([u.reg_read(reg) for reg in regs])
  original,changed=outputs
  check(changed[0]==(1 if original[0]==0 else original[0]),('classification',case,original[0],changed[0]))
  check(changed[1:]==original[1:],('registers flags or FPU changed',case))
  decisions+=1
 # Native TakeMoraleDamage: preserve ordinary racial low-morale routing and
 # morale subtraction, but never reissue depleted routing/flags at zero.
 for threshold,cur,loss in [(20,21,2),(16,17,2),(40,41,2),(8,9,2),(25,26,2),(48,49,2),(20,10,1),(20,1,2),(20,0,.25)]:
  paired=[]
  for patched in (False,True):
   u,put,fp=make(image,cave,patched,cur,134,threshold)
   body=bytearray(raw[DAMAGE:DAMAGE+0xd2]);struct.pack_into('<I',body,1,image+0x5f3fb8);u.mem_write(image+DAMAGE,bytes(body));put(image+0x5f3fb8,WORLD)
   put(STACK+0x8008,0);fp(STACK+0x8004,loss)
   calls=[]
   def extern(uc,ip,size,data):
    kinds={0x228a2b:('dead',0,0),0x2277b6:('definition',0,0),0x277828:('depleted_route',1,0),0x2777b0:('low_morale_route',1,0),0x2287b3:('event',0,8)}
    if ip-image not in kinds:return
    kind,result,cleanup=kinds[ip-image];sp=uc.reg_read(UC_X86_REG_ESP);ret=struct.unpack('<I',uc.mem_read(sp,4))[0]
    if kind not in ('dead','definition'):calls.append(kind)
    uc.reg_write(UC_X86_REG_EAX,result);uc.reg_write(UC_X86_REG_ESP,sp+4+cleanup);uc.reg_write(UC_X86_REG_EIP,ret)
   u.hook_add(UC_HOOK_CODE,extern);u.emu_start(image+DAMAGE,END,count=1000)
   check(u.reg_read(UC_X86_REG_EIP)==END,('damage return',threshold,cur,patched))
   check(u.reg_read(UC_X86_REG_ESP)==STACK+0x800c,('damage cleanup',threshold,cur,patched))
   morale=struct.unpack('<f',u.mem_read(ORG+0x5c,4))[0];check(morale==max(0,cur-loss),('native morale subtraction',morale))
   paired.append(calls)
  if cur>threshold:check(paired[0]==paired[1]==['low_morale_route'],('racial retreat changed',threshold,paired))
  elif cur>loss:check(paired[0]==paired[1],('positive low morale changed',paired))
  else:check('depleted_route' not in paired[1] and 'event' not in paired[1],('zero-depleted reaction remains',paired))
  damage_rows.append(dict(image=hex(image),threshold=threshold,before=cur,loss=loss,native_calls=paired[0],candidate_calls=paired[1]))
 # Native AddMorale must be able to clear the depleted actor flag even when
 # the company is still in Rout below its racial recovery threshold.
 for query in (False,True):
  for cur,maximum,gain in [(0,134,0.125),(0.527,134,0.125),(15.9,16,0.125),(19.9,134,0.125),(134,134,1)]:
   paired=[]
   for patched in (False,True):
    u,put,fp=make(image,cave,patched,cur,maximum,20,query)
    u.mem_write(image+0x2157b9,raw[0x2157b9:0x2157f4]);fp(STACK+0x8004,gain);events=[]
    def event(uc,ip,size,data):
     if ip!=image+0x2287b3:return
     sp=uc.reg_read(UC_X86_REG_ESP);ret=struct.unpack('<I',uc.mem_read(sp,4))[0]
     events.append(struct.unpack('<II',uc.mem_read(sp+4,8)))
     uc.reg_write(UC_X86_REG_ESP,sp+12);uc.reg_write(UC_X86_REG_EIP,ret)
    u.hook_add(UC_HOOK_CODE,event);u.emu_start(image+0x2157b9,END,count=500)
    check(u.reg_read(UC_X86_REG_EIP)==END and u.reg_read(UC_X86_REG_ESP)==STACK+0x8008,('AddMorale ABI',patched,cur))
    value=struct.unpack('<f',u.mem_read(ORG+0x5c,4))[0]
    expected=min(maximum,struct.unpack('<f',struct.pack('<f',struct.unpack('<f',struct.pack('<f',cur))[0]+gain))[0])
    check(value==expected,('native AddMorale amount',cur,value,expected))
    if patched:check(events==[(5,0)],('depleted flag not cleared',cur,query,events))
    paired.append(events)
   recovery_rows.append(dict(image=hex(image),before=cur,maximum=maximum,query=query,native_events=paired[0],candidate_events=paired[1]))
report=dict(passed=True,checks=checks,decision_cases=decisions,native_damage_cases=len(damage_rows),image_bases=3,
 native_decision_called_once=True,native_thresholds_preserved=True,registers_flags_fpu_preserved=True,
 morale_values_not_forced=True,native_recovery_cases=len(recovery_rows),limitations='Routing transition and actor-flag callbacks are modeled; full live reproduction is separate.',damage_cases=damage_rows,recovery_cases=recovery_rows)
(a.out/'morale-native-results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('MORALE_NATIVE_PASS',checks,'checks;',decisions,'classifications;',len(damage_rows),'native damage cases;',len(recovery_rows),'native recovery cases')
