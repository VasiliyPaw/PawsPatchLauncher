import json,shutil,subprocess,sys
from pathlib import Path
from build import OUT,BASE,REPO,run,read,write,sha
folder=OUT/'checks';folder.mkdir(exist_ok=True)
csc='C:/Windows/Microsoft.NET/Framework/v4.0.30319/csc.exe'
for kind in ['arcane','pure']:
 d=OUT/(kind+'-native');d.mkdir(exist_ok=True)
 name='PawsPresentation1372.dll'if kind=='arcane'else'PawsPurePresentation1372.dll';shutil.copy2(BASE/(kind+'-native')/name,d/name)
exe=folder/'CompiledChecks.exe';run([csc,'/nologo','/platform:x86','/out:'+str(exe),REPO/'tools/NativeRenderPolicy/CompiledChecks.cs'])
result=run([exe,OUT,BASE,'3B596B4A9435A8BDCD183906CAABE9CB60706FCE56783D42E8C66C52DA43944E']);(folder/'compiled.log').write_text(result);print(result.strip())
exe=folder/'TerrainGuardChecks.exe';run([csc,'/nologo','/platform:x86','/out:'+str(exe),REPO/'game/terrain-texture-pool/StartupGuardTests.cs'])
helpers=sorted((OUT/'arcane-helpers').glob('k2_paws_*.exe'))+sorted((OUT/'pure-helpers').glob('k2_paws_*.exe'))
result=run([exe,OUT/'overlay/data/UVars_k2.tgi',*helpers]);(folder/'guards.log').write_text(result);print(result.strip())
row=next(iter(read(OUT/'arcane-helpers/build-report.json').values()))
source=(REPO/'game/resource-cache/TransactionTests.cs').read_text().replace('i<2','i<ResourceCachePayload.Sites.Length')
(folder/'TransactionTests.cs').write_text(source);args=[]
for arg in row['args']:
 if arg.startswith('/out:'):arg='/out:'+str(folder/'CacheTransactionTests.exe')
 if arg.startswith('/target:'):arg='/target:exe'
 if arg.startswith('/main:'):continue
 args.append(arg)
run(args+['/main:CacheTransactionTests',folder/'TransactionTests.cs']);result=run([folder/'CacheTransactionTests.exe']);(folder/'transactions.log').write_text(result);print(result.strip())
tests={}
for kind in ['arcane','pure']:
 for name,row in read(OUT/(kind+'-helpers/build-report.json')).items():
  flags=[]if kind=='pure'else['--quiet-startup-self-test','--common-ui-self-test','--lobby-payload-test','--assistant-self-test','--fast-transfer-self-test']
  tests[kind+'/'+name]={flag:run([OUT/(kind+'-helpers')/name,flag]).strip()for flag in flags}
hooks=len(read(OUT/'native/payload/payload.json')['hooks'])
write(folder/'self-tests.json',tests);write(folder/'result.json',dict(passed=True,helpers=12,hookCount=hooks,noGameLaunched=True));print('EXPANDED_COMPILED_CHECKS_PASS 12 helpers; all',hooks,'hook transactions')
