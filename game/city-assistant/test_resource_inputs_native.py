"""Run emitted input machine code at three ASLR bases, no live game/desktop I/O."""
import argparse, struct, sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--native',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.legacy.parent/'lobby_colors_1372/deps_r15'))
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
checks=0
def check(ok,label):
    global checks
    assert ok,label
    checks+=1

for game,cave in [(0x460000,0x10000000),(0x650000,0x21000000),(0x12000000,0x60000000)]:
    u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(game,0x700000);u.mem_map(cave,0x30000);u.mem_map(0x30000000,0x20000)
    data=bytearray((a.native/'AssistantPayload.bin').read_bytes());fix=(a.native/'AssistantFixups.bin').read_bytes()
    for i in range(struct.unpack_from('<I',fix)[0]):
        k,o,v=struct.unpack_from('<III',fix,4+i*12)
        struct.pack_into('<I',data,o,((game+v) if k==1 else cave+v if k==2 else game+v-cave-o-4)&0xffffffff)
    u.mem_write(cave,bytes(data))
    def w(addr,v):u.mem_write(addr,struct.pack('<I',v))
    def r(addr):return struct.unpack('<I',u.mem_read(addr,4))[0]
    def f(addr,v):u.mem_write(addr,struct.pack('<f',v))
    def rf(addr):return struct.unpack('<f',u.mem_read(addr,4))[0]
    def text(addr):
        chars=[]
        for i in range(40):
            v=struct.unpack('<H',u.mem_read(addr+2*i,2))[0]
            if not v:break
            chars.append(chr(v))
        return ''.join(chars)
    widgets=[0x30001000+i*0x400 for i in range(5)]
    children=[v+0x100 for v in widgets]
    for i,v in enumerate(widgets):
        w(cave+(0x50 if i==0 else 0x1c000+(i-1)*4),v);w(v+0x6c,children[i]);w(children[i]+0x80,v+0x200)
    ui=0x30004000;active=0x30005000;stack=0x30006000;event=0x30007000
    w(game+0x5f3fc0,ui);w(ui+0x34,active);w(ui+0xb4,stack)
    seen={'original':0,'blur':0,'popped':0}
    native={game+(v-0x460000):name for v,name in [(0x4805de,'string'),(0x481375,'free'),(0x704ea1,'render'),(0x6ffc02,'get'),(0x70ade6,'finish'),(0x71c8c0,'pop'),(0x70b372,'original'),(0x70b356,'blur'),(0x704d12,'step'),(0x704da5,'step')]}
    def hook(uc,addr,size,_):
        if addr not in native:return
        name=native[addr];sp=uc.reg_read(UC_X86_REG_ESP);ecx=uc.reg_read(UC_X86_REG_ECX);cleanup=0
        if name=='string':w(ecx,r(sp+4));cleanup=4
        elif name=='render':
            target=r(r(ecx+0x6c)+0x80);value=text(r(r(sp+4)))
            uc.mem_write(target,(value+'\0').encode('utf-16le'));cleanup=4
        elif name=='get':uc.reg_write(UC_X86_REG_EAX,ecx+0x80)
        elif name=='pop':w(stack,0);seen['popped']+=1;cleanup=4
        elif name=='original':seen['original']+=1;cleanup=4
        elif name=='blur':seen['blur']+=1
        elif name=='step':seen['original']+=1;cleanup=4
        uc.reg_write(UC_X86_REG_EIP,r(sp));uc.reg_write(UC_X86_REG_ESP,sp+4+cleanup)
    u.hook_add(UC_HOOK_CODE,hook)
    def run(off,eax=0,edx=0,ecx=0,arg=None):
        sp=0x3001f000;w(sp,0x30000000)
        if arg is not None:w(sp+4,arg)
        for reg,v in [(UC_X86_REG_ESP,sp),(UC_X86_REG_EAX,eax),(UC_X86_REG_EDX,edx),(UC_X86_REG_ECX,ecx),
                      (UC_X86_REG_EBX,123),(UC_X86_REG_ESI,456),(UC_X86_REG_EDI,789),(UC_X86_REG_EBP,888)]:u.reg_write(reg,v)
        u.emu_start(cave+off,0x30000000,count=5000)
        check(u.reg_read(UC_X86_REG_ESP)==sp+4+(4 if arg is not None else 0),'balanced stack')
        check([u.reg_read(x) for x in [UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP]]==[123,456,789,888],'nonvolatile registers')
        return u.reg_read(UC_X86_REG_EAX)
    def focus(i):w(active+4,children[i]);w(stack,active);run(0x4300)
    def draft(i,s):u.mem_write(widgets[i]+0x200,(s+'\0').encode('utf-16le'))
    def key(k,down=True):
        u.mem_write(event+4,bytes([1 if down else 2]));u.mem_write(event+8,struct.pack('<H',k));return run(0x4800,ecx=active,arg=event)
    def value(i):return r(cave+0x44) if i==0 else rf(cave+0x1b000+i*4)
    w(cave+0x7c,0);w(cave,5555)
    for i in range(5):
        focus(i);check(run(0x4200)==i+1,'focus maps field');check(r(cave+0x80)==i+1 and r(cave+0x58)==0,'editing pauses')
        for s,valid in [('0',True),('2',True),('9999',True),('0012',True),('',False),('-1',False),('1.2',False),('12a',False),('12345',i==0),('9999999',i==0),('10000000',False),('１２',False)]:
            draft(i,s);got=run(0x4400);check(bool(u.reg_read(UC_X86_REG_EDX))==valid,'strict parse '+s)
            if valid:check(got==int(s),'parsed value')
        old=[value(j) for j in range(5)];rev=r(cave+0x1c020)
        draft(i,'23');check(key(13)==1,'enter consumed');check(value(i)==23,'enter commits right resource')
        check(all(value(j)==old[j] for j in range(5) if j!=i),'other values untouched')
        check(r(cave+0x1c020)==rev+(0 if i==0 else 2),'floor revision only for floors')
        before=r(cave+0x54);key(13);check(r(cave+0x54)==before,'held enter no duplicate')
        key(13,False);check(r(cave+0x80)==0 and r(cave+0x58)==1 and r(stack)==0,'release exits without chat')
        focus(i);draft(i,'999');key(27);key(27,False)
        check(value(i)==23 and text(widgets[i]+0x200)=='23','escape restores committed value')
        focus(i);draft(i,'999');run(0x4b00,ecx=active)
        check(value(i)==23 and text(widgets[i]+0x200)=='23','outside click restores committed value')
        focus(i);draft(i,'');key(13);key(13,False)
        check(value(i)==23 and r(cave+0x88)==1 and r(cave+0x80)==i+1,'invalid enter stays editing')
        key(27);key(27,False)
        before=r(cave+0x54);run(0x6800,eax=23,edx=i);check(r(cave+0x54)==before,'unchanged value no revision')
        for val in [0,9999999 if i==0 else 9999]:
            run(0x6800,eax=val,edx=i);run(0x6900,eax=i);check(value(i)==val and text(widgets[i]+0x200)==str(val),'bounds render')
        for val in [0xffffffff,10000000 if i==0 else 10000]:
            old=value(i);run(0x6800,eax=val,edx=i);check(value(i)==old,'bad commit rejected')
        run(0x6800,eax=0,edx=i)
        run(0x4d00,ecx=widgets[i],arg=0);check(value(i)==0,'step clamps zero')
        run(0x4c00,ecx=widgets[i],arg=0);check(value(i)==(100 if i==0 else 1),'proper step size')
    check(seen['original']==0,'no native chat received handled enter/escape')
    focus(1);draft(1,'432');w(active+4,children[2]);run(0x4300)
    check(text(widgets[1]+0x200)=='1' and r(cave+0x80)==3,'switch restores only old field')
    w(active+4,0x3000a000);run(0x4300);check(run(0x4200)==0,'unrelated editbox not owned')
    key(13);check(seen['original']==1,'unrelated enter reaches original')
    run(0x4c00,ecx=0x3000a000,arg=0);check(seen['original']==2,'unrelated step reaches original')
    focus(4);w(stack,0x30008000);check(run(0x4200)==0,'covered input not focused')
    old=[value(i) for i in range(5)];run(0x6c00)
    check(all(r(cave+0x1c000+i*4)==0 for i in range(4)),'destroy clears widget handles')
    check(old==[value(i) for i in range(5)],'destroy preserves committed values')
    run(0x6500);check(run(0x4200)==0,'absent fields safe to render and query')

root=Path(__file__).parent
for lang in ['en','ru']:
    layout=(root/f'paw_city_{lang}.tgi').read_text(encoding='utf-8')
    locale=(root/f'localization_{lang}.tgi').read_text(encoding='utf-8')
    for name,glyph in [('Stone',137),('Wood',136),('Iron',138),('Mana',134)]:
        check(layout.count(f'[Paw{name}Floor Template=NumericEditboxWidget]')==1,'one native field per resource')
        check(f'paw_city_{name.lower()}_icon = "{chr(glyph)}"' in locale,'stock game glyph identity')
        section=layout.split(f'[Paw{name}Floor Template=NumericEditboxWidget]')[1].split('    [Paw')[0]
        check(section.count('[Client Template=LabelWidget]')==2,'hidden step buttons still require native Client/Label nodes')
        check(section.count('[Label Template=SharedSmallCenteredLabelVE]')==2,'both native button captions defined')
    check(layout.count('max_characters = 4')==4,'compact four digit inputs')
    check(layout.count('max_characters = 7')==1,'reserve stays separate')
print('CITY_RESOURCE_INPUTS_PASS',checks,'checks; no game or windows opened')
