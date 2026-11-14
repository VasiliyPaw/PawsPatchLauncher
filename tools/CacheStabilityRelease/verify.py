"""Compiled-helper, full selection matrix and actual transactional installer QA."""
import argparse,shutil
from context import *
FROZEN=WS/'outputs/buffer-ownership-release-20261113'
LAUNCHER=WS/'outputs/launcher-1.0.16-release-20261114/source/src/PawsPatchLauncher/bin/Release/net8.0-windows'
def launcher():
 assert (LAUNCHER/'PawsPatchLauncher.dll').is_file();return LAUNCHER
def project(folder,source):
 folder.mkdir(exist_ok=False);snapshot=folder/'launcher';snapshot.mkdir()
 for p in launcher().glob('*.dll'):shutil.copy2(p,snapshot/p.name)
 refs=''.join('<Reference Include="'+p.stem+'"><HintPath>'+str(p)+'</HintPath></Reference>'for p in snapshot.glob('*.dll'))
 (folder/'QA.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0-windows</TargetFramework><UseWPF>true</UseWPF><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup><ItemGroup><Using Include="System.IO" />'+refs+'</ItemGroup></Project>');(folder/'Program.cs').write_text(source)
def compiled():
 folder=OUT/'compiled-checks';folder.mkdir();compiler=Path('C:/Windows/Microsoft.NET/Framework/v4.0.30319/csc.exe')
 for name,source,extra in [('CompiledHelpersChecks',REPO/'tools/BufferOwnershipRelease/CompiledHelpersChecks.cs',[FROZEN/'arcane-helpers',FROZEN/'pure-helpers',sha(GRAPHICS/'d3d9.dll')]),('OfflineColorChecks',REPO/'tools/LobbyColorsRelease/OfflineColorChecks.cs',[sha(REPO/'game/beta7/PawLobbyColorsPayload.bin')])]:
  exe=folder/(name+'.exe');run([compiler,'/nologo','/target:exe','/platform:x86','/out:'+str(exe),source]);print(run([exe,OUT/'arcane-helpers',OUT/'pure-helpers',*extra],folder/(name+'.log')),flush=True)
 write(folder/'result.json',dict(passed=True,helpers=12,nativePayloadsUnchanged=True,gamesLaunched=False))
def catalog():
 source=(REPO/'outputs/arcane-051-release-20261109/stable/catalog-qa/Program.cs').read_text()
 source=source.replace('var after=channel=="stable"?Read(Path.Combine(root,"signed/feed/v3/stable.json")):before;','var after=channel=="beta"?Read(Path.Combine(root,"signed/feed/v3/beta.json")):before;').replace('channel=="stable"&&mod==GameMod.ArcaneWars&&patch','channel=="beta"&&patch')
 source=source.replace('selected.Single(p=>p.Id=="pawpatch-core").Version=="0.5.0"','selected.Single(p=>p.Id==(mod==GameMod.ArcaneWars?"pawpatch-core":"pure-fixes-data")).Version==(mod==GameMod.ArcaneWars?"'+VERSIONS['arcane']+'":"'+VERSIONS['pure']+'")')
 source=source.replace('var newFiles=new Dictionary','foreach(var p in JsonDocument.Parse(File.ReadAllText(Path.Combine(args[4],"build-report.json"))).RootElement.EnumerateObject())helperNames.Add(p.Name);\nvar newFiles=new Dictionary')
 source=source.replace('foreach(var file in Directory.EnumerateFiles(Path.Combine(root,"assets"),"*.zip"))','foreach(var file in Directory.EnumerateFiles(root,"*.zip",SearchOption.AllDirectories).Where(p=>p.Contains("assets")))').replace('ARCANE_STABLE_ALL_SWITCHES_PASS','THREE_BETA_CACHE_FIX_ALL_SWITCHES_PASS')
 write(OUT/'preparation.json',dict(assets=[dict(id=p['id'])for p in read(OUT/'packages.json')]))
 folder=OUT/'catalog-qa';project(folder,source);print(run([SDK,'run','--project',folder/'QA.csproj','-c','Release','--',OUT,REPO,OUT/'arcane-helpers',OUT,OUT/'pure-helpers'],OUT/'catalog-checks.log')[-1400:],flush=True)
 assert 'THREE_BETA_CACHE_FIX_ALL_SWITCHES_PASS'in(OUT/'catalog-checks.log').read_text()
def seed_cache(fixture):
 target=fixture/'cache/downloads';target.mkdir(parents=True,exist_ok=True)
 for folder in [FROZEN/'pure-installer-fixture/cache/downloads',FROZEN/'arcane-installer-fixture/cache/downloads',Path('G:/PawPure050OptQA-20261109/installer/cache/downloads'),Path('G:/PawsWork/Retained/PawsArcane051ReleaseQA-20261109/beta-install/cache/downloads')]:
  for p in folder.rglob('*.zip'):
   dest=target/p.relative_to(folder);dest.parent.mkdir(parents=True,exist_ok=True)
   sourceLong='\\\\?\\'+str(p.resolve());targetLong='\\\\?\\'+str(dest.resolve())
   if not os.path.exists(targetLong)and os.path.isfile(sourceLong):os.link(sourceLong,targetLong)
def installers():
 # Existing no-launch matrix uses the real launcher 1.0.15 transactional installer.
 # Independent small files, read-only hardlinks for immutable base archives only.
 source=(REPO/'tools/PatchMatrixRunner/Program.cs').read_text();source='using System.IO;\nusing System.Net.Http;\nusing System.Runtime.InteropServices;\n'+source
 source=source.replace('        EnsureNoGame();','        // No-launch fixture; no process control.')
 source=source.replace('var mode = options.GetValueOrDefault("mode", "plan");','var mode = options.GetValueOrDefault("mode", "plan");if(mode!="verify")throw new InvalidOperationException("No-launch verification only");')
 source=source.replace('if (settings.PureBetaFeatures)','if (settings.PureBetaFeatures && !settings.DataOnly)')
 source=source.replace('internal static class Program\n{','internal static class Program\n{\n    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool CreateHardLinkW(string target,string source,IntPtr reserved);')
 old='                File.Copy(source, Path.Combine(game, Path.GetFileName(source)));'
 new='''                {string target=Path.Combine(game,Path.GetFileName(source));if(Path.GetExtension(source).Equals(".rwd",StringComparison.OrdinalIgnoreCase)){if(!CreateHardLinkW(target,source,IntPtr.Zero))throw new IOException("Immutable base hardlink failed");}else File.Copy(source,target);}'''
 assert old in source;source=source.replace(old,new)
 anchor='        foreach (var (relative, expected) in baseline)\n        {'
 addition='''
            if(Path.GetExtension(relative).Equals(".rwd",StringComparison.OrdinalIgnoreCase)){
                string archiveTarget=CryptoAndIO.SafeChildPath(game,relative);if(!File.Exists(archiveTarget)){Directory.CreateDirectory(Path.GetDirectoryName(archiveTarget)!);string archiveSource=CryptoAndIO.SafeChildPath(stock,relative);if(!File.Exists(archiveSource))archiveSource=CryptoAndIO.SafeChildPath("G:/PawGraphicsQA-20261113/game",relative);File.Copy(archiveSource,archiveTarget);File.SetAttributes(archiveTarget,FileAttributes.Normal);}
                if(!string.Equals(await CryptoAndIO.Sha256Async(CryptoAndIO.SafeChildPath(game,relative)),expected,StringComparison.OrdinalIgnoreCase))throw new InvalidDataException("Immutable base archive mismatch");continue;
            }
'''
 assert anchor in source;source=source.replace(anchor,anchor+addition)
 # Actual base assets must remain immutable and packages must not replace them.
 for p in read(OUT/'packages.json'):
  import zipfile
  with zipfile.ZipFile(read(OUT/'package-audit.json')[p['id']]['archive'])as z:assert not any(n.lower()in['payload/data.rwd','payload/music.rwd']for n in z.namelist())
 start=source.index('    private static IEnumerable<Case> PureBetaCases()');end=source.index('    private static IEnumerable<Case> PureStableCases()',start);block=source[start:end];at=block.rfind('    }')
 block=block[:at]+'''        foreach(string mod in new[]{GameMod.Vanilla,GameMod.Immortals}){
            yield return new Case(mod+"-pure-file-only",new UserSettings{Mod=mod,Channel="beta",DataOnly=true,VanillaPawPatchEnabled=true,ImmortalsPawPatchEnabled=true,GameVoiceLanguage="en"});
            yield return new Case(mod+"-pure-beta-reapply",new UserSettings{Mod=mod,Channel="beta",VanillaPawPatchEnabled=true,ImmortalsPawPatchEnabled=true,GameVoiceLanguage="en"});
        }
'''+block[at:];source=source[:start]+block+source[end:]
 # Use the accepted focused Arcane case list (8 helpers + locale paths).
 accepted=(REPO/'outputs/arcane-051-release-20261109/stable/installation-qa/Program.cs').read_text();i=accepted.index('    private static IEnumerable<Case> Cases()');j=accepted.index('    private static IEnumerable<Case>',i+10);focused=accepted[i:j].replace('"stable-helper-"','"beta-helper-"').replace('"stable-locale-"','"beta-locale-"').replace('Channel="stable"','Channel="beta"')
 i=source.index('    private static IEnumerable<Case> Cases()');j=source.index('    private static IEnumerable<Case>',i+10);source=source[:i]+focused+source[j:]
 # File.Copy preserves readonly source attributes. Clear them on independent
 # fixture copies only, never on shared Data.rwd/Music.rwd hardlinks.
 anchor='        // QA-only development context for this isolated genuine Steam executable.'
 assert anchor in source;source=source.replace(anchor,'        foreach(string f in Directory.EnumerateFiles(game,"*",SearchOption.AllDirectories))if(!new[]{"Data.rwd","Music.rwd"}.Contains(Path.GetFileName(f)))File.SetAttributes(f,FileAttributes.Normal);\n'+anchor)
 folder=OUT/'installer-qa-r6';project(folder,source)
 for p in(REPO/'tools/PatchMatrixRunner').glob('*.cs'):
  if p.name!='Program.cs':shutil.copy2(p,folder/p.name)
 stock=Path('G:/PawsWork/BaseGame/1.3.72');before={n:sha(stock/n)for n in ['Data.rwd','Music.rwd']}
 for kind,extra,count in [('pure',['--pure-beta-smoke=true'],20),('arcane',['--channel=beta','--mod=arcane-wars'],12)]:
  fixture=Path('G:/PawCacheReleaseQA-20261114')/(kind+'-r6');seed_cache(fixture)
  args=[SDK,'run','--project',folder/'QA.csproj','-c','Release','--','--root='+str(fixture),'--stock='+str(stock),'--stable='+str(OUT/'local-feeds/stable.json'),'--beta='+str(OUT/'local-feeds/beta.json'),'--key='+str(OUT/'public.pem'),'--mode=verify',*extra]
  log=OUT/(kind+'-installer-checks.log');print(run(args,log)[-1800:],flush=True);assert log.read_text().count('INSTALL_PASS ')==count
 assert before=={n:sha(stock/n)for n in before};write(OUT/'installer-result.json',dict(passed=True,pureCases=20,arcaneCases=12,launcher='1.0.16',launcherDllSha256=sha(launcher()/'PawsPatchLauncher.dll'),baseArchivesUnchanged=True,gamesLaunched=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['compiled','catalog','installers']);globals()[p.parse_args().action]()
