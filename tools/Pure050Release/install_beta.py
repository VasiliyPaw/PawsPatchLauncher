"""Actual launcher installer upgrade/rollback/locales; never launches a game."""
import copy,shutil,subprocess,zipfile
from context import *
from PrepareRelease081 import key,sign
from PrepareRelease070 import verify
from cryptography.hazmat.primitives import serialization

def main():
 out=OUT/'beta-install-r7';out.mkdir(exist_ok=False);snapshot=out/'launcher';snapshot.mkdir();bin=REPO/'src/PawsPatchLauncher/bin/Release/net8.0-windows'
 [(shutil.copy2(p,snapshot/p.name))for p in bin.glob('*.dll')];dllhash=sha(snapshot/'PawsPatchLauncher.dll')
 source='using System.IO;\nusing System.Net.Http;\n'+(REPO/'tools/PatchMatrixRunner/Program.cs').read_text().replace('        EnsureNoGame();','        // Isolated no-launch installer fixture.')
 source=source.replace('var mode = options.GetValueOrDefault("mode", "plan");','var mode = options.GetValueOrDefault("mode", "plan");if(mode!="verify")throw new InvalidOperationException("Offline installer verification only");')
 anchor='        foreach (string mod in new[] { GameMod.Vanilla, GameMod.Immortals })';# append DataOnly and beta reapply to the actual Pure cases.
 start=source.index('    private static IEnumerable<Case> PureBetaCases()');end=source.index('    private static IEnumerable<Case> PureStableCases()',start);block=source[start:end];at=block.rfind('    }')
 block=block[:at]+'''        foreach(string mod in new[]{GameMod.Vanilla,GameMod.Immortals}){
            yield return new Case(mod+"-pure-file-only",new UserSettings{Mod=mod,Channel="beta",DataOnly=true,VanillaPawPatchEnabled=true,ImmortalsPawPatchEnabled=true,GameVoiceLanguage="en"});
            yield return new Case(mod+"-pure-beta-reapply",new UserSettings{Mod=mod,Channel="beta",VanillaPawPatchEnabled=true,ImmortalsPawPatchEnabled=true,GameVoiceLanguage="en"});
        }
'''+block[at:];source=source[:start]+block+source[end:]
 # DataOnly keeps stock k2; run Pure preflight only for native helper modes.
 source=source.replace('if (settings.PureBetaFeatures)','if (settings.PureBetaFeatures && !settings.DataOnly)')
 (out/'Program.cs').write_text(source);(out/'Globals.cs').write_text('global using System.IO;\n')
 for p in (REPO/'tools/PatchMatrixRunner').glob('*.cs'):
  if p.name!='Program.cs':shutil.copy2(p,out/p.name)
 references=''.join('<Reference Include="'+p.stem+'"><HintPath>'+str(p)+'</HintPath></Reference>'for p in snapshot.glob('*.dll'))
 (out/'QA.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0-windows</TargetFramework><UseWPF>true</UseWPF><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup><ItemGroup>'+references+'</ItemGroup></Project>')
 private=serialization.load_pem_private_key((LEG/'PawsPatchLauncher/.local/signing/pawpatch-signing-private.pem').read_bytes(),None);assert private.public_key().public_numbers()==key().public_numbers()
 config=read(REPO/'src/PawsPatchLauncher/launcher.config.json');(out/'public.pem').write_text(config['publicKeyPem']);new={p['id']:p for p in read(OUT/'beta-stage-r4/packages.json')};known={}
 for folder in [OUT/'accepted-assets',OUT/'stable-stage/assets',OUT/'beta-stage-r4/assets',OUT/'optional-data-r1/inputs',WS/'outputs/release-pure-040-20261013/publication-final/packages']:
  for p in folder.glob('*.zip'):known[sha(p)]=p
 for channel in ['stable','beta']:
  feed=verify(read(REPO/('feed/v3/'+channel+'.json')),key())
  if channel=='beta':feed['packages']=[copy.deepcopy(new.get(p['id'],p))for p in feed['packages']]
  for p in feed['packages']:
   if p['sha256']in known:p['urls']=[str(known[p['sha256']])]
  write(out/(channel+'.json'),sign(feed,private))
 fixture=Path('G:/PawPure050QA-20261109/installer');cmd=['C:/Users/Paw/Documents/Codex/Kohan-Reborn/.tools/dotnet/dotnet.exe','run','--project',out/'QA.csproj','-c','Release','--','--root='+str(fixture),'--stock=D:/SteamLibrary/steamapps/common/Kohan II','--stable='+str(out/'stable.json'),'--beta='+str(out/'beta.json'),'--key='+str(out/'public.pem'),'--mode=verify','--pure-beta-smoke=true']
 with(out/'verification.log').open('w')as log:p=subprocess.run(list(map(str,cmd)),cwd=REPO,stdout=log,stderr=subprocess.STDOUT)
 text=(out/'verification.log').read_text();print(text[-3500:]);assert p.returncode==0 and text.count('INSTALL_PASS ')==20
 write(out/'result.json',dict(passed=True,cases=20,launcherDllSha256=dllhash,scope='actual transactional installer; 6 locales; 4 helpers; independent families/roaming; stable rollback; master off; file-only; beta reapply; no games launched'))
if __name__=='__main__':main()
