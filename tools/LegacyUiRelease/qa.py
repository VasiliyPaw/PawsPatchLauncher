from context import *
import shutil
Q=O/'installer-qa';REF=O/'launcher-reference';ROOTS={'arcane':'G:/PawsWork/QA/Arcane060-20261115','vanilla':'G:/PawsWork/QA/Pure050Beta7-20261116/vanilla','immortals':'G:/PawsWork/QA/Pure050Beta7-20261116/immortals'}
def project(folder):
 folder.mkdir(parents=True,exist_ok=True);refs=''.join('<Reference Include="'+f.stem+'"><HintPath>'+str(f)+'</HintPath></Reference>'for f in REF.glob('*.dll'));(folder/'QA.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0-windows</TargetFramework><UseWPF>true</UseWPF><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup><ItemGroup><Using Include="System.IO" />'+refs+'</ItemGroup></Project>')
def setup():
 project(Q)
 for f in(PR/'installer-qa').glob('*.cs'):shutil.copy2(f,Q/f.name)
 print(run([SDK,'build',Q/'QA.csproj','-c','Release'],O/'qa-build.log'),flush=True)
def invoke(mod,feeds=O/'local-feeds',case=None):
 root=Path(ROOTS[mod]);name='arcane-wars'if mod=='arcane'else mod;args=[SDK,'run','--project',Q/'QA.csproj','-c','Release','--no-build','--','--root='+str(root),'--stock=G:/PawsWork/BaseGame/1.3.72','--stable='+str(feeds/'stable.json'),'--beta='+str(feeds/'beta.json'),'--key='+str(O/'public.pem'),'--mode=verify','--mod='+name]
 if case:args+=['--case='+name+'-'+case]
 return run(args,O/(mod+('-'+case if case else'')+'-installer.log'))
def verify_game(mod):
 root=Path(ROOTS[mod]);game=root/'game';name='arcane-wars'if mod=='arcane'else mod;common='common-ui'if mod=='arcane'else'pure-beta-common';base=read(O/'graphics-baseline.json')[common]
 for n,r in base['files'].items():assert sha(game/n)==r['sha256'],n
 for n,r in read(O/'stock-skins.json').items():assert sha(game/n)==r['sha256']
 for n in read(O/'hd-removals.json'):assert not(game/n).exists(),n
 assert 'paws-hd-ui'not in(game/'startup/autoexec.txt').read_text()
 if mod=='arcane':
  state=read(game/'.pawpatch/state.json');old=read(O/'terrain-preserved.json');r=state['modules']['arcane-biome-textures'];assert r['version']==old['version']and r['archiveSha256']==old['sha256']
  for n,r in read(PR/'terrain-merge.json')['files'].items():assert sha(game/n)==r['sha256'].upper()
 return len(base['files'])
def install(mod):
 game=Path(ROOTS[mod])/'game';pid='pawpatch-core'if mod=='arcane'else'pure-fixes-data';expected=ARC if mod=='arcane'else PURE;name='arcane-wars'if mod=='arcane'else mod
 processes=run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object Name -eq 'k2.exe' | Select-Object -ExpandProperty ExecutablePath"]);assert str(game/'k2.exe').lower()not in processes.lower()
 before=read(game/'.pawpatch/state.json');assert before['modules'][pid]['version']in [ARC,'0.6.0-beta.5']if mod=='arcane'else before['modules'][pid]['version']in [PURE,'0.5.0-beta.9'];native={str(p.relative_to(game)):sha(p)for p in[game/'k2.exe',game/'d3d9.dll',*list((game/'Mods').glob('*.dll'))]if p.exists()};write(O/(mod+'-installed-before.json'),dict(modules=before['modules'],native=native))
 print(invoke(mod),flush=True);receipts={n:read(Path(ROOTS[mod])/(name+'-'+n+'-hd-installed.json'))for n in['upgrade','colors','sync','colors-sync','off','reapply']}
 for n,state in receipts.items():
  if n=='off':assert('common-ui'if mod=='arcane'else'pure-beta-common')not in state['modules']
  else:assert state['modules'][pid]['version']==expected
 assert all(sha(game/n)==h for n,h in native.items());images=verify_game(mod);restored=read(Path(ROOTS[mod])/(name+'-off-restored-skins.json'));assert all(restored[n.lower()].upper()==r['sha256']for n,r in read(O/'stock-skins.json').items())
 result=dict(passed=True,cases=6,upgradeFrom=before['modules'][pid]['version'],version=expected,legacyImagesVerified=images,hdPathsAbsent=len(read(O/'hd-removals.json')),stockSkinArchivesVerified=6,allFourHelperSelections=True,rollback=True,reapply=True,nativeUnchanged=native,originalArchivesUnchanged=all(sha(game/n)==sha(Path('G:/PawsWork/BaseGame/1.3.72')/n)for n in['Data.rwd','Music.rwd']),nativeGameLaunched=False);write(O/(mod+'-installer-result.json'),result);print('OLD_GRAPHICS_INSTALLER_PASS',mod,flush=True)
if __name__=='__main__':setup()if sys.argv[1]=='setup'else install(sys.argv[1])
