import argparse,sys,struct,json,subprocess,hashlib,re,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LEGACY=Path('G:/CodexData/projects/Codex/2026-08-11/kohan-ii-d-steamlibrary-steamapps-common/work')
TCC=ROOT.parents[1]/'work/crash-20260914-continue/tools/tinycc/tcc/tcc.exe'
sys.path[:0]=[str(LEGACY/'pydeps_readable'),str(LEGACY/'lobby_colors_1372/deps_r15')]
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
raw=(LEGACY/'k2_runtime_1372_20260904.bin').read_bytes()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 ks=Ks(KS_ARCH_X86,KS_MODE_32);md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
 blocks=[('orders_dispatch','pushfd;cmp dword ptr [ecx+0x3c],2;jne native;popfd;jmp 0x20000100;native:popfd;jmp 0x20000200'),
 ('update_dispatch','pushfd;cmp dword ptr [ecx+0x3c],2;jne native;popfd;jmp 0x20000700;native:popfd;jmp 0x20000800'),
 ('filter_dispatch','''pushfd;cmp dword ptr [esp+36],2;jne native;push ebp;mov ebp,esp;pushad;sub esp,528;lea eax,[esp+15];and eax,0xfffffff0;fxsave [eax];fninit;fldcw word ptr [eax];push eax;push dword ptr [ebp+20];push dword ptr [ebp+16];call 0x20000300;add esp,8;mov [ebp-4],eax;pop eax;fxrstor [eax];add esp,528;popad;test eax,eax;pop ebp;jnz native;popfd;fldz;ret 36;native:popfd;jmp 0x20000400'''),
 ('filter_original','mov eax,0x20000500;jmp 0x20000600')]
 values={0x20000100:'(U)air_orders',0x20000200:'base+0x1d3d29',0x20000300:'(U)allowed',0x20000400:'(U)filter_original',0x20000500:'base+'+hex(struct.unpack_from('<I',raw,0x5cee7)[0]-0x460000),0x20000600:'base+0x5ceeb',0x20000700:'(U)air_update',0x20000800:'base+0x1d4094'}
 header='/* Generated x86 tail dispatch; build.py. */\n'
 for name,asm in blocks:
  code=bytes(ks.asm(asm,0x10000000)[0]);header+=f'static unsigned char*{name};\nstatic const unsigned char {name}_code[]={{'+','.join(hex(x) for x in code)+'};\n'
 header+='static int init_dispatch(void){unsigned char jump[5];unsigned i;DWORD old;\n'
 for name,_ in blocks:header+=f'{name}=VirtualAlloc(0,4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);if(!{name})return 0;memcpy({name},{name}_code,sizeof({name}_code));\n'
 for name,asm in blocks:
  code=bytes(ks.asm(asm,0x10000000)[0])
  for ins in md.disasm(code,0x10000000):
   for op in ins.operands:
    if op.type==2 and op.imm in values:
     relative=ins.mnemonic in ('jmp','call');offset=ins.address-0x10000000+ins.imm_offset
     header+=f'*(U*)({name}+{offset})={values[op.imm]}' +(f'-(U)({name}+{offset+4})' if relative else '')+';\n'
 for name,_ in blocks:header+=f'if(!VirtualProtect({name},4096,PAGE_EXECUTE_READ,&old))return 0;FlushInstructionCache(GetCurrentProcess(),{name},sizeof({name}_code));\n'
 expected=raw[0x5cee6:0x5ceeb];assert expected[0]==0xb8
 header+='jump[0]=0xe9;*(U*)(jump+1)=(U)filter_dispatch-(base+0x5ceeb);\n'
 header+=' {unsigned char expected[5];expected[0]=0xb8;*(U*)(expected+1)=base+'+hex(struct.unpack_from('<I',raw,0x5cee7)[0]-0x460000)+';return prepare(0x5cee6,expected,jump,5);}}\n'
 (out/'dispatch.h').write_text(header);shutil.copy2(HERE/'runtime.c',out/'runtime.c')
 shutil.copy2(HERE/'qa.h',out/'qa.h')
 shutil.copy2(HERE/'day_clock.h',out/'day_clock.h');shutil.copy2(HERE/'paws_day_clock.tgi',out/'paws_day_clock.tgi')
 for macro,name in [([], 'PawUiScoutTest.dll'),(['-DPAW_QA'],'PawUiScoutQA.dll')]:
  subprocess.run([str(TCC),'-shared','-Wall','-Werror']+macro+[str(out/'runtime.c'),'-o',str(out/name),'-lkernel32','-luser32'],check=True)
 baseline=json.loads(Path('C:/PawsNoHotJoinQA-20261107/helpers-r2/build-report.json').read_text());name='k2_paws_lobby_colors_mp_1372_experimental.exe';row=baseline[name]
 shutil.copy2('C:/PawsNoHotJoinQA-20261107/helpers-r2/paws_player_colors.ini',out/'paws_player_colors.ini');(out/'paws_patch_versions.ini').write_text('[Versions]\nArcaneWars=0.82.1.8\nPawPatch=0.5.0-ui-test.5\n')
 sources=out/'source';sources.mkdir();args=[]
 # Rebuild a single private helper from the exact no-hotjoin baseline, changing only the presentation block.
 hud=out/'hud-builder.py';s=(ROOT/'game/widescreen-ui/build_hud_native.py').read_text();s=s.replace(' mov edx,[eax+4]',' lea edx,[{image+0x491788}]\n cmp [eax],edx\n je editor\n mov edx,[eax+4]');hud.write_text(s)
 presentation=None
 for arg in row['args']:
  if arg.startswith('/out:'):arg='/out:'+str(out/name)
  elif arg.lower().endswith('.cs'):
   src=Path(arg);assert sha(src).upper()==row['sources'][str(src)].upper(),src;dst=sources/src.name;shutil.copy2(src,dst);arg=str(dst)
   if src.name.endswith('LargeMapsIdentity.cs'):dst.write_text(dst.read_text().replace('0.5.0-beta.4','0.5.0-ui-test.5'))
   if src.name.endswith('ReleaseStartup.cs'):
    s=dst.read_text();old='Process[] games = Process.GetProcessesByName("k2");';assert s.count(old)==1;s=s.replace(old,'Process[] games = Process.GetProcessesByName("k2").Where(p => String.Equals(p.MainModule.FileName, expectedPath, StringComparison.OrdinalIgnoreCase)).ToArray();');dst.write_text(s)
   if src.name.endswith(('PawAssistantParties.cs','PawAssistantRuntime.cs','.generated.cs')):
    s=dst.read_text();s=s.replace('Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments)','Environment.GetEnvironmentVariable("PAWS_TEST_DOCUMENTS")').replace('Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData)','Environment.GetEnvironmentVariable("PAWS_TEST_APPDATA")')
    if src.name.endswith('.generated.cs'):
     old='Process[] running = Process.GetProcessesByName("k2");';assert s.count(old)==1;s=s.replace(old,'Process[] running = Process.GetProcessesByName("k2").Where(p => String.Equals(p.MainModule.FileName, gamePath, StringComparison.OrdinalIgnoreCase)).ToArray();')
     old='ProcessStartInfo start = new ProcessStartInfo(gamePath)';assert s.count(old)==1;s=s.replace(old,'if (!File.Exists(Path.Combine(gameDirectory, "ui-scout-test.marker")) || String.IsNullOrEmpty(Environment.GetEnvironmentVariable("PAWS_TEST_DOCUMENTS"))) throw new IOException("Use Start-Test.cmd in the private UI test folder");\n                ProcessStartInfo start = new ProcessStartInfo(gamePath, "+Exec Mods/rig.txt")')
     old='                    UseShellExecute = true,';assert s.count(old)==1;s=s.replace(old,'                    UseShellExecute = false,')
     old='            MonitorRuntime(game, process, counters, syncSignal, logPath);';assert s.count(old)==1;s=s.replace(old,'            File.WriteAllText(Path.Combine(gameDirectory, "Mods/ui-scout-helper-ready.marker"), "READY");\n'+old)
    dst.write_text(s)
   if src.name.endswith('GamePresentation1372.cs'):presentation=dst
  args.append(arg)
 assert presentation
 subprocess.run([sys.executable,str(hud),'--legacy',str(LEGACY),'--out',str(out/'hud'),'--update-source',str(presentation)],check=True)
 subprocess.run(args,check=True)
 (out/'build.json').write_text(json.dumps(dict(helper=name,sha256=sha(out/name),dllSha256=sha(out/'PawUiScoutTest.dll'),args=args,baselineHelperSha256=row['sha256']),indent=2))
 print('UI_SCOUT_BUILD_READY',out)
if __name__=='__main__':main()
