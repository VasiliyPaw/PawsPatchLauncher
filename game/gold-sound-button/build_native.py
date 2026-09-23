"""Extend the common UI payload; preserve the existing formatter/menu bytecode."""
from pathlib import Path
import argparse, hashlib, json, struct, sys

def build(analysis, out):
    sys.path[:0] = [str(analysis/'pydeps_readable'), str(analysis/'lobby_colors_1372/deps_r15')]
    from keystone import Ks, KS_ARCH_X86, KS_MODE_32
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_IMM
    beta = Path(__file__).resolve().parents[1]/'beta7'
    raw = bytearray((beta/'PawCommonUiPayload.bin').read_bytes())
    fix = (beta/'PawCommonUiFixups.bin').read_bytes()
    fixes = [struct.unpack_from('<III',fix,i) for i in range(4,len(fix),12)]
    # Our three reserved areas are outside both existing hooks and menu labels.
    raw[0x1fc:0x2d4] = bytes(0xd8)
    raw[0x600:0x800] = bytes(0x200)
    fixes = [f for f in fixes if not (0x1fc <= f[1] < 0x2d4 or 0x600 <= f[1] < 0x800)]
    assert hashlib.sha256(raw).hexdigest() == 'fcb67709ac4cc85ea8f67252fff7c083b11de3e4ab0c28d5505d9896368df2a3'
    assert len(fixes) == 5
    native = (analysis/'k2_runtime_1372_20260904.bin').read_bytes()
    assert hashlib.sha256(native).hexdigest() == 'b865d8206990c4f055c51de857f0b09b88ab5ee3b6ae74ee5232134001aa591c'
    image, cave = 0x460000, 0x10000000
    # The extra Game child has no simulation command. Its copied vtable changes
    # Activate (nullable action) and explicitly retains a normal zero sort key.
    # Mouse press/release still uses the native sound/pressed-state handling.
    for off in range(-4,0xd4,4):
        target = struct.unpack_from('<I',native,0x504be4+off)[0]
        kind,value = (2,0x780) if off == 0x6c else (2,0x790) if off == 0xa8 else (1,target-image)
        dest = 0x200+off
        struct.pack_into('<I',raw,dest,(cave if kind==2 else image)+value)
        fixes.append((kind,dest,value))
    raw[0x780] = 0xc3
    # Attach early, after VWorld but before SidePanel. Equal-key native children
    # are stable, so menus cover the button and receive clicks before it.
    raw[0x790:0x793] = bytes.fromhex('d9eec3') # fldz; ret
    name = 'PawGoldSoundButton\0'.encode('utf-16le')
    raw[0x700:0x700+len(name)] = name
    source = f'''
        push ebp
        mov ebp, esp
        push ecx
        push dword ptr [ebp+8]
        call dword ptr [edx+0xd0]
        pushfd
        pushad
        sub esp, 544
        lea eax, [esp+15]
        and eax, 0xfffffff0
        fxsave [eax]
        fninit
        fldcw word ptr [eax]
        push eax
        sub esp, 4
        mov ecx, esp
        push {cave+0x700}
        call {image+0x205de}
        mov esi, esp
        push 0
        push 0
        push 0
        push 1
        push esi
        call {image+0x2b88c0}
        add esp, 20
        mov edi, eax
        mov ecx, [esi]
        sub ecx, 16
        call {image+0x21375}
        add esp, 4
        test edi, edi
        jz done
        mov dword ptr [edi], {cave+0x200}
        mov ecx, [ebp-4]
        push 0
        push edi
        call {image+0x2b7486}
        test al, al
        jnz done
        mov ecx, edi
        mov eax, [edi]
        push 1
        call dword ptr [eax]
    done:
        pop eax
        fxrstor [eax]
        add esp, 544
        popad
        popfd
        leave
        ret 4
    '''
    code = bytes(Ks(KS_ARCH_X86,KS_MODE_32).asm(source,cave+0x600)[0])
    assert len(code) <= 0x100
    raw[0x600:0x600+len(code)] = code
    md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
    for ins in md.disasm(code,cave+0x600):
        for operand in ins.operands:
            if operand.type != CS_OP_IMM: continue
            value=operand.imm & 0xffffffff
            at=ins.address-cave+ins.imm_offset
            if image <= value < image+0x700000 and ins.mnemonic=='call': fixes.append((3,at,value-image))
            elif cave <= value < cave+0x1000 and ins.mnemonic in ('push','mov'): fixes.append((2,at,value-cave))
    assert len({f[1] for f in fixes})==len(fixes) <=128
    (beta/'PawCommonUiPayload.bin').write_bytes(raw)
    (beta/'PawCommonUiFixups.bin').write_bytes(struct.pack('<I',len(fixes))+b''.join(struct.pack('<III',*f) for f in fixes))
    out.mkdir(parents=True,exist_ok=True)
    assert native[0xc772e:0xc7734] == bytes.fromhex('ff92d0000000')
    (out/'sound-button-native.json').write_text(json.dumps({'hookRva':0xc772e,'originalVirtualMethodOffset':0xd0,'caveOffset':0x600,'codeBytes':len(code),'fixups':len(fixes),'payloadSha256':hashlib.sha256(raw).hexdigest(),'simulationCommands':False},indent=2))
    (out/'sound-button.asm').write_text(source)
    print('SOUND_BUTTON_NATIVE_BUILT',len(code),'bytes;',len(fixes),'relocations')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--analysis',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();build(a.analysis,a.out)
