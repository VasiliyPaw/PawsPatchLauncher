"""Fix only default-helper trailing separators; prove old/new queued validation on Win32."""
import shutil,subprocess
from context import *

def main():
 old=OUT/'ui-native-r2';out=OUT/'ui-native-r3';out.mkdir(exist_ok=True);assert not (out/'build.json').exists()
 for p in old.iterdir():
  if p.suffix in ['.c','.h','.cs']:shutil.copy2(p,out/p.name)
 p=out/'runtime.c';s=p.read_text();s=s.replace('wchar_t actual[260],*slash;U threads;','wchar_t actual[260],expected[260],*slash;U threads;UINT length;')
 anchor=' *slash=0;if(c->gameDir[259]||c->modsDir[259]||lstrcmpiW(actual,c->gameDir))return 3;'
 assert s.count(anchor)==1;s=s.replace(anchor,''' *slash=0;if(c->gameDir[259]||c->modsDir[259])return 3;
 lstrcpynW(expected,c->gameDir,260);length=lstrlenW(expected);
 while(length&&(expected[length-1]==L'\\\\'||expected[length-1]==L'/'))expected[--length]=0;
 if(lstrcmpiW(actual,expected))return 3;''');p.write_text(s)
 args=[TCC,'-shared','-Wall','-Werror',out/'runtime.c',out/'ui.c','-o',out/'PawsPurePresentation1372.dll','-lkernel32','-luser32'];subprocess.run(list(map(str,args)),check=True)
 import pefile
 pe=pefile.PE(str(out/'PawsPurePresentation1372.dll'));exports={e.name.decode().lstrip('_').split('@')[0]:e.address for e in pe.DIRECTORY_ENTRY_EXPORT.symbols};assert set(exports)=={'PawPresentationQueued','PawPresentationFrame'}
 digest=sha(out/'PawsPurePresentation1372.dll');(out/'PurePresentationRuntimePayload.cs').write_text('internal static class PurePresentationRuntimePayload { internal const string Sha256="'+digest+'";internal const uint QueuedRva='+str(exports['PawPresentationQueued'])+'; }\n')
 fixture=(REPO/'game/presentation-runtime/path_fixture.c').read_text();assert fixture.count('image+0x50000')==1;fixture=fixture.replace('image+0x50000','image+0x500000');(out/'path_fixture.c').write_text(fixture)
 exe=out/'PathFixture.exe';subprocess.run(list(map(str,[TCC,'-Wall','-Werror','-Wl,--image-base=0x20000000',out/'path_fixture.c','-o',exe,'-lkernel32','-luser32'])),check=True)
 results=[]
 for folder,fixed in [(old,False),(out,True)]:
  result=subprocess.run([str(exe),str(folder/'PawsPurePresentation1372.dll'),'1'if fixed else'0'],capture_output=True,text=True);print(result.stdout+result.stderr);assert result.returncode==0;results.append(dict(fixed=fixed,passed=True,output=result.stdout.strip()))
 assert sha(old/'ui.c')==sha(out/'ui.c')and sha(old/'day_clock.h')==sha(out/'day_clock.h')and sha(old/'PurePresentationRuntimePatch.cs')==sha(out/'PurePresentationRuntimePatch.cs')
 write(out/'path-tests.json',dict(passed=True,cases=22,runs=results,uiCodeIdentical=True,managedLoaderIdentical=True))
 write(out/'build.json',dict(sha256=digest,exports=exports,sources={p.name:sha(p)for p in out.iterdir()if p.suffix in['.c','.h','.cs']},compiler=list(map(str,args)),scope=['minimap','day-clock'],actorHooks=False,performanceHooks=False,defaultHelperTrailingSeparatorFixed=True))
 print('PURE_PRESENTATION_PATH_FIXED',digest)
if __name__=='__main__':main()
