"""Compile the final native 80/20 count split; never attaches to the game."""
import argparse,hashlib,json,struct,subprocess,sys
from pathlib import Path
HOOK=0x25839b
GUARD_RVA=0x258389
GUARD=bytes.fromhex('d84de88b5e08518b4e04d95de8f30f2c45e8894630660f6e43280f5bc0f30f1145e8f30f104320f30f110424e862daffffd84de8d95de8f30f2c7de8897e34')
IMAGE=0x460000;CAVE=0x10000000
def main():
 p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--compiler',required=True);a=p.parse_args()
 sys.path[:0]=[str(a.legacy/'pydeps_readable'),str(a.legacy/'lobby_colors_1372/deps_r15')]
 import pefile
 from keystone import Ks,KS_ARCH_X86,KS_MODE_32
 from capstone import Cs,CS_ARCH_X86,CS_MODE_32,CS_OP_IMM
 raw=(a.legacy/'k2_runtime_1372_20260904.bin').read_bytes()
 assert hashlib.sha256(raw).hexdigest()=='b865d8206990c4f055c51de857f0b09b88ab5ee3b6ae74ee5232134001aa591c'
 assert raw[HOOK:HOOK+8]==bytes.fromhex('894630660f6e4328')
 assert raw[GUARD_RVA:GUARD_RVA+len(GUARD)]==GUARD
 a.out.mkdir(parents=True,exist_ok=True);dll=a.out/'counts.dll'
 subprocess.run([a.compiler,'-shared','-nostdlib','-Wl,--image-base=0x10000000',str(Path(__file__).with_name('counts.c')),'-o',str(dll)],check=True)
 pe=pefile.PE(str(dll));assert not hasattr(pe,'DIRECTORY_ENTRY_IMPORT')
 exports={s.name.decode():s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols};fn=exports['split_count']
 code=bytearray(pe.get_memory_mapped_image());entry=(len(code)+15)&~15;code.extend(bytes(entry-len(code)))
 fixups=[(e.rva,0,1) for block in pe.DIRECTORY_ENTRY_BASERELOC for e in block.entries if e.type==3]
 ks=Ks(KS_ARCH_X86,KS_MODE_32)
 asm=f'''pushfd; pushad; mov ebx,esp; sub esp,528;
 lea eax,[esp+15]; and eax,0xfffffff0; fxsave [eax]; push eax;
 push dword ptr [ebx+28]; push esi; push {IMAGE}; call {CAVE+fn}; add esp,12;
 mov [ebx+28],eax; pop eax; fxrstor [eax]; mov esp,ebx; popad; popfd;
 mov [esi+0x30],eax; movd xmm0,[ebx+0x28]; jmp {IMAGE+HOOK+8};'''
 wrapper=bytes(ks.asm(asm,CAVE+entry)[0]);code.extend(wrapper)
 md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
 for ins in md.disasm(wrapper,CAVE+entry):
  for op in ins.operands:
   if op.type==CS_OP_IMM:
    if op.imm==IMAGE:fixups.append((ins.address-CAVE+ins.imm_offset,1,0))
    elif op.imm==IMAGE+HOOK+8:fixups.append((ins.address-CAVE+ins.imm_offset,1,-1))
 hooks=[dict(site=HOOK,offset=entry,original=raw[HOOK:HOOK+8].hex())]
 data_offset=0x20000;data_size=28+4096*32
 def append_wrapper(site,length,asm):
  off=(len(code)+15)&~15;code.extend(bytes(off-len(code)));wrapper=bytes(ks.asm(asm,CAVE+off)[0]);code.extend(wrapper)
  for ins in md.disasm(wrapper,CAVE+off):
   for op in ins.operands:
    if op.type!=CS_OP_IMM:continue
    if op.imm==IMAGE:fixups.append((ins.address-CAVE+ins.imm_offset,1,0))
    elif op.imm==CAVE+data_offset:fixups.append((ins.address-CAVE+ins.imm_offset,0,1))
    elif IMAGE<=op.imm<IMAGE+0x690000:fixups.append((ins.address-CAVE+ins.imm_offset,1,-1 if ins.mnemonic in ('call','jmp') else 0))
  hooks.append(dict(site=site,offset=off,original=raw[site:site+length].hex()))
 pre='pushfd; pushad; mov ebx,esp; sub esp,528; lea eax,[esp+15]; and eax,0xfffffff0; fxsave [eax]; push eax;'
 post='pop eax; fxrstor [eax]; mov esp,ebx; popad; popfd;'
 assert raw[0x255e09:0x255e0f]==bytes.fromhex('8b4df48ac35f')
 append_wrapper(0x255e09,6,pre+f'movzx eax,byte ptr [ebx+16]; push eax; push {CAVE+data_offset}; push {IMAGE}; call {CAVE+exports["plan_map"]}; add esp,12;'+post+f'mov ecx,[ebp-12]; mov al,bl; pop edi; jmp {IMAGE+0x255e0f};')
 assert raw[0x247a27:0x247a2c]==bytes.fromhex('e8b579e2ff')
 append_wrapper(0x247a27,5,pre+f'push dword ptr [ebx+24]; push dword ptr [ebx+4]; push {CAVE+data_offset}; push {IMAGE}; call {CAVE+exports["select_table"]}; add esp,16; mov [ebx+24],eax;'+post+f'jmp {IMAGE+0x6f3e1};')
 assert len(code)<data_offset
 size=(data_offset+data_size+4095)&~4095
 meta=dict(image=IMAGE,cave=CAVE,entry=entry,function=fn,exports=exports,allocation=size,fixups=fixups,hook=HOOK,guardRva=GUARD_RVA,guard=GUARD.hex(),hooks=hooks,dataOffset=data_offset,dataSize=data_size,revision=2)
 (a.out/'counts.bin').write_bytes(code);(a.out/'counts.json').write_text(json.dumps(meta,indent=2))
 src='using System;\ninternal static class FoundationCountsPayload {\n internal const int Allocation='+str(size)+';\n internal const uint Entry='+str(entry)+';\n internal const uint DataOffset='+str(data_offset)+';\n internal static readonly uint[] Entries=new uint[]{'+','.join(str(h['offset']) for h in hooks)+'};\n internal static byte[] Build(uint image,uint cave){byte[] b=TerrainPatch.Hex("'+code.hex()+'");\n'
 for off,im,cv in fixups:
  src+=f'Add(b,{off},unchecked((image-0x460000)*{im}u+(cave-0x10000000)*'+('uint.MaxValue' if cv==-1 else str(cv)+'u')+'));\n'
 src+='return b;}\n static void Add(byte[] b,int o,uint d){Buffer.BlockCopy(BitConverter.GetBytes(unchecked(BitConverter.ToUInt32(b,o)+d)),0,b,o,4);}\n}\n'
 (a.out/'FoundationCountsPayload.cs').write_text(src)
 print('FOUNDATION_COUNTS_BUILD_PASS',len(code),'bytes; no imports, RNG or game writes')
if __name__=='__main__':main()
