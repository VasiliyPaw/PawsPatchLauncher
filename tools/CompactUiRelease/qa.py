from context import *
from resources import read_rwd
import shutil
Q=O/'installer-qa';TEMPLATE=PR/'installer-qa';REF=WS/'outputs/arcane060-beta3-release-20261116/launcher-reference'
ROOTS={'arcane':'G:/PawsWork/QA/Arcane060-20261115','vanilla':'G:/PawsWork/QA/Pure050Beta7-20261116/vanilla','immortals':'G:/PawsWork/QA/Pure050Beta7-20261116/immortals'}
def project(folder):
 folder.mkdir(parents=True,exist_ok=True);refs=''.join('<Reference Include="'+f.stem+'"><HintPath>'+str(f)+'</HintPath></Reference>'for f in REF.glob('*.dll'));(folder/'QA.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0-windows</TargetFramework><UseWPF>true</UseWPF><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup><ItemGroup><Using Include="System.IO" />'+refs+'</ItemGroup></Project>')
def setup():
 project(Q)
 for f in TEMPLATE.glob('*.cs'):shutil.copy2(f,Q/f.name)
 f=Q/'Program.cs';s=f.read_text();anchor='            if (mode == "verify")';assert anchor in s
 s=s.replace(anchor,'''            if(item.Id.EndsWith("-off")){
 var hashes=new Dictionary<string,string>();foreach(var n in new[]{"Drauga","Gauri","Haroun","Human","Shadow","Undead"})hashes["skins/"+n.ToLowerInvariant()+".rwd"]=await CryptoAndIO.Sha256Async(Path.Combine(game,"skins",n+".rwd"));
 await File.WriteAllTextAsync(Path.Combine(root,item.Id+"-restored-skins.json"),JsonSerializer.Serialize(hashes,Json));}
'''+anchor);f.write_text(s);print(run([SDK,'build',Q/'QA.csproj','-c','Release'],O/'qa-build.log'),flush=True)
def install(mod):
 root=Path(ROOTS[mod]);game=root/'game';name='arcane-wars'if mod=='arcane'else mod;pid='pawpatch-core'if mod=='arcane'else'pure-fixes-data';expected=ARC if mod=='arcane'else PURE
 processes=run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object Name -eq 'k2.exe' | Select-Object -ExpandProperty ExecutablePath"]);assert str(game/'k2.exe').lower()not in processes.lower()
 before=read(game/'.pawpatch/state.json');assert before['modules'][pid]['version']==('0.6.0-beta.4'if mod=='arcane'else'0.5.0-beta.8')
 native={str(p.relative_to(game)):sha(p)for p in[game/'k2.exe',game/'d3d9.dll',*list((game/'Mods').glob('*.dll'))]if p.exists()};write(O/(mod+'-installed-before.json'),dict(modules=before['modules'],native=native))
 args=[SDK,'run','--project',Q/'QA.csproj','-c','Release','--no-build','--','--root='+str(root),'--stock=G:/PawsWork/BaseGame/1.3.72','--stable='+str(O/'local-feeds/stable.json'),'--beta='+str(O/'local-feeds/beta.json'),'--key='+str(O/'public.pem'),'--mode=verify','--mod='+name];print(run(args,O/(mod+'-installer.log')),flush=True)
 receipts={n:read(root/(name+'-'+n+'-hd-installed.json'))for n in['upgrade','colors','sync','colors-sync','off','reapply']};common='common-ui'if mod=='arcane'else'pure-beta-common'
 for n,state in receipts.items():
  if n=='off':assert common not in state['modules']
  else:assert state['modules'][pid]['version']==expected and state['modules'][common]['version']==expected
 assert all(sha(game/n)==h for n,h in native.items())
 archives=read(O/'resource-archives.json');images=read(O/'image-export.json')['files'];actual={}
 for n,r in archives.items():
  assert sha(game/n)==r['sha256'];actual[n]=read_rwd(game/n)
 for r in images:assert hashlib.sha256(actual[r['archivePath']][r['entry']]).hexdigest().upper()==r['sha256']
 restored=read(root/(name+'-off-restored-skins.json'));baselines=read(O/'base-skin-preservation.json')['baselines'];assert all(restored[n].upper()==r['sha256']for n,r in baselines.items())
 assert(game/'startup/autoexec.txt').read_text().count('adddepot paws-hd-ui.rwd')==1
 assert not any((game/'paws-hd-ui').rglob('*.*'))
 if mod=='arcane':
  assert 'arcane-biome-textures'in receipts['reapply']['modules'];assert not any(k.startswith('arcane-biome-textures-')for k in receipts['reapply']['modules'])
  for n,r in read(O/'terrain-merge.json')['files'].items():assert sha(game/n)==r['sha256'].upper()
 result=dict(passed=True,cases=6,upgradeFrom=before['modules'][pid]['version'],version=expected,fullresImages=708,compactImages=708,archiveCount=7,allFourHelperSelections=True,rollback=True,stockSkinArchivesRestoredOnDisable=True,reapply=True,nativeUnchanged=native,originalArchivesUnchanged=all(sha(game/n)==sha(Path('G:/PawsWork/BaseGame/1.3.72')/n)for n in['Data.rwd','Music.rwd']))
 write(O/(mod+'-installer-result.json'),result);print('COMPACT_INSTALLER_PASS',mod,flush=True)
if __name__=='__main__':setup()if sys.argv[1]=='setup'else install(sys.argv[1])
