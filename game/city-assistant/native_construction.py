"""Read-only in-flight construction forecast for the verified 1.3.72 bridge.

No simulation hooks or writes: capture runs on the existing UI-thread snapshot.
ConstructionComponent +28 is the upgrade target (665de0 / 66663e); new
construction uses actor definition +4 and flag 00200000. Costs are debited
before the active work is published (665e28 / 680bf7 -> 6959d8).
EconomyComponent +18/+28 are the production/upkeep vectors actually registered
with the kingdom, gated by +10/+11 (66d272). Subtract these, not nominal old
building values: new-building upkeep can already be included in live income.
"""
import ast
from pathlib import Path


def install(m):
    b, S = m.b, m.S
    b.payload.extend(bytes(0x30000 - len(b.payload)))
    b.n.SIZE = 0x30000

    # Reuse the guarded observer/definition queries without changing legacy or
    # production sources. Fail if an upstream anchor changes.
    def source_at(offset):
        tree = ast.parse(Path(m.o.e.__file__).read_text(encoding='utf-8-sig'))
        nodes = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == 'emit'
                 and isinstance(n.args[0], ast.Constant) and n.args[0].value == offset]
        assert len(nodes) == 1
        return eval(compile(ast.Expression(nodes[0].args[1]), '<legacy observer>', 'eval'), vars(m.o.e))

    capture = source_at(0x2000)
    anchor = f'mov dword ptr [{S+0x128}],0'
    assert capture.count(anchor) == 1
    capture = capture.replace(anchor, anchor + f'\ncall {S+0x5600}')
    anchor = f'mov ecx,edi; call {S+0x2800}'
    assert capture.count(anchor) == 1
    capture = capture.replace(anchor, f'mov ecx,edi; call {S+0x5700}\n' + anchor)
    m.replace(0x2000, capture, 0x800)

    # Header +2c: work count; +30: coherent forecast. Aggregates are native-only.
    # +1b020: adverse changes, +1b040: expected changes (five economic resources).
    m.replace(0x5600, f'''
push eax; push ecx; push edi
mov dword ptr [{S+0x12c}],0; mov dword ptr [{S+0x130}],1
xor eax,eax; mov edi,{S+0x1b020}; mov ecx,16; cld; rep stosd
pop edi; pop ecx; pop eax; ret
''', 0x100)

    # Visit EVERY owned city, even if under siege or busy. Each actor is
    # deduplicated before adding its effects (city/main/children may overlap).
    m.replace(0x5700, f'''
push ebx; push esi; push edi
mov edi,ecx; mov esi,dword ptr [edi+0x98]
test esi,esi; jz work_city_bad
cmp dword ptr [esi+0x1c],256; ja work_city_bad
push edi; push edi; call {S+0x5900}; add esp,8
mov eax,dword ptr [esi+0x14]; test eax,eax; jz work_children_start
push eax; push edi; call {S+0x5900}; add esp,8
work_children_start: xor ebx,ebx
work_children:
cmp ebx,dword ptr [esi+0x1c]; jae work_city_done
mov eax,dword ptr [esi+0x18]; test eax,eax; jz work_city_bad
mov eax,dword ptr [eax+ebx*4]; test eax,eax; jz work_city_bad
push eax; push edi; call {S+0x5900}; add esp,8
inc ebx; jmp work_children
work_city_bad: mov dword ptr [{S+0x130}],0
work_city_done: pop edi; pop esi; pop ebx; ret
''', 0x200)

    m.replace(0x5900, f'''
push ebp; mov ebp,esp; push ebx; push esi; push edi
mov edi,dword ptr [ebp+12]; mov ecx,edi
mov eax,dword ptr [ecx]; call dword ptr [eax+0x108]
cmp eax,dword ptr [{S+0x10c}]; jne work_actor_done
mov eax,dword ptr [edi+0x9c]; test eax,eax; jz work_no_component
cmp dword ptr [eax],0x93fe58; jne work_actor_bad
mov esi,dword ptr [eax+0x28]; test esi,esi; jnz work_upgrade
test dword ptr [edi+0x100],0x20000000; jnz work_actor_bad
test dword ptr [edi+0x100],0x00200000; jz work_actor_done
mov esi,dword ptr [edi+4]; mov ebx,13; jmp work_dedup
work_upgrade: mov ebx,21
work_dedup:
test esi,esi; jz work_actor_bad
xor edx,edx
work_seen:
cmp edx,dword ptr [{S+0x12c}]; jae work_append
mov eax,edx; shl eax,7
mov ecx,dword ptr [edi+0x14]
cmp ecx,dword ptr [{S+0x20004}+eax]; je work_actor_done
inc edx; jmp work_seen
work_append:
cmp edx,512; jae work_actor_bad
push ebx; push esi; push edi; push dword ptr [ebp+8]
call {S+0x5c00}; add esp,16; jmp work_actor_done
work_no_component:
test dword ptr [edi+0x100],0x20200000; jz work_actor_done
work_actor_bad: mov dword ptr [{S+0x130}],0
work_actor_done: pop edi; pop esi; pop ebx; pop ebp; ret
''', 0x300)

    append = source_at(0x2a00).replace(str(S+0x120), str(S+0x12c)).replace(str(S+0x8000), str(S+0x20000))
    start = append.index('cmp dword ptr [ebp+20],0x15;')
    end = append.index('append_store:', start)
    append = append[:start] + f'''
mov ecx,dword ptr [ebp+12]; mov edx,ebx; call {S+0x6000}
movss xmm1,dword ptr [ebp-4]; subss xmm1,xmm0
movss dword ptr [ebp-4],xmm1
''' + append[end:]
    # Retain native resource order in work records (including optional Shards).
    # The aggregate below projects these records onto five economic resources.
    append = append.replace('append_count: inc', f'append_count: call {S+0x6200}\ninc')
    m.replace(0x5c00, append, 0x300)

    # ECX actor, EDX resource -> XMM0 contribution already included in kingdom.
    m.replace(0x6000, f'''
push ebx; push esi
xorps xmm0,xmm0
cmp edx,dword ptr [{S+0x118}]; jae current_bad
mov esi,dword ptr [ecx+0x84]; test esi,esi; jz current_done
cmp dword ptr [esi],0x940ef0; jne current_bad
cmp dword ptr [esi+4],ecx; jne current_bad
cmp byte ptr [esi+0x10],0; je current_upkeep
cmp edx,dword ptr [esi+0x1c]; jae current_bad
mov ebx,dword ptr [esi+0x18]; test ebx,ebx; jz current_bad
movss xmm0,dword ptr [ebx+edx*4]
current_upkeep:
cmp byte ptr [esi+0x11],0; je current_done
cmp edx,dword ptr [esi+0x2c]; jae current_bad
mov ebx,dword ptr [esi+0x28]; test ebx,ebx; jz current_bad
subss xmm0,dword ptr [ebx+edx*4]; jmp current_done
current_bad: mov dword ptr [{S+0x130}],0
current_done: pop esi; pop ebx; ret
''', 0x200)

    # EDI work record. Count future positive income for goals only; it never
    # funds a new order. A besieged/selling actor's gains are not dependable.
    m.replace(0x6200, f'''
push eax; push ebx; push ecx; push edx
mov eax,dword ptr [ebp+12]; mov eax,dword ptr [eax+0x100]
mov ecx,dword ptr [ebp+8]; or eax,dword ptr [ecx+0x100]
and eax,0x40100000; mov dword ptr [edi+92],eax
xor ebx,ebx
cmp dword ptr [{S+0x118}],9; je aggregate_loop
cmp dword ptr [{S+0x118}],10; jne aggregate_bad
aggregate_loop:
cmp ebx,5; jae aggregate_done
mov edx,ebx
cmp dword ptr [{S+0x118}],10; jne aggregate_index_ready
test ebx,ebx; jz aggregate_index_ready
inc edx
aggregate_index_ready:
movss xmm0,dword ptr [edi+20+edx*4]
movd ecx,xmm0; and ecx,0x7f800000; cmp ecx,0x7f800000; je aggregate_bad
xorps xmm1,xmm1; minss xmm1,xmm0
addss xmm1,dword ptr [{S+0x1b020}+ebx*4]
movss dword ptr [{S+0x1b020}+ebx*4],xmm1
test eax,eax; jz aggregate_expected
xorps xmm1,xmm1; minss xmm0,xmm1
aggregate_expected:
addss xmm0,dword ptr [{S+0x1b040}+ebx*4]
movss dword ptr [{S+0x1b040}+ebx*4],xmm0
inc ebx; jmp aggregate_loop
aggregate_bad: mov dword ptr [{S+0x130}],0
aggregate_done: pop edx; pop ecx; pop ebx; pop eax; ret
''', 0x200)
