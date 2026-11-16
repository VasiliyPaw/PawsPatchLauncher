from context import *
import shutil
Q=O/'installer-qa'
def project():
 Q.mkdir(exist_ok=True)
 refs=''.join('<Reference Include="'+f.stem+'"><HintPath>'+str(f)+'</HintPath></Reference>'for f in(O/'launcher-reference').glob('*.dll'))
 (Q/'QA.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0-windows</TargetFramework><UseWPF>true</UseWPF><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup><ItemGroup><Using Include="System.IO" />'+refs+'</ItemGroup></Project>')
 (Q/'Program.cs').write_text((B2/'installer-qa/Program.cs').read_text().replace('beta2-','beta3-'))
 for f in(B2/'installer-qa').glob('*.cs'):
  if f.name!='Program.cs':shutil.copy2(f,Q/f.name)
 before=read(FIX/'game/.pawpatch/state.json');assert before['modules']['pawpatch-core']['version']=='0.6.0-beta.2'
 write(O/'installed-before.json',dict(modules={k:dict(version=v['version'],sha256=v['archiveSha256'])for k,v in before['modules'].items()}))
 print('BETA2_FIXTURE_PINNED',flush=True)
def apply(case):
 assert not subprocess.check_output(['powershell','-NoProfile','-Command',r"Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -eq 'G:\PawsWork\QA\Arcane060-20261115\game\k2.exe' } | Select-Object -ExpandProperty ProcessId"],text=True).strip()
 args=[SDK,'run','--project',Q/'QA.csproj','-c','Release','--','--root='+str(FIX),'--stock=G:/PawsWork/BaseGame/1.3.72','--stable='+str(O/'local-feeds/stable.json'),'--beta='+str(O/'local-feeds/beta.json'),'--key='+str(O/'public.pem'),'--mode=apply','--case='+case]
 print(run(args,O/('install-'+case+'.log')),flush=True)
 state=read(FIX/'game/.pawpatch/state.json');game=FIX/'game';dll=game/'Mods/PawsCaptureKnowledge.dll'
 if case=='beta3-off':
  assert 'pawpatch-core'not in state['modules']and not dll.exists()
  assert not(game/'Mods/plugins.txt').exists()or'PawsCaptureKnowledge'not in(game/'Mods/plugins.txt').read_text()
 else:
  assert state['modules']['pawpatch-core']['version']==VERSION
  assert sha(dll)==read(CAND/'verification.json')['productionSha256']
  assert len((game/'Mods/plugins.txt').read_text().splitlines())==10
  assert sha(game/'data/ui/game/paws_day_clock.tgi')==sha(CWORK/'source/game/ui-scout-test/paws_day_clock.tgi')
  before=read(O/'installed-before.json')['modules']
  for k,v in state['modules'].items():
   if k.startswith('arcane-biome-textures-'):assert dict(version=v['version'],sha256=v['archiveSha256'])==before[k]
  assert len([k for k in state['modules']if k.startswith('arcane-biome-textures-')])==4
 result=dict(passed=True,version=VERSION,case=case,newModulePresent=dll.exists(),baseArchivesUnchanged=all(sha(game/n)==sha(Path('G:/PawsWork/BaseGame/1.3.72')/n)for n in ['Data.rwd','Music.rwd']))
 assert result['baseArchivesUnchanged'];write(O/(case+'-result.json'),result)
if __name__=='__main__':project()if sys.argv[1]=='project'else apply(sys.argv[1])
