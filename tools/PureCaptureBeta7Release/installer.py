from context import *
import shutil
Q=O/'installer-qa';Q.mkdir(exist_ok=True);AV=WS/'outputs/arcane060-beta3-release-20261116'
def setup():
 refs=''.join('<Reference Include="'+f.stem+'"><HintPath>'+str(f)+'</HintPath></Reference>'for f in(AV/'launcher-reference').glob('*.dll'))
 (Q/'QA.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0-windows</TargetFramework><UseWPF>true</UseWPF><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup><ItemGroup><Using Include="System.IO" />'+refs+'</ItemGroup></Project>')
 s=(AV/'installer-qa/Program.cs').read_text();a=s.index('    private static IEnumerable<Case> Cases()');b=s.index('    private static IEnumerable<Case>',a+10)
 cases='''    private static IEnumerable<Case> Cases(){
 foreach(var mod in new[]{GameMod.Vanilla,GameMod.Immortals})foreach(var id in new[]{"upgrade","colors","sync","colors-sync","off","reapply"}){
 var s=new UserSettings{Mod=mod,Channel="beta",PawPatchEnabled=true,VanillaPawPatchEnabled=id!="off",ImmortalsPawPatchEnabled=id!="off",GameTextLanguage="en",RussianLocalization=false,GameVoiceLanguage="en"};var c=GameMod.PureComponents(s);c.Colors=id.Contains("colors");c.IgnoreDesync=id.Contains("sync");yield return new Case(mod+"-"+id,s);
 }}
'''
 s=s[:a]+cases+s[b:]
 # Capture a receipt for each transactional step, including the disabled state.
 anchor='            if (mode == "verify")';s=s.replace(anchor,'            await File.WriteAllTextAsync(Path.Combine(root,item.Id+"-installed.json"),JsonSerializer.Serialize(installer.LoadState(),Json));\n'+anchor)
 (Q/'Program.cs').write_text(s)
 for f in(AV/'installer-qa').glob('*.cs'):
  if f.name!='Program.cs':shutil.copy2(f,Q/f.name)
 # Pin the old beta feed to verified baseline archives for upgrade QA.
 for channel in ['stable','beta']:
  f=verify(read(O/'before'/f'feed/v3/{channel}.json'),key())
  if channel=='beta':
   for p in f['packages']:
    if p['id']in['pure-fixes-data','pure-fixes-runtime','pure-beta-common']:p['urls']=[str(O/'baseline-assets'/Path(p['urls'][0]).name)]
  from cryptography.hazmat.primitives import serialization
  write(O/'old-feeds'/f'{channel}.json',sign(f,serialization.load_pem_private_key(KEY.read_bytes(),None)))
 print('PURE_INSTALLER_QA_READY')
def apply(mode,old=False):
 root=FIX/mode;root.mkdir(parents=True,exist_ok=True);feeds=O/('old-feeds'if old else'local-feeds')
 args=[SDK,'run','--project',Q/'QA.csproj','-c','Release','--no-build','--','--root='+str(root),'--stock=G:/PawsWork/BaseGame/1.3.72','--stable='+str(feeds/'stable.json'),'--beta='+str(feeds/'beta.json'),'--key='+str(O/'public.pem'),'--mode='+('apply'if old else'verify'),'--mod='+mode]
 if old:args+=['--case='+mode+'-upgrade']
 print(run(args,O/('installer-'+mode+('-old'if old else'-new')+'.log')),flush=True)
 if old:
  state=read(root/'game/.pawpatch/state.json');assert state['modules']['pure-fixes-data']['version']=='0.5.0-beta.6';write(O/(mode+'-installed-before.json'),state)
 else:
  receipts={n:read(root/(mode+'-'+n+'-installed.json'))for n in ['upgrade','colors','sync','colors-sync','off','reapply']}
  for n,s in receipts.items():
   if n=='off':assert not any(k in s['modules']for k in ['pure-fixes-runtime','pure-beta-common'])
   else:assert s['modules']['pure-fixes-data']['version']==VERSION and s['modules']['pure-fixes-runtime']['version']==RUNTIME and s['modules']['pure-beta-common']['version']==VERSION
  assert sha(root/'game/data/ui/game/paws_day_clock.tgi')==sha(S/'game/ui-scout-test/paws_day_clock.tgi')
  write(O/(mode+'-installer-result.json'),dict(passed=True,upgradeFrom='0.5.0-beta.6',cases=6,allFourHelpers=True,rollback=True,reapply=True))
if __name__=='__main__':setup()if sys.argv[1]=='setup'else apply(sys.argv[1],len(sys.argv)>2 and sys.argv[2]=='old')


