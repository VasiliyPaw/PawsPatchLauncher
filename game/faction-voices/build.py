"""Build a relocatable, import-free audio-only hook. No installed game writes."""
import argparse,hashlib,json,struct,subprocess,sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
def build(legacy,out):
 sys.path[:0]=[str(legacy/'pydeps_readable'),str(legacy/'lobby_colors_1372/deps_r15')]
 import pefile
 from keystone import Ks,KS_ARCH_X86,KS_MODE_32
 from capstone import Cs,CS_ARCH_X86,CS_MODE_32,CS_OP_IMM
 out.mkdir(parents=True,exist_ok=True)
 runtime=(legacy/'k2_runtime_1372_20260904.bin').read_bytes()
 assert hashlib.sha256(runtime).hexdigest()=='b865d8206990c4f055c51de857f0b09b88ab5ee3b6ae74ee5232134001aa591c'
 site=0x2c61d9;guard=bytes.fromhex('e88c87d5ff');assert runtime[site:site+5]==guard
 compiler=HERE.parents[3]/'work/crash-20260914-continue/tools/tinycc/tcc/tcc.exe'
 dll=out/'voices.dll'
 subprocess.run([str(compiler),'-shared','-nostdlib','-Wall','-Werror','-Wl,--image-base=0x10000000',str(HERE/'voices.c'),str(compiler.parent/'lib/libtcc1-32.a'),'-o',str(dll)],check=True)
 pe=pefile.PE(str(dll));assert not hasattr(pe,'DIRECTORY_ENTRY_IMPORT')
 buf=bytearray(pe.get_memory_mapped_image());exports={s.name.decode():s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols}
 fix=[(e.rva,0,1) for block in pe.DIRECTORY_ENTRY_BASERELOC for e in block.entries if e.type==3]
 entry=(len(buf)+4095)&~4095;state=entry+0x1000;buf.extend(bytes(state+64-len(buf)))
 image=0x460000;cave=0x10000000
 # Replace only audio argument 1; argument 5 is the event owner kingdom.
 # Argument 3 supplies the native actor fallback when the owner is absent.
 code=bytes(Ks(KS_ARCH_X86,KS_MODE_32).asm(f'pushfd;pushad;mov ebp,esp;sub esp,528;and esp,0xfffffff0;fxsave [esp];push dword ptr[ebp+48];push dword ptr[ebp+56];push dword ptr[ebp+40];push {cave+state};call {cave+exports["select_voice"]};add esp,16;mov [ebp+40],eax;fxrstor [esp];mov esp,ebp;popad;popfd;jmp {image+0x1e96a};',cave+entry)[0])
 buf[entry:entry+len(code)]=code
 owner=entry+0x100
 owner_code=bytes(Ks(KS_ARCH_X86,KS_MODE_32).asm('mov ecx,[esp+4];mov eax,[ecx];jmp dword ptr[eax+0x108];',cave+owner)[0]);buf[owner:owner+len(owner_code)]=owner_code
 md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
 for ins in md.disasm(code,cave+entry):
  for op in ins.operands:
   if op.type!=CS_OP_IMM:continue
   if ins.mnemonic=='jmp' and op.imm==image+0x1e96a:fix.append((ins.address-cave+ins.imm_offset,1,-1))
   elif ins.mnemonic=='push' and op.imm==cave+state:fix.append((ins.address-cave+ins.imm_offset,0,1))
 meta=dict(revision=1,preferredImage=image,preferredCave=cave,entry=entry,ownerAdapter=owner,state=state,size=len(buf),site=site,guard=guard.hex(),fixups=fix,exports=exports,
  dataFields=['magic','image','royalist','council','nationalist','ceyah','fallen','other','calls','switched','lastFaction','lastLanguage','ownerAdapter'])
 payload=out/'FactionVoices.bin';payload.write_bytes(buf);meta['sha256']=hashlib.sha256(buf).hexdigest()
 (out/'FactionVoices.json').write_text(json.dumps(meta,indent=2)+'\n')
 print('FACTION_VOICE_NATIVE_READY',len(buf),meta['sha256'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();build(a.legacy,a.out)
