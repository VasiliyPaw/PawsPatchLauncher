"""Five isolated native numeric inputs; four income floors and the gold reserve.

No new input hooks: extend the accepted reserve hooks to recognize our widgets.
The game UI owns committed floors after startup. A seqlock/ack blocks dispatch
until the helper has consumed them. Pending construction accounting is untouched.
"""

def install(m, load):
    S=m.S; b=m.b
    for i,name in enumerate(('PawStoneFloor','PawWoodFloor','PawIronFloor','PawManaFloor')):
        raw=(name+'\0').encode('utf-16le')
        assert len(raw)<=32
        b.payload[0x1c100+i*32:0x1c100+i*32+len(raw)]=raw
    # Caller owns EBP's native string temporary and EDI's panel pointer.
    m.replace(0x6400,f'''
push esi
xor esi,esi
create_loop:
mov eax,esi; shl eax,5; add eax,{S+0x1c100}
push eax; lea ecx,[ebp-4]; call 0x4805de
push 0; push 0; push 0; lea eax,[ebp-4]; push eax; call 0x704bf1; add esp,16
mov dword ptr [{S+0x1c000}+esi*4],eax
push 0; push eax; mov ecx,edi; call 0x717486
mov ecx,dword ptr [ebp-4]; sub ecx,16; call 0x481375
inc esi; cmp esi,4; jb create_loop
pop esi; ret
''',0x100)
    # Render after native layout loading, including reloads of the same panel.
    m.replace(0x6500,f'''
pushfd; pushad
mov ebx,1
render_all:
mov eax,ebx; call {S+0x6900}
inc ebx; cmp ebx,5; jb render_all
popad; popfd; ret
''',0x100)
    load=load.replace(f'call {S+0x5200}',f'call {S+0x5200}; call {S+0x6400}')
    load=load.replace('load_done:\n',f'load_done:\ncall {S+0x6500}\n')
    m.replace(0x1200,load,0x400)
    # EAX index 0..4 -> ECX widget, EAX unchanged.
    m.replace(0x6600,f'''
xor ecx,ecx; cmp eax,4; ja widget_done
test eax,eax; jz widget_gold
mov ecx,dword ptr [{S+0x1bffc}+eax*4]; ret
widget_gold: mov ecx,dword ptr [{S+0x50}]
widget_done: ret
''',0x80)
    # EDX native Editbox child -> EAX input ID 1..5, zero for other controls.
    m.replace(0x6680,f'''
test edx,edx; jz child_none
xor eax,eax
child_loop:
call {S+0x6600}; test ecx,ecx; jz child_next
cmp edx,dword ptr [ecx+0x6c]; je child_found
child_next: inc eax; cmp eax,5; jb child_loop
child_none: xor eax,eax; ret
child_found: inc eax; ret
''',0x80)
    # EAX index -> EAX committed integer. Resource floor floats are exact integers.
    m.replace(0x6700,f'''
test eax,eax; jz value_gold
cvttss2si eax,dword ptr [{S+0x1b000}+eax*4]; ret
value_gold: mov eax,dword ptr [{S+0x44}]; ret
''',0x100)
    # EAX value, EDX index. Preserve registers. No revision for unchanged input.
    m.replace(0x6800,f'''
pushfd; pushad
cmp edx,4; ja commit_done
test eax,eax; js commit_done
test edx,edx; jz commit_gold
cmp eax,9999; ja commit_done
cvtsi2ss xmm0,eax
movd ecx,xmm0
cmp ecx,dword ptr [{S+0x1b000}+edx*4]; je commit_done
inc dword ptr [{S+0x1c020}]
mov dword ptr [{S+0x1b000}+edx*4],ecx
inc dword ptr [{S+0x1c020}]
jmp commit_changed
commit_gold:
cmp eax,dword ptr [{S+0xa4}]; ja commit_done
cmp eax,dword ptr [{S+0x44}]; je commit_done
mov dword ptr [{S+0x44}],eax
commit_changed:
inc dword ptr [{S+0x54}]
mov eax,dword ptr [{S}]; mov dword ptr [{S+0x70}],eax
commit_done: popad; popfd; ret
''',0x100)
    # EAX index; copies stack text into the game's own ref-counted string.
    m.replace(0x6900,f'''
pushfd; pushad; sub esp,36
call {S+0x6600}; test ecx,ecx; jz render_done
cmp dword ptr [ecx+0x6c],0; je render_done
mov esi,ecx; call {S+0x6700}; lea edi,[esp+30]
xor edx,edx; mov word ptr [edi],dx; mov ebx,10
render_digits: xor edx,edx; div ebx; add edx,48; sub edi,2
mov word ptr [edi],dx; test eax,eax; jnz render_digits
mov ecx,esp; push edi; call 0x4805de
mov eax,esp; push eax; mov ecx,esi; call 0x704ea1
mov ecx,dword ptr [esp]; sub ecx,16; call 0x481375
mov dword ptr [{S+0x88}],0
render_done: add esp,36; popad; popfd; ret
''',0x200)
    m.replace(0x6b00,f'''
push eax
mov eax,dword ptr [{S+0x80}]; test eax,eax; jz active_done
dec eax; call {S+0x6900}
active_done: pop eax; ret
''',0x100)
    # Destroy only native handles, not the saved income targets.
    m.replace(0x6c00,f'''
pushfd; pushad
mov edi,{S+0x1c000}; xor eax,eax; mov ecx,4; cld; rep stosd
popad; popfd; ret
''',0x100)
    m.replace(0x4000,f'''
pushfd; pushad
mov ecx,dword ptr [{S+0x50}]; test ecx,ecx; jz gold_done
cmp dword ptr [ecx+0x6c],0; je gold_done
xor eax,eax; call {S+0x6900}
mov dword ptr [{S+0x7c}],0
gold_done: popad; popfd; ret
''',0x200)
    # Ensure the active editbox is at the top of the game's input stack.
    m.replace(0x4200,f'''
xor eax,eax
mov ecx,dword ptr [0xa53fc0]; test ecx,ecx; jz focus_done
mov edx,dword ptr [ecx+0xb4]; test edx,edx; jz focus_done
mov ecx,dword ptr [ecx+0x34]; test ecx,ecx; jz focus_done
cmp ecx,dword ptr [edx]; jne focus_done
mov edx,dword ptr [ecx+4]; jmp {S+0x6680}
focus_done: ret
''',0x100)
    m.replace(0x4300,f'''
pushfd; pushad
call {S+0x4200}; test eax,eax; jz not_editing
cmp eax,dword ptr [{S+0x80}]; je still_editing
call {S+0x6b00}
mov dword ptr [{S+0x80}],eax; mov dword ptr [{S+0x84}],0
still_editing: mov dword ptr [{S+0x58}],0; jmp input_done
not_editing:
cmp dword ptr [{S+0x80}],0; je input_ready
call {S+0x6b00}
mov dword ptr [{S+0x80}],0; mov dword ptr [{S+0x84}],0
input_ready:
cmp dword ptr [{S+0x7c}],0; jne input_done
mov dword ptr [{S+0x58}],1
input_done: popad; popfd; ret
''',0x100)
    m.replace(0x4400,f'''
push esi; push ebx
mov eax,dword ptr [{S+0x80}]; test eax,eax; jz parse_bad
dec eax; mov ebx,4; test eax,eax; jnz parse_widget
mov ebx,7
parse_widget: call {S+0x6600}; test ecx,ecx; jz parse_bad
mov ecx,dword ptr [ecx+0x6c]; test ecx,ecx; jz parse_bad
call 0x6ffc02; test eax,eax; jz parse_bad
mov esi,dword ptr [eax]; test esi,esi; jz parse_bad
xor eax,eax; xor edx,edx
parse_digit: movzx ecx,word ptr [esi]; test ecx,ecx; jz parse_end
sub ecx,48; cmp ecx,9; ja parse_bad
inc edx; cmp edx,ebx; ja parse_bad
imul eax,eax,10; add eax,ecx; add esi,2; jmp parse_digit
parse_end: test edx,edx; jz parse_bad
mov edx,1; pop ebx; pop esi; ret
parse_bad: xor edx,edx; pop ebx; pop esi; ret
''',0x100)
    m.replace(0x4800,f'''
push ebp; mov ebp,esp; push ebx; push esi; push edi
mov edi,ecx; mov esi,dword ptr [ebp+8]
call {S+0x4200}; test eax,eax; jz key_original
push eax; dec eax; call {S+0x6600}
mov ecx,dword ptr [ecx+0x6c]; cmp ecx,dword ptr [edi+4]
pop eax; jne key_original
mov dword ptr [{S+0x80}],eax; mov dword ptr [{S+0x58}],0
movzx ebx,word ptr [esi+8]
cmp ebx,13; je key_owned
cmp ebx,27; jne key_original
key_owned:
test byte ptr [esi+4],1; jz key_release
cmp dword ptr [{S+0x84}],0; jne key_consume
cmp ebx,27; je key_cancel
call {S+0x4400}; test edx,edx; jz key_invalid
mov edx,dword ptr [{S+0x80}]; dec edx; call {S+0x6800}
key_cancel:
call {S+0x6b00}; mov dword ptr [{S+0x84}],ebx; jmp key_consume
key_invalid: mov dword ptr [{S+0x88}],1; jmp key_consume
key_release:
test byte ptr [esi+4],2; jz key_consume
cmp ebx,dword ptr [{S+0x84}]; jne key_consume
mov dword ptr [{S+0x80}],0; mov dword ptr [{S+0x84}],0
mov ecx,edi; call 0x70ade6
mov ecx,dword ptr [0xa53fc0]; push 0; call 0x71c8c0
mov dword ptr [{S+0x58}],1
key_consume: mov eax,1; jmp key_done
key_original: push esi; mov ecx,edi; call 0x70b372
key_done: pop edi; pop esi; pop ebx; mov esp,ebp; pop ebp; ret 4
''',0x300)
    m.replace(0x4b00,f'''
pushfd; pushad
mov edx,dword ptr [ecx+4]; call {S+0x6680}
test eax,eax; jz blur_done
dec eax; call {S+0x6900}
mov dword ptr [{S+0x80}],0; mov dword ptr [{S+0x84}],0
mov dword ptr [{S+0x58}],1
blur_done: popad; popfd; jmp 0x70b356
''',0x100)
    # Floor step buttons are hidden in the compact layout, but keep callbacks
    # correct if the engine invokes them. Unrelated numeric controls unchanged.
    for offset,sign,original in [(0x4c00,1,0x704d12),(0x4d00,-1,0x704da5)]:
        m.replace(offset,f'''
pushfd; pushad
mov esi,ecx; xor ebx,ebx
step_find: mov eax,ebx; call {S+0x6600}; cmp ecx,esi; je step_owned
inc ebx; cmp ebx,5; jb step_find
popad; popfd; jmp {original}
step_owned:
mov eax,ebx; call {S+0x6700}
mov ecx,9999; mov edx,{sign}
test ebx,ebx; jnz step_calc
mov ecx,dword ptr [{S+0xa4}]; mov edx,{sign*100}
step_calc: add eax,edx; cmp eax,0; jge step_max; xor eax,eax
step_max: cmp eax,ecx; jle step_set; mov eax,ecx
step_set: mov edx,ebx; call {S+0x6800}
mov eax,ebx; call {S+0x6900}
mov dword ptr [{S+0x80}],0; mov dword ptr [{S+0x84}],0
popad; popfd; ret 4
''',0x100)
