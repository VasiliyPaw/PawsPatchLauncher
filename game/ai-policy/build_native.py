import argparse,subprocess,sys,struct,json,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
SITES=[(0x1e54c7,0x1e552b,2,0,False),(0x1ded9c,0x1dc876,0,1,False),(0x1dee7c,0x1dc876,0,1,False),(0x1d1667,0x1ee5b3,5,2,True),(0x1d1838,0x1ee5b3,5,2,True),(0x1dc997,0x21cc0e,4,3,False),(0x1dcb10,0x21cc0e,4,3,False)]
SITES += [(s,0x1dd5b0,1,4,False) for s in (0x1dd2fb,0x1dd47c,0x1dd4de)]
SITES += [(0x1decbb,0x1dc808,2,5,False),(0x21ca57,0x222693,5,6,False),(0x21ca36,0x21de6a,4,7,False),(0x21cae2,0x21cb03,5,8,False),(0x21f34d,0x220a80,3,9,False)]
SITES += [(0x21c938,0x21de6a,4,7,False),(0x21c965,0x21d1e3,6,10,False)]
SITES += [(0x263443,0x020ece,0,11,False),(0x263736,0x020f30,0,12,False),
 (0x2635a2,0x2641fd,4,13,False),(0x2638bd,0x2641fd,4,13,False),
 (0x26260a,0x24a798,1,14,False),(0x250565,0x24a798,1,14,False),
 (0x26275f,0x24a798,1,14,False),(0x262c71,0x262616,3,15,True),
 (0x26486a,0x1f6318,1,16,True)]
SITES += [(0x1e0b05,0x020f30,0,17,False),
 (0x1e280f,0x2273b0,0,18,False),
 (0x1e50fa,0x1e5127,3,20,False),(0x202b3f,0x2937b8,2,21,False)]
SITES += [(0x1e4807,0x1e4e8c,3,22,False)] # live SelectGoals vector/budget, after native local exchange
SITES += [(0x1e4779,0x1e4c9d,3,23,False)] # pending-goal recruitment; caller performs native activation
SITES += [(0x1f77b6,0x1ee2f3,1,24,True)] # score before native attack-region candidate comparison
SITES += [(0x5b738,0x1f731b,1,25,True)] # guard native enemy/own region CV against 0/0
SITES += [(s,0x1e3cda,2,30,False) for s in (0x1e5547,0x1e58ee,0x1dc76a)] # native goal affordability
SITES += [(s,0x1deee8,1,31,False) for s in (0x1deccd,0x1decf3)] # replace company in final recruiting pass
SITES += [(0x1dc3c6,0x2f397,1,32,False)] # revalidate reserved replacement before native Disband command
SITES += [(0x1d48e3,0x5cee6,9,33,True)] # finish exploring a remembered settlement camp without an attack goal
SITES += [(0x1ef0d9,0x1f2cda,0,34,False), # native player's tactical update, AI-thread scope
 (0x1e8538,0x1e4736,3,35,False),(0x1e877f,0x1e47be,3,36,False),
 (0x1e89dd,0x1e3e34,1,38,False)] # native command affordability after a changed assignment
SITES += [(0x1e15c1,0x135740,6,39,False)] # log every overrun; rate-limit only the following UI formatting/notice
SITES += [(0x1dd748,0x05c7b9,3,40,True), # recruitment-only actor/property priority scope
 (0x05c7ef,0x1eeb0b,1,42,False),(0x05c888,0x1eeb0b,1,42,False),
 (0x05c87d,0x1eeb2b,1,43,False),
 (0x1dbf72,0x1eeb0b,1,44,False),(0x1dbf7c,0x1eeb2b,1,45,False), # specific recruit requests
 (0x1ecc8e,0x1ee8a3,1,46,False),(0x1ece64,0x1ee978,1,47,False), # owned actors; EDI survives callees
 (0x1e0253,0x1ec21c,4,48,False)] # native player reconstruction, before actor registration
SITES += [(s,0x1ee81a,2,49,True) for s in (0x1d54ee,0x1d5557)] # reject builders in native hero-target selection
SITES += [(0x1d5937,0x214a99,1,50,False)] # final native hero attachment validation
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
  args='mov eax,[ebp]; add eax,8;' if mode in (11,18) else 'lea eax,[ebp+8];'
  if mode==41:args='lea eax,[ebp-28];'
  if mode in (46,47):args='lea eax,[ebp-36];'
  # Native callers may keep live x87 temporaries below their return value.
  # Give the C callback its own empty stack with the caller's control word;
  # restore the complete original x87/SSE state afterwards.
  return ('pushfd; pushad; sub esp,528; lea eax,[esp+15]; and eax,0xfffffff0; fxsave [eax]; fninit; fldcw word ptr [eax]; push eax;'
   +f'lea eax,[ebp-8]; push eax; {args} push eax; push dword ptr [ebp-4]; push {mode}; push {data}; push {image}; call {base+fn}; add esp,24;'
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
 # This is a mapped PE image. Parse the game's relocation directory by RVA,
 # not raw file offsets. Absolute operands in guards must follow game ASLR.
 pe_offset=struct.unpack_from('<I',raw,60)[0]
 reloc_rva,reloc_size=struct.unpack_from('<II',raw,pe_offset+24+96+5*8)
 game_relocs=[];cursor=reloc_rva
 while cursor<reloc_rva+reloc_size:
  page,block_size=struct.unpack_from('<II',raw,cursor)
  assert block_size>=8 and cursor+block_size<=reloc_rva+reloc_size
  for entry in range(cursor+8,cursor+block_size,2):
   value=struct.unpack_from('<H',raw,entry)[0]
   if value>>12==3:game_relocs.append(page+(value&4095))
  cursor+=block_size
 for i,(site,target,argc,mode,fp) in enumerate(SITES):
  off=size+i*512;addr=base+off
  asm='push ebp; mov ebp,esp; sub esp,40; mov [ebp-4],ecx; mov dword ptr [ebp-8],0;'
  if mode==40:
   asm+=callback(40)+'popad; popfd; push eax; mov eax,[ebp-8]; mov [ebp-28],eax; pop eax; mov ecx,[ebp-4];'
  if mode in (46,47):asm+='mov [ebp-32],edi; push eax; mov eax,[ebp+8]; mov [ebp-36],eax; pop eax;'
  if mode==9:asm+=callback(mode)+'popad; popfd; cmp dword ptr [ebp-8],0; jne skipped; mov ecx,[ebp-4];'
  if mode==12:asm+=callback(mode)+'popad; popfd;'
  if mode in (23,35,36,38):
   asm+=callback(37 if mode==23 else mode)+'popad; popfd; cmp dword ptr [ebp-8],0; jne fast_skipped; mov ecx,[ebp-4];'
  if mode==31:asm+=callback(mode)+'popad; popfd; test dword ptr [ebp-8],0x100; je replacement_native; mov eax,[ebp-8]; and eax,255; jmp replacement_done; replacement_native: mov ecx,[ebp-4];'
  if mode==5:asm+=callback(29)+'popad; popfd; cmp dword ptr [ebp-8],0; je capacity_native; mov eax,[ebp-8]; jmp capacity_done; capacity_native: mov ecx,[ebp-4];'
  asm+=';'.join(f'push dword ptr [ebp+{8+j*4}]' for j in reversed(range(argc)))+';'
  asm+=f'call {image+target};'
  if mode in (23,35,36):asm+='fast_skipped:;'
  if mode==38:asm+='jmp fast_returned; fast_skipped: xor eax,eax; fast_returned:;'
  if mode==5:asm+='capacity_done:;'
  if mode in (8,39):asm+=f'lea esp,[esp+{argc*4}];' # cdecl caller removes copied arguments, preserving callee flags.
  # Keep the original extended-precision return for unchanged candidates.
  # Logging must not silently round every native priority to float32.
  asm+='fst dword ptr [ebp-8]; fstp tbyte ptr [ebp-24]; push eax; mov eax,[ebp-8]; mov [ebp-12],eax; pop eax;' if fp else 'mov [ebp-8],eax;'
  if mode not in (9,12,31,35,36,38):asm+=callback(41 if mode==40 else mode)
  if fp:asm+='mov eax,[ebp-8]; cmp eax,[ebp-12]; jne changed; fld tbyte ptr [ebp-24]; jmp returned; changed: fld dword ptr [ebp-8]; returned:;'
  if mode not in (9,12,31,35,36,38):asm+='popad; popfd;'
  if mode in (4,7,13,14,18,30,32,42,43,44,45,50):asm+='mov eax,[ebp-8];'
  if mode==9:asm+='skipped:;'
  if mode==31:asm+='replacement_done:;'
  if mode==39:
   # Skip the caller's six-argument cleanup together with UI formatting. No
   # temporary string exists yet. RET 24 removes those original arguments.
   # Preserve the native logger's flags in either branch.
   asm+=f'pushfd; cmp dword ptr [ebp-8],0; je notice_shown; popfd; mov dword ptr [ebp+4],{image+0x1e15e5}; mov esp,ebp; pop ebp; ret 24; notice_shown: popfd;'
  asm+=f'mov esp,ebp; pop ebp; ret {0 if mode in (8,39) else argc*4};'
  put(off,asm,[target]+([0x1e15e5] if mode==39 else []))
  original=raw[site:site+5];assert original==b'\xe8'+struct.pack('<i',target-site-5)
  guard_start=site-(5 if mode==39 else 3);guard_end=site+(14 if mode==22 else 10)
  guard_relocs=[r-guard_start for r in game_relocs if guard_start<=r<guard_end]
  assert all(0<=r<=guard_end-guard_start-4 for r in guard_relocs),'Guard cannot split a relocation'
  wrappers.append(dict(site=site,target=target,offset=off,original=original.hex(),guard=raw[guard_start:guard_end].hex(),guardStart=guard_start,guardRelocations=guard_relocs,argc=argc,mode=mode,fp=fp,cdecl=mode in (8,39),pre=mode in (9,12,31,35,36,38)))
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
 routing_size=struct.unpack_from('<I',cb,exports['routing_size'])[0]
 routing_report=query_pointer+4+struct.unpack_from('<I',cb,exports['routing_report_offset'])[0]
 data_size=struct.unpack_from('<I',cb,exports['policy_data_size'])[0]
 meta=dict(image=image,cave=base,codeSize=size+wrapper_size,dataOffset=size+wrapper_size,allocation=size+wrapper_size+data_size,queryOffset=query,queryPointerOffset=query_pointer,routingOffset=query_pointer+4,routingSize=routing_size,fixups=fixups,wrappers=wrappers,evaluate=fn)
 (a.out/'ai-policy.json').write_text(json.dumps(meta,indent=2))
 src='using System;\ninternal static class AiPolicyPayload {\n'
 src+=f'internal const int CodeSize={meta["codeSize"]}, DataOffset={meta["dataOffset"]}, Allocation={meta["allocation"]};\n'
 src+=f'internal const int QueryOffset={query}, QueryPointerOffset={query_pointer};\n'
 src+=f'internal const int RouteReportOffset={routing_report};\n'
 src+='internal static readonly uint[] Sites={'+','.join(str(x['site']) for x in wrappers)+'};\n'
 src+='internal static readonly uint[] GuardStarts={'+','.join(str(x['guardStart']) for x in wrappers)+'};\n'
 src+='internal static readonly uint[] Offsets={'+','.join(str(x['offset']) for x in wrappers)+'};\n'
 src+='internal static readonly string[] Guards={'+','.join('"'+x['guard']+'"' for x in wrappers)+'};\n'
 src+='internal static readonly int[][] GuardRelocations={'+','.join('new int[]{'+','.join(str(o) for o in x['guardRelocations'])+'}' for x in wrappers)+'};\n'
 src+='internal static byte[] Guard(int index,uint image){byte[] b=TerrainPatch.Hex(Guards[index]);foreach(int o in GuardRelocations[index])Add(b,o,unchecked(image-0x460000));return b;}\n'
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
