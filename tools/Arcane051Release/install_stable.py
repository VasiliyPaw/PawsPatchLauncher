"""Run the real transactional installer on 12 owned, no-launch compositions."""
import json,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];OUT=REPO/'outputs/arcane-051-release-20261109';STAGE=OUT/'stable';SDK='C:/Users/Paw/Documents/Codex/Kohan-Reborn/.tools/dotnet/dotnet.exe'
FIXTURE=Path('C:/PawsArcane051ReleaseQA-20261109/stable-install')
def main():
 qa=STAGE/'installation-qa';qa.mkdir(exist_ok=True)
 text=(REPO/'tools/PatchMatrixRunner/Program.cs').read_text()
 text=text.replace('var mode = options.GetValueOrDefault("mode", "plan");','var mode = options.GetValueOrDefault("mode", "plan"); if(mode!="verify") throw new InvalidOperationException("This promotion fixture never launches a game");')
 text=text.replace('        EnsureNoGame();','        // Offline fixture install only; another chat may use its separate game.')
 start=text.index('    private static IEnumerable<Case> Cases()');end=text.index('    private static IEnumerable<Case> PureBetaCases()',start)
 text=text[:start]+'''    private static IEnumerable<Case> Cases()
    {
        for(int bits=0;bits<8;bits++) {
            var s=new UserSettings{Mod=GameMod.ArcaneWars,Channel="stable",PawPatchEnabled=true,CustomPlayerColors=(bits&1)!=0,DesyncMode=(bits&2)!=0?"continue":"official",IndependentHostility=(bits&4)!=0,GameVoiceLanguage="en",ImprovedAi=(bits&1)!=0,IgnoreZeroMorale=(bits&2)!=0};
            GameLanguages.SetText(s,bits%2==0?"en":"ru");yield return new Case("stable-helper-"+bits,s);
        }
        foreach(string language in new[]{"de","fr","cs","uk"}) {
            var s=new UserSettings{Mod=GameMod.ArcaneWars,Channel="stable",PawPatchEnabled=language!="uk",GameVoiceLanguage="en",ImprovedAi=true};
            GameLanguages.SetText(s,language);yield return new Case("stable-locale-"+language,s);
        }
    }
''' +text[end:]
 (qa/'Program.cs').write_text(text)
 for source in (REPO/'tools/PatchMatrixRunner').glob('*.cs'):
  if source.name!='Program.cs':(qa/source.name).write_bytes(source.read_bytes())
 (qa/'QA.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0-windows</TargetFramework><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup><ItemGroup><ProjectReference Include="'+str(REPO/'src/PawsPatchLauncher/PawsPatchLauncher.csproj')+'" /></ItemGroup></Project>')
 config=json.loads((REPO/'src/PawsPatchLauncher/launcher.config.json').read_text());public=STAGE/'public.pem';public.write_text(config['publicKeyPem'])
 # Reuse previously verified originals; ModDB availability is unrelated to this promotion.
 cached=Path('C:/PawsNoHotJoinQA-20261107/package-matrix/cache/downloads/arcane-wars')
 for source in cached.rglob('*.zip'):
  target=FIXTURE/'cache/downloads/arcane-wars'/source.relative_to(cached)
  target.parent.mkdir(parents=True,exist_ok=True)
  if not target.exists():shutil.copy2(source,target)
 cmd=[SDK,'run','--project',str(qa/'QA.csproj'),'-c','Release','--','--root='+str(FIXTURE),'--stock=D:/SteamLibrary/steamapps/common/Kohan II','--stable='+str(STAGE/'local-feeds/v3-stable.json'),'--beta='+str(OUT/'before/feed/v3/beta.json'),'--key='+str(public),'--mode=verify','--channel=stable','--mod=arcane-wars']
 with (STAGE/'installation-checks.log').open('w') as f:r=subprocess.run(cmd,cwd=REPO,stdout=f,stderr=subprocess.STDOUT)
 if r.returncode:print((STAGE/'installation-checks.log').read_text()[-4000:]);r.check_returncode()
 print((STAGE/'installation-checks.log').read_text()[-2000:])
if __name__=='__main__':main()
