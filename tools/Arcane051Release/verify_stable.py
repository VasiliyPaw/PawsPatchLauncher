"""Build and run launcher-native promotion selection/install checks in owned fixtures."""
import json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];OUT=REPO/'outputs/arcane-051-release-20261109';STAGE=OUT/'stable'
def main():
 qa=STAGE/'catalog-qa';qa.mkdir(exist_ok=True)
 old=Path('C:/PawsNoHotJoinQA-20261107/catalog-qa/Program.cs').read_text()
 old=old.replace('Path.Combine(root,"before/feed/v3/"+channel+".json")','Path.Combine(args[3],"before/feed/v3/"+channel+".json")')
 old=old.replace('channel=="beta"?Read(Path.Combine(root,"signed/feed/v3/beta.json")):before','channel=="stable"?Read(Path.Combine(root,"signed/feed/v3/stable.json")):before')
 old=old.replace('var changed=new HashSet<string>{"pawpatch-core","common-ui","player-colors","desync-continue"};','var changed=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"preparation.json"))).RootElement.GetProperty("assets").EnumerateArray().Select(a=>a.GetProperty("id").GetString()!).ToHashSet();')
 old=old.replace('channel=="beta"&&mod==GameMod.ArcaneWars&&patch','channel=="stable"&&mod==GameMod.ArcaneWars&&patch').replace('=="0.5.0-beta.4"','=="0.5.0"')
 old=old.replace('Check(channel=="beta"?after.Launcher.Version=="1.0.8":after.Launcher.Version==before.Launcher.Version&&after.Launcher.Sha256==before.Launcher.Sha256,"Launcher scope");','Check(after.Launcher.Version==before.Launcher.Version&&after.Launcher.Sha256==before.Launcher.Sha256,"Launcher scope");')
 old=old.replace('NO_HOTJOIN_ALL_SWITCHES_CATALOG_PASS','ARCANE_STABLE_ALL_SWITCHES_PASS').replace('beta launcher 1.0.8','launcher retained')
 (qa/'Program.cs').write_text(old)
 (qa/'QA.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0-windows</TargetFramework><UseWPF>true</UseWPF><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup><ItemGroup><ProjectReference Include="'+str(REPO/'src/PawsPatchLauncher/PawsPatchLauncher.csproj')+'" /></ItemGroup></Project>')
 cmd=['C:/Users/Paw/Documents/Codex/Kohan-Reborn/.tools/dotnet/dotnet.exe','run','--project',str(qa/'QA.csproj'),'-c','Release','--',str(STAGE),str(REPO),str(STAGE/'helpers'),str(OUT)]
 with (STAGE/'catalog-checks.log').open('w') as f:r=subprocess.run(cmd,cwd=REPO,stdout=f,stderr=subprocess.STDOUT)
 r.check_returncode();print((STAGE/'catalog-checks.log').read_text()[-1500:])
if __name__=='__main__':main()
