"""Exercise the native hover caller and selector before tooltip formatting.

The enabled-interface query is stubbed; widget selection and parent fallback
execute original x86. This covers the gate missed by layout-only tests.
"""
import argparse, json, struct, sys
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--analysis',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
p.add_argument('--payload',type=Path)
p.add_argument('--fixups',type=Path)
a=p.parse_args()
sys.path.insert(0,str(a.analysis/'lobby_colors_1372/deps_r15'))
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *

root=Path(__file__).resolve().parents[1]/'beta7'
raw=(a.payload or root/'PawCommonUiPayload.bin').read_bytes()
fix=(a.fixups or root/'PawCommonUiFixups.bin').read_bytes()
native=(a.analysis/'k2_runtime_1372_20260904.bin').read_bytes()
checks=0
def check(ok,why):
    global checks
    checks+=1
    assert ok,why

cases=[
    # kind, title, body, parent body, enabled, selected owner
    ('button',True,False,False,True,'child'),
    ('button',True,False,True,True,'child'),
    ('button',True,False,False,False,'none'),
    ('button',False,False,False,True,'none'),
    ('button',False,False,True,True,'parent'),
    ('other',True,False,False,True,'none'),
    ('other',True,False,True,True,'parent'),
    ('other',True,True,True,True,'child'),
    ('other',False,True,False,True,'child'),
    ('other',True,True,False,False,'none'),
]
for image,cave in [(0x460000,0x10000000),(0x80000,0x2ec0000),(0x6a0000,0x19000000)]:
    for kind,title,body,parent_body,enabled,expected in cases:
        u=Uc(UC_ARCH_X86,UC_MODE_32)
        u.mem_map(image,0x700000);u.mem_write(image,native)
        u.mem_map(cave,0x1000);u.mem_map(0x30000000,0x10000)
        def wr(p,v):u.mem_write(p,struct.pack('<I',v&0xffffffff))
        def rd(p):return struct.unpack('<I',u.mem_read(p,4))[0]
        relocated=bytearray(raw)
        for at in range(4,len(fix),12):
            k,off,value=struct.unpack_from('<III',fix,at)
            struct.pack_into('<I',relocated,off,{1:image+value,2:cave+value,3:image+value-(cave+off+4)}[k]&0xffffffff)
        u.mem_write(cave,bytes(relocated))
        child,parent,sp,end=[0x30000000+x for x in (0x1000,0x2000,0x8000,0xf000)]
        def string(at,text):
            data=text.encode('utf-16le')
            wr(at-12,len(text));u.mem_write(at,data+b'\0\0')
            return at
        blank=string(0x30003010,'');name=string(0x30003110,"Paw's Patch");other=string(0x30003210,'native body')
        wr(child,cave+0x200 if kind=='button' else image+0x504be4)
        wr(child+8,parent if parent_body else 0)
        wr(child+0x3c,name if title else blank);wr(child+0x40,other if body else blank)
        wr(parent,image+0x504be4);wr(parent+0x40,other if parent_body else blank)
        before=bytes(u.mem_read(child,0x80)),bytes(u.mem_read(parent,0x80))
        queries=[]
        def hook(u,pc,size,data):
            if pc!=image+0x2b6cba:return
            queries.append(u.reg_read(UC_X86_REG_ECX))
            s=u.reg_read(UC_X86_REG_ESP)
            u.reg_write(UC_X86_REG_EAX,1 if enabled else 0)
            u.reg_write(UC_X86_REG_EIP,rd(s));u.reg_write(UC_X86_REG_ESP,s+4)
        u.hook_add(UC_HOOK_CODE,hook)
        # First prove the released selection path rejects title-only buttons.
        def select(target):
            u.mem_write(image+0x2bfa43,b'\xe8'+struct.pack('<i',target-(image+0x2bfa48)))
            u.ctl_remove_cache(image+0x2bfa43,image+0x2bfa5c)
            u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,child)
            u.reg_write(UC_X86_REG_EDI,0);u.reg_write(UC_X86_REG_EBP,0xabcdef01)
            u.reg_write(UC_X86_REG_EBX,0x12345678);u.reg_write(UC_X86_REG_ESI,0x87654321)
            u.emu_start(image+0x2bfa43,image+0x2bfa5c,count=200)
            check(u.reg_read(UC_X86_REG_EIP)==image+0x2bfa5c,'hover call completed')
            check(u.reg_read(UC_X86_REG_ESP)==sp,'hover call stack unchanged')
            check([u.reg_read(r) for r in (UC_X86_REG_EBP,UC_X86_REG_EBX,UC_X86_REG_ESI)]==[0xabcdef01,0x12345678,0x87654321],'nonvolatile registers retained')
            return u.reg_read(UC_X86_REG_EDI)
        original=select(image+0x2b6ec8)
        if kind=='button' and title and not body and not parent_body:
            check(original==0,'released empty-body gate reproduces missing tooltip')
        selected=select(cave+0xb00 if any(raw[0xb00:0xc00]) else image+0x2b6ec8)
        check(selected=={'child':child,'parent':parent,'none':0}[expected],f'title-only button hover reaches the tooltip formatter: {kind,title,body,parent_body,enabled,hex(image)}, selected={hex(selected)}, expected={expected}, queries={queries}')
        if kind!='button' or not title or not enabled:
            check(selected==original,'all other hover selection stays native')
        check((bytes(u.mem_read(child,0x80)),bytes(u.mem_read(parent,0x80)))==before,'no title/body or parent mutation')
        if kind=='button' and title and enabled:
            check(queries[-1]==child,'native enabled check still runs for button')

a.out.mkdir(parents=True,exist_ok=True)
(a.out/'tooltip-hover-tests.json').write_text(json.dumps(dict(passed=True,checks=checks,originalNativeHoverCaller=True,originalNativeParentSelector=True,enabledQueryStubbed=True,gameLaunched=False),indent=2))
print('BUTTON_HOVER_SELECTION_PASS',checks)
