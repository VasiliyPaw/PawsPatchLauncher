from context import *
import shutil,zipfile
Q=O/'installer-qa';REF=AP/'launcher-reference'
ROOTS={'arcane':'G:/PawsWork/QA/Arcane060-20261115','vanilla':'G:/PawsWork/QA/Pure050Beta7-20261116/vanilla','immortals':'G:/PawsWork/QA/Pure050Beta7-20261116/immortals'}
def project(folder):
 folder.mkdir(parents=True,exist_ok=True);refs=''.join('<Reference Include="'+f.stem+'"><HintPath>'+str(f)+'</HintPath></Reference>'for f in REF.glob('*.dll'))
 (folder/'QA.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0-windows</TargetFramework><UseWPF>true</UseWPF><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup><ItemGroup><Using Include="System.IO" />'+refs+'</ItemGroup></Project>')
def setup():
 project(Q)
 s=(AP/'installer-qa/Program.cs').read_text();a=s.index('    private static IEnumerable<Case> Cases()');b=s.index('    private static IEnumerable<Case>',a+10)
 s=s[:a]+'''    private static IEnumerable<Case> Cases(){
 foreach(var mod in new[]{GameMod.ArcaneWars,GameMod.Vanilla,GameMod.Immortals})foreach(var id in new[]{"upgrade","colors","sync","colors-sync","off","reapply"}){
 var ss=new UserSettings{Mod=mod,Channel="beta",PawPatchEnabled=id!="off",VanillaPawPatchEnabled=id!="off",ImmortalsPawPatchEnabled=id!="off",GameTextLanguage="en",RussianLocalization=false,GameVoiceLanguage="en",CustomPlayerColors=id.Contains("colors"),DesyncMode=id.Contains("sync")?"continue":"official"};
 var c=GameMod.PureComponents(ss);c.Colors=id.Contains("colors");c.IgnoreDesync=id.Contains("sync");yield return new Case(mod+"-"+id,ss);}}
''' +s[b:]
 anchor='            if (mode == "verify")';s=s.replace(anchor,'            await File.WriteAllTextAsync(Path.Combine(root,item.Id+"-hd-installed.json"),JsonSerializer.Serialize(installer.LoadState(),Json));\n'+anchor)
 (Q/'Program.cs').write_text(s)
 for f in(AP/'installer-qa').glob('*.cs'):
  if f.name!='Program.cs':shutil.copy2(f,Q/f.name)
 print(run([SDK,'build',Q/'QA.csproj','-c','Release'],O/'qa-build.log'),flush=True)
def install(mod):
 root=Path(ROOTS[mod]);game=root/'game';expected=ARC if mod=='arcane'else PURE;name='arcane-wars'if mod=='arcane'else mod
 processes=run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object Name -eq 'k2.exe' | Select-Object -ExpandProperty ExecutablePath"])
 assert str(game/'k2.exe').lower()not in processes.lower(),'Fixture is active'
 before=read(game/'.pawpatch/state.json');pid='pawpatch-core'if mod=='arcane'else'pure-fixes-data';assert before['modules'][pid]['version']==('0.6.0-beta.3'if mod=='arcane'else'0.5.0-beta.7')
 native={str(p.relative_to(game)):sha(p)for p in [game/'k2.exe',game/'d3d9.dll',*list((game/'Mods').glob('*.dll'))]if p.exists()};write(O/(mod+'-installed-before.json'),dict(modules=before['modules'],native=native))
 args=[SDK,'run','--project',Q/'QA.csproj','-c','Release','--no-build','--','--root='+str(root),'--stock=G:/PawsWork/BaseGame/1.3.72','--stable='+str(O/'local-feeds/stable.json'),'--beta='+str(O/'local-feeds/beta.json'),'--key='+str(O/'public.pem'),'--mode=verify','--mod='+name]
 print(run(args,O/(mod+'-installer.log')),flush=True)
 receipts={n:read(root/(name+'-'+n+'-hd-installed.json'))for n in['upgrade','colors','sync','colors-sync','off','reapply']}
 for n,s in receipts.items():
  common='common-ui'if mod=='arcane'else'pure-beta-common'
  if n=='off':assert common not in s['modules']
  else:assert s['modules'][pid]['version']==expected and s['modules'][common]['version']==expected
 state=read(game/'.pawpatch/state.json');assert all(sha(game/n)==h for n,h in native.items())
 images=read(O/'image-export.json')['files']
 assert len(images)==708
 for r in images:assert sha(game/r['path'])==r['sha256'].upper(),r['path']
 assert (game/'startup/autoexec.txt').read_text().count('adddepot paws-hd-ui/')==1
 old=receipts['off']['modules'];assert not any(k in old for k in ['common-ui','pure-beta-common'])
 write(O/(mod+'-installer-result.json'),dict(passed=True,cases=6,upgradeFrom=before['modules'][pid]['version'],version=expected,fullresImages=708,allFourHelperSelections=True,rollback=True,reapply=True,nativeUnchanged=native,originalArchivesUnchanged=all(sha(game/n)==sha(Path('G:/PawsWork/BaseGame/1.3.72')/n)for n in['Data.rwd','Music.rwd'])))
 print('INSTALLER_HD_PASS',mod,flush=True)
def reset(mod):
 from cryptography.hazmat.primitives import serialization
 feeds=O/'old-feeds'
 for channel in['stable','beta']:
  f=verify(read(O/'before'/f'feed/v3/{channel}.json'),key())
  if channel=='beta':
   for q in f['packages']:
    if not q['urls']:continue
    for base in[AP,PP]:
     p=base/'assets'/Path(q['urls'][0]).name
     if p.exists()and sha(p)==q['sha256']:q['urls']=[str(p)];break
  write(feeds/(channel+'.json'),sign(f,serialization.load_pem_private_key(KEY.read_bytes(),None)))
 root=Path(ROOTS[mod]);name='arcane-wars'if mod=='arcane'else mod
 args=[SDK,'run','--project',Q/'QA.csproj','-c','Release','--no-build','--','--root='+str(root),'--stock=G:/PawsWork/BaseGame/1.3.72','--stable='+str(feeds/'stable.json'),'--beta='+str(feeds/'beta.json'),'--key='+str(O/'public.pem'),'--mode=apply','--mod='+name,'--case='+name+'-upgrade']
 print(run(args,O/(mod+'-reset.log')),flush=True)
if __name__=='__main__':
 if sys.argv[1]=='setup':setup()
 elif sys.argv[1]=='reset':reset(sys.argv[2])
 else:install(sys.argv[1])
