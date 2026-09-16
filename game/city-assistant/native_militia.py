"""Observe city centers/children and issue normal, ownership-checked orders.

30000..31000 is a separate executable page; 31000..41000 holds up to 4096
16-byte records (city ID, actor ID, capability state, work flags:
bit 0 construction, bit 1 temporarily blocked by the 0x40000000 state).
No simulation flags are written. Both opening (23) and recall (24) use the
same registered TellActorCommandOrder transport as a player's button click.
"""


def install(m):
    # Stock DenizenComponent::UpdateCommands (668FD9) suppresses commands for
    # 0x40000000, not siege (0x00100000). Do not reuse the economic-order mask:
    # a player's sally/recall button remains available while under siege.
    S, b = m.S, m.b
    b.payload.extend(bytes(0x41000 - len(b.payload)))
    b.n.SIZE = 0x41000
    m.replace(0x7800, f'jmp {S+0x30000}', 0x100)
    m.replace(0x30000, f'''
push ebx; push esi; push edi
mov edi,ecx; mov esi,dword ptr [edi+0x98]
test esi,esi; jz militia_city_bad
cmp dword ptr [esi+0x1c],256; ja militia_city_bad
mov eax,dword ptr [esi+0x14]; test eax,eax; jz militia_children_start
push eax; push edi; call {S+0x30200}; add esp,8
militia_children_start: xor ebx,ebx
militia_children:
cmp ebx,dword ptr [esi+0x1c]; jae militia_city_done
mov eax,dword ptr [esi+0x18]; test eax,eax; jz militia_city_bad
mov eax,dword ptr [eax+ebx*4]; test eax,eax; jz militia_city_bad
cmp eax,dword ptr [esi+0x14]; je militia_child_next
push eax; push edi; call {S+0x30200}; add esp,8
militia_child_next: inc ebx; jmp militia_children
militia_city_bad: mov dword ptr [{S+0x1ac}],0
militia_city_done: pop edi; pop esi; pop ebx; ret
''', 0x200)
    m.replace(0x30200, f'''
push ebp; mov ebp,esp; push ebx; push esi; push edi
mov edi,dword ptr [ebp+12]; mov ecx,edi
mov eax,dword ptr [ecx]; call dword ptr [eax+0x108]
cmp eax,dword ptr [{S+0x10c}]; jne militia_actor_done
mov esi,dword ptr [{S+0x1a8}]; cmp esi,4096; jae militia_actor_bad
shl esi,4; add esi,{S+0x31000}
mov eax,dword ptr [ebp+8]; mov eax,dword ptr [eax+0x14]; mov dword ptr [esi],eax
mov eax,dword ptr [edi+0x14]; mov dword ptr [esi+4],eax
mov dword ptr [esi+8],0; mov dword ptr [esi+12],0
mov eax,dword ptr [ebp+8]; mov eax,dword ptr [eax+0x100]
or eax,dword ptr [edi+0x100]
test eax,0x40000000; jz militia_check_construction
or dword ptr [esi+12],2
militia_check_construction:
test dword ptr [edi+0x100],0x20200000; jnz militia_unfinished
mov eax,dword ptr [edi+0x9c]; test eax,eax; jz militia_probe
cmp dword ptr [eax+0x28],0; jne militia_unfinished
militia_probe:
mov ecx,edi; mov eax,dword ptr [ecx]; push 24; call dword ptr [eax+0x34]
test al,al; jz militia_probe_closed
mov dword ptr [esi+8],2; jmp militia_actor_append
militia_probe_closed:
mov ecx,edi; mov eax,dword ptr [ecx]; push 23; call dword ptr [eax+0x34]
test al,al; jz militia_actor_append
mov dword ptr [esi+8],1; jmp militia_actor_append
militia_unfinished: or dword ptr [esi+12],1
militia_actor_append: inc dword ptr [{S+0x1a8}]; jmp militia_actor_done
militia_actor_bad: mov dword ptr [{S+0x1ac}],0
militia_actor_done: pop edi; pop esi; pop ebx; pop ebp; ret
''', 0x200)
    # Return a CURRENT child pointer only if it still belongs to the requested
    # owned city. Never trust a pointer/owner captured in an earlier snapshot.
    m.replace(0x30400, f'''
push ebx; push esi; push edi
mov ecx,dword ptr [0xa4f72c]; push dword ptr [{S+0x198}]; call 0x481117
test eax,eax; jz militia_find_none; mov edi,eax
mov ecx,edi; mov eax,dword ptr [ecx]; call dword ptr [eax+0x108]
cmp eax,dword ptr [{S+0x10c}]; jne militia_find_none
test dword ptr [edi+0x100],0x40000000; jnz militia_find_wait
mov esi,dword ptr [edi+0x98]; test esi,esi; jz militia_find_none
cmp dword ptr [esi+0x1c],256; ja militia_find_none
mov edi,dword ptr [esi+0x14]; test edi,edi; jz militia_find_children
mov eax,dword ptr [edi+0x14]; cmp eax,dword ptr [{S+0x188}]; je militia_find_owner
militia_find_children: xor ebx,ebx
militia_find_loop:
cmp ebx,dword ptr [esi+0x1c]; jae militia_find_none
mov eax,dword ptr [esi+0x18]; test eax,eax; jz militia_find_none
mov edi,dword ptr [eax+ebx*4]; inc ebx; test edi,edi; jz militia_find_none
mov eax,dword ptr [edi+0x14]; cmp eax,dword ptr [{S+0x188}]; jne militia_find_loop
militia_find_owner:
mov ecx,edi; mov eax,dword ptr [ecx]; call dword ptr [eax+0x108]
cmp eax,dword ptr [{S+0x10c}]; jne militia_find_none
test dword ptr [edi+0x100],0x60200000; jnz militia_find_wait
mov eax,dword ptr [edi+0x9c]; test eax,eax; jz militia_find_ok
cmp dword ptr [eax+0x28],0; jne militia_find_wait
militia_find_ok: mov eax,edi; jmp militia_find_done
militia_find_wait: mov dword ptr [{S+0x190}],4
militia_find_none: xor eax,eax
militia_find_done: pop edi; pop esi; pop ebx; ret
''', 0x200)
    # Immutable mailbox: 180 serial,184 epoch,188 actor ID,18c time,
    # 190 result,194 reply,198 city ID,19c desired open state (0/1).
    m.replace(0x7400, f'''
push ebp; mov ebp,esp; sub esp,32; push ebx; push esi; push edi
mov eax,dword ptr [{S+0x180}]; cmp eax,dword ptr [{S+0x194}]; je militia_done
mov dword ptr [ebp-4],eax; mov dword ptr [{S+0x190}],2
cmp dword ptr [{S+0x128}],1; jne militia_reply
cmp dword ptr [{S+0xb4}],0; jne militia_reply
mov eax,dword ptr [{S+0x19c}]; cmp eax,1; ja militia_reply
cmp eax,dword ptr [{S+0xc0}]; jne militia_reply
mov ebx,24; sub ebx,eax
mov eax,dword ptr [{S+0x184}]; cmp eax,dword ptr [{S+0x104}]; jne militia_reply
movss xmm0,dword ptr [{S+0x110}]; ucomiss xmm0,dword ptr [{S+0x18c}]
jp militia_reply; jbe militia_done
call {S+0x30400}; test eax,eax; jz militia_reply; mov edi,eax
mov edx,47; sub edx,ebx
mov ecx,edi; mov eax,dword ptr [ecx]; push edx; call dword ptr [eax+0x34]
test al,al; jnz militia_already
mov ecx,edi; mov eax,dword ptr [ecx]; push ebx; call dword ptr [eax+0x34]
test al,al; jz militia_reply
push 64; call 0x74f03c; add esp,4; test eax,eax; jz militia_reply
mov ecx,eax; push ebx; call 0x68f4e9
inc dword ptr [eax+4]; mov dword ptr [ebp-8],eax
push edi; lea eax,[ebp-8]; push eax; lea ecx,[ebp-20]; call 0x52d843
lea ecx,[ebp-20]; call 0x533d5f; test al,al; jz militia_destroy
lea ecx,[ebp-20]; call 0x533d57
mov dword ptr [{S+0x190}],1
militia_destroy: lea ecx,[ebp-20]; call 0x533d3c; jmp militia_reply
militia_already: mov dword ptr [{S+0x190}],3
militia_reply: mov eax,dword ptr [ebp-4]; mov dword ptr [{S+0x194}],eax
militia_done: pop edi; pop esi; pop ebx; mov esp,ebp; pop ebp; ret
''', 0x400)
