import argparse,subprocess,sys,struct,json,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
SITES=[(0x1e54c7,0x1e552b,2,0,False),(0x1ded9c,0x1dc876,0,1,False),(0x1dee7c,0x1dc876,0,1,False),(0x1d1667,0x1ee5b3,5,2,True),(0x1d1838,0x1ee5b3,5,2,True),(0x1dc997,0x21cc0e,4,3,False),(0x1dcb10,0x21cc0e,4,3,False)]
SITES += [(s,0x1dd5b0,1,4,False) for s in (0x1dd2fb,0x1dd47c,0x1dd4de)]
SITES += [(0x1decbb,0x1dc808,2,5,False),(0x21ca57,0x222693,5,6,False),(0x21ca36,0x21de6a,4,7,False),(0x21cae2,0x21cb03,5,8,False),(0x21f34d,0x220a80,3,9,False)]
SITES += [(0x21c938,0x21de6a,4,7,False),(0x21c965,0x21d1e3,6,10,False)]
def main():
 p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--compiler',required=True);a=p.parse_args()
 sys.path[:0]=[str(a.legacy/'pydeps_readable'),str(a.legacy/'lobby_colors_1372/deps_r15')]
 import pefile
 from keystone import Ks,KS_ARCH_X86,KS_MODE_32
 from capstone import Cs,CS_ARCH_X86,CS_MODE_32,CS_OP_MEM,CS_OP_IMM
 a.out.mkdir(parents=True,exist_ok=True)
 dll=a.out/'policy.dll'
 subprocess.run([a.compiler,'-shared','-nostdlib','-Wl,--image-base=0x10000000',str(Path(__file__).with_name('policy.c')),'-o',str(dll)],check=True)
 pe=pefile.PE(str(dll));assert not hasattr(pe,'DIRECTORY_ENTRY_IMPORT'),'payload must not import OS/runtime functions'
 base=pe.OPTIONAL_HEADER.ImageBase;assert base==0x10000000
 cb=bytearray(pe.get_memory_mapped_image());size=(len(cb)+4095)&~4095;cb.extend(bytes(size-len(cb)))
 exports={s.name.decode():s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols};fn=exports['evaluate']
 reloc=[e.rva for block in pe.DIRECTORY_ENTRY_BASERELOC for e in block.entries if e.type==3]
 ks=Ks(KS_ARCH_X86,KS_MODE_32);md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
 image=0x460000;wrapper_size=((len(SITES)+1)*512+4095)&~4095
 data=base+size+wrapper_size;fixups=[(off,0,1) for off in reloc];wrappers=[]
 def callback(mode):
  return ('pushfd; pushad; sub esp,528; lea eax,[esp+15]; and eax,0xfffffff0; fxsave [eax]; push eax;'
   +f'lea eax,[ebp-8]; push eax; lea eax,[ebp+8]; push eax; push dword ptr [ebp-4]; push {mode}; push {data}; push {image}; call {base+fn}; add esp,24;'
   +'pop eax; fxrstor [eax]; add esp,528;')
 def put(off,asm,targets):
  addr=base+off;code=bytes(ks.asm(asm,addr)[0]);assert len(code)<512
  cb.extend(bytes(max(0,off+len(code)-len(cb))));cb[off:off+len(code)]=code
  for ins in md.disasm(code,addr):
   for op in ins.operands:
    if op.type==CS_OP_IMM:
     if op.imm==image or op.imm in [image+t for t in targets]:fixups.append((ins.address-base+ins.imm_offset,1,-1 if ins.mnemonic=='call' else 0))
     elif op.imm==data:fixups.append((ins.address-base+ins.imm_offset,0,1))
 raw=(a.legacy/'k2_runtime_1372_20260904.bin').read_bytes()
 assert hashlib.sha256(raw).hexdigest()=='b865d8206990c4f055c51de857f0b09b88ab5ee3b6ae74ee5232134001aa591c'
 for i,(site,target,argc,mode,fp) in enumerate(SITES):
  off=size+i*512;addr=base+off
  asm='push ebp; mov ebp,esp; sub esp,24; mov [ebp-4],ecx; mov dword ptr [ebp-8],0;'
  if mode==9:asm+=callback(mode)+'popad; popfd; cmp dword ptr [ebp-8],0; jne skipped; mov ecx,[ebp-4];'
  asm+=';'.join(f'push dword ptr [ebp+{8+j*4}]' for j in reversed(range(argc)))+';'
  asm+=f'call {image+target};'
  if mode==8:asm+=f'lea esp,[esp+{argc*4}];' # cdecl caller removes copied arguments, preserving callee flags.
  # Keep the original extended-precision return for unchanged candidates.
  # Logging must not silently round every native priority to float32.
  asm+='fst dword ptr [ebp-8]; fstp tbyte ptr [ebp-24]; push eax; mov eax,[ebp-8]; mov [ebp-12],eax; pop eax;' if fp else 'mov [ebp-8],eax;'
  if mode!=9:asm+=callback(mode)
  if fp:asm+='mov eax,[ebp-8]; cmp eax,[ebp-12]; jne changed; fld tbyte ptr [ebp-24]; jmp returned; changed: fld dword ptr [ebp-8]; returned:;'
  if mode!=9:asm+='popad; popfd;'
  if mode==4:asm+='mov eax,[ebp-8];'
  if mode==9:asm+='skipped:;'
  asm+=f'mov esp,ebp; pop ebp; ret {0 if mode==8 else argc*4};'
  put(off,asm,[target])
  original=raw[site:site+5];assert original==b'\xe8'+struct.pack('<i',target-site-5)
  wrappers.append(dict(site=site,target=target,offset=off,original=original.hex(),guard=raw[site-3:site+10].hex(),argc=argc,mode=mode,fp=fp,cdecl=mode==8,pre=mode==9))
 query=size+len(SITES)*512
 # cdecl bridge: native ResourceVector constructor, aggregate upkeep and destructor.
 asm='push ebp; mov ebp,esp; push ebx; push esi; push edi; sub esp,16; lea ecx,[ebp-28];'
 asm+=f'call {image+0x22607d}; push 0; push dword ptr [ebp+16]; push dword ptr [ebp+12]; lea eax,[ebp-28]; push eax; call {image+0x20dae6}; add esp,16;'
 asm+='mov ebx,[ebp-20]; cmp ebx,16; ja invalid; mov esi,[ebp-24]; mov edi,[ebp+20]; mov ecx,ebx; cld; rep movs dword ptr es:[edi], dword ptr [esi]; jmp dispose; invalid: xor ebx,ebx; dispose: lea ecx,[ebp-28];'
 asm+=f'call {image+0x226166}; mov eax,ebx; lea esp,[ebp-12]; pop edi; pop esi; pop ebx; pop ebp; ret;'
 put(query,asm,[0x22607d,0x20dae6,0x226166])
 assert len(cb)<=size+wrapper_size
 (a.out/'ai-policy.bin').write_bytes(cb)
 query_pointer=128+2048*128+8192*20+24
 meta=dict(image=image,cave=base,codeSize=size+wrapper_size,dataOffset=size+wrapper_size,allocation=size+wrapper_size+query_pointer+4,queryOffset=query,queryPointerOffset=query_pointer,fixups=fixups,wrappers=wrappers,evaluate=fn)
 (a.out/'ai-policy.json').write_text(json.dumps(meta,indent=2))
 src='using System;\ninternal static class AiPolicyPayload {\n'
 src+=f'internal const int CodeSize={meta["codeSize"]}, DataOffset={meta["dataOffset"]}, Allocation={meta["allocation"]};\n'
 src+=f'internal const int QueryOffset={query}, QueryPointerOffset={query_pointer};\n'
 src+='internal static readonly uint[] Sites={'+','.join(str(x['site']) for x in wrappers)+'};\n'
 src+='internal static readonly uint[] Offsets={'+','.join(str(x['offset']) for x in wrappers)+'};\n'
 src+='internal static readonly string[] Guards={'+','.join('"'+x['guard']+'"' for x in wrappers)+'};\n'
 src+='internal static readonly string[] Originals={'+','.join('"'+x['original']+'"' for x in wrappers)+'};\n'
 src+='internal static byte[] Build(uint image,uint cave) { byte[] b=TerrainPatch.Hex("'+cb.hex()+'");\n'
 for off,im,cv in fixups:
  expr=[]
  if im:expr.append('(image-0x460000)')
  if cv==1:expr.append('(cave-0x10000000)')
  if cv==-1:expr.append('(0x10000000-cave)')
  src+=f'Add(b,{off},unchecked({"+".join(expr)}));\n'
 src+='return b;} static void Add(byte[] b,int o,uint d){Buffer.BlockCopy(BitConverter.GetBytes(unchecked(BitConverter.ToUInt32(b,o)+d)),0,b,o,4);}}\n'
 (a.out/'AiPolicyPayload.cs').write_text(src)
 print('AI_POLICY_BUILD_PASS',len(cb),'bytes',len(fixups),'relocations',len(wrappers),'hooks')
if __name__=='__main__':main()
