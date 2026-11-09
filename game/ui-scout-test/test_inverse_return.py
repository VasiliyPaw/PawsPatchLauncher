"""Native caller's EAX pointer contract, including the observed crash address.

Uses compiled callbacks and the established x86 fixture. The actual native
inverse routine returns the destination pointer (MOV EAX,[EBP+8], RET 12), and
the real caller at RVA D5000 immediately reads [EAX]/[EAX+4]. Coordinates alone
are insufficient to validate this boundary. No live process is accessed.
"""
import argparse,json,struct,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--expect-bug',type=int,choices=[0,1],required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
source=Path(__file__).with_name('test_native.py');sys.argv=[str(source),'--build',str(a.build)]
scope={'__file__':str(source)};exec(compile(source.read_text().split('\nfor image,dll in ')[0],str(source),'exec'),scope)
Fixture=scope['Fixture']
from unicorn import UcError
from unicorn.x86_const import *
checks=0;rows=[]
def check(ok,why):
 global checks
 checks+=1;assert ok,why
for image,dll in [(0xa50000,0xff10000),(0x460000,0x10000000),(0xb30000,0x14000000)]:
 for scale in [1.,1.1,2.,4.]:
  for match,own in [(True,True),(True,False),(False,True)]:
   f=Fixture(image,dll);state=f.heap+0x11000;widget=f.heap+0x12000;terrain=f.heap+0x13000;out=f.heap+0x14000
   f.w(image+0x5f92f4,4 if match else 0);f.w(image+0x5f92b4+16,state);f.w(state,image+0x48d0dc);f.w(f.world+0x30,terrain);f.f(terrain+12,1280);f.f(terrain+16,1280)
   f.asm(image+0x2a42aa,'mov eax,[esp+4];mov dword ptr [eax],0x44200000;mov dword ptr [eax+4],0x44200000;ret 12')
   f.invoke(f.exports['Test_View'],[widget,*[struct.unpack('<I',struct.pack('<f',v))[0]for v in [scale,.4,.6]]],cdecl=True)
   self=widget if own else widget+0x100
   f.u.reg_write(UC_X86_REG_FPSW,0x21)
   returned=f.invoke(f.entries[4],[out,200,600],ecx=self)
   if not a.expect_bug:check(returned==out,'Native destination pointer survives every wrapper branch')
   elif match and own:check(returned!=out,'Released callback violates return contract')
   for site in [0xd5000,0xd5785,0x2a4570,0x2a47ee]:
    callsite=image+site
    f.asm(callsite,'call '+str(f.entries[4])+';movss xmm0,[eax];movss xmm1,[eax+4];jmp '+str(f.stop))
    f.u.mem_write(f.stack,struct.pack('<III',out,200,600));f.u.reg_write(UC_X86_REG_ESP,f.stack);f.u.reg_write(UC_X86_REG_ECX,self);f.u.reg_write(UC_X86_REG_EDX,0);f.u.reg_write(UC_X86_REG_FPSW,0x21)
    fault=None
    try:f.u.emu_start(callsite,f.stop,count=100000)
    except UcError as e:fault=str(e)
    eax=f.u.reg_read(UC_X86_REG_EAX);eip=f.u.reg_read(UC_X86_REG_EIP)
    if not a.expect_bug:
     check(fault is None and eip==f.stop,'Native caller reads both returned coordinates safely')
     check(eax==out,'EAX still identifies start, not end, of the two-float result')
     check(f.u.reg_read(UC_X86_REG_ESP)==f.stack+12,'Native callee cleanup preserved')
    rows.append(dict(image=hex(image),site=hex(site),scale=scale,match=match,own=own,expected=hex(out),eax=hex(eax),eip=hex(eip),fault=fault))
if a.expect_bug:
 observed=[r for r in rows if r['image']=='0xa50000'and r['site']=='0xd5000'and r['scale']==1.0 and r['match']and r['own']]
 check(len(observed)==1 and observed[0]['eip']=='0xb25005'and observed[0]['eax']=='0x4021'and observed[0]['fault']is not None,'Reproduce exact dump EIP and invalid EAX')
result=dict(passed=True,expectBug=bool(a.expect_bug),checks=checks,cases=len(rows),compiledDll=str(a.build/'PawUiScoutQA.dll'),liveGameTested=False,observations=rows)
a.report.write_text(json.dumps(result,indent=2));print('INVERSE_RETURN_CONTRACT_PASS',checks,'checks;',len(rows),'caller cases; expectBug='+str(bool(a.expect_bug)))
