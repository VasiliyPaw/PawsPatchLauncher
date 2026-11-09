"""Offline native/compiled checks and real installer checks; no game launches."""
import argparse,shutil,sys
from context import *
FROZEN=REPO/'outputs/pure-041-050-20261109/beta-install-r7/launcher'

def project(folder,source):
 folder.mkdir(parents=True,exist_ok=False);snapshot=folder/'launcher';snapshot.mkdir()
 for p in FROZEN.glob('*.dll'):shutil.copy2(p,snapshot/p.name)
 refs=''.join('<Reference Include="'+p.stem+'"><HintPath>'+str(p)+'</HintPath></Reference>'for p in snapshot.glob('*.dll'))
 (folder/'QA.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0-windows</TargetFramework><UseWPF>true</UseWPF><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup><ItemGroup><Using Include="System.IO" />'+refs+'</ItemGroup></Project>')
 (folder/'Program.cs').write_text(source)

def native():
 folder=OUT/'native-checks';folder.mkdir(exist_ok=True)
 compiler=Path('C:/Windows/Microsoft.NET/Framework/v4.0.30319/csc.exe');exe=folder/'OfflineColorChecks.exe'
 run([compiler,'/nologo','/target:exe','/platform:x86','/out:'+str(exe),REPO/'tools/LobbyColorsRelease/OfflineColorChecks.cs'])
 print(run([exe,OUT/'arcane-helpers',OUT/'pure-helpers',sha(REPO/'game/beta7/PawLobbyColorsPayload.bin')],folder/'compiled-color-checks.log'),flush=True)
 exe=folder/'EmbeddedRuntimeChecks.exe'
 run([compiler,'/nologo','/target:exe','/platform:x86','/out:'+str(exe),REPO/'tools/MinimapCrashRelease/EmbeddedRuntimeChecks.cs'])
 print(run([exe,OUT/'arcane-helpers',OUT/'pure-helpers',read(OUT/'arcane-native/build.json')['sha256'],read(OUT/'pure-native/build.json')['sha256']],folder/'embedded-runtime-checks.log'),flush=True)
 for kind in ['arcane','pure']:
  result=read(OUT/(kind+'-native')/'return-contract.json');assert result['passed']and result['checks']==468 and result['cases']==144 and not result['expectBug']
  assert read(OUT/(kind+'-native')/'qa/native-test.json')['passed']
 write(folder/'result.json',dict(passed=True,helpers=12,compiledNativeCases=288,compiledNativeAssertions=936,colorPayloadUnchanged=True,embeddedRuntimeVerified=True,gamesLaunched=False))

def catalog():
 source=(REPO/'outputs/arcane-051-release-20261109/stable/catalog-qa/Program.cs').read_text()
 source=source.replace('var after=channel=="stable"?Read(Path.Combine(root,"signed/feed/v3/stable.json")):before;','var after=channel=="beta"?Read(Path.Combine(root,"signed/feed/v3/beta.json")):before;')
 source=source.replace('channel=="stable"&&mod==GameMod.ArcaneWars&&patch','channel=="beta"&&patch')
 source=source.replace('selected.Single(p=>p.Id=="pawpatch-core").Version=="0.5.0"','selected.Single(p=>p.Id==(mod==GameMod.ArcaneWars?"pawpatch-core":"pure-fixes-data")).Version==(mod==GameMod.ArcaneWars?"0.5.1-beta.3":"0.5.0-beta.4")')
 source=source.replace('var helperNames=new HashSet<string>', 'var helperNames=new HashSet<string>')
 source=source.replace('var newFiles=new Dictionary', 'foreach(var p in JsonDocument.Parse(File.ReadAllText(Path.Combine(args[4],"build-report.json"))).RootElement.EnumerateObject())helperNames.Add(p.Name);\nvar newFiles=new Dictionary')
 source=source.replace('foreach(var file in Directory.EnumerateFiles(Path.Combine(root,"assets"),"*.zip"))','foreach(var file in Directory.EnumerateFiles(root,"*.zip",SearchOption.AllDirectories).Where(p=>p.Contains("assets")))')
 source=source.replace('ARCANE_STABLE_ALL_SWITCHES_PASS','THREE_BETAS_ALL_SWITCHES_PASS')
 # Source reads before/feed/v3; preparation assets is a set of changed package IDs.
 write(OUT/'preparation.json',dict(assets=[dict(id=p['id'])for p in read(OUT/'packages.json')]))
 folder=OUT/'catalog-qa';project(folder,source)
 log=OUT/'catalog-checks.log';print(run([SDK,'run','--project',folder/'QA.csproj','-c','Release','--',OUT,REPO,OUT/'arcane-helpers',OUT,OUT/'pure-helpers'],log)[-1600:],flush=True)
 assert 'THREE_BETAS_ALL_SWITCHES_PASS'in log.read_text()

def seed_cache(fixture):
 target=fixture/'cache/downloads';target.mkdir(parents=True,exist_ok=True)
 for folder in [Path('G:/PawPure050OptQA-20261109/installer/cache/downloads'),Path('C:/PawsArcane051ReleaseQA-20261109/beta-install/cache/downloads')]:
  for p in folder.rglob('*.zip'):
   dest=target/p.relative_to(folder);dest.parent.mkdir(parents=True,exist_ok=True)
   if not dest.exists():shutil.copy2(p,dest)

def installers():
 # Adapt the accepted 20-case Pure installer driver, keeping its real installer
 # and native preflight. It never launches a game or modifies the stock source.
 source=(REPO/'tools/Pure050Release/install_beta.py').read_text()
 source=source.replace("out=OUT/'beta-install-r7'","out=OUT/'pure-installer-qa'")
 source=source.replace("bin=REPO/'src/PawsPatchLauncher/bin/Release/net8.0-windows'","bin=REPO/'outputs/pure-041-050-20261109/beta-install-r7/launcher'")
 source=source.replace("OUT/'beta-stage-r4/packages.json'","OUT/'packages.json'")
 old="[OUT/'accepted-assets',OUT/'stable-stage/assets',OUT/'beta-stage-r4/assets',OUT/'optional-data-r1/inputs',WS/'outputs/release-pure-040-20261013/publication-final/packages']"
 new="[REPO/'outputs/pure-041-050-20261109/accepted-assets',REPO/'outputs/pure-041-050-20261109/stable-stage/assets',REPO/'outputs/pure-041-050-20261109/beta-stage-r4/assets',REPO/'outputs/pure-041-050-20261109/optional-data-r1/inputs',OUT/'pure/assets',OUT/'arcane/assets',REPO.parents[1]/'outputs/release-pure-040-20261013/publication-final/packages']"
 assert old in source;source=source.replace(old,new)
 source=source.replace("Path('G:/PawPure050QA-20261109/installer')","Path('F:/PawsMinimapCrashPublish-20261109/pure-installer-fixture')")
 source=source.replace("feed=verify(read(REPO/('feed/v3/'+channel+'.json')),key())","feed=verify(read(OUT/('local-feeds/'+channel+'.json')),key())")
 source=source.replace('from context import *','from context import *\nWS=REPO.parents[1]')
 seed_cache(OUT/'pure-installer-fixture')
 (OUT/'pure-installer-driver.py').write_text(source)
 exec(compile(source,str(OUT/'pure-installer-driver.py'),'exec'),dict(__name__='__main__',__file__=str(OUT/'pure-installer-driver.py')))
 source=(REPO/'outputs/arcane-051-release-20261109/stable/installation-qa/Program.cs').read_text()
 source=source.replace('        EnsureNoGame();','        // Private no-launch installer verification.')
 source=source.replace('"stable-helper-"','"beta-helper-"').replace('"stable-locale-"','"beta-locale-"').replace('Channel="stable"','Channel="beta"')
 folder=OUT/'arcane-installer-qa';project(folder,source)
 for p in (REPO/'tools/PatchMatrixRunner').glob('*.cs'):
  if p.name!='Program.cs':shutil.copy2(p,folder/p.name)
 fixture=OUT/'arcane-installer-fixture';seed_cache(fixture)
 args=[SDK,'run','--project',folder/'QA.csproj','-c','Release','--','--root='+str(fixture),'--stock=D:/SteamLibrary/steamapps/common/Kohan II','--stable='+str(OUT/'local-feeds/stable.json'),'--beta='+str(OUT/'local-feeds/beta.json'),'--key='+str(OUT/'public.pem'),'--mode=verify','--channel=beta','--mod=arcane-wars']
 log=OUT/'arcane-installer-checks.log';print(run(args,log)[-2000:],flush=True)
 assert log.read_text().count('INSTALL_PASS ')==12
 write(OUT/'installer-result.json',dict(passed=True,pureCases=20,arcaneCases=12,gamesLaunched=False))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['native','catalog','installers']);a=p.parse_args();globals()[a.action]()
