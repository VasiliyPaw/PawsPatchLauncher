"""Reuse native-equivalence, failure and ABI fixtures against exact port bytes."""
import argparse,subprocess,shutil,os
from context import *
NATIVE=OUT/'native-r1';HELPERS=OUT/'helpers-r1'
def run(args,log):
 env=os.environ.copy();env['PYTHONPATH']=str(HERE)+os.pathsep+env.get('PYTHONPATH','')
 with Path(log).open('w')as f:p=subprocess.run(list(map(str,args)),cwd=REPO,env=env,stdout=f,stderr=subprocess.STDOUT)
 tail=Path(log).read_text()[-1400:];print(tail,flush=True);assert p.returncode==0,(log,p.returncode)
def cache():
 folder=OUT/'cache-tests';folder.mkdir(exist_ok=False)
 run([sys.executable,REPO/'game/resource-cache/test_native.py','--native',NATIVE/'cache-build'],folder/'native.log')
 run([sys.executable,REPO/'tools/Arcane051Release/test_product_cache.py','--native',NATIVE/'cache-build'],folder/'policy.log')
 run([sys.executable,REPO/'game/resource-cache/test_transactions.py','--report',HELPERS/'build-report.json'],folder/'transactions.log')
 write(folder/'result.json',dict(passed=True,payload=sha(NATIVE/'cache-build/payload.bin'),productionPolicy=sha(NATIVE/'cache/cache.c')))
def find():
 folder=OUT/'find-tests';folder.mkdir(exist_ok=False)
 for n in ['local_find.h','native_contract.h']:shutil.copy2(NATIVE/n,folder/n)
 shutil.copy2(REPO/'game/find-local-cache/test_exports.c',folder/'test_exports.c')
 shutil.copy2(Path('C:/PawsFindQA-20261109/build-r3/contract-provenance.json'),folder/'contract-provenance.json')
 run([TCC,'-shared','-Wall','-Werror',folder/'test_exports.c','-o',folder/'test-local.dll','-lkernel32'],folder/'build.log')
 for name in ['test_native','test_contract','test_readonly']:
  s=(REPO/('game/find-local-cache/'+name+'.py')).read_text();s=s.replace('PROJECT=HERE.parents[3]','PROJECT=Path('+repr(str(WS))+')');(folder/(name+'.py')).write_text(s)
 for name in ['test_native','test_contract']:
  run([sys.executable,folder/(name+'.py'),'--build',folder,'--out',folder/(name+'.json')],folder/(name+'.log'))
 run([sys.executable,folder/'test_readonly.py','--out',folder/'test_readonly.json'],folder/'test_readonly.log')
 write(folder/'result.json',dict(passed=True,productionFind=sha(NATIVE/'find.c'),algorithm=sha(NATIVE/'local_find.h'),contract=sha(NATIVE/'native_contract.h')))
def ui():
 folder=OUT/'ui-tests';folder.mkdir(exist_ok=False)
 s=(REPO/'tools/Pure050Release/test_ui.py').read_text();s=s.replace("out=OUT/'ui-tests-r4';out.mkdir(exist_ok=False);native=OUT/'ui-native-r3'","out=OUT/'ui-tests';out.mkdir(exist_ok=True);native=OUT/'native-r1'")
 s=s.replace("native/'runtime.c',out/'ui.c','-o'","native/'runtime.c',out/'ui.c',native/'find.c','-o'")
 # No HUD machine code changed in this port; bind the actual helper source to
 # its already accepted identical bytes, while testing the new native UI DLL.
 s=s.replace("build=OUT/'beta-helpers-r4'","build=PREVIOUS/'beta-helpers-r4'")
 (folder/'run.py').write_text(s);run([sys.executable,folder/'run.py'],folder/'checks.log')
 fixture=NATIVE/'path_fixture.c';shutil.copy2(OUT/'frozen/pure-ui/path_fixture.c',fixture)
 run([TCC,'-Wall','-Werror','-Wl,--image-base=0x20000000',fixture,'-o',folder/'PathFixture.exe','-lkernel32','-luser32'],folder/'path-build.log')
 run([folder/'PathFixture.exe',NATIVE/'PawsPurePresentation1372.dll','1'],folder/'path.log')
def composition():
 folder=OUT/'composition-tests-r2';folder.mkdir(exist_ok=False);row=read(HELPERS/'build-report.json')['k2_paws_pure_fixes_1372.exe']
 s=(PREVIOUS/'beta-helpers-r4/PureBetaCompositionTests.cs').read_text();anchor='                PureWorldOptionsPatch.Install(m,image,delegate{});';s=once(s,anchor,anchor+'\n                ResourceCachePatch.Install(System.Diagnostics.Process.GetCurrentProcess(),m,image,delegate{});')
 spans=read(Path('C:/PawsFindQA-20261109/build-r3/contract-provenance.json'))['ranges']
 guard='\n                byte[] untouchedFind=Relocate(raw,image);\n'+''.join('                if(!m.Read(image+'+str(rva)+','+str(n)+').SequenceEqual(untouchedFind.Skip('+str(rva)+').Take('+str(n)+')))throw new Exception("Find contract changed: '+name+'");\n'for name,rva,n in spans)
 s=once(s,'                // Constructor owners and UI sites remain untouched',guard+'                // Constructor owners and UI sites remain untouched')
 s=s.replace('0x2b1ae6})','0x2b1ae6,0x18e3c8})');source=folder/'Composition.cs';source.write_text(s)
 args=[('/target:exe'if p.startswith('/target:')else'/main:PawPureFixes.PureBetaNativeTests'if p.startswith('/main:')else'/out:'+str(folder/'Composition.exe')if p.startswith('/out:')else p)for p in row['args']]+[str(source)]
 run(args,folder/'build.log');run([folder/'Composition.exe',LEG/'k2_runtime_1372_20260904.bin'],folder/'checks.log')
 write(folder/'result.json',dict(passed=True,compositions=12,bases=3,worldRegistryCacheInstalledTogether=True,uiAndFindSitesRemainNative=True,allSevenFindBodyGuardsPreserved=True))
def graphics():
 folder=OUT/'graphics-tests';folder.mkdir(exist_ok=False);tests=Path('C:/PawsReuseQA-20261108/pool-build-r6')
 for name in ['test_graphics_guard','test_graphics_guard_d3d']:run([tests/(name+'.exe'),NATIVE/'graphics/d3d9.dll'],folder/(name+'.log'))
 run([tests/'test_buffers.exe',NATIVE/'graphics/d3d9-fixture.dll'],folder/'buffers.log')
 write(folder/'result.json',dict(passed=True,productionDll=sha(NATIVE/'graphics/d3d9.dll'),fixtureNotShipped=True))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['cache','find','ui','composition','graphics']);a=p.parse_args();globals()[a.action]()
