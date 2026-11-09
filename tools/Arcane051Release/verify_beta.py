"""Reuse the accepted selection/install regression against local beta bytes."""
import argparse,json,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];OUT=REPO/'outputs/arcane-051-release-20261109';SDK='C:/Users/Paw/Documents/Codex/Kohan-Reborn/.tools/dotnet/dotnet.exe';FIXTURE=Path('C:/PawsArcane051ReleaseQA-20261109/beta-install')
def run(cmd,log):
 with log.open('w') as f:r=subprocess.run(cmd,cwd=REPO,stdout=f,stderr=subprocess.STDOUT)
 print(log.read_text()[-3000:],flush=True);r.check_returncode()
def project(qa):
 qa.mkdir(exist_ok=True);(qa/'QA.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0-windows</TargetFramework><UseWPF>true</UseWPF><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup><ItemGroup><Using Include="System.IO" /><ProjectReference Include="'+str(REPO/'src/PawsPatchLauncher/PawsPatchLauncher.csproj')+'" /></ItemGroup></Project>')
def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--action',choices=['catalog','install'],required=True);a=p.parse_args();stage=a.stage.resolve();proof=json.loads((stage/'preparation.json').read_text());qa=stage/(a.action+'-qa');project(qa)
 if a.action=='catalog':
  source=(OUT/'stable/catalog-qa/Program.cs').read_text();source=source.replace('channel=="stable"','channel=="beta"').replace('signed/feed/v3/stable.json','local-feeds/beta.json').replace('=="0.5.0"','=="'+proof['version']+'"').replace('ARCANE_STABLE_ALL_SWITCHES_PASS','ARCANE_BETA_ALL_SWITCHES_PASS');(qa/'Program.cs').write_text(source)
  cmd=[SDK,'run','--project',str(qa/'QA.csproj'),'-c','Release','--',str(stage),str(REPO),proof['helpers'],str(stage)]
 else:
  source=(OUT/'stable/installation-qa/Program.cs').read_text();source=source.replace('Channel="stable"','Channel="beta"').replace('"stable-helper-"','"beta-helper-"').replace('"stable-locale-"','"beta-locale-"');(qa/'Program.cs').write_text(source)
  for source in (REPO/'tools/PatchMatrixRunner').glob('*.cs'):
   if source.name!='Program.cs':(qa/source.name).write_bytes(source.read_bytes())
  for cached in [Path('C:/PawsNoHotJoinQA-20261107/package-matrix/cache/downloads'),Path('C:/PawsArcane051ReleaseQA-20261109/stable-install/cache/downloads')]:
   for source in cached.rglob('*.zip'):
    target=FIXTURE/'cache/downloads'/source.relative_to(cached);target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists():shutil.copy2(source,target)
  cmd=[SDK,'run','--project',str(qa/'QA.csproj'),'-c','Release','--','--root='+str(FIXTURE),'--stock=D:/SteamLibrary/steamapps/common/Kohan II','--stable='+str(stage/'local-feeds/stable.json'),'--beta='+str(stage/'local-feeds/beta.json'),'--key='+str(stage/'public.pem'),'--mode=verify','--channel=beta','--mod=arcane-wars']
 run(cmd,stage/(a.action+'-checks.log'))
if __name__=='__main__':main()
