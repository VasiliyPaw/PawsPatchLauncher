"""Build only a local terrain probe; does not patch or launch a game."""
import argparse,json,struct,subprocess
from pathlib import Path
from audit import LEGACY,RAW,BASE
import pefile
from keystone import Ks,KS_ARCH_X86,KS_MODE_32

p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--compiler',required=True);a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=True)
subprocess.run([a.compiler,'-shared','-nostdlib','-Wall','-Werror','-Wl,--image-base=0x10000000',str(Path(__file__).with_name('prototype.c')),'-o',str(a.out/'prototype.dll')],check=True)
pe=pefile.PE(str(a.out/'prototype.dll'));assert not hasattr(pe,'DIRECTORY_ENTRY_IMPORT')
code=bytearray(pe.get_memory_mapped_image());exports={s.name.decode():s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols}
fix=[(e.rva,0,1) for b in pe.DIRECTORY_ENTRY_BASERELOC for e in b.entries if e.type==3]
ks=Ks(KS_ARCH_X86,KS_MODE_32);cave=0x10000000
wrapper=(len(code)+4095)&~4095;adapter=wrapper+0x200;state=wrapper+0x1000
code.extend(bytes(state-len(code)))
# Native callee cleans arguments. Retains cdecl caller's preserved registers.
asm='push ebp;mov ebp,esp;push ebx;push esi;mov ebx,[ebp+16];mov esi,[ebp+20];test ebx,ebx;jz call_native;args:dec ebx;push dword ptr [esi+ebx*4];test ebx,ebx;jnz args;call_native:mov ecx,[ebp+12];call dword ptr [ebp+8];pop esi;pop ebx;leave;ret;'
data=bytes(ks.asm(asm,cave+adapter)[0]);code[adapter:adapter+len(data)]=data
# Original call first, then preserve all integer/FPU/SIMD state around probe.
site=0x2469b7;assert RAW[site:site+5]==bytes.fromhex('e89db7ffff')
asm=f'call {BASE+0x242159};pushfd;pushad;mov ebp,esp;sub esp,528;and esp,0xfffffff0;fxsave [esp];push esi;push {cave+state};call {cave+exports["tick"]};add esp,8;fxrstor [esp];mov esp,ebp;popad;popfd;jmp {BASE+site+5};'
data=bytes(ks.asm(asm,cave+wrapper)[0]);code[wrapper:wrapper+len(data)]=data
from capstone import Cs,CS_ARCH_X86,CS_MODE_32,CS_OP_IMM
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
for ins in md.disasm(data,cave+wrapper):
    for op in ins.operands:
        if op.type!=CS_OP_IMM:continue
        if op.imm==cave+state:fix.append((ins.address-cave+ins.imm_offset,0,1))
        if ins.mnemonic in ('call','jmp') and BASE<=op.imm<BASE+len(RAW):fix.append((ins.address-cave+ins.imm_offset,1,-1))
(a.out/'prototype.bin').write_bytes(code)
(a.out/'prototype.json').write_text(json.dumps(dict(size=state+4096,state=state,entry=wrapper,adapter=adapter,hook=site,before=RAW[site:site+5].hex(),fixups=fix,exports=exports),indent=2))
print('Built local prototype',len(code),'bytes; state',hex(state))
