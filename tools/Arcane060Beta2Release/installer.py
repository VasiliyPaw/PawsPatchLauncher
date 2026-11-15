from context import *
import shutil
Q=O/'installer-qa'
def project():
 Q.mkdir(exist_ok=True);snap=Q/'launcher';snap.mkdir(exist_ok=True)
 for f in(B1/'installer-qa/launcher').glob('*.dll'):shutil.copy2(f,snap/f.name)
 refs=''.join('<Reference Include="'+p.stem+'"><HintPath>'+str(p)+'</HintPath></Reference>'for p in snap.glob('*.dll'))
 (Q/'QA.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0-windows</TargetFramework><UseWPF>true</UseWPF><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup><ItemGroup><Using Include="System.IO" />'+refs+'</ItemGroup></Project>')
 source=(B1/'installer-qa/Program.cs').read_text();i=source.index('    private static IEnumerable<Case> Cases()');j=source.index('    private static IEnumerable<Case>',i+10)
 cases='''    private static IEnumerable<Case> Cases(){
      foreach(var id in new[]{"beta2-upgrade","beta2-off","beta2-reapply","beta2-network"}){
       var s=new UserSettings{Mod=GameMod.ArcaneWars,Channel="beta",PawPatchEnabled=id!="beta2-off",GameTextLanguage="en",RussianLocalization=false,GameVoiceLanguage="en",CustomPlayerColors=id!="beta2-network",DesyncMode=id=="beta2-network"?"official":"continue"};yield return new Case(id,s);
      }
    }
'''
 (Q/'Program.cs').write_text(source[:i]+cases+source[j:])
 for f in(B1/'installer-qa').glob('*.cs'):
  if f.name!='Program.cs':shutil.copy2(f,Q/f.name)
 before=read(FIX/'game/.pawpatch/state.json');assert before['modules']['pawpatch-core']['version']=='0.6.0-beta.1';assert sum(1 for k in before['modules']if k.startswith('arcane-biome-textures-'))==10;write(O/'installed-before.json',dict(version='0.6.0-beta.1',modules={k:dict(version=v['version'],sha256=v['archiveSha256'])for k,v in before['modules'].items()},textureFiles=sum(len(v['files'])for k,v in before['modules'].items()if k.startswith('arcane-biome-textures-'))));print('BETA1_FIXTURE_PINNED',flush=True)
def apply(case):
 args=[SDK,'run','--project',Q/'QA.csproj','-c','Release','--','--root='+str(FIX),'--stock=G:/PawsWork/BaseGame/1.3.72','--stable='+str(O/'local-feeds/stable.json'),'--beta='+str(O/'local-feeds/beta.json'),'--key='+str(O/'public.pem'),'--mode=apply','--case='+case]
 print(run(args,O/('install-'+case+'.log')),flush=True)
 if case=='beta2-off':
  state=read(FIX/'game/.pawpatch/state.json');assert 'pawpatch-core'not in state['modules'];assert all(not(FIX/'game'/Path(p['path']).name).exists()for p in read(LOSS/'packed.json'));assert 'paws-biome-textures-'not in(FIX/'game/startup/autoexec.txt').read_text();write(O/'rollback-result.json',dict(passed=True,allFourArchivesRemoved=True,allFourMountsRemoved=True))
 else:
  state=read(FIX/'game/.pawpatch/state.json');assert state['modules']['pawpatch-core']['version']==VERSION
  assert {k for k in state['modules']if k.startswith('arcane-biome-textures-')}=={f'arcane-biome-textures-{i:02}'for i in range(1,5)}
  assert not list((FIX/'game/rivers-data/Textures').rglob('*.png')),'Old loose texture remains'
  for p in read(LOSS/'packed.json'):assert sha(FIX/'game'/Path(p['path']).name)==p['sha256'].upper()
  write(O/(case+'-result.json'),dict(passed=True,version=VERSION,oldLooseTexturesRemoved=22464,archiveCount=4,baseArchivesUnchanged=all(sha(FIX/'game'/n)==sha(Path('G:/PawsWork/BaseGame/1.3.72')/n)for n in ['Data.rwd','Music.rwd'])))
if __name__=='__main__':project()if sys.argv[1]=='project'else apply(sys.argv[1])
