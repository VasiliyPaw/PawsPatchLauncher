"""Local party preferences and read-only successful-save notifications.

Verified 1.3.72: SessionSource +8 = m_filename (debug label 91e920),
source kind +4 = 2 for saves. SaveGame task 62184d catches failure and calls
62e720 with status 2 only on success (3 on failure), task +20 is filename.
No save serialization, file content or simulation state is altered.
"""

def prepare_load(m, load):
    S=m.S
    start=load.index('test ebx,ebx; jz load_done')
    end=load.index('load_done:',start)
    load=load[:start]+f'''test ebx,ebx; jz load_done
push 100; mov ecx,dword ptr [{S+0x50}]; call 0x704c74
inc dword ptr [{S+0x5c}]
'''+load[end:]
    return load.replace('load_done:',f'load_done: call {S+0x30600}')

def install(m):
    S,b=m.S,m.b
    b.payload.extend(bytes(0x46000-len(b.payload)));b.n.SIZE=0x46000
    assert b.n.raw[0x1c19f9:0x1c19fe]==bytes.fromhex('e822cd0000')
    # Render committed values, including the toggle, after a party switch or
    # panel recreation. Never re-import stale widget values during restoration.
    m.replace(0x30600,f'''
pushfd; pushad
cmp dword ptr [{S+0xb8}],1; jne render_done
mov ecx,dword ptr [{S+0x4c}]; test ecx,ecx; jz render_done
cmp dword ptr [{S+0x40}],0; je render_off
push 1; push 0; call 0x7186d4; jmp render_numbers
render_off: push 1; push 0; call 0x7186f2
render_numbers:
call {S+0x4000}; call {S+0x6500}
mov dword ptr [{S+0x58}],1
render_done: popad; popfd; ret
''',0x100)
    m.replace(0x1c00,f'''
cmp dword ptr [{S+0x7c}],0; je render_return
jmp {S+0x30600}
render_return: ret
''',0x200)
    # Even revision publishes the copied source identity. Managed side restores
    # through a suspended process and ACKs that exact generation before ready.
    m.replace(0x1a00,f'''
pushfd; pushad
cmp dword ptr [0xa59218],2; jne inactive
mov ebx,dword ptr [0xa53fb8]; test ebx,ebx; jz inactive
cmp ebx,dword ptr [{S+0x74}]; jne boundary
movss xmm0,dword ptr [ebx+0xe8]; ucomiss xmm0,dword ptr [{S+0x78}]
jp active; jae active
boundary:
inc dword ptr [{S+0x1b0}]
mov dword ptr [{S+0xb8}],0; mov dword ptr [{S+0x58}],0
mov dword ptr [{S+0x7c}],1; mov dword ptr [{S+0x80}],0
mov dword ptr [{S+0x84}],0; mov dword ptr [{S+0x88}],0
mov dword ptr [{S+0x1b8}],-1; mov word ptr [{S+0x1f000}],0
mov eax,dword ptr [0xa53fe4]; test eax,eax; jz source_done
mov ecx,dword ptr [eax+0x64]; mov dword ptr [{S+0x1b8}],ecx
mov esi,dword ptr [eax+0x68]; mov edi,{S+0x1f000}; call {S+0x30700}
source_done:
mov dword ptr [{S+0x1bc}],ebx
inc dword ptr [{S+0x1b0}]
active:
mov dword ptr [{S+0x74}],ebx
mov eax,dword ptr [ebx+0xe8]; mov dword ptr [{S+0x78}],eax
call {S+0x1c00}; jmp done
inactive: mov dword ptr [{S+0x74}],0
done: popad; popfd; ret
''',0x200)
    # ESI native GameString text -> EDI bounded UTF-16 buffer, no native calls.
    m.replace(0x30700,'''
mov word ptr [edi],0; cmp esi,0x10000; jb copy_return
mov ecx,dword ptr [esi-12]; test ecx,ecx; jz copy_return
cmp ecx,511; ja copy_return
cld; rep movsw; mov word ptr [edi],0
copy_return: ret
''',0x100)
    # Patched CALL site uses a JMP trampoline; original argument is still on
    # stack. Publish a bounded 16-slot ring only after SaveGame succeeded.
    m.replace(0x30900,f'''
pushfd; pushad
cmp dword ptr [esp+36],2; jne saved_done
cmp dword ptr [{S+0xb8}],1; jne saved_done
mov eax,dword ptr [{S+0x1b0}]; test eax,eax; jz saved_done
test eax,1; jnz saved_done
cmp eax,dword ptr [{S+0x1b4}]; jne saved_done
mov ebx,dword ptr [{S+0x1c0}]; inc ebx
mov edx,ebx; and edx,15; imul edx,edx,0x500; add edx,{S+0x41000}
mov dword ptr [edx],0; mov dword ptr [edx+4],eax
mov esi,dword ptr [esi+0x20]; lea edi,[edx+16]; call {S+0x30700}
mov eax,dword ptr [{S+0x40}]; mov dword ptr [edx+0x410],eax
mov eax,dword ptr [{S+0x44}]; mov dword ptr [edx+0x414],eax
mov esi,{S+0x1b004}; lea edi,[edx+0x418]; mov ecx,4; cld; rep movsd dword ptr es:[edi], dword ptr [esi]
mov dword ptr [edx],ebx; mov dword ptr [{S+0x1c0}],ebx
saved_done: popad; popfd
call 0x62e720; jmp 0x6219fe
''',0x200)
