"""Execute the actual C#-built payload in an emulator; never start or attach to k2."""
from pathlib import Path
import argparse,hashlib,json,random,struct,sys

p=argparse.ArgumentParser()
p.add_argument('--out',type=Path,required=True)
p.add_argument('--deps',type=Path,required=True)
p.add_argument('--original-ui-payload',type=Path)
args=p.parse_args();sys.path.insert(0,str(args.deps))
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.x86_const import *

checks=0
def check(ok,label):
    global checks
    checks+=1
    if not ok:raise AssertionError(label)
def pack(v):return struct.pack('<I',v&0xffffffff)
constructor=bytes.fromhex('C74108FFFF7F7F8BC1C7410CFFFF7FFFC74110FFFF7F7F66C741140101C741180000803FC6412000C3')
layouts=[(0x460000,0x10000000),(0x80000,0x02ec0000),(0x6a0000,0x19000000)]
saved={UC_X86_REG_EAX:0x12345678,UC_X86_REG_EBX:0x23456789,UC_X86_REG_ECX:0x34567890,
       UC_X86_REG_EDX:0x45678901,UC_X86_REG_ESI:0x56789012,UC_X86_REG_EDI:0x67890123,UC_X86_REG_EBP:0x30009000}
rng=random.Random(1372)
values=[0,0x80000000,0x3f800000,0xbf800000,0x3e800000,0xbe800000,0x7f800000,0xff800000,0x7fc12345,1,0x80000001]+[rng.getrandbits(32) for _ in range(1000)]
terrain_cases=[0,0x80000000,0xbf800000,0x41400000,0x42800000,0x7fc12345,0x7f800000,0xffffffff]
payloads=[]
for index,(image,cave) in enumerate(layouts):
    raw=(args.out/f'payload-{index}.bin').read_bytes()
    check(len(raw)==4096,'payload extent')
    check(raw[47:128]==bytes(81) and raw[141:]==bytes(4096-141),'only two function bodies; no hidden feature payload')
    if index==0 and args.original_ui_payload:
        check(raw[:47]==args.original_ui_payload.read_bytes()[:47],'zero code is exactly the previously verified narrow formatter hook')
    payloads.append({'image':hex(image),'cave':hex(cave),'sha256':hashlib.sha256(raw).hexdigest().upper()})
    u=Uc(UC_ARCH_X86,UC_MODE_32)
    for base,size in [(image,0x700000),(cave,4096),(0x20000000,0x10000),(0x30000000,0x10000)]:u.mem_map(base,size)
    u.mem_write(cave,raw);u.mem_write(image+0x91b4e,constructor)
    writes=[];executed=[]
    def on_write(uc,access,address,size,value,data):writes.append((address,size))
    def on_code(uc,address,size,data):
        executed.append(address)
        if address in (image+0x2bcd9f,image+0x23adb8):u.emu_stop()
    u.hook_add(UC_HOOK_MEM_WRITE,on_write);u.hook_add(UC_HOOK_CODE,on_code)
    sp=0x30008000
    for value in values:
        for consumed,capacity in ((value,0x80000000),(0x80000000,value)):
            for register,v in saved.items():u.reg_write(register,v)
            u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_EFLAGS,0x246)
            u.reg_write(UC_X86_REG_FPCW,0x27f)
            before_fp=(u.reg_read(UC_X86_REG_FPCW),u.reg_read(UC_X86_REG_FPSW))
            arguments=[0x11223344,0x20000100,0x20000200,consumed,capacity,0x20000300]
            u.mem_write(sp,b''.join(pack(x) for x in arguments));writes.clear();executed.clear()
            u.emu_start(cave,0,count=100)
            found=list(struct.unpack('<6I',bytes(u.mem_read(sp,24))))
            expected=[0 if i in (3,4) and x==0x80000000 else x for i,x in enumerate(arguments)]
            check(found==expected,'only exact negative-zero formatter copies change')
            check(all(u.reg_read(r)==v for r,v in saved.items()),'zero hook preserves all registers')
            check(u.reg_read(UC_X86_REG_ESP)==sp and u.reg_read(UC_X86_REG_EFLAGS)==0x246,'zero stack and flags')
            check((u.reg_read(UC_X86_REG_FPCW),u.reg_read(UC_X86_REG_FPSW))==before_fp,'zero FP state')
            check(all(sp-8<=a and a+n<=sp+20 for a,n in writes),'zero cannot write simulation memory')
            check(all(cave<=a<cave+47 or a==image+0x2bcd9f for a in executed),'zero has no added engine or RNG calls')
    descriptor=0x20004000
    for poison in terrain_cases:
        for register,v in saved.items():u.reg_write(register,v)
        u.reg_write(UC_X86_REG_ECX,descriptor);u.reg_write(UC_X86_REG_ESP,sp)
        u.reg_write(UC_X86_REG_EFLAGS,0x246);u.reg_write(UC_X86_REG_FPCW,0x27f)
        before_fp=(u.reg_read(UC_X86_REG_FPCW),u.reg_read(UC_X86_REG_FPSW))
        initial=bytearray(bytes.fromhex('a5')*0x24);struct.pack_into('<I',initial,0x1c,poison)
        u.mem_write(descriptor,bytes(initial));u.mem_write(sp,pack(image+0x23adb8))
        writes.clear();executed.clear();u.emu_start(cave+128,0,count=100)
        expected=bytearray(initial)
        for offset,value in ((8,0x7f7fffff),(12,0xff7fffff),(16,0x7f7fffff),(24,0x3f800000),(28,0xbf800000)):struct.pack_into('<I',expected,offset,value)
        expected[20:22]=b'\x01\x01';expected[32]=0
        check(bytes(u.mem_read(descriptor,0x24))==bytes(expected),'constructor output plus initialized radius only')
        check(u.reg_read(UC_X86_REG_EAX)==descriptor and u.reg_read(UC_X86_REG_ECX)==descriptor,'constructor result and this preserved')
        check(all(u.reg_read(r)==v for r,v in saved.items() if r not in (UC_X86_REG_EAX,UC_X86_REG_ECX)),'terrain other registers')
        check(u.reg_read(UC_X86_REG_ESP)==sp+4 and u.reg_read(UC_X86_REG_EFLAGS)==0x246,'terrain returns once with flags preserved')
        check((u.reg_read(UC_X86_REG_FPCW),u.reg_read(UC_X86_REG_FPSW))==before_fp,'terrain FP state')
        check(all(descriptor<=a and a+n<=descriptor+0x24 or sp-4<=a and a+n<=sp for a,n in writes),'terrain writes restricted to descriptor and return stack')
        check(all(cave+128<=a<cave+141 or image+0x91b4e<=a<image+0x91b4e+len(constructor) or a==image+0x23adb8 for a in executed),'terrain only calls original constructor; no added RNG or other engine call')
report={'passed':True,'checks':checks,'aslrLayouts':len(layouts),'zeroInputsPerLayout':len(values)*2,'terrainPoisonInputsPerLayout':len(terrain_cases),'payloads':payloads,'gameLaunched':False,'nativeWindowsOpened':False,'scope':'actual C#-built x86 payload in Unicorn; no live-game or multiplayer acceptance'}
(args.out/'native-tests.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
