"""Build lair-only survivor readiness. Dead/unknown slots must fully recover.

The native Denizen group has two unused padding bytes at +0x0e. All group
allocations initialize them; real return callbacks set a survivor marker;
deployment, death and loading clear it. Neither saves nor owner IDs change.
"""
import argparse, hashlib, json, struct, sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
sys.path[:0]=[str(a.legacy/'lobby_colors_1372/deps_r15'),str(a.legacy/'pydeps_readable')]
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
from capstone import Cs,CS_ARCH_X86,CS_MODE_32,CS_OP_IMM,CS_OP_MEM
raw=(a.legacy/'k2_runtime_1372_20260904.bin').read_bytes();BASE=0x460000
assert hashlib.sha256(raw).hexdigest()=='b865d8206990c4f055c51de857f0b09b88ab5ee3b6ae74ee5232134001aa591c'
# Constructor dispatch 25 stores KKC_LairComponent at actor+25*4+0x60.
assert struct.unpack_from('<I',raw,0x22E16D+0x19*4)[0]==0x68E088
assert raw[0x22E158:0x22E15C].hex()=='89749f60'
assert raw[0x212019:0x21201D].hex()=='6a1958c3'
ks=Ks(KS_ARCH_X86,KS_MODE_32);md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
def asm(s,at):return bytes(ks.asm(s,at)[0])
sites=[(0x20B5C0,'8845f284c0',0),(0x20B981,'8b41608b4010',0x100),
       (0x20BC9B,'8b46148901',0x180),(0x20A12E,'83ec18568b7118',0x400),
       (0x20B3E4,'558bec5156',0x700),(0x20B446,'558bec5153',0x900),
       (0x20A328,'d95f08eb33',0xC00),(0x20BFD7,'c7460800000000',0xC80),
       (0x20C3FF,'66894a0ceb02',0xD00),(0x20C508,'a5a5a5a55f',0xD40),
       (0x20AA77,'d95e088b7610',0xD80),(0x20C0DC,'d95e08ebea',0xDC0),
       (0x20C065,'f30f114708',0xE00),(0x20C25F,'8b4e08894808',0xE80),
       (0x20AE2F,'8b7424188bd9',0xEC0)]
for rva,old,_ in sites:assert raw[rva:rva+len(bytes.fromhex(old))].hex()==old

def build(image,cave):
    b=bytearray(b'\xcc'*0x1000)
    occupied=set()
    def put(off,s):
        blob=asm(s,cave+off)
        assert off+len(blob)<=len(b)
        assert not occupied.intersection(range(off,off+len(blob))),hex(off)
        occupied.update(range(off,off+len(blob)));b[off:off+len(blob)]=blob
        return len(blob)
    # EAX=Denizen -> AL scope. Actual component, independent of names/owners.
    put(0x200,f'''
      test eax,eax
      jz no
      mov ecx,[eax+4]
      test ecx,ecx
      jz no
      cmp [ecx+0x88],eax
      jne no
      mov edx,[ecx+0xc4]
      test edx,edx
      jz no
      cmp dword ptr [edx],{image+0x4E17AC}
      jne no
      cmp [edx+4],ecx
      jne no
      mov eax,1
      ret
    no:
      xor eax,eax
      ret
    ''')
    # Org deployment: replace readiness AL, preserve other live registers.
    put(0,f'''
      push eax
      push ecx
      push edx
      mov eax,[ebp-0x20]
      call {cave+0x200}
      test al,al
      jz done
      push esi
      mov esi,edi
      call {cave+0xB00}
      pop esi
      mov byte ptr [esp+8],al
      pop edx
      pop ecx
      pop eax
      mov [ebp-0xe],al
      test al,al
      jmp {image+0x20B628}
    done:
      pop edx
      pop ecx
      pop eax
      mov [ebp-0xe],al
      test al,al
      jmp {image+0x20B5C5}
    ''')
    # EAX=Denizen, ECX=new actor, EDX=stored group. Retain HP fraction;
    # preserve all GPR/flags and touched SSE registers, use native max health.
    put(0x280,f'''
      pushfd
      pushad
      sub esp,32
      movups [esp],xmm0
      movups [esp+16],xmm1
      mov esi,ecx
      mov edi,edx
      call {cave+0x200}
      test al,al
      jz done
      mov ebx,[esi+0x60]
      test ebx,ebx
      jz done
      mov ecx,[edi+4]
      push 0
      call {image+0x29B36}
      sub esp,4
      fstp dword ptr [esp]
      movss xmm1,[esp]
      add esp,4
      xorps xmm0,xmm0
      ucomiss xmm1,xmm0
      jbe done
      movss xmm0,[edi+8]
      divss xmm0,xmm1
      mulss xmm0,[ebx+0x14]
      minss xmm0,[ebx+0x10]
      movss [ebx+0x10],xmm0
      mov word ptr [edi+0xe],0
    done:
      movups xmm0,[esp]
      movups xmm1,[esp+16]
      add esp,32
      popad
      popfd
      ret
    ''')
    put(0x100,f'''
      push eax
      mov eax,[ebp-0x20]
      call {cave+0x280}
      pop eax
      mov eax,[ecx+0x60]
      mov eax,[eax+0x10]
      jmp {image+0x20B987}
    ''')
    put(0x180,f'''
      push eax
      push ecx
      push edx
      mov edx,ecx
      mov ecx,esi
      mov eax,edi
      call {cave+0x280}
      pop edx
      pop ecx
      pop eax
      mov eax,[esi+0x14]
      mov [ecx],eax
      jmp {image+0x20BCA0}
    ''')
    def copy_native(rva,end,offset,changes):
        block=bytearray(raw[rva:end]);oldbase=BASE+rva;newbase=cave+offset
        for ins in md.disasm(block,oldbase):
            pos=ins.address-oldbase
            for op in ins.operands:
                if op.type==CS_OP_IMM and ins.mnemonic in ('call','jmp') and not oldbase<=op.imm<BASE+end:
                    assert ins.imm_size==4
                    dest=image+op.imm-BASE
                    struct.pack_into('<I',block,pos+ins.imm_offset,(dest-(newbase+pos+ins.size))&0xffffffff)
                if op.type==CS_OP_MEM and not op.mem.base and not op.mem.index and BASE<=op.mem.disp<BASE+len(raw):
                    assert ins.disp_size==4
                    struct.pack_into('<I',block,pos+ins.disp_offset,image+op.mem.disp-BASE)
        for where,expect,new in changes:
            rel=where-rva;old=bytes.fromhex(expect)
            assert block[rel:rel+len(old)]==old and len(old)==len(new)
            block[rel:rel+len(new)]=new
        b[offset:offset+len(block)]=block
    # Cities use original code. Lairs use native counters with readiness changed.
    for rva,entry,copyoff,n in [(0x20A12E,0x400,0x450,7),(0x20B3E4,0x700,0x750,5),(0x20B446,0x900,0x950,5)]:
        length=put(entry,f'''
          push eax
          push ecx
          push edx
          mov eax,ecx
          call {cave+0x200}
          test al,al
          pop edx
          pop ecx
          pop eax
          jnz {cave+copyoff}
        ''')
        b[entry+length:entry+length+n]=raw[rva:rva+n]
        put(entry+length+n,f'jmp {image+rva+n}')
    copy_native(0x20A12E,0x20A28C,0x450,[])
    positive=asm(f'xorps xmm1,xmm1; ucomiss xmm0,xmm1; jbe {cave+0x450+0x107}',cave+0x450+0x9B)
    assert len(positive)<=13
    positive+=b'\x90'*(13-len(positive))
    b[0x450+0x9B:0x450+0x9B+13]=positive
    # Preserve native HP sums and map keys, replace only lair readiness.
    off=0x450+0x20A1E1-0x20A12E
    end=0x450+0x20A22E-0x20A12E
    blob=asm(f'''fstp dword ptr [esp+0x18]
      call {cave+0xB00}
      test al,al
      jz {cave+0x450+0x20A235-0x20A12E}
      jmp {cave+end}''',cave+off)
    assert len(blob)<=end-off
    b[off:end]=blob+b'\x90'*(end-off-len(blob))
    copy_native(0x20B3E4,0x20B446,0x750,[])
    off=0x750+0x20B3FE-0x20B3E4;end=0x750+0x20B432-0x20B3E4
    blob=asm(f'call {cave+0xB00}',cave+off)
    b[off:end]=blob+b'\x90'*(end-off-len(blob))
    # A nonzero counter alone is insufficient: chooser must skip regenerating
    # dead slots too, including a dead slot with more HP than the survivor.
    copy_native(0x20B446,0x20B4A8,0x950,[])
    off=0x950+0x20B464-0x20B446
    blob=asm(f'call {cave+0xB00}; test al,al; jz {cave+0x950+0x20B48D-0x20B446}',cave+off)
    assert len(blob)==9
    b[off:off+9]=blob
    # ESI=group -> EAX=ready. Preserve every other GPR, flags, SSE and x87
    # stack. Deployed living units still count in the native UI.
    put(0xB00,f'''
      pushfd
      pushad
      sub esp,20
      movups [esp],xmm0
      cmp dword ptr [esi],0
      jne ready
      mov ebx,[esi+8]
      test ebx,ebx
      jle no
      cmp ebx,0x7f800000
      jae no
      cmp word ptr [esi+0xe],0x4c53
      je ready
      mov ecx,[esi+4]
      push 0
      call {image+0x29B36}
      fstp dword ptr [esp+16]
      mov edx,[esp+16]
      test edx,edx
      jle no
      cmp edx,0x7f800000
      jae no
      cmp ebx,edx
      jb no
    ready:
      mov dword ptr [esp+48],1
      jmp done
    no:
      mov dword ptr [esp+48],0
    done:
      movups xmm0,[esp]
      add esp,20
      popad
      popfd
      ret
    ''')
    # Group padding is private metadata only. Standard city logic never reads
    # it. Initialize BOTH allocation routes (including copies of stack data).
    put(0xD00,f'mov dword ptr [edx+0xc],ecx; jmp {image+0x20C407}')
    put(0xD40,f'''.byte 0xa5,0xa5,0xa5,0xa5
      mov word ptr [eax+0xe],0
      pop edi
      jmp {image+0x20C50D}''')
    # Exact actor-ID return, fallback unit return and pooled return all prove
    # that a living unit entered the building. Zero HP never grants readiness.
    for off,reg,store,continuation in [
      (0xC00,'edi','fstp dword ptr [edi+8]',0x20A360),
      (0xDC0,'esi','fstp dword ptr [esi+8]',0x20C0CB),
      (0xE00,'edi','movss [edi+8],xmm0',0x20C06A)]:
        put(off,f'''{store}
          pushfd
          push eax
          mov word ptr [{reg}+0xe],0
          mov eax,[{reg}+8]
          test eax,eax
          jle done
          cmp eax,0x7f800000
          jae done
          mov word ptr [{reg}+0xe],0x4c53
        done:
          pop eax
          popfd
          jmp {image+continuation}''')
    put(0xC80,f'''mov dword ptr [esi+8],0
      mov word ptr [esi+0xe],0
      jmp {image+0x20BFDE}''')
    # Legacy saves have no survivor/death provenance. Do not reinterpret their
    # partial HP as alive: wait for full regeneration after loading.
    put(0xD80,f'''fstp dword ptr [esi+8]
      mov word ptr [esi+0xe],0
      mov esi,[esi+0x10]
      jmp {image+0x20AA7D}''')
    put(0xE80,f'''mov ecx,[esi+8]
      mov [eax+8],ecx
      push ecx
      mov cx,[esi+0xe]
      mov [eax+0xe],cx
      mov word ptr [esi+0xe],0
      pop ecx
      jmp {image+0x20C265}''')
    # Zero HP always starts a replacement, including non-death engine resets.
    # Clear before native resupply adds its first positive HP, not in UI reads.
    put(0xEC0,f'''mov esi,[esp+0x18]
      mov ebx,ecx
      pushfd
      cmp dword ptr [esi+8],0
      jg done
      mov word ptr [esi+0xe],0
    done:
      popfd
      jmp {image+0x20AE35}''')
    return bytes(b)

image,cave=BASE,0x10000000;code=build(image,cave)
image2=build(image+0x10000,cave);cave2=build(image,cave+0x10000);fix=[]
for i in range(len(code)):
    if code[i]!=image2[i] or code[i]!=cave2[i]:
        if any(x[0]<=i<x[0]+4 for x in fix):continue
        off=i-2;assert off>=0;v=struct.unpack_from('<I',code,off)[0]
        di=(struct.unpack_from('<I',image2,off)[0]-v)&0xffffffff
        dc=(struct.unpack_from('<I',cave2,off)[0]-v)&0xffffffff
        assert di in (0,0x10000) and dc in (0,0xffff0000),(off,di,dc)
        fix.append((off,di!=0,dc!=0))
def relocate(ib,cb):
    out=bytearray(code)
    for off,im,cv in fix:
        value=struct.unpack_from('<I',out,off)[0]+(ib-image if im else 0)-(cb-cave if cv else 0)
        struct.pack_into('<I',out,off,value&0xffffffff)
    return bytes(out)
for ib,cb in [(0xE40000,0x21000000),(0x12000000,0x60000000)]:assert relocate(ib,cb)==build(ib,cb)
a.out.mkdir(parents=True,exist_ok=True)
(a.out/'lair_recovery.bin').write_bytes(code)
(a.out/'lair_recovery.json').write_text(json.dumps({'revision':3,'image':image,'cave':cave,'fixups':fix,'sites':sites},indent=2))
(a.out/'lair_recovery.asm.txt').write_text('\n'.join(f'{i.address-cave:04X} {i.bytes.hex():24} {i.mnemonic:8} {i.op_str}' for i in md.disasm(code,cave)))
src='// Generated by build_native.py; do not hand edit.\nusing System;\ninternal static class LairRecoveryPayload {\n internal static byte[] Build(uint image,uint cave) {\n  byte[] b=TerrainPatch.Hex("'+code.hex().upper()+'");\n'
for off,im,cv in fix:
    expression=('image-0x460000' if im else '0')+('-cave+0x10000000' if cv else '')
    src+=f'  Add(b,{off},unchecked({expression}));\n'
src+='  return b;\n }\n'
src+=' internal static readonly uint[] Sites={'+','.join(f'0x{s:X}' for s,_,_ in sites)+'};\n'
src+=' internal static readonly uint[] Offsets={'+','.join(f'0x{s:X}' for _,_,s in sites)+'};\n'
src+=' internal static readonly byte[][] Originals={'+','.join('TerrainPatch.Hex("'+s.upper()+'")' for _,s,_ in sites)+'};\n'
src+=' internal static void ValidateOriginalFunctions(IMemory memory,uint image) {VisitGuards(image,delegate(uint a,byte[] b){TerrainPatch.Expect(memory,a,b);});}\n internal static void VisitGuards(uint image,Action<uint,byte[]> sink) {\n byte[] b;\n'
guards=[]
for start,end in [(0x20A12E,0x20A28C),(0x20B3E4,0x20B4A8),(0x29B36,0x29B62),
                  (0x20A315,0x20A32D),(0x20C3DF,0x20C41B),(0x20C4D9,0x20C515),
                  (0x20BF9C,0x20BFE0),(0x20AA6A,0x20AA82)]:
    block=raw[start:end];absolute=[]
    for ins in md.disasm(block,BASE+start):
        for op in ins.operands:
            if op.type==CS_OP_MEM and not op.mem.base and not op.mem.index and BASE<=op.mem.disp<BASE+len(raw):
                absolute.append(ins.address-BASE-start+ins.disp_offset)
    src+=' b=TerrainPatch.Hex("'+block.hex().upper()+'");\n'
    for off in absolute:src+=f' Add(b,{off},unchecked(image-0x460000));\n'
    src+=f' sink(image+0x{start:X},b);\n'
    guards.append({'rva':start,'bytes':block.hex(),'absolute':absolute})
src+=' }\n static void Add(byte[] b,int o,uint d){Buffer.BlockCopy(BitConverter.GetBytes(unchecked(BitConverter.ToUInt32(b,o)+d)),0,b,o,4);}\n}\n'
(a.out/'guards.json').write_text(json.dumps(guards,indent=2))
(a.out/'LairRecoveryPayload.cs').write_text(src)
print(f'Built r3: {len(code)} native bytes, {len(fix)} relocations at three bases; {len(sites)} hooks, lair-only readiness.')
