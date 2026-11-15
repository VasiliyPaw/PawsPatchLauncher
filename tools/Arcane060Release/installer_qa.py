from release_context import *
import shutil
Q=O/'installer-qa';FIX=Path('G:/PawsWork/QA/Arcane060-20261115')
def project():
 Q.mkdir(exist_ok=True);snap=Q/'launcher';snap.mkdir(exist_ok=True)
 launcher=WS/'work/launcher-1014-release/src/PawsPatchLauncher/bin/Release/net8.0-windows'
 for f in launcher.glob('*.dll'):shutil.copy2(f,snap/f.name)
 refs=''.join('<Reference Include="'+f.stem+'"><HintPath>'+str(f)+'</HintPath></Reference>'for f in snap.glob('*.dll'))
 (Q/'QA.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0-windows</TargetFramework><UseWPF>true</UseWPF><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup><ItemGroup><Using Include="System.IO" />'+refs+'</ItemGroup></Project>')
 source=(S/'tools/PatchMatrixRunner/Program.cs').read_text();source='using System.IO;\nusing System.Net.Http;\n'+source
 source=source.replace('        EnsureNoGame();','        // Installation-only fixture; no process control.')
 source=source.replace('if (settings.PureBetaFeatures)','if (settings.PureBetaFeatures && settings.Mod != GameMod.ArcaneWars && !settings.DataOnly)')
 source=source.replace('bytes = await File.ReadAllBytesAsync(CryptoAndIO.SafeChildPath(stock, relative));','bytes = await File.ReadAllBytesAsync(CryptoAndIO.SafeChildPath(File.Exists(CryptoAndIO.SafeChildPath(stock,relative)) ? stock : "G:/PawGraphicsQA-20261113/game", relative));')
 source=source.replace('Directory.CreateDirectory(game);','Directory.CreateDirectory(game);')
 # This fixture owns independent archive copies, including skin archives.
 source=source.replace('// QA-only development context','foreach(string f in Directory.EnumerateFiles(game,"*",SearchOption.AllDirectories))File.SetAttributes(f,FileAttributes.Normal);\n        // QA-only development context')
 i=source.index('    private static IEnumerable<Case> Cases()');j=source.index('    private static IEnumerable<Case>',i+10)
 source=source[:i]+'''    private static IEnumerable<Case> Cases(){
      foreach(var id in new[]{"arcane-on","arcane-off","arcane-on-again"}) {
       var s=new UserSettings{Mod=GameMod.ArcaneWars,Channel="beta",PawPatchEnabled=id!="arcane-off",GameTextLanguage="en",RussianLocalization=false,GameVoiceLanguage="en",CustomPlayerColors=true,DesyncMode="continue"};
       yield return new Case(id,s);
      }
    }
'''+source[j:]
 (Q/'Program.cs').write_text(source)
 for p in(S/'tools/PatchMatrixRunner').glob('*.cs'):
  if p.name!='Program.cs':shutil.copy2(p,Q/p.name)
 # Feed caches contain immutable archives only; no source fixture is modified.
 dest=FIX/'cache/downloads'
 roots=[WS/'outputs/cache-stability-release-20261114/baseline-assets',WS/'work/r24-racial-build-beta-20261114/published',WS/'outputs/arcane-051-release-20261109',Path('G:/PawsWork/Retained/PawsArcane051ReleaseQA-20261109/beta-install/cache/downloads')]
 known={}
 for root in roots:
  for f in root.rglob('*.zip'):
   if f.stat().st_size<500000000:known.setdefault(sha(f),f)
 for f in [O/'before/feed/v3/beta.json',O/'signed/feed/v3/beta.json']:
  for p in verify(read(f),key())['packages']:
   if p['sha256'].upper()not in known:continue
   target=dest/p['id']/p['version']/(p['sha256'].upper()+'.zip');target.parent.mkdir(parents=True,exist_ok=True)
   if not target.exists():os.link(known[p['sha256'].upper()],target)
 print('QA_PROJECT_READY',len(known),'cached archives',flush=True)
def install(stage,case):
 feed=O/'local-feeds/beta.json'
 if stage=='baseline':
  from cryptography.hazmat.primitives import serialization
  raw=verify(read(O/'before/feed/v3/beta.json'),key());raw['channel']='beta';private=serialization.load_pem_private_key(KEY.read_bytes(),None);feed=O/'local-feeds/old-beta.json';write(feed,sign(raw,private))
 args=[SDK,'run','--project',Q/'QA.csproj','-c','Release','--','--root='+str(FIX),'--stock=G:/PawsWork/BaseGame/1.3.72','--stable='+str(O/'local-feeds/stable.json'),'--beta='+str(feed),'--key='+str(O/'public.pem'),'--mode=apply','--case='+case]
 print(run(args,O/('installer-'+stage+'-'+case+'.log')),flush=True)
if __name__=='__main__':
 if sys.argv[1]=='project':project()
 else:install(sys.argv[1],sys.argv[2])
