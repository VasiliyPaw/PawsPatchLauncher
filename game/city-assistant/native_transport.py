"""Observe local build/upgrade groups from successful send to native processing.

5343B8 serializes commands for BOTH TellActor and TellSelected. Only the local
request writer admin+274 is tracked (not decrees, recordings or replay buffers).
The ordering-player ID is set by the native SetPlayer envelope. A group ends
AFTER its entire native Process call, including every selected-actor payment.
No timeout is evidence of processing. Rejected/unacknowledged transport fails
closed until a native world boundary; the observer never modifies simulation.
"""

def install(m):
    S=m.S
    assert m.b.n.raw[0xd43b8:0xd43be]==bytes.fromhex('53568b742410')
    assert m.b.n.raw[0xd3d81:0xd3d87]==bytes.fromhex('568bf18b4e08')
    assert m.b.n.raw[0xd39dc:0xd39e1]==bytes.fromhex('b84a268800')
    # Native serialization prologue, with all incoming registers/flags restored.
    m.replace(0x7b00,f'''
pushfd; pushad
mov eax,dword ptr [0xa53fec]; test eax,eax; jz sent_done
lea edx,[eax+0x274]; cmp edx,dword ptr [esp+40]; jne sent_done
mov edx,dword ptr [eax+0x230]; test edx,edx; jz sent_done
cmp byte ptr [edx+0xe],0; jne sent_done
mov edx,dword ptr [edx+0x20]; mov ecx,dword ptr [esp+44]
xor eax,eax; call {S+0x7c80}
sent_done: popad; popfd
push ebx; push esi; mov esi,dword ptr [esp+0x10]; jmp 0x5343be
''',0x80)
    # Wrap the entire original process. The saved order is still referenced by
    # its native caller. Preserve the original return registers and flags.
    for offset,original in [(0x7b80,'push esi; mov esi,ecx; mov ecx,dword ptr [esi+8]; jmp 0x533d87'),
                            (0x7c00,'mov eax,0x88264a; jmp 0x5339e1')]:
        m.replace(offset,f'''
push ecx; call process_original
pushfd; pushad
mov eax,dword ptr [0xa53fec]; test eax,eax; jz processed_done
mov edx,dword ptr [eax+0x2a4]; test edx,edx; jz processed_done
cmp byte ptr [edx+0xe],0; jne processed_done
mov edx,dword ptr [edx+0x20]; mov ecx,dword ptr [esp+36]
mov ecx,dword ptr [ecx+4]; mov eax,1; call {S+0x7c80}
processed_done: popad; popfd; lea esp,[esp+4]; ret
process_original: {original}
''',0x80)
    # EAX 0 send / 1 processed, ECX command, EDX issuing player stable ID.
    # 128 groups {player,kind,target,count}; +d0 total, +dc unknown overflow.
    m.replace(0x7c80,f'''
push ebp; mov ebp,esp; sub esp,20
mov dword ptr [ebp-4],eax; mov dword ptr [ebp-8],edx
call {S+0x7f00}
test ecx,ecx; jz group_done
mov eax,dword ptr [ecx+8]; test eax,eax; jz group_done
mov eax,dword ptr [eax+0xc]
cmp eax,13; je group_kind
cmp eax,21; jne group_done
group_kind:
mov dword ptr [ebp-12],eax; mov eax,dword ptr [ecx+0x14]
test eax,eax; jz group_done
mov dword ptr [ebp-16],eax; mov dword ptr [ebp-20],0
inc dword ptr [{S+0xe0}]
mov edi,{S+0x1e000}; mov esi,128
group_find:
cmp dword ptr [edi+12],0; jne group_compare
cmp dword ptr [ebp-20],0; jne group_next
mov dword ptr [ebp-20],edi; jmp group_next
group_compare:
mov eax,dword ptr [ebp-8]; cmp eax,dword ptr [edi]; jne group_next
mov eax,dword ptr [ebp-12]; cmp eax,dword ptr [edi+4]; jne group_next
mov eax,dword ptr [ebp-16]; cmp eax,dword ptr [edi+8]; je group_found
group_next: add edi,16; dec esi; jnz group_find
cmp dword ptr [ebp-4],0; jne group_unlock
mov edi,dword ptr [ebp-20]; test edi,edi; jz group_unknown
mov eax,dword ptr [ebp-8]; mov dword ptr [edi],eax
mov eax,dword ptr [ebp-12]; mov dword ptr [edi+4],eax
mov eax,dword ptr [ebp-16]; mov dword ptr [edi+8],eax
group_found:
cmp dword ptr [ebp-4],0; jne group_processed
cmp dword ptr [{S+0xd0}],4096; jae group_unknown
inc dword ptr [edi+12]; inc dword ptr [{S+0xd0}]; jmp group_unlock
group_processed:
dec dword ptr [edi+12]; dec dword ptr [{S+0xd0}]; jmp group_unlock
group_unknown: mov dword ptr [{S+0xdc}],1
group_unlock: inc dword ptr [{S+0xe0}]
group_done: mov esp,ebp; pop ebp; ret
''',0x280)
    # Reset only at a verified native world/menu/time boundary, never because
    # buffers happen to be empty or a network round trip has taken too long.
    m.replace(0x7f00,f'''
pushfd; pushad
sub esp,16; movdqu xmmword ptr [esp],xmm0
mov ebx,dword ptr [0xa53fb8]
cmp dword ptr [0xa59218],2; je transport_world
xor ebx,ebx
transport_world:
cmp ebx,dword ptr [{S+0xd4}]; jne transport_reset
test ebx,ebx; jz transport_reset_done
movss xmm0,dword ptr [ebx+0xe8]; ucomiss xmm0,dword ptr [{S+0xd8}]
jb transport_reset
jmp transport_time
transport_reset:
inc dword ptr [{S+0xe0}]
mov dword ptr [{S+0xd4}],ebx
mov dword ptr [{S+0xd0}],0; mov dword ptr [{S+0xdc}],0
mov edi,{S+0x1e000}; xor eax,eax; mov ecx,512; cld; rep stosd
inc dword ptr [{S+0xe0}]
test ebx,ebx; jz transport_reset_done
transport_time:
mov eax,dword ptr [ebx+0xe8]; mov dword ptr [{S+0xd8}],eax
transport_reset_done: movdqu xmm0,xmmword ptr [esp]; lea esp,[esp+16]; popad; popfd; ret
''',0x100)
