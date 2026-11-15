from context import *
import shutil
root=O/'candidate-repository';folder=root/'checks';folder.mkdir(parents=True,exist_ok=True)
for rel in ['src/PawsPatchLauncher/launcher.config.json']:
 p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(S/rel,p)
for rel in ['feed/v2/stable.json','feed/v2/beta.json','feed/v3/stable.json','feed/v3/beta.json','feed/stable.json','feed/beta.json']:
 p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(O/'signed'/rel,p)
tests=WS/'work/launcher-1014-release/tests/PawsPatchLauncher.Tests/bin/Release/net8.0-windows/PawsPatchLauncher.Tests.dll';assert tests.is_file()
refs=''.join('<Reference Include="'+p.stem+'"><HintPath>'+str(p)+'</HintPath></Reference>'for p in(O/'installer-qa/launcher').glob('*.dll'))
(folder/'QA.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0-windows</TargetFramework><UseWPF>true</UseWPF><ImplicitUsings>enable</ImplicitUsings></PropertyGroup><ItemGroup>'+refs+'</ItemGroup></Project>')
(folder/'Program.cs').write_text('using System.Reflection;var a=Assembly.LoadFrom(args[0]);var t=a.GetType("PublishedBetaCatalogTests",true)!;var m=t.GetMethod("Run",BindingFlags.Static|BindingFlags.NonPublic)!;Console.WriteLine("CANDIDATE_REPOSITORY_CATALOG_PASS "+m.Invoke(null,new object[]{null}));')
print(run([SDK,'run','--project',folder/'QA.csproj','-c','Release','--',tests],O/'repository-catalog-checks.log'),flush=True)
