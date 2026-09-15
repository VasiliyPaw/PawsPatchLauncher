"""Native queue-aware city/mine automation and the ordinary militia command.

Accepted build/upgrade orders are already prepaid actors/components, including
work waiting for builders (67f305 -> 680a80 and 665d6f -> 665de0). Do not create
a second private construction queue or debit that work again. Militia uses the
registered sally_forth command 23, with recall 24 as the native open-state probe.
"""

def install(m, load):
    S,b=m.S,m.b
    def replace_once(text,old,new):
        assert text.count(old)==1,old
        return text.replace(old,new)
    capture=replace_once(m.capture_code,'bridge_complete: mov',f'''bridge_complete: call {S+0x6d00}
mov eax,dword ptr [{S+0xd0}]; mov dword ptr [{S+0x134}],eax
mov edx,dword ptr [{S+0xdc}]; mov dword ptr [{S+0x138}],edx
or eax,edx; jnz transport_wait
mov eax,dword ptr [{S+0xe0}]; test eax,1; jnz transport_wait
cmp eax,dword ptr [{S+0xe4}]; je transport_ready
transport_wait:
mov dword ptr [{S+0x130}],0
transport_ready: mov''')
    capture=replace_once(capture,f'mov ecx,edi; call {S+0x5700}',f'mov ecx,edi; call {S+0x7800}\nmov ecx,edi; call {S+0x5700}')
    capture=replace_once(capture,f'call {S+0x3000}',f'call {S+0x3000}; call {S+0x7400}')
    # Retain world age at the first native observation, before local kingdom/UI
    # readiness. Invalid snapshots can reset the bridge epoch; they must not
    # lose a fresh world's initial timestamp. Clear only on an actual menu exit.
    capture=replace_once(capture,f'cmp ebx,dword ptr [{S+0x108}]',f'call {S+0x1e00}\ncmp ebx,dword ptr [{S+0x108}]')
    capture=replace_once(capture,'bridge_inactive:',f'''bridge_inactive:
cmp dword ptr [0xa59218],2; je preserve_world_birth
mov dword ptr [{S+0x1a0}],0
preserve_world_birth:''')
    capture=replace_once(capture,f'mov dword ptr [{S+0x128}],0',
        f'mov dword ptr [{S+0x128}],0; mov dword ptr [{S+0x1a8}],0; mov dword ptr [{S+0x1ac}],1')
    m.replace(0x2000,capture,0x800)
    assert set(b.payload[0x1e00:0x1e80]) <= {0, 0x90}, 'World-birth code reservation is occupied'
    m.replace(0x1e00,f'''
push eax
cmp ebx,dword ptr [{S+0x1a0}]; jne birth_new
movss xmm0,dword ptr [ebx+0xe8]; ucomiss xmm0,dword ptr [{S+0x1a4}]
jae birth_update
birth_new:
mov dword ptr [{S+0x1a0}],ebx
mov eax,dword ptr [ebx+0xe8]; mov dword ptr [{S+0x13c}],eax
birth_update:
mov eax,dword ptr [ebx+0xe8]; mov dword ptr [{S+0x1a4}],eax
pop eax; ret
''',0x80)

    # Another actor's queued work does not block this settlement. Native
    # CanBuild still owns capacity, terrain, branch and payment legality.
    m.replace(0x2800,f'''
test dword ptr [ecx+0x100],0x40100000; jnz city_blocked
mov eax,dword ptr [ecx+0x98]; test eax,eax; jz structure_check
cmp dword ptr [eax+0x1c],256; ja city_blocked
mov eax,dword ptr [eax+0x14]; test eax,eax; jz city_blocked
test dword ptr [eax+0x100],0x40100000; jnz city_blocked
xor eax,eax; ret
structure_check:
cmp dword ptr [ecx+0x94],0; je city_blocked
jmp {S+0x2900}
city_blocked: mov eax,1; ret
''',0x100)
    m.replace(0x2900,'''
test dword ptr [ecx+0x100],0x60300000; jnz actor_busy
mov eax,dword ptr [ecx+0x9c]; test eax,eax; jz actor_idle
cmp dword ptr [eax+0x28],0; jne actor_busy
actor_idle: xor eax,eax; ret
actor_busy: mov eax,1; ret
''',0x100)
    upgrades=replace_once(m.observer_source(0x2c00),'mov edi,dword ptr [ebp+8];',
        f'mov edi,dword ptr [ebp+8]; mov ecx,edi; call {S+0x2900}; test eax,eax; jnz upgrades_done\n')
    m.replace(0x2c00,upgrades,0x200)

    # Kingdom +2d0/+2d4: owned independent structures, verified against native
    # registration/removal 697035 / 697366. All outstanding work contributes;
    # only actual mine definitions become new auto-upgrade candidates.
    m.replace(0x6d00,f'''
push ebx; push esi; push edi; push ebp
mov ebp,dword ptr [{S+0x10c}]; xor ebx,ebx
cmp dword ptr [ebp+0x2d4],4096; ja mine_bad
mine_loop:
cmp ebx,dword ptr [ebp+0x2d4]; jae mine_done
mov eax,dword ptr [ebp+0x2d0]; test eax,eax; jz mine_bad
mov edi,dword ptr [eax+ebx*4]; test edi,edi; jz mine_next
mov ecx,edi; mov eax,dword ptr [ecx]; call dword ptr [eax+0x108]
cmp eax,ebp; jne mine_next
cmp dword ptr [edi+0x98],0; jne mine_next
cmp dword ptr [edi+0x94],0; je mine_next
push edi; push edi; call {S+0x5900}; add esp,8
mov eax,dword ptr [edi+4]; call {S+0x7000}; test eax,2; jz mine_next
mov esi,dword ptr [{S+0x11c}]; cmp esi,256; jae mine_bad
mov eax,dword ptr [edi+0x14]; mov dword ptr [{S+0x19000}+esi*8],eax
mov ecx,edi; call {S+0x2800}; or eax,2
mov dword ptr [{S+0x19004}+esi*8],eax
inc dword ptr [{S+0x11c}]
test eax,1; jnz mine_next
push edi; push edi; call {S+0x2c00}; add esp,8
mine_next: inc ebx; jmp mine_loop
mine_bad: mov dword ptr [{S+0x130}],0
mine_done: pop ebp; pop edi; pop esi; pop ebx; ret
''',0x300)

    # EAX definition -> flags 1 market, 2 mine. Internal UTF-16 data IDs,
    # independent of race/localization/module relocation; bounded to 128 chars.
    m.replace(0x7000,'''
push ecx; push edx; push esi
test eax,eax; jz name_none
mov esi,dword ptr [eax+8]; test esi,esi; jz name_none
mov ecx,128
name_loop:
cmp ecx,8; jb name_none
movzx eax,word ptr [esi]; test eax,eax; jz name_none
cmp eax,95; jne name_next
cmp word ptr [esi+2],109; jne name_next
cmp word ptr [esi+4],97; jne name_mine
cmp word ptr [esi+6],114; jne name_next
cmp word ptr [esi+8],107; jne name_next
cmp word ptr [esi+10],101; jne name_next
cmp word ptr [esi+12],116; jne name_next
cmp word ptr [esi+14],0; jne name_next
mov eax,1; jmp name_done
name_mine:
cmp word ptr [esi+4],105; jne name_next
cmp word ptr [esi+6],110; jne name_next
cmp word ptr [esi+8],101; jne name_next
movzx eax,word ptr [esi+10]; test eax,eax; jz name_is_mine
cmp eax,95; jne name_next
name_is_mine: mov eax,2; jmp name_done
name_next: add esi,2; dec ecx; jmp name_loop
name_none: xor eax,eax
name_done: pop esi; pop edx; pop ecx; ret
''',0x180)

    raw=('PawNewCityMilitia\0').encode('utf-16le')
    b.payload[0x1c200:0x1c200+len(raw)]=raw
    load=replace_once(load,f'call {S+0x6400}',f'call {S+0x6400}; call {S+0x7200}')
    load=replace_once(load,f'call {S+0x6500}',f'call {S+0x6500}; call {S+0x7300}')
    m.replace(0x1200,load,0x400)
    m.replace(0x7200,f'''
push {S+0x1c200}; lea ecx,[ebp-4]; call 0x4805de
push 0; push 0; push 0; lea eax,[ebp-4]; push eax; call 0x7184e9; add esp,16
mov dword ptr [{S+0xc4}],eax
push 0; push eax; mov ecx,edi; call 0x717486
mov ecx,dword ptr [ebp-4]; sub ecx,16; call 0x481375
ret
''',0x100)
    # Native Check / Uncheck are separate methods taking (notify, update).
    # Render the persisted value with notification disabled, before tick reads
    # the widget. Passing the value as an argument to Uncheck loses default ON.
    m.replace(0x7300,f'''
pushfd; pushad
mov ecx,dword ptr [{S+0xc4}]; test ecx,ecx; jz militia_render_done
cmp dword ptr [{S+0xc0}],1; jne militia_render_unchecked
push 1; push 0; call 0x7186d4; jmp militia_render_done
militia_render_unchecked: push 1; push 0; call 0x7186f2
militia_render_done: popad; popfd; ret
''',0x80)
    m.replace(0x7380,f'''
mov ecx,dword ptr [{S+0xc4}]; test ecx,ecx; jz militia_tick_done
mov eax,dword ptr [ecx+0x24]; shr eax,7; and eax,1
cmp eax,dword ptr [{S+0xc0}]; je militia_tick_done
mov dword ptr [{S+0xc0}],eax; inc dword ptr [{S+0xc8}]
militia_tick_done: ret
''',0x80)
    # Existing tick helper is called under pushad/pushfd. Preserve its gear code.
    gear=f'''
call {S+0x7380}
mov ecx,dword ptr [{S+0xa8}]; test ecx,ecx; jz gear_done
mov eax,dword ptr [ecx+0x24]; shr eax,7; and eax,1
cmp eax,dword ptr [{S+0xb0}]; je gear_done
mov dword ptr [{S+0xb0}],eax; mov dword ptr [{S+0xb4}],1
inc dword ptr [{S+0xac}]
gear_done: ret
'''
    m.replace(0x5300,gear,0x100)
    m.replace(0x6c00,f'''
pushfd; pushad
mov dword ptr [{S+0xc4}],0
mov edi,{S+0x1c000}; xor eax,eax; mov ecx,4; cld; rep stosd
popad; popfd; ret
''',0x100)

    from native_militia import install as install_militia
    install_militia(m)
    # ECX current production, EDX upkeep. Every economic resource must be
    # strictly above its target BEFORE a market order, after adverse queued work.
    m.replace(0x7900,f'''
push ebx; push edi
mov ebx,1
market_floor_loop:
mov edi,ebx; cmp dword ptr [{S+0x118}],10; jne market_floor_index
inc edi
market_floor_index:
movss xmm0,dword ptr [ecx+edi*4]; subss xmm0,dword ptr [edx+edi*4]
addss xmm0,dword ptr [{S+0x1b020}+ebx*4]
movd eax,xmm0; and eax,0x7f800000; cmp eax,0x7f800000; je market_floor_no
ucomiss xmm0,dword ptr [{S+0x1b000}+ebx*4]; jp market_floor_no; jbe market_floor_no
inc ebx; cmp ebx,5; jb market_floor_loop
mov eax,1; jmp market_floor_done
market_floor_no: xor eax,eax
market_floor_done: pop edi; pop ebx; ret
''',0x200)
