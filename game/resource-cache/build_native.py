"""Build an import-free, ASLR-relocated presentation-only cache payload."""
import argparse,base64,hashlib,json,struct,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
LEG=Path('G:/CodexData/projects/Codex/2026-08-11/kohan-ii-d-steamlibrary-steamapps-common/work')
WS=HERE.parents[3]
IMAGE=0x460000;CAVE=0x10000000

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 sys.path[:0]=[str(LEG/'pydeps_readable'),str(LEG/'lobby_colors_1372/deps_r15')]
 import pefile
 from keystone import Ks,KS_ARCH_X86,KS_MODE_32
 from capstone import Cs,CS_ARCH_X86,CS_MODE_32,CS_OP_IMM
 compiler=WS/'work/crash-20260914-continue/tools/tinycc/tcc/tcc.exe'
 build=out/'freestanding.c';build.write_text('#include "'+(HERE/'cache.c').as_posix()+'"\nint __attribute__((stdcall)) _dllstart(void*m,unsigned r,void*u){return 1;}\n')
 args=[str(compiler),'-shared','-nostdlib','-Wall','-Werror','-Wl,--image-base=0x10000000',str(build),str(compiler.parent/'lib/libtcc1-32.a'),'-o',str(out/'cache.dll')]
 subprocess.run(args,check=True)
 pe=pefile.PE(str(out/'cache.dll'));assert not hasattr(pe,'DIRECTORY_ENTRY_IMPORT')
 buf=bytearray(pe.get_memory_mapped_image());exports={x.name.decode():x.address for x in pe.DIRECTORY_ENTRY_EXPORT.symbols}
 fixes=[(e.rva,0,1) for b in pe.DIRECTORY_ENTRY_BASERELOC for e in b.entries if e.type==3]
 wrapper=(len(buf)+4095)&~4095;frame=wrapper;trampoline=wrapper+0x100;weights=wrapper+0x200;state=wrapper+0x1000;size=state+4096
 buf.extend(bytes(state-len(buf)))
 ks=Ks(KS_ARCH_X86,KS_MODE_32);md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
 def asm(off,code):
  b=bytes(ks.asm(code,CAVE+off)[0]);assert len(b)<=256;buf[off:off+len(b)]=b
  for ins in md.disasm(b,CAVE+off):
   at=ins.address-CAVE
   for op in ins.operands:
    if op.type!=CS_OP_IMM:continue
    if ins.mnemonic in ('call','jmp') and IMAGE<=op.imm<IMAGE+0x700000:fixes.append((at+ins.imm_offset,1,-1))
    elif ins.mnemonic in ('push','mov') and IMAGE<=op.imm<IMAGE+0x700000:fixes.append((at+ins.imm_offset,1,0))
    elif ins.mnemonic in ('push','mov') and CAVE<=op.imm<CAVE+size:fixes.append((at+ins.imm_offset,0,1))
 asm(trampoline,f'mov eax,{IMAGE+0x42d4ca};jmp {IMAGE+0x13c639};')
 save='pushfd;pushad;mov esi,esp;sub esp,528;and esp,0xfffffff0;fxsave [esp];'
 restore='fxrstor [esp];mov esp,esi;popad;popfd;'
 asm(frame,f'call {CAVE+trampoline};'+save+f'push {CAVE+state};call {CAVE+exports["rc_tick"]};add esp,4;'+restore+'ret;')
 asm(weights,'push ebp;mov ebp,esp;'+save+f'push dword ptr[ebp+16];push dword ptr[ebp+12];push dword ptr[ebp+8];push ecx;push {CAVE+state};call {CAVE+exports["rc_weights"]};add esp,20;'+restore+'pop ebp;ret 12;')
 raw=(LEG/'k2_runtime_1372_20260904.bin').read_bytes();assert hashlib.sha256(raw).hexdigest()=='b865d8206990c4f055c51de857f0b09b88ab5ee3b6ae74ee5232134001aa591c'
 hooks=[dict(site=0x13c634,entry=frame,original=raw[0x13c634:0x13c639].hex(),imageFixup=1),dict(site=0x1b5c02,entry=weights,original=raw[0x1b5c02:0x1b5c09].hex(),imageFixup=-1)]
 assert hooks[0]['original']=='b8cad48800' and hooks[1]['original']=='83ec208b542424'
 (out/'payload.bin').write_bytes(buf)
 (out/'payload.json').write_text(json.dumps(dict(image=IMAGE,cave=CAVE,state=state,size=size,exports=exports,hooks=hooks,fixups=fixes,imports=[],sourceSha256=hashlib.sha256((HERE/'cache.c').read_bytes()).hexdigest(),compiler=args),indent=2))
 cs='using System;\ninternal static class ResourceCachePayload {\n'
 cs+=f'internal const uint State={state};internal const int CodeSize={state},Allocation={size};\n'
 cs+='internal static readonly uint[] Sites={'+','.join(hex(x['site']) for x in hooks)+'},Entries={'+','.join(str(x['entry']) for x in hooks)+'};\n'
 cs+='internal static byte[] Original(int i,uint image){byte[] b=TerrainPatch.Hex(i==0?"'+hooks[0]['original']+'":"'+hooks[1]['original']+'");if(i==0)Add(b,1,unchecked(image-0x460000));return b;}\n'
 cs+='internal static byte[] Build(uint image,uint cave){byte[] b=Convert.FromBase64String("'+base64.b64encode(buf).decode()+'");\n'
 for at,im,cv in fixes:
  parts=[]
  if im:parts.append(('' if im>0 else '0-')+'(image-0x460000)')
  if cv:parts.append(('' if cv>0 else '0-')+'(cave-0x10000000)')
  cs+=f'Add(b,{at},unchecked('+ '+'.join(parts)+'));\n'
 cs+='return b;}\nstatic void Add(byte[] b,int at,uint delta){Buffer.BlockCopy(BitConverter.GetBytes(unchecked(BitConverter.ToUInt32(b,at)+delta)),0,b,at,4);}\n}\n'
 (out/'ResourceCachePayload.cs').write_text(cs)
 print('RESOURCE_CACHE_NATIVE_BUILD_PASS',len(buf),len(fixes),'fixups; no imports')
if __name__=='__main__':main()
