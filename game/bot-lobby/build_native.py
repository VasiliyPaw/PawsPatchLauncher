import argparse,subprocess,sys,struct,json,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
HOOKS=[(0x104a79,0x29d6df,'menu_tick',False),(0x127c70,0x128c9a,'row_tick',False),(0x12c0ef,0x1267b8,'row_destroy',True),(0x1057ac,0x1041ec,'menu_destroy',True),(0x1041d4,0x21375,'menu_create',False)]
def main():
 p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--compiler',required=True);a=p.parse_args()
 sys.path[:0]=[str(a.legacy/'pydeps_readable'),str(a.legacy/'lobby_colors_1372/deps_r15')]
 import pefile
 from keystone import Ks,KS_ARCH_X86,KS_MODE_32
 from capstone import Cs,CS_ARCH_X86,CS_MODE_32,CS_OP_IMM
 a.out.mkdir(parents=True,exist_ok=True);dll=a.out/'controls.dll'
 subprocess.run([a.compiler,'-shared','-nostdlib','-Wl,--image-base=0x10000000',str(Path(__file__).with_name('controls.c')),'-o',str(dll)],check=True)
 pe=pefile.PE(str(dll));assert not hasattr(pe,'DIRECTORY_ENTRY_IMPORT')
 base=pe.OPTIONAL_HEADER.ImageBase;assert base==0x10000000
 code=bytearray(pe.get_memory_mapped_image());size=(len(code)+4095)&~4095;code.extend(bytes(size-len(code)))
 exports={s.name.decode():s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols}
 reloc=[(e.rva,0,1) for block in pe.DIRECTORY_ENTRY_BASERELOC for e in block.entries if e.type==3]
 ks=Ks(KS_ARCH_X86,KS_MODE_32);md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
 image=0x460000;data=base+size+4096;hooks=[]
 raw=(a.legacy/'k2_runtime_1372_20260904.bin').read_bytes()
 assert hashlib.sha256(raw).hexdigest()=='b865d8206990c4f055c51de857f0b09b88ab5ee3b6ae74ee5232134001aa591c'
 for index,(site,target,name,before) in enumerate(HOOKS):
  off=size+index*512;addr=base+off
  invoke=f'pushfd;pushad;sub esp,528;lea eax,[esp+15];and eax,0xfffffff0;fxsave [eax];push eax;push dword ptr [ebp-8];push {data};push {image};call {base+exports[name]};add esp,12;pop eax;fxrstor [eax];add esp,528;popad;popfd;'
  original=f'mov ecx,[ebp-4];call {image+target};'
  selfreg='esi' if name=='menu_create' else 'ecx'
  asm=f'push ebp;mov ebp,esp;sub esp,8;mov [ebp-4],ecx;mov [ebp-8],{selfreg};'+(invoke+original if before else original+invoke)+'mov esp,ebp;pop ebp;ret;'
  blob=bytes(ks.asm(asm,addr)[0]);assert len(blob)<512
  code.extend(bytes(max(0,off+len(blob)-len(code))));code[off:off+len(blob)]=blob
  for ins in md.disasm(blob,addr):
   for op in ins.operands:
    if op.type==CS_OP_IMM:
     if op.imm in (image,image+target):reloc.append((ins.address-base+ins.imm_offset,1,-1 if ins.mnemonic=='call' else 0))
     elif op.imm==data:reloc.append((ins.address-base+ins.imm_offset,0,1))
  original=raw[site:site+5];assert original==b'\xe8'+struct.pack('<i',target-site-5)
  hooks.append(dict(site=site,target=target,name=name,before=before,offset=off,original=original.hex(),guard=raw[site-3:site+10].hex()))
 assert len(code)<size+4096
 meta=dict(image=image,cave=base,dataOffset=size+4096,allocation=size+4096+16384,fixups=reloc,hooks=hooks,exports=exports)
 (a.out/'controls.bin').write_bytes(code);(a.out/'controls.json').write_text(json.dumps(meta,indent=2))
 src='using System;\ninternal static class BotLobbyPayload {\n'
 src+=f'internal const int DataOffset={meta["dataOffset"]}, Allocation={meta["allocation"]};\n'
 src+='internal static readonly uint[] Sites={'+','.join(str(x['site']) for x in hooks)+'};\n'
 src+='internal static readonly uint[] Offsets={'+','.join(str(x['offset']) for x in hooks)+'};\n'
 src+='internal static readonly string[] Guards={'+','.join('"'+x['guard']+'"' for x in hooks)+'};\n'
 src+='internal static readonly string[] Originals={'+','.join('"'+x['original']+'"' for x in hooks)+'};\n'
 src+='internal static byte[] Build(uint image,uint cave){byte[] b=TerrainPatch.Hex("'+code.hex()+'");\n'
 for off,im,cv in reloc:
  expr=[]
  if im:expr.append('(image-0x460000)')
  if cv==1:expr.append('(cave-0x10000000)')
  if cv==-1:expr.append('(0x10000000-cave)')
  src+=f'Add(b,{off},unchecked({"+".join(expr)}));\n'
 src+='return b;}static void Add(byte[]b,int o,uint d){Buffer.BlockCopy(BitConverter.GetBytes(unchecked(BitConverter.ToUInt32(b,o)+d)),0,b,o,4);}}'
 (a.out/'BotLobbyPayload.cs').write_text(src)
 print('BOT_LOBBY_BUILD_PASS',len(code),'bytes',len(reloc),'relocations')
if __name__=='__main__':main()
