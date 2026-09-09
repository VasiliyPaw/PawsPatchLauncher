"""Extend the accepted r9 native bridge; no change to simulation or networking."""
import argparse,sys,struct,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
a=p.parse_args();sys.path.insert(0,str(a.legacy.resolve()))
import build_city_interaction as m
b=m.b;S=m.S
from native_construction import install as install_construction
install_construction(m)
assert b.n.raw[0x188215:0x18821a]==bytes.fromhex('b84e358900')
assert b.n.raw[0x1883de:0x1883e4]==bytes.fromhex('565733ff8bf1')
name=("PawCitySettings\0").encode('utf-16le');b.payload[0xb50:0xb50+len(name)]=name
label=("Client\0").encode('utf-16le');b.payload[0xba8:0xba8+len(label)]=label
# Add a native settings toggle to the F1 panel before its layout is loaded.
anchor='mov ebx,1\nload_original:'
assert m.load.count(anchor)==1
code=m.load.replace(anchor,f'call {S+0x5200}\n'+anchor)
m.replace(0x1200,code,0x400)
m.replace(0x5200,f'''
push {S+0xb50}; lea ecx,[ebp-4]; call 0x4805de
push 0; push 0; push 0; lea eax,[ebp-4]; push eax; call 0x7184e9; add esp,16
mov dword ptr [{S+0xa8}],eax
push 0; push eax; mov ecx,edi; call 0x717486
mov ecx,dword ptr [ebp-4]; sub ecx,16; call 0x481375
mov dword ptr [{S+0xb0}],0
push {S+0xba8}; lea ecx,[ebp-4]; call 0x4805de
lea eax,[ebp-4]; push 0; push eax; call 0x4e1d30; add esp,8
push 0; push eax; mov ecx,dword ptr [{S+0xa8}]; call 0x717486
mov ecx,dword ptr [ebp-4]; sub ecx,16; call 0x481375
ret
''',0x100)
m.replace(0x1600,f'''
pushfd
cmp ecx,dword ptr [{S+0x48}]; jne destroy_done
mov dword ptr [{S+0x48}],0; mov dword ptr [{S+0x4c}],0; mov dword ptr [{S+0x50}],0
mov dword ptr [{S+0x90}],0; mov dword ptr [{S+0x80}],0; mov dword ptr [{S+0x84}],0
mov dword ptr [{S+0xa8}],0
call {S+0x6c00}
destroy_done: popfd; jmp 0x51b71e
''',0x100)
m.replace(0x1700,f'''
pushfd; pushad
cmp ecx,dword ptr [{S+0x48}]; jne tick_done
call {S+0x1c00}; call {S+0x4300}; call {S+0x4600}; call {S+0x5300}
inc dword ptr [{S+0x60}]
mov ecx,dword ptr [{S+0x4c}]; test ecx,ecx; jz tick_done
mov eax,dword ptr [ecx+0x24]; shr eax,7; and eax,1
cmp eax,dword ptr [{S+0x40}]; je tick_done
mov dword ptr [{S+0x40}],eax; inc dword ptr [{S+0x54}]
mov eax,dword ptr [{S}]; mov dword ptr [{S+0x70}],eax
tick_done: popad; popfd; jmp 0x51b205
''',0x200)
m.replace(0x5300,f'''
mov ecx,dword ptr [{S+0xa8}]; test ecx,ecx; jz gear_done
mov eax,dword ptr [ecx+0x24]; shr eax,7; and eax,1
cmp eax,dword ptr [{S+0xb0}]; je gear_done
mov dword ptr [{S+0xb0}],eax
mov dword ptr [{S+0xb4}],1
inc dword ptr [{S+0xac}]
gear_done: ret
''',0x100)
# Last-moment economic gate, after native ownership/busy/legality checks.
# ESI points at the freshly generated candidate. Protect all five economic
# resources, using current engine income and adverse outstanding commitments.
m.replace(0x3900,f'''
call {S+0x4200}; test eax,eax; jnz input_invalid
cmp dword ptr [{S+0x7c}],0; jne input_invalid
cmp dword ptr [{S+0x80}],0; jne input_invalid
cmp dword ptr [{S+0xb4}],0; jne input_invalid
cmp dword ptr [{S+0xb8}],1; jne input_invalid
mov eax,dword ptr [{S+0x1c020}]; test eax,1; jnz input_invalid
cmp eax,dword ptr [{S+0x1c024}]; jne input_invalid
jmp {S+0x5000}
input_invalid: xor eax,eax; ret
''',0x100)
m.replace(0x5000,f'''
push ebx; push ecx; push edx; push edi
cmp dword ptr [{S+0x130}],1; jne unsafe
cmp dword ptr [{S+0x118}],9; je resource_order_ok
cmp dword ptr [{S+0x118}],10; jne unsafe
resource_order_ok:
mov eax,dword ptr [{S+0x10c}]; test eax,eax; jz unsafe
mov ecx,dword ptr [eax+0x1a8]; mov edx,dword ptr [eax+0x1c0]
test ecx,ecx; jz unsafe; test edx,edx; jz unsafe
xor ebx,ebx
resource_loop:
cmp ebx,5; jae safe
mov edi,ebx
cmp dword ptr [{S+0x118}],10; jne resource_index_ready
test ebx,ebx; jz resource_index_ready
inc edi
resource_index_ready:
movss xmm0,dword ptr [ecx+edi*4]; subss xmm0,dword ptr [edx+edi*4]
addss xmm0,dword ptr [{S+0x1b020}+ebx*4]
movd eax,xmm0; and eax,0x7f800000; cmp eax,0x7f800000; je unsafe
movss xmm1,dword ptr [{S+0x1b000}+ebx*4]
test ebx,ebx; jnz non_gold_floor
xorps xmm1,xmm1
non_gold_floor:
minss xmm1,xmm0
movss xmm2,dword ptr [esi+20+edi*4]
xorps xmm3,xmm3; ucomiss xmm2,xmm3; jp unsafe; jae resource_next
addss xmm0,xmm2; ucomiss xmm0,xmm1; jp unsafe; jb unsafe
resource_next: inc ebx; jmp resource_loop
safe: mov eax,1; jmp gate_end
unsafe: xor eax,eax
gate_end: pop edi; pop edx; pop ecx; pop ebx; ret
''',0x200)

# The game uses a D3D hardware cursor. Its per-frame update and WM_SETCURSOR
# handler compete with the owned WinForms dialog's Windows cursor. While the
# settings lock is held, hide only the game's D3D cursor and skip SetCursor(NULL).
# No polling, global cursor replacement, input interception or simulation change.
hide_cursor='''
popfd
mov eax,dword ptr [ecx+0x1c]; test eax,eax; jz cursor_done
push 0; push eax; mov edx,dword ptr [eax]; call dword ptr [edx+0x30]
cursor_done: ret
'''
m.replace(0x5400,f'''
pushfd; cmp dword ptr [{S+0xb4}],0; jne dialog_cursor
popfd; mov eax,0x89354e; jmp 0x5e821a
dialog_cursor:
'''+hide_cursor,0x100)
m.replace(0x5500,f'''
pushfd; cmp dword ptr [{S+0xb4}],0; jne dialog_cursor
popfd; push esi; push edi; xor edi,edi; mov esi,ecx; jmp 0x5e83e4
dialog_cursor:
'''+hide_cursor,0x100)
from native_resource_inputs import install as install_inputs
install_inputs(m,code)
a.out.mkdir(parents=True,exist_ok=False)
(a.out/'AssistantPayload.bin').write_bytes(b.payload)
(a.out/'AssistantFixups.bin').write_bytes(struct.pack('<I',len(b.fixups))+b''.join(struct.pack('<III',*f) for f in b.fixups))
(a.out/'manifest.json').write_text(json.dumps(dict(m.manifest,revision='city-policy-local-r13',size=len(b.payload),fixupCount=len(b.fixups)),indent=2)+'\n')
print('POLICY_NATIVE_BUILT',len(b.fixups))
