import argparse,subprocess,sys,struct,json,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
HOOKS=[(0x48bbec,0xbfbf0,'tick',False),(0x48bb08,0xbf939,'resource_tick',False),(0x48bc2c,0xbf010,'reset',True),(0x48bbe4,0xc0575,'reset',True)]
def main():
 p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--compiler',required=True);a=p.parse_args()
 sys.path[:0]=[str(a.legacy/'pydeps_readable'),str(a.legacy/'lobby_colors_1372/deps_r15')]
 import pefile
 from keystone import Ks,KS_ARCH_X86,KS_MODE_32
 from capstone import Cs,CS_ARCH_X86,CS_MODE_32,CS_OP_IMM
 a.out.mkdir(parents=True,exist_ok=True);dll=a.out/'panel.dll'
 subprocess.run([a.compiler,'-shared','-nostdlib','-Wall','-Werror','-Wl,--image-base=0x10000000',str(Path(__file__).with_name('panel.c')),'-o',str(dll)],check=True)
 pe=pefile.PE(str(dll));assert not hasattr(pe,'DIRECTORY_ENTRY_IMPORT');base=pe.OPTIONAL_HEADER.ImageBase;assert base==0x10000000
 code=bytearray(pe.get_memory_mapped_image());size=(len(code)+4095)&~4095;code.extend(bytes(size-len(code)))
 exports={s.name.decode():s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols}
 reloc=[(e.rva,0,1) for block in getattr(pe,'DIRECTORY_ENTRY_BASERELOC',[]) for e in block.entries if e.type==3]
 ks=Ks(KS_ARCH_X86,KS_MODE_32);md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
 image=0x460000;data=base+size+4096;hooks=[];raw=(a.legacy/'k2_runtime_1372_20260904.bin').read_bytes()
 assert hashlib.sha256(raw).hexdigest()=='b865d8206990c4f055c51de857f0b09b88ab5ee3b6ae74ee5232134001aa591c'
 for index,(site,target,name,tail) in enumerate(HOOKS):
  assert struct.unpack_from('<I',raw,site)[0]==image+target,(hex(site),raw[site:site+4].hex())
  off=size+index*256;addr=base+off
  asm=f'pushfd;pushad;mov ebx,ecx;sub esp,528;lea eax,[esp+15];and eax,0xfffffff0;fxsave [eax];push eax;push ebx;push {data};push {image};call {base+exports[name]};add esp,12;pop eax;fxrstor [eax];add esp,528;popad;popfd;'
  asm+=(f'jmp {image+target};' if tail else 'ret;')
  blob=bytes(ks.asm(asm,addr)[0]);assert len(blob)<256
  code.extend(bytes(max(0,off+len(blob)-len(code))));code[off:off+len(blob)]=blob
  for ins in md.disasm(blob,addr):
   for op in ins.operands:
    if op.type==CS_OP_IMM:
     if op.imm in (image,image+target):reloc.append((ins.address-base+ins.imm_offset,1,-1 if ins.mnemonic=='jmp' else 0))
     elif op.imm==data:reloc.append((ins.address-base+ins.imm_offset,0,1))
  hooks.append(dict(site=site,target=target,name=name,offset=off,tail=tail))
 assert len(code)<size+4096
 meta=dict(image=image,cave=base,dataOffset=size+4096,allocation=size+8192,fixups=reloc,hooks=hooks,exports=exports)
 (a.out/'panel.bin').write_bytes(code);(a.out/'panel.json').write_text(json.dumps(meta,indent=2))
 src='using System;\ninternal static class AllyEconomyPayload {\n'
 src+=f'internal const int DataOffset={meta["dataOffset"]}, Allocation={meta["allocation"]};\n'
 for key in ('Sites','Targets','Offsets'):
  field={'Sites':'site','Targets':'target','Offsets':'offset'}[key];src+='internal static readonly uint[] '+key+'={'+','.join(str(x[field]) for x in hooks)+'};\n'
 src+='internal static byte[] Build(uint image,uint cave){byte[] b=TerrainPatch.Hex("'+code.hex()+'");\n'
 for off,im,cv in reloc:
  expr=[]
  if im:expr.append('(image-0x460000)')
  if cv==1:expr.append('(cave-0x10000000)')
  if cv==-1:expr.append('(0x10000000-cave)')
  src+=f'Add(b,{off},unchecked({"+".join(expr)}));\n'
 src+='return b;}static void Add(byte[]b,int o,uint d){Buffer.BlockCopy(BitConverter.GetBytes(unchecked(BitConverter.ToUInt32(b,o)+d)),0,b,o,4);}}'
 (a.out/'AllyEconomyPayload.cs').write_text(src)
 print('ALLY_ECONOMY_BUILD_PASS',len(code),'bytes',len(reloc),'relocations')
if __name__=='__main__':main()
