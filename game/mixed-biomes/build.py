"""Build guarded native hooks and one isolated helper. No publication commands."""
from pathlib import Path
import sys,json,struct,subprocess,hashlib,re,base64
HERE=Path(__file__).resolve().parent;WS=HERE.parents[3];OUT=WS/'outputs/mixed-biomes-r2-20261106';NATIVE=OUT/'native';REPO=HERE.parents[1]
LEG=Path('G:/CodexData/projects/Codex/2026-08-11/kohan-ii-d-steamlibrary-steamapps-common/work')
sys.path[:0]=[str(LEG/'pydeps_readable'),str(LEG/'lobby_colors_1372/deps_r15')]
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
from capstone import Cs,CS_ARCH_X86,CS_MODE_32,CS_OP_IMM
import pefile
raw=(LEG/'k2_runtime_1372_20260904.bin').read_bytes();assert hashlib.sha256(raw).hexdigest()=='b865d8206990c4f055c51de857f0b09b88ab5ee3b6ae74ee5232134001aa591c'
IMAGE=0x460000;CAVE=0x10000000;ks=Ks(KS_ARCH_X86,KS_MODE_32);md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
compiler=WS/'work/crash-20260914-continue/tools/tinycc/tcc/tcc.exe'
subprocess.run([str(compiler),'-shared','-nostdlib','-Wall','-Werror','-I'+str(NATIVE),'-Wl,--image-base=0x10000000',str(HERE/'biomes.c'),str(compiler.parent/'lib/libtcc1-32.a'),'-o',str(NATIVE/'biomes.dll')],check=True)
pe=pefile.PE(str(NATIVE/'biomes.dll'));assert not hasattr(pe,'DIRECTORY_ENTRY_IMPORT')
buf=bytearray(pe.get_memory_mapped_image());exports={s.name.decode():s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols}
fix=[(e.rva,0,1) for b in pe.DIRECTORY_ENTRY_BASERELOC for e in b.entries if e.type==3]
wrapper=(len(buf)+4095)&~4095;adapter=wrapper+0x100;tramp=wrapper+0x200;allow=wrapper+0x300;cap=wrapper+0x500;sort=wrapper+0x700
size=wrapper+0x1000;state=size;buf.extend(bytes(size-len(buf)))
def asm(off,s):
 code=bytes(ks.asm(s,CAVE+off)[0]);buf[off:off+len(code)]=code
 for ins in md.disasm(code,CAVE+off):
  at=ins.address-CAVE
  if ins.disp_size==4 and IMAGE<=ins.disp<IMAGE+len(raw):fix.append((at+ins.disp_offset,1,0))
  for op in ins.operands:
   if op.type!=CS_OP_IMM:continue
   if ins.mnemonic in ('call','jmp') and IMAGE<=op.imm<IMAGE+len(raw):fix.append((at+ins.imm_offset,1,-1))
   elif ins.mnemonic in ('push','mov') and IMAGE<=op.imm<IMAGE+len(raw):fix.append((at+ins.imm_offset,1,0))
   elif CAVE<=op.imm<CAVE+size+4096 and ins.mnemonic in ('push','mov'):fix.append((at+ins.imm_offset,0,1))
 return len(code)
asm(adapter,'push ebp;mov ebp,esp;push ebx;push esi;mov ebx,[ebp+16];mov esi,[ebp+20];test ebx,ebx;jz native;args:dec ebx;push dword ptr[esi+ebx*4];test ebx,ebx;jnz args;native:mov ecx,[ebp+12];call dword ptr[ebp+8];pop esi;pop ebx;leave;ret;')
asm(wrapper,f'pushfd;pushad;mov ebp,esp;sub esp,528;and esp,0xfffffff0;fxsave [esp];push ecx;push {CAVE+state};call {CAVE+exports["generate"]};add esp,8;mov [ebp+28],eax;fxrstor [esp];mov esp,ebp;popad;popfd;ret;')
asm(tramp,f'mov eax,{IMAGE+0x43ff0d};jmp {IMAGE+0x2566be};')
asm(allow,f'''push ebp;mov ebp,esp;push ebx;push esi;push edi;
 push dword ptr[ebp+32];push dword ptr[ebp+28];push dword ptr[ebp+24];push dword ptr[ebp+20];push dword ptr[ebp+16];push dword ptr[ebp+12];push dword ptr[ebp+8];
 call {CAVE+tramp};test al,al;jz done;
 pushfd;pushad;mov esi,esp;sub esp,528;and esp,0xfffffff0;fxsave [esp];push dword ptr[ebp+20];push dword ptr[ebp+12];push {CAVE+state};call {CAVE+exports["allowed"]};add esp,12;
 test eax,eax;jnz keep;mov dword ptr[esi+28],0;keep:fxrstor [esp];mov esp,esi;popad;popfd;
 done:pop edi;pop esi;pop ebx;leave;ret 28;''')
# Return a pointer to the effective limit. Ordinary maps/mod values retain the
# original pointer. The three callers share this adapter and preserve flags.
check_id=''
ident=('unit_limit_provided'+'\0').encode('utf-16le')
for off in range(0,len(ident),4):
 part=ident[off:off+4];check_id+=f'cmp {"dword" if len(part)==4 else "word"} ptr[edx+{off}],{int.from_bytes(part,"little")};jne done;'
asm(cap,f'''pushfd;push ecx;push edx;mov eax,[eax+0x1b4];cmp dword ptr[eax],20;jne done;
 test edx,edx;jz done;mov edx,[edx+8];test edx,edx;jz done;{check_id}
 mov ecx,[{IMAGE+0x5f3fb8}];test ecx,ecx;jz done;mov ecx,[ecx+0x30];test ecx,ecx;jz done;
 cmp dword ptr[ecx+0xc],0x44960000;jb done;cmp dword ptr[ecx+0xc],0x7f800000;jae done;
 cmp dword ptr[ecx+0x10],0x44960000;jb done;cmp dword ptr[ecx+0x10],0x7f800000;jae done;
 mov eax,{CAVE+cap+0x100};done:pop edx;pop ecx;popfd;ret;''')
struct.pack_into('<I',buf,cap+0x100,25)
for off,setup in [(wrapper+0x800,f'push ecx;mov ecx,[{IMAGE+0x5f3fb4}];mov ecx,[ecx+0x34];mov edx,[ecx+edx*4];call {CAVE+cap};pop ecx;'),(wrapper+0x900,f'mov edx,edi;call {CAVE+cap};'),(wrapper+0xa00,f'mov edx,[ebp-0x20];call {CAVE+cap};')]:asm(off,'push edx;'+setup+'pop edx;ret;')
asm(sort,f'''pushfd;pushad;mov ebp,esp;sub esp,528;and esp,0xfffffff0;fxsave [esp];push ecx;push {CAVE+state};call {CAVE+exports['sort_main']};add esp,8;fxrstor [esp];mov esp,ebp;popad;popfd;jmp {IMAGE+0x2a51b1};''')
hooks=[dict(site=0x25697a,entry=wrapper,n=5,op=0xe8),dict(site=0x2566b9,entry=allow,n=5,op=0xe9)]
for site,entry in zip((0x235c4c,0x5c138,0xbf32d),(wrapper+0x800,wrapper+0x900,wrapper+0xa00)):hooks.append(dict(site=site,entry=entry,n=6,op=0xe8))
hooks.append(dict(site=0x1251a8,entry=sort,n=5,op=0xe8))
assert raw[0x25697a:0x25697f]==bytes.fromhex('e89a050000')
assert raw[0x2566b9:0x2566be]==b'\xb8'+struct.pack('<I',IMAGE+0x43ff0d)
assert raw[0x1251a8:0x1251ad]==bytes.fromhex('e804001800')
for h in hooks:
 h['before']=raw[h['site']:h['site']+h['n']].hex()
 if h['site'] in (0x235c4c,0x5c138,0xbf32d):assert h['before']=='8b80b4010000'
meta=dict(stateBytes=6295552,size=size,state=state,adapter=adapter,capCore=cap,exports=exports,fixups=fix,hooks=hooks)
(NATIVE/'payload.bin').write_bytes(buf);(NATIVE/'payload.json').write_text(json.dumps(meta,indent=2))
cs='''using System;using System.Collections.Generic;
internal static class MixedBiomesTestPatch {
 internal static void Install(IMemory m,uint image,Action<string> log) {
 uint cave=0;var done=new List<int>();bool safe=true;
 uint[] sites={SITES};int[] sizes={SIZES};uint[] entries={ENTRIES};byte[] ops={OPS};
 byte[][] originals={ORIGINALS};
 for(int i=0;i<sites.Length;i++){if(i==1)Buffer.BlockCopy(BitConverter.GetBytes(image+0x43ff0d),0,originals[i],1,4);TerrainPatch.Expect(m,image+sites[i],originals[i]);}
 try {cave=m.Allocate(SIZE+6295552);byte[] b=Convert.FromBase64String("PAYLOAD");
 FIXUPS
 m.Write(cave,b);TerrainPatch.Expect(m,cave,b);m.MakeExecutable(cave,SIZE);m.Flush(cave,b.Length);
 m.Write(cave+STATE,BitConverter.GetBytes(image));m.Write(cave+STATE+4,BitConverter.GetBytes(cave+ADAPTER));
 for(int i=0;i<sites.Length;i++){byte[] j=new byte[sizes[i]];for(int k=0;k<j.Length;k++)j[k]=0x90;j[0]=ops[i];Buffer.BlockCopy(BitConverter.GetBytes(unchecked(cave+entries[i]-image-sites[i]-5)),0,j,1,4);done.Add(i);m.WriteCode(image+sites[i],j);TerrainPatch.Expect(m,image+sites[i],j);m.Flush(image+sites[i],j.Length);}
 log("LOCAL_MIXED_BIOMES r2; state="+(cave+STATE).ToString("X8")+"; companies25 minWidth=1200 minHeight=1200");
 }catch{for(int k=done.Count-1;k>=0;k--){int i=done[k];try{m.WriteCode(image+sites[i],originals[i]);TerrainPatch.Expect(m,image+sites[i],originals[i]);m.Flush(image+sites[i],originals[i].Length);}catch{safe=false;}}if(cave!=0&&safe)m.Free(cave);throw;}
 }
}
'''
values={'SITES':','.join('0x%x'%h['site'] for h in hooks),'SIZES':','.join(str(h['n']) for h in hooks),'ENTRIES':','.join(str(h['entry']) for h in hooks),'OPS':','.join('0x%x'%h['op'] for h in hooks),'ORIGINALS':','.join('TerrainPatch.Hex("'+h['before']+'")' for h in hooks),'PAYLOAD':base64.b64encode(buf).decode(),'SIZE':str(size),'STATE':str(state),'ADAPTER':str(adapter)}
rel=[]
for at,im,cv in fix:
 delta=[]
 if im:delta.append('(image-0x460000)')
 if cv:delta.append('(cave-0x10000000)' if cv==1 else '(0x10000000-cave)')
 rel.append(f'Buffer.BlockCopy(BitConverter.GetBytes(unchecked(BitConverter.ToUInt32(b,{at})+{"+".join(delta)})),0,b,{at},4);')
values['FIXUPS']='\n'.join(rel)
for k in sorted(values,key=len,reverse=True):cs=cs.replace(k,values[k])
(NATIVE/'MixedBiomesTestPatch.cs').write_text(cs)
# Generate centered pause and save menus using the already-verified primary-view
# layout adapter. Only these two additional named widgets are selected.
builder=(HERE.parent/'widescreen-ui/build_hud_native.py').read_text()
builder=builder.replace("('ConnectionStatusDialog','dialog'),", "('ConnectionStatusDialog','dialog'),('GameMenuDialog','editor'),('StagingFileSavedDialog','editor'),('StagingFileLoadSavedDialog','editor'),")
local=OUT/'build_hud_native_local.py';local.write_text(builder)
subprocess.run([sys.executable,str(local),'--legacy',str(LEG),'--out',str(OUT/'hud')],check=True)
# Reuse the full beta.11 feature composition, adding the local hooks only.
manifest=json.loads((WS/'outputs/release-morale-20261106/qa-helper/qa-manifest.json').read_text());args=[];sources=OUT/'source';sources.mkdir(exist_ok=True)
for arg in manifest['args']:
 if arg.startswith('/out:'):arg='/out:'+str(Path('G:/PawMixedBiomesTest-20261106/game/k2_paws_ui_1372.exe'))
 elif arg.lower().endswith('.cs'):
  p=Path(arg);t=p.read_text(encoding='utf-8-sig').replace('0.4.2-beta.11','0.4.2-local-mixed.2')
  if p.name.endswith('GamePresentation1372.cs'):
   start=t.index('    // BEGIN GENERATED HUD LAYOUT');end=t.index('    // END GENERATED HUD LAYOUT',start)+len('    // END GENERATED HUD LAYOUT')
   t=t[:start]+(OUT/'hud/HudLayout.generated.txt').read_text().rstrip()+t[end:]
  if p.name.endswith('ReleaseStartup.cs'):
   anchor='                RandomMapPatch.Verify(memory, address, map);';assert anchor in t;t=t.replace(anchor,anchor+'\n                MixedBiomesTestPatch.Install(memory,address,log);')
   f=Path('G:/PawMixedBiomesTest-20261106/game/data/RandomMap/rmc_temperate03.tgi');t=t.replace('75C096D8095EA5EDB93D27B06E74F8BBFBB0D557A05D311D0CFCCD4889A3D7AB',hashlib.sha256(f.read_bytes()).hexdigest().upper())
  if p.name.endswith('RandomMapBundle.cs'):
   f=Path('G:/PawMixedBiomesTest-20261106/game/data/RandomMap/rmc_temperate03.tgi');old=re.search(r'DataAfter = "([A-F0-9]+)"',t)[1];t=t.replace(old,hashlib.sha256(f.read_bytes()).hexdigest().upper())
  dest=sources/p.name;dest.write_text(t,encoding='utf-8');arg=str(dest)
 args.append(arg)
args.append(str(NATIVE/'MixedBiomesTestPatch.cs'))
subprocess.run(args,check=True,cwd=REPO)
launcher_args=[args[0],'/nologo','/target:winexe','/platform:x86','/optimize+','/r:System.Windows.Forms.dll','/out:'+str(Path('G:/PawMixedBiomesTest-20261106/Смешанные биомы — тест.exe')),str(HERE/'TestLauncher.cs')]
subprocess.run(launcher_args,check=True,cwd=REPO)
statefile=Path('G:/PawMixedBiomesTest-20261106/game/.pawpatch/state.json');installed=json.loads(statefile.read_text(encoding='utf-8-sig'))
for name,module in installed['modules'].items():
 if name in ('pawpatch-core','player-colors','desync-continue','common-ui','powers-shards-original'):module['version']='0.4.2-local-mixed.2'
 for item in module.get('files',[]):
  path=statefile.parents[1]/item['path'].replace('\\','/')
  if path.is_file():item['sha256']=hashlib.sha256(path.read_bytes()).hexdigest().upper()
statefile.write_text(json.dumps(installed),encoding='utf-8')
(OUT/'build.json').write_text(json.dumps(dict(args=args,launcherArgs=launcher_args,native=meta,fixture='G:/PawMixedBiomesTest-20261106'),indent=2))
print('LOCAL_HELPER_BUILT',len(buf),'native bytes',len(fix),'relocations')
