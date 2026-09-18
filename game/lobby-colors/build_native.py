"""Build the player-color UI and its host-authoritative multiplayer transport.

The transport appends a dedicated request/decree pair to Kohan II's native
order registry. Only stable kingdom/color IDs cross the wire; process-local
descriptor pointers never do. All players in an MP lobby must use this build.
"""
from pathlib import Path
import hashlib, json, struct, sys, re, argparse
parser = argparse.ArgumentParser()
parser.add_argument('--legacy', type=Path, required=True, help='Read-only verified native research inputs and Python dependencies')
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
ROOT = args.legacy.resolve()
sys.path.insert(0, str(ROOT / 'pydeps_r3'))
sys.path.insert(0, str(ROOT / 'deps_r15'))
sys.path.insert(0, str(ROOT.parent / 'pydeps_readable'))
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
import capstone

BASE, GAME, SIZE = 0x10000000, 0x460000, 0x42000
PLAYER_COUNT, MAX_COLORS = 16, 64
# Confirmed from the full live 1.3.72 registry, not one static initializer group.
# Preserve every stock ID and append the same pair on all patched peers.
STOCK_ORDER_COUNT = 334
WIRE_TAG = 0x50430000  # r18: complete private-session snapshots; same build on all peers.
SNAPSHOT_TAG = 0x50435301
DESCRIPTOR_TAG = 0x50440000
STATE, PAL_COUNT, USED_MASK = BASE+0x100, BASE+0x140, BASE+0x180
COLORS, KSTR, LABELS = BASE+0x200, BASE+0x300, BASE+0x400
RANDOM_ID, RANDOM_LABEL, RANDOM_KEY, RANDOM_COLOR = BASE+0x500, BASE+0x504, BASE+0x508, BASE+0x50c
CHOICES, ASSIGNED, ORDER = BASE+0x600, BASE+0x680, BASE+0x700
ICON_KEYS = BASE+0x800  # 64 (choice, player pointer) pairs; text owned in record+24.
CUSTOM_DESC, PAL_SOURCE, RECORDS = BASE+0xa00, BASE+0x1400, BASE+0x2000
NET_STATE, DECREE_DESC, REQUEST_DESC = BASE+0x1900, BASE+0x1940, BASE+0x1950
DECREE_NAME, REQUEST_NAME = BASE+0x1960, BASE+0x1964
# Session-local native participant IDs, never nicknames or kingdom ordinals.
# Native Session::AddPlayer increments session+F4 and replicates player+20 in
# complete-session snapshots. IDs survive seat changes and object reconstruction;
# a disconnected/replaced participant receives a new ID, so cannot inherit a seat.
OWNERS, PREFERENCES = BASE+0x3d000, BASE+0x3d100
PREFERENCE_COUNT = 256
RETIRED = json.loads((Path(__file__).with_name("retired-colors.json")).read_text("utf-8"))
assert len(RETIRED) == 10
assert len({c['id'] for c in RETIRED}) == len({c['wire_id'] for c in RETIRED}) == 10
assert RETIRED[0]['id']=='paws_light_red' and RETIRED[0]['wire_id']==0x5044fffe
assert all(0x3da00<=c['descriptor']<c['descriptor']+36<=0x3de00 for c in RETIRED)
assert all(0x3da00<=c['name_pointer']<c['name_pointer']+4<=0x3e000 for c in RETIRED)
assert all(not (d['descriptor']<=c['name_pointer']<d['descriptor']+36) for c in RETIRED for d in RETIRED)
assert all(0x5044ff00<=c['wire_id']<=0x5044fffe for c in RETIRED)
NAMES = ['ensure','find','eligible','lookup','mask','apply','refresh','callback','create','clear','ctor_hook','tick_hook','dtor_hook']
NAMES += ['state_init','allocate','commit','create_world_hook','configure_world_hook','active','index']
NAMES += ['update_icon']
NAMES += ['selected_index']
NAMES += ['select_and_refresh']
NAMES += ['network_init','network_send','network_apply','network_request','network_decree']
NAMES += ['empty_icon_eligible']
NAMES += ['shuffle_mp']
NAMES += ['network_decode']
NAMES += ['sync_decree_boundary']
F = {name:BASE+0x10000+i*0x1000 for i,name in enumerate(NAMES)}
# Keep the accepted ABI/loader offsets; the boundary helper occupies <0x800 bytes.
F['can_edit'] = BASE+0x2f800
F.update(snapshot_write=BASE+0x30000, snapshot_read=BASE+0x31000,
         session_write_hook=BASE+0x32000, session_read_hook=BASE+0x33000)
F.update(color_wire_write=BASE+0x34000, color_wire_read=BASE+0x35000,
         saved_color_lookup=BASE+0x36000)
F.update(color_conflict=BASE+0x37000, on_kingdom_assigned=BASE+0x38000,
         player_kingdom_copy_hook=BASE+0x39000)
F.update(is_saved_source=BASE+0x3a000, saved_entry=BASE+0x3b000,
         refresh_saved=BASE+0x3c000)
F.update(preference=BASE+0x3e000, remember_choice=BASE+0x3f000,
         bind_snapshot=BASE+0x40000)
F['popup_rect_hook'] = BASE+0x41000
payload = bytearray(SIZE)
fixups, routines = [], []
ks = Ks(KS_ARCH_X86,KS_MODE_32)
md = capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32); md.detail=True
raw = (ROOT.parent/'k2_runtime_1372_20260904.bin').read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == 'B865D8206990C4F055C51DE857F0B09B88AB5EE3B6AE74EE5232134001AA591C', 'Unexpected mapped game baseline'
cursor=0x5000
def string(s):
    global cursor
    b=(s+'\0').encode('utf-16le'); va=BASE+cursor
    payload[cursor:cursor+len(b)]=b; cursor=(cursor+len(b)+3)&~3
    return va
kids = [string('kingdom%02d'%i) for i in range(1,PLAYER_COUNT+1)]
widget=string('PawColor')
remember=string('StagingRememberSPSettings')
random_id=string('paws_random')
random_key=string('staging_WorldParamsPanel_random_option_text')
decree_order_name=string('TGC_DecreePawSetKingdomColorOrder')
request_order_name=string('TGC_RequestPawSetKingdomColorOrder')
default_id=string('default')
gray_id=string('gray')
label_format=string('<color=%g,%g,%g>%s<rc>')
for color in RETIRED:
    color['id_va'] = string(color['id'])
    color['label_va'] = string(color['name_en'])
assert cursor < 0x6000, 'Static strings overlap injected palette strings'
def asm(name, source):
    va=F[name]
    try:
        encoding,_=ks.asm(source,addr=va)
    except Exception:
        for line_no,line in enumerate(source.splitlines(),1):
            for statement in line.split(';'):
                statement=statement.strip()
                if not statement or statement.endswith(':') or statement.split()[0] in ('ja','je','jne','jz','jmp','jb','jae','jc','jnc'):
                    continue
                try: ks.asm(statement,addr=va)
                except Exception: print('Assembler rejected',name,'line',line_no,repr(statement))
        raise
    b=bytes(encoding)
    assert len(b)<0x1000,(name,len(b))
    payload[va-BASE:va-BASE+len(b)]=b
    listing=[]
    for ins in md.disasm(b,va):
        listing.append('%08X %-30s %s %s'%(ins.address,ins.bytes.hex(' '),ins.mnemonic,ins.op_str))
        for op in ins.operands:
            if op.type==capstone.x86.X86_OP_IMM:
                v=op.imm & 0xffffffff
                off=ins.address-BASE+ins.imm_offset
                if ins.group(capstone.CS_GRP_CALL) or ins.group(capstone.CS_GRP_JUMP):
                    if GAME<=v<GAME+len(raw):
                        assert ins.imm_size==4
                        fixups.append((3,off,v-GAME))
                elif GAME<=v<GAME+len(raw) or BASE<=v<BASE+SIZE:
                    assert ins.imm_size==4,(name,ins.mnemonic,hex(v))
                    fixups.append((1 if v<BASE else 2,off,v-(GAME if v<BASE else BASE)))
            elif op.type==capstone.x86.X86_OP_MEM:
                v=op.mem.disp & 0xffffffff
                if GAME<=v<GAME+len(raw) or BASE<=v<BASE+SIZE:
                    assert ins.disp_size==4
                    fixups.append((1 if v<BASE else 2,ins.address-BASE+ins.disp_offset,v-(GAME if v<BASE else BASE)))
    routines.append({'name':name,'offset':va-BASE,'length':len(b),'assembly':'\n'.join(listing)})

# Const engine strings are constructed once. Player colors are private descriptor
# copies populated from paws_player_colors.ini; the game DB and its iteration order
# remain untouched, so independent kingdoms keep their stock colors.
ensure_parts=[]
for i,s in enumerate(kids):
    ensure_parts.append(f'push {s}; mov ecx,{KSTR+i*4}; call 0x4805de')
# Save-only descriptors use separate storage and reserved wire IDs. They are
# never inserted into COLORS, the picker, or random allocation.
retired_init = []
for i, color in enumerate(RETIRED):
    desc, name = BASE + color['descriptor'], BASE + color['name_pointer']
    rgb = [struct.unpack('<I', struct.pack('<f', c/255))[0] for c in color['rgb']]
    retired_init.append(f"""
    mov esi,ebx; mov edi,{desc}; mov ecx,9
copy_retired_{i}:
    mov eax,dword ptr [esi]; mov dword ptr [edi],eax
    add esi,4; add edi,4; dec ecx; jnz copy_retired_{i}
    push {color['id_va']}; mov ecx,{desc+8}; call 0x4805de
    mov eax,dword ptr [{name}]; test eax,eax; jnz retired_name_{i}
    mov eax,{color['label_va']}
retired_name_{i}:
    push eax; mov ecx,{desc+0x10}; call 0x4805de
    mov dword ptr [{desc+0x18}],{rgb[0]}
    mov dword ptr [{desc+0x1c}],{rgb[1]}
    mov dword ptr [{desc+0x20}],{rgb[2]}
    """)
asm('ensure',f'''
    push ebx; push esi; push edi
    cmp dword ptr [{STATE}],1; je ready
    cmp dword ptr [0xa53fb4],0; je fail
    cmp dword ptr [{PAL_COUNT}],1; jb fail
    cmp dword ptr [{PAL_COUNT}],{MAX_COLORS}; ja fail
    cmp dword ptr [{STATE+4}],0; jne colors
    { ';'.join(ensure_parts) }
    mov dword ptr [{STATE+4}],1
colors:
    mov ecx,dword ptr [0xa53fb4]; add ecx,0x3cc
    push {default_id}; call 0x48edb9; test eax,eax; jz fail
    mov ebx,eax
    mov ecx,dword ptr [0xa53fb4]; add ecx,0x3cc
    push {gray_id}; call 0x48edb9; test eax,eax; jz fail
    mov dword ptr [{RANDOM_COLOR}],eax
    xor esi,esi
descriptors:
    mov edi,esi; imul edi,0x24; add edi,{CUSTOM_DESC}
    push esi; push edi
    mov esi,ebx; mov ecx,9
copy_descriptor: mov eax,dword ptr [esi]; mov dword ptr [edi],eax
    add esi,4; add edi,4; dec ecx; jnz copy_descriptor
    pop edi; pop esi
    mov eax,esi; imul eax,20; add eax,{PAL_SOURCE}
    push dword ptr [eax]; lea ecx,[edi+8]; call 0x4805de
    mov eax,esi; imul eax,20; add eax,{PAL_SOURCE}
    push dword ptr [eax+4]; lea ecx,[edi+0x10]; call 0x4805de
    mov eax,esi; imul eax,20; add eax,{PAL_SOURCE}
    mov edx,dword ptr [eax+8]; mov dword ptr [edi+0x18],edx
    mov edx,dword ptr [eax+12]; mov dword ptr [edi+0x1c],edx
    mov edx,dword ptr [eax+16]; mov dword ptr [edi+0x20],edx
    mov dword ptr [esi*4+{COLORS}],edi
    inc esi; cmp esi,dword ptr [{PAL_COUNT}]; jb descriptors
    { ''.join(retired_init) }
    push {random_id}; mov ecx,{RANDOM_ID}; call 0x4805de
    push {random_key}; mov ecx,{RANDOM_KEY}; call 0x4805de
    mov ecx,{RANDOM_LABEL}; call 0x480633
    push 0xa629c4; push {RANDOM_KEY}; mov ecx,dword ptr [0xa53fd8]; call 0x4d1800
    push eax; mov ecx,{RANDOM_LABEL}; call 0x483fb6
    xor esi,esi
labels:
    lea ecx,[esi*4+{LABELS}]; call 0x480633
    mov ecx,dword ptr [esi*4+{COLORS}]
    push dword ptr [ecx+0x10]
    sub esp,24
    fld dword ptr [ecx+0x18]; fstp qword ptr [esp]
    fld dword ptr [ecx+0x1c]; fstp qword ptr [esp+8]
    fld dword ptr [ecx+0x20]; fstp qword ptr [esp+16]
    push {label_format}; lea eax,[esi*4+{LABELS}]; push eax
    call 0x4810c4; add esp,36
    inc esi; cmp esi,dword ptr [{PAL_COUNT}]; jb labels
    mov dword ptr [{STATE}],1
ready:
    call {F['network_init']}
    mov eax,1; pop edi; pop esi; pop ebx; ret
fail: xor eax,eax; pop edi; pop esi; pop ebx; ret
''')

# ECX=slot -> EAX=side record. Never dereference stale entries; destructor clears.
asm('find',f'''
    mov eax,{RECORDS}; mov edx,64
again: cmp dword ptr [eax],ecx; je done
    add eax,32; dec edx; jnz again
    xor eax,eax
done: ret
''')

# EAX=index -> parameters from active world source. Const string ref ABI.
asm('lookup',f'''
    push esi; mov esi,eax
    mov ecx,dword ptr [0xa53fe4]; test ecx,ecx; jz fail
    add ecx,0x60; call 0x5c18a5; test eax,eax; jz fail
    lea ecx,[eax+4]; lea eax,[esi*4+{KSTR}]; push eax
    call 0x6f56d7; pop esi; ret
fail: xor eax,eax; pop esi; ret
''')

# ECX=slot -> EAX=verified editable source entry, 0 outside new-game staging.
# Live lobby evidence: +F0 is the editable source returned by native lookup;
# +F4 is a different resolved/display copy. Never require their pointers to match.
# Multiplayer additionally requires the custom native order pair to be registered.
asm('eligible',f'''
    push ebx; push esi; push edi; mov esi,ecx
    call {F['is_saved_source']}; test eax,eax; jnz fail
    call {F['ensure']}; test eax,eax; jz fail
    mov ebx,dword ptr [0xa53fe4]; test ebx,ebx; jz fail
    cmp byte ptr [ebx+0x100],0; je single_player
    cmp dword ptr [{NET_STATE}],1; jne fail
    jmp session_mode
single_player:
    cmp dword ptr [ebx+0x128],0; jne fail
session_mode:
    cmp dword ptr [ebx+0x6c],5; je fail
    cmp dword ptr [ebx+0x60],1; je staging
    cmp dword ptr [ebx+0x60],2; jne fail
staging:
    cmp dword ptr [esi+0xf8],5; je fail
    cmp dword ptr [esi+0xf4],0; je fail
    mov edx,dword ptr [esi+0xec]; test edx,edx; jz fail
    xor edi,edi
again:
    mov edx,dword ptr [esi+0xec]
    push dword ptr [edi*4+{KSTR}]; push dword ptr [edx+0x24]
    call 0x481574; add esp,8; test eax,eax; jz found
    inc edi; cmp edi,{PLAYER_COUNT}; jb again; jmp fail
found:
    mov eax,edi; call {F['lookup']}
    cmp eax,dword ptr [esi+0xf0]; jne fail
    test eax,eax; jz fail
    push eax; mov ecx,ebx; call {F['state_init']}; pop eax
    jmp done
fail: xor eax,eax
done: pop edi; pop esi; pop ebx; ret
''')

# Reserve only explicit choices of active players; random choices share the pool.
asm('mask',f'''
    push ebx; push esi; push edi
    mov dword ptr [{USED_MASK}],0
    mov dword ptr [{USED_MASK+4}],0
    xor esi,esi
again:
    mov ecx,dword ptr [0xa53fe4]
    lea eax,[esi*4+{KSTR}]; push eax; call 0x5c6c0a
    test eax,eax; jz next
    mov eax,esi; call {F['lookup']}; test eax,eax; jz next
    mov edi,dword ptr [esi*4+{CHOICES}]
    cmp edi,dword ptr [{PAL_COUNT}]; jae next
    bts dword ptr [{USED_MASK}],edi
next: inc esi; cmp esi,{PLAYER_COUNT}; jb again
    mov eax,dword ptr [{USED_MASK}]
    mov edx,dword ptr [{USED_MASK+4}]
    pop edi; pop esi; pop ebx; ret
''')

# ECX=slot, EDX=palette index or PAL_COUNT=Random. In multiplayer the UI sends a
# request to the host and changes only after the authoritative decree returns.
asm('apply',f'''
    push ebp; mov ebp,esp; push ebx; push esi; push edi
    mov esi,ecx; mov edi,edx; inc dword ptr [{STATE+12}]
    cmp edi,dword ptr [{PAL_COUNT}]; ja reject
    call {F['can_edit']}; test eax,eax; jz reject
    mov ecx,esi
    call {F['eligible']}; test eax,eax; jz reject
    mov ecx,dword ptr [eax]; call {F['index']}; cmp eax,{PLAYER_COUNT}; jae reject
    mov ebx,eax
    mov eax,dword ptr [0xa53fe4]
    cmp byte ptr [eax+0x100],0; je local_apply
    mov eax,ebx; call {F['lookup']}; test eax,eax; jz reject
    mov ecx,ebx; mov edx,edi
    call {F['network_send']}; test eax,eax; jz reject
    mov eax,1; jmp done
local_apply:
    cmp dword ptr [ebx*4+{CHOICES}],edi; je same
    cmp edi,dword ptr [{PAL_COUNT}]; je accepted
    call {F['mask']}; bt dword ptr [{USED_MASK}],edi; jc reject
accepted:
    mov dword ptr [ebx*4+{CHOICES}],edi
    mov ecx,ebx; mov edx,edi; call {F['remember_choice']}
    inc dword ptr [{STATE+16}]
    mov eax,1; jmp done
same: mov eax,2; jmp done
reject: inc dword ptr [{STATE+20}]; xor eax,eax
done: mov dword ptr [{STATE+24}],eax
    pop edi; pop esi; pop ebx; pop ebp; ret
''')

# Color list contains current + free colors, using native localized descriptor names.
# Rebuild only on changed color/mask/eligibility, not every rendered frame.
# The outer label may not exist during the first list construction, so a stable
# cached selection retries the stock label sync on later ticks without rebuilding.
asm('refresh',f'''
    push ebp; mov ebp,esp; sub esp,0x30
    push ebx; push esi; push edi; mov esi,ecx
    call {F['find']}; test eax,eax; jz done
    mov ebx,eax; mov edi,dword ptr [ebx+4]; test edi,edi; jz done
    cmp dword ptr [ebx+20],0; jne done
    call {F['is_saved_source']}; test eax,eax; jz new_game
    mov ecx,esi; call {F['refresh_saved']}; jmp done
new_game:
    mov ecx,esi; call {F['eligible']}; test eax,eax; jz hide
    mov ecx,dword ptr [eax]; call {F['index']}; cmp eax,{PLAYER_COUNT}; jae hide
    mov eax,dword ptr [eax*4+{CHOICES}]; mov dword ptr [ebp-4],eax
    mov ecx,esi; call {F['can_edit']}
    push eax; mov ecx,edi; call 0x71728f
    mov eax,dword ptr [ebp-4]
    mov edx,eax; mov ecx,esi; call {F['update_icon']}
    call {F['mask']}; mov dword ptr [ebp-8],eax
    mov eax,dword ptr [{USED_MASK+4}]; mov dword ptr [ebp-16],eax
    cmp dword ptr [ebx+16],1; jne build
    mov eax,dword ptr [ebp-8]; cmp eax,dword ptr [ebx+12]; jne build
    mov eax,dword ptr [ebp-16]; cmp eax,dword ptr [ebx+28]; jne build
    mov eax,dword ptr [ebp-4]; cmp eax,dword ptr [ebx+8]; jne build
    mov dword ptr [ebx+20],1
    mov edx,dword ptr [ebp-4]; mov ecx,dword ptr [edi+0x6c]
    call {F['selected_index']}
    push eax; mov ecx,edi; call {F['select_and_refresh']}
    mov dword ptr [ebx+20],0; jmp done
build:
    mov dword ptr [ebx+20],1
    mov dword ptr [ebx+16],1
    mov eax,dword ptr [ebp-4]; mov dword ptr [ebx+8],eax
    mov eax,dword ptr [ebp-8]; mov dword ptr [ebx+12],eax
    mov eax,dword ptr [ebp-16]; mov dword ptr [ebx+28],eax
    push 1; mov ecx,edi; call 0x717271
    push edi; lea ecx,[ebp-0x30]; call 0x70517f
    push 0; push {RANDOM_ID}; push {RANDOM_LABEL}
    lea ecx,[ebp-0x30]; call 0x70502e
    mov dword ptr [ebp-12],0
list:
    mov edx,dword ptr [ebp-12]; mov eax,dword ptr [edx*4+{COLORS}]
    cmp edx,dword ptr [ebp-4]; je additem
    bt dword ptr [{USED_MASK}],edx; jc next
additem:
    push 0; add eax,8; push eax
    mov eax,dword ptr [ebp-12]; lea eax,[eax*4+{LABELS}]; push eax
    lea ecx,[ebp-0x30]; call 0x70502e
next:
    inc dword ptr [ebp-12]
    mov eax,dword ptr [ebp-12]; cmp eax,dword ptr [{PAL_COUNT}]; jb list
    lea ecx,[ebp-0x30]; call 0x7051b1
    lea ecx,[ebp-0x30]; call 0x7051a6
    mov edx,dword ptr [ebp-4]; mov ecx,dword ptr [edi+0x6c]
    call {F['selected_index']}
    push eax; mov ecx,edi; call {F['select_and_refresh']}
    mov dword ptr [ebx+20],0; jmp done
hide:
    mov edx,dword ptr [{PAL_COUNT}]; mov ecx,esi; call {F['update_icon']}
    cmp dword ptr [ebx+16],0; je done
    mov dword ptr [ebx+16],0
    push 0; mov ecx,edi; call 0x717271
done:
    pop edi; pop esi; pop ebx; mov esp,ebp; pop ebp; ret
''')

asm('callback',f'''
    push ebp; mov ebp,esp; push esi; push edi
    mov esi,ecx
    call {F['find']}; test eax,eax; jz done
    cmp dword ptr [eax+20],0; jne done
    push dword ptr [{RANDOM_ID}]; push dword ptr [ebp+8]
    call 0x481574; add esp,8; test eax,eax; jnz explicit
    mov ecx,esi; mov edx,dword ptr [{PAL_COUNT}]; call {F['apply']}; jmp done
explicit:
    xor edi,edi
again:
    mov eax,dword ptr [edi*4+{COLORS}]; test eax,eax; jz next
    push dword ptr [eax+8]; push dword ptr [ebp+8]
    call 0x481574; add esp,8; test eax,eax; jz found
next: inc edi; cmp edi,dword ptr [{PAL_COUNT}]; jb again; jmp done
found: mov ecx,esi; mov edx,edi; call {F['apply']}
done:
    mov ecx,esi; call {F['refresh']}
    mov ecx,dword ptr [ebp+8]; sub ecx,0x10; call 0x481375
    pop edi; pop esi; pop ebp; ret 4
''')

asm('create',f'''
    push ebp; mov ebp,esp; sub esp,4; push ebx; push esi; push edi
    mov esi,ecx; mov ebx,{RECORDS}; mov edi,64
again: cmp dword ptr [ebx],0; je found
    add ebx,32; dec edi; jnz again; jmp done
found:
    mov dword ptr [ebx],esi
    push {widget}; lea ecx,[ebp-4]; call 0x4805de
    push 0; push {F['callback']}; push esi; call 0x58bb94
    push eax; push 0; lea eax,[ebp-4]; push eax; push esi
    call 0x707b37; add esp,28
    mov edi,eax; mov dword ptr [ebx+4],eax
    push 0; push eax; mov ecx,esi; call 0x717486
    mov ecx,dword ptr [ebp-4]; sub ecx,0x10; call 0x481375
    push 0; mov ecx,edi; call 0x717271
    inc dword ptr [{STATE+8}]
done: pop edi; pop esi; pop ebx; mov esp,ebp; pop ebp; ret
''')
asm('clear',f'''
    push ebx
    call {F['find']}; test eax,eax; jz done
    mov ebx,eax
    mov ecx,dword ptr [ebx+24]; test ecx,ecx; jz cleared_text
    sub ecx,0x10; call 0x481375
cleared_text:
    mov eax,ebx; sub eax,{RECORDS}; shr eax,2
    mov dword ptr [eax+{ICON_KEYS}],0
    mov dword ptr [eax+{ICON_KEYS+4}],0
    mov eax,ebx
    mov edx,8
again: mov dword ptr [eax],0; add eax,4; dec edx; jnz again
done: pop ebx; ret
''')
asm('ctor_hook',f'''
    pushfd; pushad; mov ecx,edi; call {F['create']}; popad; popfd
    mov ecx,dword ptr [ebp-0xc]; mov eax,edi; jmp 0x5867aa
''')
asm('tick_hook',f'''
    push esi; mov esi,ecx; call 0x587c56
    pushfd; pushad; mov ecx,esi; call {F['refresh']}; popad; popfd
    pop esi; ret
''')
asm('dtor_hook',f'''
    pushfd; pushad; call {F['clear']}; popad; popfd
    push esi; mov esi,ecx; lea ecx,[esi+0x98]; jmp 0x5867c1
''')

# ECX=raw kingdom ID -> player index or PLAYER_COUNT. Independent families reject.
asm('index',f'''
    push esi; push edi; mov esi,ecx; xor edi,edi
again: push dword ptr [edi*4+{KSTR}]; push esi
    call 0x481574; add esp,8; test eax,eax; jz done
    inc edi; cmp edi,{PLAYER_COUNT}; jb again
done: mov eax,edi; pop edi; pop esi; ret
''')

# A new staging session starts at Random. SP uses a private xorshift shuffle;
# MP defers its shuffle until allocation, AFTER native launch finalizes the
# shared world seed. A lobby's raw MapSeed=0 means Random, not the resolved seed.
asm('state_init',f'''
    push ebx; push esi; push edi; mov esi,ecx
    cmp dword ptr [{STATE+32}],1; jne reset
    cmp dword ptr [{STATE+28}],esi; jne reset
    cmp dword ptr [{STATE+40}],0; je done
    cmp dword ptr [esi+0x64],0; jne done
    mov dword ptr [{STATE+40}],0
    mov dword ptr [{STATE+44}],0
    xor edi,edi
reuse:
    mov eax,dword ptr [{PAL_COUNT}]
    mov dword ptr [edi*4+{ASSIGNED}],eax
    inc edi; cmp edi,{PLAYER_COUNT}; jb reuse
    xor edi,edi
reuse_order:
    mov dword ptr [edi*4+{ORDER}],edi
    inc edi; cmp edi,dword ptr [{PAL_COUNT}]; jb reuse_order
    jmp shuffle_start
reset:
    mov dword ptr [{STATE+28}],esi
    mov dword ptr [{STATE+32}],1
    mov dword ptr [{STATE+40}],0
    mov dword ptr [{STATE+44}],0
    push ecx
    mov edi,{OWNERS}; xor eax,eax; mov ecx,16; rep stosd
    mov edi,{PREFERENCES}; mov ecx,{PREFERENCE_COUNT*2}; rep stosd
    pop ecx
    xor edi,edi
init:
    mov eax,dword ptr [{PAL_COUNT}]
    mov dword ptr [edi*4+{CHOICES}],eax
    mov dword ptr [edi*4+{ASSIGNED}],eax
    inc edi; cmp edi,{PLAYER_COUNT}; jb init
    xor edi,edi
init_order:
    mov dword ptr [edi*4+{ORDER}],edi
    inc edi; cmp edi,dword ptr [{PAL_COUNT}]; jb init_order
shuffle_start:
    cmp byte ptr [esi+0x100],0; jne done
    mov ebx,dword ptr [{PAL_COUNT}]; dec ebx; jz done
shuffle:
    mov eax,dword ptr [{STATE+48}]; test eax,eax; jnz seeded
    mov eax,0x735a2d91
seeded:
    mov edx,eax; shl edx,13; xor eax,edx
    mov edx,eax; shr edx,17; xor eax,edx
    mov edx,eax; shl edx,5; xor eax,edx
    mov dword ptr [{STATE+48}],eax
    lea ecx,[ebx+1]; xor edx,edx; div ecx
    mov eax,dword ptr [ebx*4+{ORDER}]
    mov ecx,dword ptr [edx*4+{ORDER}]
    mov dword ptr [ebx*4+{ORDER}],ecx
    mov dword ptr [edx*4+{ORDER}],eax
    dec ebx; jnz shuffle
done: pop edi; pop esi; pop ebx; ret
''')

asm('active',f'''
    push ebx; push esi; xor ebx,ebx; xor esi,esi
again:
    mov ecx,dword ptr [0xa53fe4]
    lea eax,[esi*4+{KSTR}]; push eax; call 0x5c6c0a
    test eax,eax; jz next
    mov eax,esi; call {F['lookup']}; test eax,eax; jz next
    bts ebx,esi
next: inc esi; cmp esi,{PLAYER_COUNT}; jb again
    mov eax,ebx; pop esi; pop ebx; ret
''')

# ECX is not an input. Return 1 when the allocation order is ready, 0 if the
# MP source is unavailable. SP's existing private RNG/order is untouched.
# Native FinalizeLaunchSettings 0x5c9621..0x5c9649 resolves MapSeed (session+10c)
# using the synchronized session RNG (+138), then writes WorldParams+4c.
# +138 is serialized at 0x5c7916 and deserialized at 0x5c7d5d. Read the FINAL
# seed through the same native source getter; never call/write either native RNG.
asm('shuffle_mp',f'''
    push ebx; push esi; push edi
    mov ecx,dword ptr [0xa53fe4]; test ecx,ecx; jz fail
    cmp byte ptr [ecx+0x100],0; je success
    cmp dword ptr [{PAL_COUNT}],1; jb fail
    cmp dword ptr [{PAL_COUNT}],{MAX_COLORS}; ja fail
    add ecx,0x60; call 0x5c18a5; test eax,eax; jz fail
    mov esi,dword ptr [eax+0x4c]
    xor esi,0x50415743
    jnz init_start
    mov esi,0x735a2d91
init_start:
    xor edi,edi
init:
    mov dword ptr [edi*4+{ORDER}],edi
    inc edi; cmp edi,dword ptr [{PAL_COUNT}]; jb init
    mov ebx,dword ptr [{PAL_COUNT}]; dec ebx; jz success
shuffle:
    mov eax,esi; shl eax,13; xor esi,eax
    mov eax,esi; shr eax,17; xor esi,eax
    mov eax,esi; shl eax,5; xor esi,eax
    mov eax,esi; lea ecx,[ebx+1]; xor edx,edx; div ecx
    mov eax,dword ptr [ebx*4+{ORDER}]
    mov ecx,dword ptr [edx*4+{ORDER}]
    mov dword ptr [ebx*4+{ORDER}],ecx
    mov dword ptr [edx*4+{ORDER}],eax
    dec ebx; jnz shuffle
success: mov eax,1; jmp done
fail: xor eax,eax
done: pop edi; pop esi; pop ebx; ret
''')

# Explicit active choices reserve their colors first; Random receives a unique
# remaining color. Allocation is frozen once native world creation consumes it.
asm('allocate',f'''
    push ebx; push esi; push edi
    call {F['shuffle_mp']}; test eax,eax; jz done
    call {F['active']}; mov dword ptr [{STATE+44}],eax
    mov dword ptr [{USED_MASK}],0
    mov dword ptr [{USED_MASK+4}],0
    xor esi,esi
explicit:
    mov eax,dword ptr [{PAL_COUNT}]
    mov dword ptr [esi*4+{ASSIGNED}],eax
    bt dword ptr [{STATE+44}],esi; jnc next_explicit
    mov edi,dword ptr [esi*4+{CHOICES}]
    cmp edi,dword ptr [{PAL_COUNT}]; jae next_explicit
    bt dword ptr [{USED_MASK}],edi; jc duplicate
    bts dword ptr [{USED_MASK}],edi
    mov dword ptr [esi*4+{ASSIGNED}],edi; jmp next_explicit
duplicate: mov eax,dword ptr [{PAL_COUNT}]; mov dword ptr [esi*4+{CHOICES}],eax
next_explicit: inc esi; cmp esi,{PLAYER_COUNT}; jb explicit
    xor esi,esi
random:
    bt dword ptr [{STATE+44}],esi; jnc next_random
    mov eax,dword ptr [esi*4+{ASSIGNED}]
    cmp eax,dword ptr [{PAL_COUNT}]; jb next_random
    xor edi,edi
scan:
    mov eax,dword ptr [edi*4+{ORDER}]
    bt dword ptr [{USED_MASK}],eax; jnc take
    inc edi; cmp edi,dword ptr [{PAL_COUNT}]; jb scan; jmp next_random
take: bts dword ptr [{USED_MASK}],eax; mov dword ptr [esi*4+{ASSIGNED}],eax
next_random: inc esi; cmp esi,{PLAYER_COUNT}; jb random
    mov eax,1
done:
    pop edi; pop esi; pop ebx; ret
''')

# ECX=kingdom parameter entry about to be consumed by native world creation.
# Only the color field is changed, and only for this armed new session.
# Save/replay loads, independent families and non-participants bypass.
asm('commit',f'''
    push ebx; push esi; push edi; mov esi,ecx
    cmp dword ptr [{STATE+32}],1; jne done
    mov ebx,dword ptr [0xa53fe4]; test ebx,ebx; jz done
    cmp ebx,dword ptr [{STATE+28}]; jne done
    cmp byte ptr [ebx+0x100],0; je commit_mode
    cmp dword ptr [{NET_STATE}],1; jne done
commit_mode:
    call {F['is_saved_source']}; test eax,eax; jnz done
    cmp dword ptr [ebx+0x6c],5; je done
    cmp dword ptr [ebx+0x60],2; ja done
    mov ecx,dword ptr [esi]; call {F['index']}; cmp eax,{PLAYER_COUNT}; jae done
    mov edi,eax
    cmp dword ptr [{STATE+40}],0; jne allocated
    call {F['allocate']}
    test eax,eax; jz done
    mov dword ptr [{STATE+40}],1
allocated:
    bt dword ptr [{STATE+44}],edi; jnc done
    mov eax,dword ptr [edi*4+{ASSIGNED}]
    cmp eax,dword ptr [{PAL_COUNT}]; jae done
    mov eax,dword ptr [eax*4+{COLORS}]; test eax,eax; jz done
    mov dword ptr [esi+0x20],eax
    inc dword ptr [{STATE+52}]
done: pop edi; pop esi; pop ebx; ret
''')
asm('create_world_hook',f'''
    pushfd; pushad; mov ecx,ebx; call {F['commit']}; popad; popfd
    mov eax,dword ptr [ebx+0x20]; mov dword ptr [ebp-0x10],eax
    jmp 0x6f551c
''')
asm('configure_world_hook',f'''
    pushfd; pushad; mov ecx,ebx; call {F['commit']}; popad; popfd
    push dword ptr [ebx+0x20]; mov ecx,edi; jmp 0x6f5179
''')

# Empty rows have no player object, so they intentionally fail editable-color
# eligibility. Validate only their UI preview without admitting them to apply,
# network orders, color reservation or world commit. Native 0x563584 explicitly
# accepts a null player and uses KingdomGlyphInfo as its default marker.
asm('empty_icon_eligible',f'''
    push ebx; push esi; mov esi,ecx
    call {F['is_saved_source']}; test eax,eax; jnz fail
    cmp dword ptr [esi+0xec],0; jne fail
    cmp dword ptr [esi+0xf8],5; je fail
    cmp dword ptr [esi+0xf4],0; je fail
    call {F['ensure']}; test eax,eax; jz fail
    mov ebx,dword ptr [0xa53fe4]; test ebx,ebx; jz fail
    cmp byte ptr [ebx+0x100],0; je single_player
    cmp dword ptr [{NET_STATE}],1; jne fail
    jmp session_mode
single_player:
    cmp dword ptr [ebx+0x128],0; jne fail
session_mode:
    cmp dword ptr [ebx+0x6c],5; je fail
    cmp dword ptr [ebx+0x60],1; je staging
    cmp dword ptr [ebx+0x60],2; jne fail
staging:
    mov eax,dword ptr [esi+0xf0]; test eax,eax; jz fail
    mov ecx,dword ptr [eax]; call {F['index']}
    cmp eax,{PLAYER_COUNT}; jae fail
    call {F['lookup']}; test eax,eax; jz fail
    cmp eax,dword ptr [esi+0xf0]; jne fail
    jmp done
fail: xor eax,eax
done: pop esi; pop ebx; ret
''')

# ECX=slot, EDX=choice. UI-only preview: the native formatter sees a stack copy
# of kingdom parameters, never a modified live entry. Preserve its player glyph.
# Cache the owned engine string; restore it if a stock lobby refresh replaces it.
# Same text means no allocation and no label setter. Destructor releases the cache.
asm('update_icon',f'''
    push ebp; mov ebp,esp; sub esp,0x80
    push ebx; push esi; push edi
    mov esi,ecx; mov dword ptr [ebp-4],edx
    mov dword ptr [ebp-16],0
    call {F['is_saved_source']}; test eax,eax; jz new_game
    mov ecx,esi; call {F['saved_entry']}; test eax,eax; jz done
    mov edx,dword ptr [eax+0x20]; test edx,edx; jz done
    mov dword ptr [ebp-16],edx; mov dword ptr [ebp-4],edx
    jmp verified
new_game:
    mov edx,dword ptr [ebp-4]; mov ecx,esi
    cmp edx,dword ptr [{PAL_COUNT}]; ja done
    call {F['eligible']}; test eax,eax; jnz verified
    mov edx,dword ptr [ebp-4]; cmp edx,dword ptr [{PAL_COUNT}]; jne done
    mov ecx,esi; call {F['empty_icon_eligible']}; test eax,eax; jz done
verified:
    mov edi,eax
    cmp dword ptr [esi+0xac],0; je done
    mov ecx,esi; call {F['find']}; test eax,eax; jz done
    mov ebx,eax
    mov eax,ebx; sub eax,{RECORDS}; shr eax,2; add eax,{ICON_KEYS}
    mov dword ptr [ebp-8],eax
    cmp dword ptr [ebx+24],0; je rebuild
    mov edx,dword ptr [ebp-4]; cmp dword ptr [eax],edx; jne rebuild
    mov edx,dword ptr [esi+0xec]; cmp dword ptr [eax+4],edx; je display
rebuild:
    mov eax,dword ptr [ebp-16]; test eax,eax; jnz descriptor_ready
    mov eax,dword ptr [ebp-4]
    cmp eax,dword ptr [{PAL_COUNT}]; jne palette
    mov eax,dword ptr [{RANDOM_COLOR}]; jmp descriptor_ready
palette:
    mov eax,dword ptr [eax*4+{COLORS}]
descriptor_ready: test eax,eax; jz done
    push esi
    mov esi,edi; lea edi,[ebp-0x80]; mov ecx,0x1b; cld
copy_parameter: mov edx,dword ptr [esi]; mov dword ptr [edi],edx
    add esi,4; add edi,4; dec ecx; jnz copy_parameter
    pop esi
    mov dword ptr [ebp-0x60],eax
    push dword ptr [esi+0xec]
    lea eax,[ebp-0x80]; push eax
    lea eax,[ebp-12]; push eax; call 0x563584; add esp,12
    mov ecx,dword ptr [ebx+24]; test ecx,ecx; jz store
    sub ecx,0x10; call 0x481375
store:
    mov eax,dword ptr [ebp-12]; mov dword ptr [ebx+24],eax
    mov eax,dword ptr [ebp-8]; mov edx,dword ptr [ebp-4]
    mov dword ptr [eax],edx
    mov edx,dword ptr [esi+0xec]; mov dword ptr [eax+4],edx
    inc dword ptr [{STATE+60}]
display:
    mov ecx,dword ptr [esi+0xac]; call 0x718fbc
    test eax,eax; jz set_label
    mov eax,dword ptr [eax]; test eax,eax; jz set_label
    push dword ptr [ebx+24]; push eax; call 0x481574; add esp,8
    test eax,eax; jz done
set_label:
    mov ecx,dword ptr [esi+0xac]; lea eax,[ebx+24]; push eax
    mov eax,dword ptr [ecx]; call dword ptr [eax+0xc8]
    inc dword ptr [{STATE+56}]
done: pop edi; pop esi; pop ebx; mov esp,ebp; pop ebp; ret
''')

# ECX=native dropdown object, EDX=choice. Random is always the first item.
# The caller also refreshes the outer label when the inner list already selected
# item zero during construction and the stock setter therefore reports no change.
asm('selected_index',f'''
    cmp edx,dword ptr [{PAL_COUNT}]; jne explicit
    xor eax,eax; ret
explicit:
    cmp edx,dword ptr [{PAL_COUNT}]; jae invalid
    mov eax,dword ptr [edx*4+{COLORS}]; test eax,eax; jz invalid
    add eax,8; push eax; call 0x701f84; ret
invalid: or eax,0xffffffff; ret
''')

# ECX=outer dropdown widget, [ESP+4]=native item index. Call AFTER repopulator End:
# native End restores its captured old ID (empty on first entry), wiping any
# selection made before End. Keep the caller's rebuilding guard until this returns.
asm('select_and_refresh',f'''
    push esi; mov esi,ecx
    push dword ptr [esp+8]; mov ecx,esi; call 0x702a38
    test al,al; jne done
    mov ecx,esi; call 0x702c7a
done: pop esi; ret 4
''')

# Append exactly two native order types after all 334 stock entries.
# The count guard prevents silently assigning incompatible wire IDs.
asm('network_init',f'''
    push ebx; push esi; push edi
    cmp dword ptr [{NET_STATE}],1; je ready
    cmp dword ptr [{NET_STATE}],0xffffffff; je fail
    mov eax,dword ptr [0xa30134]; test eax,eax; jz fail
    cmp dword ptr [eax+4],{STOCK_ORDER_COUNT}; jne disable
    push {decree_order_name}; mov ecx,{DECREE_NAME}; call 0x4805de
    push {request_order_name}; mov ecx,{REQUEST_NAME}; call 0x4805de
    push dword ptr [{DECREE_NAME}]
    push {F['network_decree']}
    mov ecx,{DECREE_DESC}; call 0x5bdaf8; add esp,8
    cmp dword ptr [{DECREE_DESC+4}],{STOCK_ORDER_COUNT}; jne disable
    push dword ptr [{REQUEST_NAME}]
    push {F['network_request']}
    mov ecx,{REQUEST_DESC}; call 0x5bdaf8; add esp,8
    cmp dword ptr [{REQUEST_DESC+4}],{STOCK_ORDER_COUNT+1}; jne disable
    mov dword ptr [{NET_STATE}],1
ready: mov eax,1; pop edi; pop esi; pop ebx; ret
disable: mov dword ptr [{NET_STATE}],0xffffffff
fail: xor eax,eax; pop edi; pop esi; pop ebx; ret
''')

# ECX=kingdom ordinal, EDX=palette ordinal (PAL_COUNT means Random).
# Wire v3 contains two uint32 values, NOT player-object references. The old
# 5bd034/5bd050 pair serializes a player object's +0x20 handle, not a string!
# Tagged kingdom ordinals reject legacy payloads before any string dereference.
asm('network_send',f'''
    push ebp; mov ebp,esp; sub esp,8
    push ebx; push esi; push edi
    mov dword ptr [ebp-4],ecx; mov dword ptr [ebp-8],edx
    xor ebx,ebx
    call {F['is_saved_source']}; test eax,eax; jnz done
    cmp ecx,{PLAYER_COUNT}; jae done
    cmp edx,dword ptr [{PAL_COUNT}]; ja done
    or dword ptr [ebp-4],{WIRE_TAG}
    cmp dword ptr [{NET_STATE}],1; jne done
    cmp dword ptr [0xa53fec],0; je done
    call 0x5bdae4; test eax,eax; jz done
    mov esi,eax; mov ecx,esi; mov eax,dword ptr [esi]; call dword ptr [eax+4]
    call 0x5bdaed; test al,al; jz finish
    call 0x5bda80; push eax; call 0x5bda70; add esp,4
    call 0x5bdac3; test eax,eax; jz finish
    mov edi,eax
    push {REQUEST_DESC}; push edi; call 0x5bda54; add esp,8
    push dword ptr [ebp-4]; push edi; call 0x4cacb4; add esp,8
    push dword ptr [ebp-8]; push edi; call 0x4cacb4; add esp,8
    mov ebx,1
finish:
    mov ecx,esi; mov eax,dword ptr [esi]; call dword ptr [eax+8]
done: mov eax,ebx
    pop edi; pop esi; pop ebx; mov esp,ebp; pop ebp; ret
''')

# Validate every wire ordinal before looking up LOCAL immortal engine strings.
# EAX=success, ECX/EDX=local kingdom/color IDs. Never trust a network pointer.
asm('network_decode',f'''
    sub ecx,{WIRE_TAG}
    cmp ecx,{PLAYER_COUNT}; jae reject
    cmp edx,dword ptr [{PAL_COUNT}]; ja reject
    mov ecx,dword ptr [ecx*4+{KSTR}]; test ecx,ecx; jz reject
    cmp edx,dword ptr [{PAL_COUNT}]; je random
    mov edx,dword ptr [edx*4+{COLORS}]; test edx,edx; jz reject
    mov edx,dword ptr [edx+8]; jmp valid
random: mov edx,dword ptr [{RANDOM_ID}]
valid: test edx,edx; jz reject
    mov eax,1; ret
reject: xor eax,eax; ret
''')

# ECX=kingdom ID, EDX=color ID, EAX=0 validate only / nonzero commit. This lets
# the host queue the decree before changing its own state, like the stock orders.
asm('network_apply',f'''
    push ebp; mov ebp,esp; sub esp,12
    push ebx; push esi; push edi
    mov dword ptr [ebp-4],ecx; mov dword ptr [ebp-8],edx; mov dword ptr [ebp-12],eax
    call {F['is_saved_source']}; test eax,eax; jnz reject
    test ecx,ecx; jz reject
    test edx,edx; jz reject
    mov eax,dword ptr [0xa53fe4]; test eax,eax; jz reject
    cmp byte ptr [eax+0x100],0; je reject
    mov ecx,eax; call {F['state_init']}
    mov ecx,dword ptr [ebp-4]; call {F['index']}
    cmp eax,{PLAYER_COUNT}; jae reject
    mov ebx,eax; call {F['lookup']}; test eax,eax; jz reject
    push dword ptr [{RANDOM_ID}]; push dword ptr [ebp-8]
    call 0x481574; add esp,8; test eax,eax; jnz explicit
    mov edi,dword ptr [{PAL_COUNT}]; jmp validated
explicit:
    xor edi,edi
find_color:
    mov eax,dword ptr [edi*4+{COLORS}]; test eax,eax; jz next_color
    push dword ptr [eax+8]; push dword ptr [ebp-8]
    call 0x481574; add esp,8; test eax,eax; jz validated
next_color: inc edi; cmp edi,dword ptr [{PAL_COUNT}]; jb find_color; jmp reject
validated:
    cmp edi,dword ptr [{PAL_COUNT}]; je accepted
    mov eax,ebx; mov edx,edi; call {F['color_conflict']}; test eax,eax; jnz reject
accepted:
    cmp dword ptr [ebx*4+{CHOICES}],edi; je same
    cmp dword ptr [ebp-12],0; je valid
    mov dword ptr [ebx*4+{CHOICES}],edi
    mov ecx,ebx; mov edx,edi; call {F['remember_choice']}
    mov dword ptr [{STATE+40}],0
    inc dword ptr [{NET_STATE+4}]
valid:
    mov eax,1; jmp done
same: mov eax,2; jmp done
reject: inc dword ptr [{NET_STATE+8}]; xor eax,eax
done: pop edi; pop esi; pop ebx; mov esp,ebp; pop ebp; ret
''')

# Host-side request callback. The stock permission check binds the kingdom ID to
# the actual ordering connection (or permits the host for AI slots). Accepted
# choices are decreed to every peer and applied locally, matching stock orders.
asm('network_request',f'''
    push ebp; mov ebp,esp; sub esp,16
    push ebx; push esi; push edi
    mov esi,dword ptr [ebp+8]; test esi,esi; jz done
    lea eax,[ebp-4]; push eax; push esi; call 0x4cac49; add esp,8
    lea eax,[ebp-8]; push eax; push esi; call 0x4cac49; add esp,8
    cmp dword ptr [{NET_STATE}],1; jne done
    mov ebx,dword ptr [0xa53fe4]; test ebx,ebx; jz done
    cmp byte ptr [ebx+0x100],0; je done
    cmp dword ptr [ebx+0x60],1; je staging
    cmp dword ptr [ebx+0x60],2; jne done
staging:
    mov ecx,dword ptr [0xa53fec]; test ecx,ecx; jz done
    call 0x5a90d5; test al,al; jz done
    mov ecx,dword ptr [ebp-4]; mov edx,dword ptr [ebp-8]
    call {F['network_decode']}; test eax,eax; jz denied
    mov dword ptr [ebp-12],ecx; mov dword ptr [ebp-16],edx
    mov eax,dword ptr [0xa53fec]
    mov edx,dword ptr [eax+0x2a4]; test edx,edx; jz denied
    cmp edx,dword ptr [eax+0xc]; je check_native_permission
    lea eax,[ebp-12]; push eax; mov ecx,ebx; call 0x5c6c0a
    mov ecx,dword ptr [0xa53fec]
    cmp eax,dword ptr [ecx+0x2a4]; jne denied
check_native_permission:
    lea eax,[ebp-12]; push eax; mov ecx,ebx; call 0x5cb17b
    test al,al; jz denied
    mov ecx,dword ptr [ebp-12]; mov edx,dword ptr [ebp-16]; xor eax,eax
    call {F['network_apply']}; test eax,eax; jz denied
    call 0x5bdace; test eax,eax; jz denied
    mov edi,eax
    mov ecx,edi; call {F['sync_decree_boundary']}
    push {DECREE_DESC}; push edi; call 0x5bda54; add esp,8
    push dword ptr [ebp-4]; push edi; call 0x4cacb4; add esp,8
    push dword ptr [ebp-8]; push edi; call 0x4cacb4; add esp,8
    mov ecx,dword ptr [ebp-12]; mov edx,dword ptr [ebp-16]; mov eax,1
    call {F['network_apply']}
    push eax; mov ecx,edi; call {F['sync_decree_boundary']}; pop eax
    test eax,eax; jz denied
    inc dword ptr [{NET_STATE+12}]; jmp done
denied: inc dword ptr [{NET_STATE+16}]
done: pop edi; pop esi; pop ebx; mov esp,ebp; pop ebp; ret
''')

# Peer-side decree callback. Only a host-produced, already validated order reaches
# this path. Stable IDs are resolved against each process's private palette.
asm('network_decree',f'''
    push ebp; mov ebp,esp; sub esp,8
    push ebx; push esi; push edi
    mov esi,dword ptr [ebp+8]; test esi,esi; jz done
    lea eax,[ebp-4]; push eax; push esi; call 0x4cac49; add esp,8
    lea eax,[ebp-8]; push eax; push esi; call 0x4cac49; add esp,8
    cmp dword ptr [{NET_STATE}],1; jne done
    mov eax,dword ptr [0xa53fe4]; test eax,eax; jz done
    cmp byte ptr [eax+0x100],0; je done
    mov ecx,dword ptr [ebp-4]; mov edx,dword ptr [ebp-8]
    call {F['network_decode']}; test eax,eax; jz done
    call {F['network_apply']}; test eax,eax; jz done
    inc dword ptr [{NET_STATE+20}]
done: pop edi; pop esi; pop ebx; mov esp,ebp; pop ebp; ret
''')

# The client dispatcher (5AEA6F/5AEAD7) hashes bit positions around EVERY decree.
# Native request handlers mirror these markers on the host (e.g. 58CF6F/58CFFD).
# 5BDA54 only writes the type ID: it does NOT emit those synchronizer events.
# Omitting the two markers produced log-137's exact 41/114-bit divergence.
# ECX = native output stream. Use its live position, including preceding orders,
# minus the native 3-bit stream header. The stock synchronizer retains all its
# thread/recording guards; no checksum resets, suppression or bypass are added.
asm('sync_decree_boundary',f'''
    mov eax,dword ptr [ecx+8]; mov edx,dword ptr [ecx+0xc]
    lea eax,[edx+eax*8]; sub eax,3
    push 0; push eax; push 0x8dbb68
    mov ecx,dword ptr [0xa53ff0]; call 0x5cdff2
    ret
''')

# ECX=visible slot. Local host may edit all eligible slots; clients only their
# exact native player object. This is UI-only, not a substitute for host checks.
asm('can_edit',f'''
    push esi; mov esi,ecx
    call {F['is_saved_source']}; test eax,eax; jnz denied
    mov eax,dword ptr [0xa53fe4]; test eax,eax; jz denied
    cmp byte ptr [eax+0x100],0; je allowed
    mov ecx,dword ptr [0xa53fec]; test ecx,ecx; jz denied
    call 0x5a90d5; test al,al; jnz allowed
    mov eax,dword ptr [0xa53fec]
    mov eax,dword ptr [eax+0xc]; test eax,eax; jz denied
    cmp eax,dword ptr [esi+0xec]; jne denied
allowed: mov eax,1; pop esi; ret
denied: xor eax,eax; pop esi; ret
''')
# Native AdminConn::SerializePrivateSessionMessage already provides a complete,
# ordered host-to-client snapshot on join / staging restoration. Append bounded
# palette ordinals there, not sixteen synthetic UI requests. These two call sites
# are private NETWORK messages only: the save/replay file format is unchanged.
# ECX=session, EDX=stream. Never serialize pointers or touch simulation RNG.
asm('snapshot_write',f'''
    push ebx; push esi; push edi
    mov ebx,ecx; mov esi,edx
    call {F['ensure']}
    mov ecx,ebx; call {F['state_init']}
    push {SNAPSHOT_TAG}; push esi; call 0x4cacb4; add esp,8
    push dword ptr [{PAL_COUNT}]; push esi; call 0x4cacb4; add esp,8
    xor edi,edi
again:
    push dword ptr [edi*4+{CHOICES}]; push esi; call 0x4cacb4; add esp,8
    inc edi; cmp edi,{PLAYER_COUNT}; jb again
    inc dword ptr [{NET_STATE+24}]
    pop edi; pop esi; pop ebx; ret
''')

# Stage and validate all sixteen entries before publishing any of them. A client
# cannot use this reader to overwrite the host. Loaded-save/replay world colors
# are owned by native saved state; never arm lobby commit for those source modes.
asm('snapshot_read',f'''
    push ebp; mov ebp,esp; sub esp,72
    push ebx; push esi; push edi
    mov ebx,ecx; mov esi,edx; xor edi,edi
read_all:
    lea eax,[ebp+edi*4-72]; push eax; push esi; call 0x4cac49; add esp,8
    inc edi; cmp edi,18; jb read_all
    cmp dword ptr [ebp-72],{SNAPSHOT_TAG}; jne invalid
    mov eax,dword ptr [{PAL_COUNT}]
    cmp dword ptr [ebp-68],eax; jne invalid
    xor edi,edi
validate:
    cmp dword ptr [ebp+edi*4-64],eax; ja invalid
    inc edi; cmp edi,{PLAYER_COUNT}; jb validate
    cmp ebx,dword ptr [0xa53fe4]; jne ignored
    call {F['is_saved_source']}; test eax,eax; jnz ignored
    cmp byte ptr [ebx+0x100],0; je ignored
    mov ecx,dword ptr [0xa53fec]; test ecx,ecx; jz ignored
    call 0x5a90d5; test al,al; jnz ignored
    cmp dword ptr [ebx+0x6c],5; je ignored
    cmp dword ptr [ebx+0x60],1; jb ignored
    cmp dword ptr [ebx+0x60],2; ja ignored
    call {F['ensure']}; test eax,eax; jz invalid
    mov ecx,ebx; call {F['state_init']}
    mov dword ptr [{STATE+40}],0
    mov dword ptr [{STATE+44}],0
    xor edi,edi
publish:
    mov eax,dword ptr [ebp+edi*4-64]
    mov dword ptr [edi*4+{CHOICES}],eax
    mov eax,dword ptr [{PAL_COUNT}]
    mov dword ptr [edi*4+{ASSIGNED}],eax
    inc edi; cmp edi,{PLAYER_COUNT}; jb publish
    call {F['bind_snapshot']}
    inc dword ptr [{NET_STATE+28}]
    mov eax,1; jmp done
invalid:
    inc dword ptr [{NET_STATE+32}]
ignored:
    xor eax,eax
done:
    pop edi; pop esi; pop ebx; mov esp,ebp; pop ebp; ret
''')

for name, original, extension in [('session_write_hook',0x5c775c,'snapshot_write'),
                                   ('session_read_hook',0x5c797a,'snapshot_read')]:
    asm(name,f'''
        push esi; push edi
        mov esi,dword ptr [esp+12]; mov edi,ecx
        push esi; call {original}
        pushfd; pushad
        mov ecx,edi; mov edx,esi; call {F[extension]}
        popad; popfd
        pop edi; pop esi; ret 4
    ''')

# Native color bit serialization only knows the enumerable stock descriptor
# index (+0xC). Private descriptors copy default's index, losing their identity
# in a loaded world's network snapshot. Keep the DB intact and use a tagged
# ordinal here instead. Both confirmed callers of each color-specific codec are
# patched; nation/faction serializers and save-file serialization are unchanged.
asm('color_wire_write',f'''
    push ebx; push esi; push edi
    mov esi,dword ptr [esp+16]; mov edi,dword ptr [esp+20]
    mov ebx,dword ptr [edi]
    mov eax,0xffffffff; test ebx,ebx; jz write
    call {F['ensure']}
    { ';'.join(f"cmp ebx,{BASE+c['descriptor']}; jne retired_write_next_{i}; mov eax,{c['wire_id']}; jmp write; retired_write_next_{i}:" for i,c in enumerate(RETIRED)) }
palette:
    xor edi,edi
find:
    cmp ebx,dword ptr [edi*4+{COLORS}]; je custom
    inc edi; cmp edi,dword ptr [{PAL_COUNT}]; jb find
    mov eax,dword ptr [ebx+0xc]; jmp write
custom:
    mov eax,edi; or eax,{DESCRIPTOR_TAG}
write:
    push eax; push esi; call 0x4cacb4; add esp,8
    pop edi; pop esi; pop ebx; ret
''')
asm('color_wire_read',f'''
    push ebp; mov ebp,esp; sub esp,4
    push ebx; push esi; push edi
    mov esi,dword ptr [ebp+8]; mov edi,dword ptr [ebp+12]
    lea eax,[ebp-4]; push eax; push esi; call 0x4cac49; add esp,8
    mov ebx,dword ptr [ebp-4]; mov eax,ebx; and eax,0xffff0000
    cmp eax,{DESCRIPTOR_TAG}; je custom
    mov eax,dword ptr [0xa4ffb0]; test eax,eax; jz invalid
    cmp ebx,dword ptr [eax+0x28]; jae invalid
    mov eax,dword ptr [eax+0x24]; mov eax,dword ptr [eax+ebx*4]; jmp publish
custom:
    and ebx,0xffff
    { ';'.join(f"cmp ebx,{c['wire_id'] & 0xffff}; je retired_read_{i}" for i,c in enumerate(RETIRED)) }
    cmp ebx,dword ptr [{PAL_COUNT}]; jae invalid
    call {F['ensure']}; test eax,eax; jz invalid
    mov eax,dword ptr [ebx*4+{COLORS}]; jmp publish
{ ';'.join(f"retired_read_{i}: call {F['ensure']}; test eax,eax; jz invalid; mov eax,{BASE+c['descriptor']}; jmp publish" for i,c in enumerate(RETIRED)) }
invalid: xor eax,eax
publish:
    mov dword ptr [edi],eax
    pop edi; pop esi; pop ebx; mov esp,ebp; pop ebp; ret
''')
# The stock save reader 69A0BB reads an engine string, resolves it through the
# color DB and traps if not found (69A140). Only extend that lookup call, not the
# global database: existing stock names/unknown-name errors keep native behavior.
asm('saved_color_lookup',f'''
    push ebx; push esi; push edi
    mov esi,dword ptr [esp+16]
    push esi; call 0x48edb9; test eax,eax; jnz done
    call {F['ensure']}; test eax,eax; jz done
    xor edi,edi
find:
    mov ebx,dword ptr [edi*4+{COLORS}]
    push dword ptr [ebx+8]; push esi; call 0x481574; add esp,8
    test eax,eax; jz found
    inc edi; cmp edi,dword ptr [{PAL_COUNT}]; jb find
    { ';'.join(f"push {c['id_va']}; push esi; call 0x481574; add esp,8; test eax,eax; jnz retired_lookup_next_{i}; mov eax,{BASE+c['descriptor']}; jmp done; retired_lookup_next_{i}:" for i,c in enumerate(RETIRED)) }
unknown:
    xor eax,eax; jmp done
found: mov eax,ebx
done: pop edi; pop esi; pop ebx; ret 4
''')

# EAX=target kingdom ordinal, EDX=explicit color. Ignore the target itself and
# absent players: keeping an absent slot's choice must not reserve that color.
# This also checks "same color" requests, which formerly bypassed conflicts.
asm('color_conflict',f'''
    push ebx; push esi; push edi
    mov ebx,eax; mov edi,edx; xor esi,esi
    cmp ebx,{PLAYER_COUNT}; jae free
    cmp edi,dword ptr [{PAL_COUNT}]; jae free
again:
    cmp esi,ebx; je next
    cmp dword ptr [esi*4+{CHOICES}],edi; jne next
    mov ecx,dword ptr [0xa53fe4]; test ecx,ecx; jz free
    lea eax,[esi*4+{KSTR}]; push eax; call 0x5c6c0a
    test eax,eax; jz next
    mov eax,esi; call {F['lookup']}; test eax,eax; jz next
    mov eax,1; jmp done
next: inc esi; cmp esi,{PLAYER_COUNT}; jb again
free: xor eax,eax
done: pop edi; pop esi; pop ebx; ret
''')

# Native player::SetKingdom runs for human and AI assignment and replicated seat
# changes. Preference belongs to player+20; OWNERS only describes where it is
# currently displayed. This also handles two-step swaps without overwriting the
# displaced player's preference. Saved kingdoms deliberately retain their colors.
asm('on_kingdom_assigned',f'''
    push ebx; push esi; push edi
    mov esi,ecx; test esi,esi; jz done
    cmp byte ptr [esi+0xe],0; jne done
    mov ebx,dword ptr [0xa53fe4]; test ebx,ebx; jz done
    cmp dword ptr [ebx+0x6c],5; je done
    cmp dword ptr [ebx+0x64],0; jne done
    cmp dword ptr [ebx+0x60],1; jb done
    cmp dword ptr [ebx+0x60],2; ja done
    call {F['ensure']}; test eax,eax; jz done
    mov ecx,ebx; call {F['state_init']}
    mov ecx,dword ptr [esi+0x20]; test ecx,ecx; jz done
    call {F['preference']}; test eax,eax; jz done
    mov ebx,eax
    xor edi,edi
clear_old:
    mov eax,dword ptr [esi+0x20]
    cmp dword ptr [edi*4+{OWNERS}],eax; jne next_old
    mov dword ptr [edi*4+{OWNERS}],0
    mov eax,dword ptr [{PAL_COUNT}]
    mov dword ptr [edi*4+{CHOICES}],eax
    mov dword ptr [edi*4+{ASSIGNED}],eax
next_old:
    inc edi; cmp edi,{PLAYER_COUNT}; jb clear_old
    mov dword ptr [{STATE+40}],0
    mov dword ptr [{STATE+44}],0
    mov ecx,dword ptr [esi+0x24]; test ecx,ecx; jz done
    call {F['index']}; cmp eax,{PLAYER_COUNT}; jae done
    mov edi,eax
    mov edx,dword ptr [ebx+4]
    call {F['color_conflict']}; test eax,eax; jz assign
    mov eax,dword ptr [{PAL_COUNT}]; mov dword ptr [ebx+4],eax
    inc dword ptr [{NET_STATE+40}]
assign:
    mov eax,dword ptr [esi+0x20]; mov dword ptr [edi*4+{OWNERS}],eax
    mov eax,dword ptr [ebx+4]; mov dword ptr [edi*4+{CHOICES}],eax
    mov eax,dword ptr [{PAL_COUNT}]; mov dword ptr [edi*4+{ASSIGNED}],eax
done: pop edi; pop esi; pop ebx; ret
''')

# ECX=native participant ID. Bounded session preference table. When all slots
# have been used, reclaim a disconnected ID; never evict a current participant.
asm('preference',f'''
    push ebx; push esi; push edi; push ebp
    mov ebx,ecx; test ebx,ebx; jz fail
    xor edi,edi; xor ebp,ebp
find:
    lea esi,[edi*8+{PREFERENCES}]
    cmp dword ptr [esi],ebx; je found
    cmp dword ptr [esi],0; jne next
    test ebp,ebp; jnz next
    mov ebp,esi
next: inc edi; cmp edi,{PREFERENCE_COUNT}; jb find
    test ebp,ebp; jnz create
    xor edi,edi
reclaim:
    lea esi,[edi*8+{PREFERENCES}]
    mov eax,dword ptr [0xa53fe4]; test eax,eax; jz fail
    mov eax,dword ptr [eax+0xc8]; mov ecx,64
roster:
    test eax,eax; jz available
    mov edx,dword ptr [eax]; test edx,edx; jz fail
    mov edx,dword ptr [edx+0x20]
    cmp edx,dword ptr [esi]; je used
    mov eax,dword ptr [eax+4]; dec ecx; jnz roster
    jmp fail
used: inc edi; cmp edi,{PREFERENCE_COUNT}; jb reclaim
    jmp fail
available: mov ebp,esi
create:
    mov dword ptr [ebp],ebx
    mov eax,dword ptr [{PAL_COUNT}]; mov dword ptr [ebp+4],eax
    mov esi,ebp
found: mov eax,esi; jmp done
fail: xor eax,eax
done: pop ebp; pop edi; pop esi; pop ebx; ret
''')

# Bind an accepted choice to the current participant immediately, not on a UI
# tick. That is essential for swaps, spectators and headless/late-joining peers.
asm('remember_choice',f'''
    push ebx; push esi; push edi
    mov ebx,ecx; mov edi,edx
    cmp ebx,{PLAYER_COUNT}; jae done
    mov ecx,dword ptr [0xa53fe4]; test ecx,ecx; jz done
    lea eax,[ebx*4+{KSTR}]; push eax; call 0x5c6c0a
    test eax,eax; jz done
    mov esi,dword ptr [eax+0x20]; test esi,esi; jz done
    mov ecx,esi; call {F['preference']}; test eax,eax; jz done
    mov dword ptr [eax+4],edi
    mov dword ptr [ebx*4+{OWNERS}],esi
done: pop edi; pop esi; pop ebx; ret
''')

asm('bind_snapshot',f'''
    push esi; xor esi,esi
again:
    mov ecx,esi; mov edx,dword ptr [esi*4+{CHOICES}]
    call {F['remember_choice']}
    inc esi; cmp esi,{PLAYER_COUNT}; jb again
    pop esi; ret
''')

# Replace the string-copy CALL inside 5BD6D5, retaining native string ownership,
# return value, changed flag, stack cleanup and all caller-visible registers.
asm('player_kingdom_copy_hook',f'''
    push esi; lea esi,[ecx-0x24]
    push dword ptr [esp+8]; call 0x483fb6
    pushfd; pushad
    mov ecx,esi; call {F['on_kingdom_assigned']}
    popad; popfd
    pop esi; ret 4
''')

# Live r7 save lobby: session+60=2, +64=2, +6c=3. Source kind (+64),
# not source mode (+60), identifies a save. Native 5C18A5 selects its world
# through session+7C. Keep this guard independent of slot/UI availability.
asm('is_saved_source',f'''
    mov eax,dword ptr [0xa53fe4]; test eax,eax; jz done
    cmp dword ptr [eax+0x64],2; sete al; movzx eax,al
done: ret
''')

# Read-only saved kingdom entry. Vacant saved kingdoms still show their color.
# Verify native lookup against the current slot, so stale rows while switching
# sources cannot display or dereference a previous save's descriptor.
asm('saved_entry',f'''
    push ebx; push esi; push edi; mov esi,ecx
    call {F['is_saved_source']}; test eax,eax; jz fail
    mov ebx,dword ptr [0xa53fe4]
    cmp dword ptr [ebx+0x6c],5; je fail
    cmp dword ptr [ebx+0x60],1; jb fail
    cmp dword ptr [ebx+0x60],4; ja fail
    cmp dword ptr [esi+0xf8],5; je fail
    mov edi,dword ptr [esi+0xf0]; test edi,edi; jz fail
    cmp dword ptr [esi+0xf4],0; je fail
    call {F['ensure']}; test eax,eax; jz fail
    mov edx,dword ptr [esi+0xf4]
    cmp dword ptr [edi],0; je fail
    cmp dword ptr [edx],0; je fail
    push dword ptr [edx]; push dword ptr [edi]
    call 0x481574; add esp,8; test eax,eax; jnz fail
    mov ecx,dword ptr [edi]; test ecx,ecx; jz fail
    call {F['index']}; cmp eax,{PLAYER_COUNT}; jae fail
    call {F['lookup']}; cmp eax,edi; jne fail
    mov edx,dword ptr [eax+0x20]; test edx,edx; jz fail
    cmp dword ptr [edx+8],0; je fail
    cmp dword ptr [edx+0x10],0; je fail
    jmp done
fail: xor eax,eax
done: pop edi; pop esi; pop ebx; ret
''')

# One disabled item, taken directly from the save (including stock colors absent
# from our palette). No writes to CHOICES/ASSIGNED, world data, or the save file.
# Cache mode=2 distinguishes this list from the editable new-game list (mode=1).
asm('refresh_saved',f'''
    push ebp; mov ebp,esp; sub esp,0x30
    push ebx; push esi; push edi; mov esi,ecx
    call {F['find']}; test eax,eax; jz done
    mov ebx,eax; cmp dword ptr [ebx+4],0; je done
    cmp dword ptr [ebx+20],0; jne done
    push 0; mov ecx,dword ptr [ebx+4]; call 0x71728f
    mov ecx,esi; call {F['saved_entry']}; test eax,eax; jz hide
    mov edi,dword ptr [eax+0x20]
    mov ecx,esi; xor edx,edx; call {F['update_icon']}
    cmp dword ptr [ebx+16],2; jne build
    cmp dword ptr [ebx+8],edi; je select
build:
    mov dword ptr [ebx+20],1
    mov dword ptr [ebx+16],2; mov dword ptr [ebx+8],edi
    mov dword ptr [ebx+12],0; mov dword ptr [ebx+28],0
    push 1; mov ecx,dword ptr [ebx+4]; call 0x717271
    lea ecx,[ebp-4]; call 0x480633
    push dword ptr [edi+0x10]
    sub esp,24
    fld dword ptr [edi+0x18]; fstp qword ptr [esp]
    fld dword ptr [edi+0x1c]; fstp qword ptr [esp+8]
    fld dword ptr [edi+0x20]; fstp qword ptr [esp+16]
    push {label_format}; lea eax,[ebp-4]; push eax
    call 0x4810c4; add esp,36
    push dword ptr [ebx+4]; lea ecx,[ebp-0x30]; call 0x70517f
    push 0; lea eax,[edi+8]; push eax; lea eax,[ebp-4]; push eax
    lea ecx,[ebp-0x30]; call 0x70502e
    lea ecx,[ebp-0x30]; call 0x7051b1
    lea ecx,[ebp-0x30]; call 0x7051a6
    mov ecx,dword ptr [ebp-4]; sub ecx,0x10; call 0x481375
select:
    mov dword ptr [ebx+20],1
    push 0; mov ecx,dword ptr [ebx+4]; call {F['select_and_refresh']}
    mov dword ptr [ebx+20],0; jmp done
hide:
    mov dword ptr [ebx+16],0
    push 0; mov ecx,dword ptr [ebx+4]; call 0x717271
done: pop edi; pop esi; pop ebx; mov esp,ebp; pop ebp; ret
''')

# DropDown::Layout overwrites the TGI list width with the closed control width.
# At its final SetRect call ESI is the outer dropdown, stack argument 1 is the
# computed logical (left, top, width, height). Widen only registered Paw controls;
# all stock dropdowns and the closed arrow keep their exact original geometry.
asm('popup_rect_hook',f'''
    pushfd; pushad
    mov eax,{RECORDS}; mov edx,64
again:
    cmp dword ptr [eax],0; je next
    cmp dword ptr [eax+4],esi; je found
next: add eax,32; dec edx; jnz again; jmp done
found:
    mov eax,dword ptr [esp+40]
    mov dword ptr [eax+8],0x43480000
done: popad; popfd; jmp 0x70cab3
''')

for left, right in zip(sorted(routines,key=lambda r:r['offset']), sorted(routines,key=lambda r:r['offset'])[1:]):
    assert left['offset']+left['length'] <= right['offset'], (left['name'], right['name'])
assert max(r['offset']+r['length'] for r in routines) <= SIZE

patches=[
    {'rva':0x1267a5,'original':raw[0x1267a5:0x1267aa].hex(),'kind':'jmp','target':F['ctor_hook']-BASE},
    {'rva':0x12693f,'original':raw[0x12693f:0x126944].hex(),'kind':'call','target':F['tick_hook']-BASE},
    {'rva':0x1267b8,'original':raw[0x1267b8:0x1267c1].hex(),'kind':'jmp','target':F['dtor_hook']-BASE},
    {'rva':0x295516,'original':raw[0x295516:0x29551c].hex(),'kind':'jmp','target':F['create_world_hook']-BASE},
    {'rva':0x295174,'original':raw[0x295174:0x295179].hex(),'kind':'jmp','target':F['configure_world_hook']-BASE},
    {'rva':0x152b5a,'original':raw[0x152b5a:0x152b5f].hex(),'kind':'jmp','target':F['session_write_hook']-BASE},
    {'rva':0x152b86,'original':raw[0x152b86:0x152b8b].hex(),'kind':'jmp','target':F['session_read_hook']-BASE},
]
for target, sites in [('color_wire_write',[0x9a0ee,0x2957ec]),
                      ('color_wire_read',[0x99f06,0x2958ce]),
                      ('saved_color_lookup',[0x23a122]),
                      ('player_kingdom_copy_hook',[0x15d6df]),
                      ('popup_rect_hook',[0x2a2ebb])]:
    for site in sites:
        assert raw[site] == 0xe8
        original_target = GAME+site+5+struct.unpack_from('<i',raw,site+1)[0]
        assert original_target == {'color_wire_write':0x4fa344,'color_wire_read':0x4fa21e,
                                   'saved_color_lookup':0x48edb9,'player_kingdom_copy_hook':0x483fb6,
                                   'popup_rect_hook':0x70cab3}[target]
        patches.append({'rva':site,'original':raw[site:site+5].hex(),'kind':'call','target':F[target]-BASE})
assert patches[0]['original']=='8b4df48bc7'
assert patches[1]['original']=='e812130000'
assert patches[2]['original']=='568bf18d8e98000000'
out=args.out; out.mkdir(parents=True,exist_ok=True)
(out/'payload.bin').write_bytes(payload)
rel=struct.pack('<I',len(fixups))+b''.join(struct.pack('<III',*r) for r in fixups)
(out/'fixups.bin').write_bytes(rel)
manifest={'mode':'single-and-multiplayer-new-game','multiplayer_supported':True,'model_game_base':GAME,
          'model_cave_base':BASE,'functions':{k:v-BASE for k,v in F.items()},'state_offset':STATE-BASE,
          'size':SIZE,'patches':patches,'fixup_count':len(fixups),'payload_sha256':hashlib.sha256(payload).hexdigest(),
          'native_gameplay_tested':False}
manifest['stock_order_count']=STOCK_ORDER_COUNT
manifest['custom_order_ids']=[STOCK_ORDER_COUNT,STOCK_ORDER_COUNT+1]
manifest['selection_after_repopulator_end']=True
manifest['empty_slot_icon_gray_ui_only']=True
manifest['wire_codec']='v3-tagged-uint32-native-4cacb4-4cac49'
manifest['wire_tag']=hex(WIRE_TAG)
manifest['host_decree_sync_boundaries']=True
manifest['client_edits_own_slot_only']=True
manifest['host_identity_not_request_sender_identity']=True
manifest['host_full_private_session_color_snapshot']=True
manifest['snapshot_tag']=hex(SNAPSHOT_TAG)
manifest['snapshot_fields']='tag,paletteCount,16 bounded ordinals (paletteCount = Random)'
manifest['snapshot_save_replay_file_format_unchanged']=True
manifest['private_color_network_descriptor_roundtrip']=True
manifest['saved_private_color_id_lookup']=True
manifest['rejoin_conflicting_color_becomes_random']=True
manifest['rejoin_check']='native player SetKingdom; newcomer loses, incumbent preserved; MP staging only'
manifest['same_color_request_checks_other_active_players']=True
manifest['saved_lobby_color_readonly_preview']=True
manifest['saved_source_kind']=2
manifest['saved_preview_preserves_new_game_choices']=True
manifest['participant_color_ownership']='native replicated player ID, independent of seat and nickname'
manifest['compact_color_control']=True
manifest['retired_colors']=[{k:v for k,v in c.items() if not k.endswith('_va')} for c in RETIRED]
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
(out/'payload.asm.txt').write_text('\n\n'.join(r['name']+'\n'+r['assembly'] for r in routines)+'\n',encoding='utf-8')

# Mechanical UI transform. Sources stay untouched; output is a staging candidate.
source=(ROOT/'evidence/packed/UI/Menus/staging.tgi').read_bytes()
text=source.decode('ascii')
def block_span(text, pattern, begin=0):
    m=re.search(pattern,text[begin:]); assert m,pattern
    start=begin+m.start(); brace=text.index('{',start); depth=1; end=brace+1
    while depth:
        if text[end]=='{': depth+=1
        elif text[end]=='}': depth-=1
        end+=1
    return start,end
for slot in ['ObserverSlot','PlayerSlot']:
    a,b=block_span(text,rf'\[{slot}\b')
    block=text[a:b]
    # Keep the original single-row height. A 20px arrow fits after the color
    # circle; only the name/AI control shifts 13px, race/faction remain in place.
    for name in ['Name','AddAI']:
        ca,cb=block_span(block,rf'\[{name}\b')
        child=block[ca:cb].replace('L = 33','L = 46').replace('R = +148','R = +135')
        block=block[:ca]+child+block[cb:]
    extra='''
                    ;; Paw player colors. Bound by the experimental launcher.
                    [PawColor Template=SharedDropDownWidget]
                    {
                        [View]
                        {
                            L = 24
                            T = 4
                            R = +20
                            B = +20
                        }

                        ;; Keep the inherited view type, but hide the closed
                        ;; caption: the adjacent circle already shows the color.
                        [SelectedItem]
                        {
                            [View]
                            {
                                L = 0
                                R = +0
                            }
                            [Label]
                            {
                            L = 0
                            R = +0
                            color = 0,0,0,0
                            text = "#staging_WorldParamsPanel_random_option_text"
                            }
                        }

                        [ListBox]
                        {
                        num_visible_items = 17
                        [View]
                        R = +200
                        }
                    }
'''
    # Native parent owns this child. Observers get it too, but it stays hidden.
    block=block[:-1]+extra+block[-1:]
    text=text[:a]+block+text[b:]
assert text.count('[PawColor Template=SharedDropDownWidget]')==2
assert text.count('text = "#staging_WorldParamsPanel_random_option_text"')==2
(out/'staging.tgi').write_bytes(text.encode('ascii'))

print('Built',len(routines),'native routines;',len(fixups),'relocations;',len(payload),'payload bytes')
print('Host-authoritative multiplayer request/decree transport is included.')
