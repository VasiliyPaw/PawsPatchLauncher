"""Final emitted aircraft branch and 90% policy, including high cave addresses."""
from context import *
import importlib.util,struct
os.environ.update(env());sys.path.insert(0,str(REPO/'tools/ExpandedCache'))
spec=importlib.util.spec_from_file_location('emitted',REPO/'tools/ExpandedCache/test_native.py');t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
from unicorn.x86_const import *
meta=read(OUT/'native/payload/payload.json');payload=(OUT/'native/payload/payload.bin').read_bytes();rows=[]
assert len(meta['hooks'])==4 and meta['hooks'][3]['site']==0x213dd0
for image,cave in [(0x460000,0x10000000),(0xca0000,0x41000000),(0x1700000,0xb1000000)]:
 for speed in [0,0x80000000,0x3a83126f,0x3dcccccd,0x3f800000,0x40d00000,0x42480000,0xbdcccccd,0xc0000000,0x7f800000,0xff800000,0x7fc12345]:
  results=[]
  for candidate in [False,True]:
   r=t.Rig(meta,payload,image,cave);u=r.u;u.reg_write(UC_X86_REG_ESI,t.t.HEAP);r.put(t.t.HEAP+0x20,speed);u.reg_write(UC_X86_REG_ESP,t.t.STACK+0x80000);u.reg_write(UC_X86_REG_EFLAGS,0x246)
   regs=[UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_EDI,UC_X86_REG_EBP]
   for i,reg in enumerate(regs):u.reg_write(reg,0x12345000+i)
   bits=struct.unpack('<I',struct.pack('<f',-.0122625))[0];u.reg_write(UC_X86_REG_XMM0,(0x12345678<<96)|bits);u.reg_write(UC_X86_REG_XMM1,0x123456789abcdef)
   before=[u.reg_read(reg)for reg in regs+[UC_X86_REG_ESI,UC_X86_REG_ESP,UC_X86_REG_EFLAGS,UC_X86_REG_XMM1]]
   u.mem_write(image+0x213dd0,bytes.fromhex('f30f594620'));u.emu_start(cave+meta['hooks'][3]['entry']if candidate else image+0x213dd0,image+0x213dd5,count=100)
   assert before==[u.reg_read(reg)for reg in regs+[UC_X86_REG_ESI,UC_X86_REG_ESP,UC_X86_REG_EFLAGS,UC_X86_REG_XMM1]]
   results.append(u.reg_read(UC_X86_REG_XMM0))
  assert results[1]==((0x12345678<<96)|bits)if speed&0x7fffffff==0 else results[0]==results[1]
  rows.append(dict(image=image,cave=cave,speed=hex(speed),native=hex(results[0]),candidate=hex(results[1])))
 r=t.Rig(meta,payload,image,cave);r.setup();r.budget(.9,.6)
 r=t.Rig(meta,payload,image,cave);r.setup();uv=t.t.HEAP+0x60000;r.put(image+0x5f9480,uv);r.put(uv+0x100,uv+0x400);r.put(uv+0x400,50);r.put(image+0x5f3fd4,r.manager-0x9c);r.put(image+0x5f92f4,4)
 r.call(cave+meta['exports']['rc_tick'],(r.state,));assert r.get(uv+0x400)==90
write(OUT/'aircraft-native-tests.json',dict(passed=True,cases=len(rows),rows=rows,ram90Applied=True));print('FINAL_AIRCRAFT_AND_90_PERCENT_NATIVE_PASS',len(rows))
