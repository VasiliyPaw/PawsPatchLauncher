"""Run actual native hooks/counters and HP transfer in Unicorn. No game launched."""
import argparse,hashlib,json,struct,sys,itertools
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--native',type=Path,required=True);a=p.parse_args()
sys.path[:0]=[str(a.legacy/'lobby_colors_1372/pydeps_r3'),str(a.legacy/'lobby_colors_1372/deps_r15'),str(a.legacy/'pydeps_readable')]
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
from capstone import Cs,CS_ARCH_X86,CS_MODE_32,CS_OP_MEM,CS_OP_IMM
raw=(a.legacy/'k2_runtime_1372_20260904.bin').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='b865d8206990c4f055c51de857f0b09b88ab5ee3b6ae74ee5232134001aa591c'
code=(a.native/'lair_recovery.bin').read_bytes();meta=json.loads((a.native/'lair_recovery.json').read_text())
ks=Ks(KS_ARCH_X86,KS_MODE_32);md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
checks=0;results=[]
def check(ok,label):
 global checks
 checks+=1
 assert ok,label
for image,cave in [(0x460000,0x10000000),(0xe40000,0x21000000),(0x12000000,0x60000000)]:
 u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(image,0x700000);u.mem_write(image,raw)
 u.mem_map(cave,0x10000);u.mem_map(0x30000000,0x300000)
 def w(p,x):u.mem_write(p,struct.pack('<I',x&0xffffffff))
 def f(p,x):u.mem_write(p,struct.pack('<f',x))
 def ri(p):return struct.unpack('<I',u.mem_read(p,4))[0]
 def rf(p):return struct.unpack('<f',u.mem_read(p,4))[0]
 def stub(p,s):
  blob=bytes(ks.asm(s,p)[0]);u.mem_write(p,blob);u.ctl_remove_cache(p,p+len(blob))
 # Rebase only reachable stock routines' absolute globals. Native relative
 # calls remain correct when the whole stock image moves by the same delta.
 for lo,hi in [(0x8F970,0x8F9A0),(0x208586,0x2085C9),(0x20A12E,0x20A36C),
               (0x20B3E4,0x20B4A8),(0x20BF9C,0x20BFE0),(0x20AE2A,0x20AF06)]:
  block=bytearray(raw[lo:hi])
  for ins in md.disasm(block,0x460000+lo):
   for op in ins.operands:
    if op.type==CS_OP_MEM and not op.mem.base and not op.mem.index and 0x460000<=op.mem.disp<0xaf0000:
     struct.pack_into('<I',block,ins.address-0x460000-lo+ins.disp_offset,op.mem.disp+image-0x460000)
  u.mem_write(image+lo,bytes(block))
 b=bytearray(code)
 for off,im,cv in meta['fixups']:
  v=struct.unpack_from('<I',b,off)[0]+(image-meta['image'] if im else 0)-(cave-meta['cave'] if cv else 0)
  struct.pack_into('<I',b,off,v&0xffffffff)
 u.mem_write(cave,bytes(b))
 for site,old,off in meta['sites']:
  u.mem_write(image+site,bytes(ks.asm(f'jmp {cave+off}',image+site)[0])+b'\x90'*(len(bytes.fromhex(old))-5))
 component,home,lair,group,data,actor,body,healthout,countout=[0x30001000+i*0x1000 for i in range(9)]
 registry=0x30020000;w(image+0x5ef72c,registry)
 owner,vt,owner_stub=0x30011000,0x30012000,0x30013000
 w(home,vt);w(vt+0x108,owner_stub);stub(owner_stub,f'mov eax,{owner}; ret')
 w(component+4,home);w(home+0x88,component);w(component+0x18,group)
 w(lair,image+0x4e17ac);w(lair+4,home);w(group+4,data)
 w(data+0x174,0x800121);f(data+0x284,6000);f(data+0x2cc,.01)
 w(actor+0x60,body);w(actor+0x14,12345);f(body+0x14,6000)
 # Only empty UI map lookup/insert are fixtures; all HP/counter math is native.
 stub(image+0x1db214,'ret 8');stub(image+0x20c333,'mov eax,ecx; ret 4')
 sp=0x302ff000;frame=0x302fe000;ret=0x30000000
 execution_end=[ret]
 def stop_before_instruction(machine,address,size,user_data):
  if address==execution_end[0]:machine.emu_stop()
 u.hook_add(UC_HOOK_CODE,stop_before_instruction)
 def run(addr,args=(),ecx=component):
  w(sp,ret)
  for i,val in enumerate(args):w(sp+4+i*4,val)
  for reg,val in [(UC_X86_REG_ESP,sp),(UC_X86_REG_ECX,ecx),(UC_X86_REG_EBP,frame),(UC_X86_REG_FPCW,0x37f)]:u.reg_write(reg,val)
  execution_end[0]=ret
  try:u.emu_start(addr,0,count=50000)
  except Exception:
   print('FAILED',hex(image),hex(addr),'lair',is_lair,'hp',hp,'eip',hex(u.reg_read(UC_X86_REG_EIP)),'esp',hex(u.reg_read(UC_X86_REG_ESP)))
   raise
  check(u.reg_read(UC_X86_REG_EIP)==ret,'routine returned')
  check(u.reg_read(UC_X86_REG_ESP)==sp+4+len(args)*4,'stack balanced')
 def segment(start,end,registers):
  for reg,val in registers.items():u.reg_write(reg,val)
  u.reg_write(UC_X86_REG_FPCW,0x37f)
  execution_end[0]=end
  try:u.emu_start(start,0,count=50000)
  except Exception:
   print('FAILED SEGMENT',hex(start),hex(end),'eip',hex(u.reg_read(UC_X86_REG_EIP)), 'esi',hex(u.reg_read(UC_X86_REG_ESI)),'edi',hex(u.reg_read(UC_X86_REG_EDI)))
   raise
  check(u.reg_read(UC_X86_REG_EIP)==end,'hook reached native continuation')
 for is_lair in (False,True):
  w(home+0xc4,lair if is_lair else 0)
  for hp,marker in itertools.product([0,1,51,3000,3560.6,5944,5999,6000],[0,0x4c53,0xcdcd]):
   f(group+8,hp);w(group,0);w(group+0xc,marker<<16)
   # Original readiness predicate supplied in AL, just as native compare does.
   regs={UC_X86_REG_ESP:sp,UC_X86_REG_EBP:frame,UC_X86_REG_EDI:group,
         UC_X86_REG_EAX:0x12345600+(hp>=6000),UC_X86_REG_ECX:0x11111111,UC_X86_REG_EDX:0x22222222,UC_X86_REG_ESI:0x33333333}
   w(frame-0x20,component)
   segment(image+0x20b5c0,image+(0x20b628 if is_lair else 0x20b5c5),regs)
   expected=int(hp>=6000 or (marker==0x4c53 and hp>0)) if is_lair else int(hp>=6000)
   check(u.reg_read(UC_X86_REG_EAX)==0x12345600+expected,'wounded readiness')
   check(u.reg_read(UC_X86_REG_ECX)==0x11111111 and u.reg_read(UC_X86_REG_EDX)==0x22222222,'ready preserves registers')
   check(u.reg_read(UC_X86_REG_ESP)==sp,'ready preserves stack')
   check(u.reg_read(UC_X86_REG_ESI)==0x33333333,'ready preserves ESI')
   w(healthout,0);w(healthout+4,0);w(countout,0);w(countout+4,0)
   run(image+0x20a12e,(healthout,countout))
   check(ri(countout)==expected and ri(countout+4)==1,'UI count agrees with deployment')
   check(abs(rf(healthout)-hp)<.01,'UI HP unchanged')
   run(image+0x20b3e4,(data,))
   check(u.reg_read(UC_X86_REG_EAX)==expected,'individual defender count')
   run(image+0x20b446,(data,))
   chooser_expected=expected if is_lair else int(hp>0)
   check(u.reg_read(UC_X86_REG_EAX)==(group if chooser_expected else 0),'individual chooser agrees with readiness')
  for hp,maxhp in [(51,6000),(5944,6000),(3560.6,3600),(3000,9000),(6001,6000)]:
   f(group+8,hp);f(body+0x14,maxhp);f(body+0x10,maxhp);w(group+0xc,0x4c530000)
   expected=min(hp/6000*maxhp,maxhp) if is_lair else maxhp
   regs={UC_X86_REG_ESP:sp,UC_X86_REG_EBP:frame,UC_X86_REG_ECX:actor,UC_X86_REG_EDX:group}
   segment(image+0x20b981,image+0x20b987,regs)
   check(abs(rf(body+0x10)-expected)<.002,'org deploy preserves HP fraction')
   check(u.reg_read(UC_X86_REG_EDX)==group and u.reg_read(UC_X86_REG_ECX)==actor,'carry preserves pointers')
   check(u.reg_read(UC_X86_REG_ESP)==sp,'carry stack')
   check(ri(group+0xc)==(0 if is_lair else 0x4c530000),'deploy clears survivor marker only for lairs')
   f(body+0x10,maxhp)
   regs={UC_X86_REG_ESP:sp,UC_X86_REG_EBP:frame,UC_X86_REG_ESI:actor,UC_X86_REG_EDI:component,UC_X86_REG_ECX:group,UC_X86_REG_EDX:0x1111}
   segment(image+0x20bc9b,image+0x20bca0,regs)
   check(abs(rf(body+0x10)-expected)<.002,'individual deploy preserves HP fraction')
   check(ri(group)==12345,'native deployment ID store replayed')
  w(group,0);f(data+0x284,6000)
 # All zero / missing / foreign component identities retain stock readiness.
 for field,value in [('vtable',image+0x4e0434),('home',home+4),('denizen',component+4)]:
  w(home+0xc4,lair);w(lair,image+0x4e17ac);w(lair+4,home);w(home+0x88,component)
  w({'vtable':lair,'home':lair+4,'denizen':home+0x88}[field],value)
  f(group+8,5944)
  regs={UC_X86_REG_ESP:sp,UC_X86_REG_EBP:frame,UC_X86_REG_EDI:group,UC_X86_REG_EAX:0,UC_X86_REG_ECX:1,UC_X86_REG_EDX:2}
  segment(image+0x20b5c0,image+0x20b5c5,regs)
  check((u.reg_read(UC_X86_REG_EAX)&255)==0,'scope rejects foreign component')
 # Full sequence using the real native ID-matched return/death and resupply
 # routines. No fake health reset is used to demonstrate regeneration.
 w(home+0xc4,lair);w(lair,image+0x4e17ac);w(lair+4,home);w(home+0x88,component)
 is_lair=True;hp=5944
 w(registry+4+12345*2,0);w(registry+0x20004+12345*4,actor)
 w(group,12345);f(group+8,6000);w(group+0xc,0)
 f(body+0x10,5944);f(body+0x14,6000)
 run(image+0x20a28c,(actor,))
 check(ri(group)==0 and abs(rf(group+8)-5944)<.002,'living return retains wounded HP')
 check(ri(group+0xc)==0x4c530000,'real living return records provenance')
 run(image+0x20b3e4,(data,));check(u.reg_read(UC_X86_REG_EAX)==1,'wounded survivor can deploy immediately')
 f(body+0x10,6000)
 segment(image+0x20b981,image+0x20b987,{UC_X86_REG_ESP:sp,UC_X86_REG_EBP:frame,UC_X86_REG_ECX:actor,UC_X86_REG_EDX:group})
 check(abs(rf(body+0x10)-5944)<.002 and ri(group+0xc)==0,'redeployment retains wounds and clears survivor provenance')
 w(group,12345);w(group+0xc,0x4c530000) # Death must clear even a stale mark.
 run(image+0x20bf9c,(actor,))
 check(ri(group)==0 and rf(group+8)==0 and ri(group+0xc)==0,'real death clears ID, HP and survivor state')
 f(owner+0x1fc,0)
 w(group+0xc,0x4c530000) # A separate engine reset must not leave stale readiness.
 for seconds,expectedhp,ready in [(1,60,0),(98,5940,0),(1,6000,1)]:
  run(image+0x20ae2a,(group,struct.unpack('<I',struct.pack('<f',seconds))[0]))
  check(abs(rf(group+8)-expectedhp)<.02,'native regeneration retains original rate')
  check(ri(group+0xc)==0,'regeneration from zero revokes stale survivor mark')
  run(image+0x20b3e4,(data,));check(u.reg_read(UC_X86_REG_EAX)==ready,'dead unit must finish ALL regeneration')
  run(image+0x20b446,(data,));check(u.reg_read(UC_X86_REG_EAX)==(group if ready else 0),'dead unit cannot bypass counter via chooser')
  w(healthout,0);w(healthout+4,0);w(countout,0);w(countout+4,0)
  run(image+0x20a12e,(healthout,countout));check(ri(countout)==ready,'UI follows dead regeneration gate')
 # A high-HP dead replacement must not be chosen over a wounded survivor.
 other=0x30015000
 w(other,0);w(other+4,data);f(other+8,5999);w(other+0xc,0);w(other+0x10,0)
 f(group+8,500);w(group+0xc,0x4c530000);w(group+0x10,other)
 run(image+0x20b3e4,(data,));check(u.reg_read(UC_X86_REG_EAX)==1,'mixed dead/survivor count')
 run(image+0x20b446,(data,));check(u.reg_read(UC_X86_REG_EAX)==group,'wounded survivor wins over nearly regenerated dead')
 f(other+8,6000)
 run(image+0x20b446,(data,));check(u.reg_read(UC_X86_REG_EAX)==other,'fully regenerated defender returns to native full-first order')
 w(group+0x10,0)
 # No uninitialized/reused padding can grant living status.
 w(group+0xc,0x4c530101)
 segment(image+0x20c3ff,image+0x20c407,{UC_X86_REG_ESP:sp,UC_X86_REG_EDX:group,UC_X86_REG_ECX:0})
 check(ri(group+0xc)==0,'default allocation clears stale provenance')
 w(other+0xc,0x4c530101);w(sp,0x12345678)
 segment(image+0x20c508,image+0x20c50d,{UC_X86_REG_ESP:sp,UC_X86_REG_EAX:group,UC_X86_REG_ESI:other,UC_X86_REG_EDI:group})
 check(ri(group+0xc)==0x101,'copied stack padding never creates a survivor')
 check(u.reg_read(UC_X86_REG_EDI)==0x12345678 and u.reg_read(UC_X86_REG_ESP)==sp+4,'copy epilogue preserved')
 # Loading never mistakes an old save's partial regeneration for a survivor.
 w(group+0xc,0x4c530101);f(healthout,5944)
 stub(ret+0x100,f'fld dword ptr [{healthout}]; jmp {image+0x20aa77}')
 segment(ret+0x100,image+0x20aa7d,{UC_X86_REG_ESP:sp,UC_X86_REG_ESI:group})
 check(abs(rf(group+8)-5944)<.002 and ri(group+0xc)==0x101,'load retains health and clears unknown survivor state')
 run(image+0x20b3e4,(data,));check(u.reg_read(UC_X86_REG_EAX)==0,'partial old-save HP conservatively waits for full recovery')
 # Additional actual return stores and native group transfer carry provenance.
 for site,end,reg in [(0x20a328,0x20a360,UC_X86_REG_EDI),(0x20c0dc,0x20c0cb,UC_X86_REG_ESI)]:
  for value,expectedmarker in [(0,0),(3500,0x4c530000)]:
   f(healthout,value);w(group+0xc,0)
   stub(ret+0x100,f'fld dword ptr [{healthout}]; jmp {image+site}')
   segment(ret+0x100,image+end,{UC_X86_REG_ESP:sp,reg:group})
   check(rf(group+8)==value and ri(group+0xc)==expectedmarker,'return mark requires positive HP')
 f(healthout,3500);w(group+0xc,0)
 stub(ret+0x100,f'movss xmm0,[{healthout}]; jmp {image+0x20c065}')
 segment(ret+0x100,image+0x20c06a,{UC_X86_REG_ESP:sp,UC_X86_REG_EDI:group})
 check(rf(group+8)==3500 and ri(group+0xc)==0x4c530000,'pooled living return records provenance')
 segment(image+0x20c25f,image+0x20c265,{UC_X86_REG_ESP:sp,UC_X86_REG_ESI:group,UC_X86_REG_EAX:other})
 check(rf(other+8)==3500 and ri(other+0xc)==0x4c530101 and ri(group+0xc)==0,'native transfer moves marker without changing HP')
 results.append({'image':hex(image),'cave':hex(cave)})
print(f'PASS {checks} native checks: real living return/death/regeneration, dead-vs-wounded selection, HP transfer, UI agreement, load/allocation safety, city isolation, three ASLR layouts.')
(a.native/'test-results.json').write_text(json.dumps({'checks':checks,'layouts':results,'gameLaunched':False},indent=2))
