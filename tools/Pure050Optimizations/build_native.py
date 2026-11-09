"""Pure UI + exact accepted generic Find/cache/graphics production code."""
import shutil,subprocess
from context import *
def main():
 frozen=OUT/'frozen'
 for n,h in read(OUT/'baseline.json')['frozen'].items():assert sha(frozen/n)==h,n
 out=OUT/'native-r1';out.mkdir(exist_ok=False);pure=frozen/'pure-ui';arcane=frozen/'arcane-native'
 s=(pure/'ui.c').read_text();s=once(s,'void __cdecl PawPresentationFrame(void);\n','');s=once(s,' PawPresentationFrame();\n','')
 assert 'PawPresentationFrame'not in s and 'air_orders'not in s and 'classify('not in s
 (out/'ui.c').write_text(s);shutil.copy2(pure/'day_clock.h',out/'day_clock.h')
 for n in ['runtime.c','find.c','local_find.h','native_contract.h']:shutil.copy2(arcane/n,out/n)
 assert 'sun_afternoon'in(out/'day_clock.h').read_text() and 'PawFindStart'in(out/'runtime.c').read_text()
 args=[TCC,'-shared','-Wall','-Werror',out/'runtime.c',out/'ui.c',out/'find.c','-o',out/'PawsPurePresentation1372.dll','-lkernel32','-luser32'];subprocess.run(list(map(str,args)),check=True)
 import pefile
 exports={e.name.decode().lstrip('_').split('@')[0]:e.address for e in pefile.PE(str(out/'PawsPurePresentation1372.dll')).DIRECTORY_ENTRY_EXPORT.symbols}
 assert set(exports)=={'PawPresentationFrame','PawPresentationQueued'}
 for folder in ['cache','cache-build','graphics']:shutil.copytree(arcane/folder,out/folder)
 assert sha(out/'graphics/d3d9.dll')==read(out/'graphics/product.json')['sha256']
 write(out/'build.json',dict(sha256=sha(out/'PawsPurePresentation1372.dll'),exports=exports,sources={p.name:sha(p)for p in out.iterdir()if p.suffix in['.c','.h']},compiler=list(map(str,args)),arcaneUiImported=False,actorHooks=False,frameSource='ResourceCache callback at state+104; no extra minimap callback',resourcePayloadSha256=sha(out/'cache-build/payload.bin'),graphicsSha256=sha(out/'graphics/d3d9.dll')))
 print('PURE_OPTIMIZED_NATIVE_BUILT',sha(out/'PawsPurePresentation1372.dll'))
if __name__=='__main__':main()
