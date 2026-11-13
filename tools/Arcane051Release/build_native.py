"""Compose frozen accepted prototypes behind a helper-owned product boundary."""
import argparse,hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];WS=REPO.parents[1]
LEG=Path('G:/CodexData/projects/Codex/2026-08-11/kohan-ii-d-steamlibrary-steamapps-common/work')
TCC=WS/'work/crash-20260914-continue/tools/tinycc/tcc/tcc.exe'
sys.path[:0]=[str(LEG/'pydeps_readable'),str(LEG/'lobby_colors_1372/deps_r15')]
import pefile
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def replace(s,a,b):assert s.count(a)==1,(a[:80],s.count(a));return s.replace(a,b)
def build_runtime(out):
 frozen=REPO/'outputs/ui-scout-20261109/build-r26'
 assert sha(frozen/'PawUiScoutTest.dll')=='D766DE843A8629CEE0A2BCE3362EE540E815362695CB890AD1D67649C55B25A6'
 for n in ['runtime.c','day_clock.h']:assert (frozen/n).read_bytes()==(REPO/'game/ui-scout-test'/n).read_bytes(),n
 for n in ['dispatch.h','day_clock.h']:shutil.copy2(frozen/n,out/n)
 s=(frozen/'runtime.c').read_text()
 s=s.replace('#define X __declspec(dllexport)','#define X')
 s=s.replace('K2Plugin_Start','PawUiStart').replace('K2Plugin_Tick','PawUiTick')
 start=s.index('X int __cdecl PawUiStart(');end=s.index('#ifdef PAW_QA',start)
 s=s[:start]+'''X int __cdecl PawUiStart(const Host*h){U threads;if(!h||h->api!=1)return 1;host=h;base=h->exeBase;threads=P(base,0x5ef728);mainThread=P(threads,0x48);return mainThread?0:1;}
int __cdecl PawUiInstall(void){return install();}
void __cdecl PawUiUndo(void){unsigned i=writeCount;DWORD old;while(i){Write*w=&writes[--i];if(!memcmp((void*)w->at,w->after,w->size)&&VirtualProtect((void*)w->at,w->size,PAGE_EXECUTE_READWRITE,&old)){memcpy((void*)w->at,w->before,w->size);VirtualProtect((void*)w->at,w->size,old,&old);FlushInstructionCache(GetCurrentProcess(),(void*)w->at,w->size);}}}
''' + s[end:]
 old='static int installed;wchar_t marker[MAX_PATH];if(busy||GetCurrentThreadId()!=mainThread||installed<0)return;if(!installed){swprintf(marker,L"%ls\\\\ui-scout-helper-ready.marker",host->modsDir);if(GetFileAttributesW(marker)==INVALID_FILE_ATTRIBUTES)return;installed=install()?-1:1;if(installed<0){host->log("ui-scout-test","INSTALL_REFUSED");return;}}'
 s=replace(s,old,'if(busy||GetCurrentThreadId()!=mainThread)return;')
 s=s.replace('ui-scout-test','presentation')
 assert '.marker' not in s and '#define PAW_QA' not in s
 (out/'ui.c').write_text(s)
 frozen=Path('C:/PawsFindQA-20261109/build-r3');assert sha(frozen/'PawFindLocalCache.dll')=='FC85DC096260455E7E65175114B6A55CD900C8566CBFE93968750071271224C0'
 for n in ['local_find.h','native_contract.h']:shutil.copy2(frozen/n,out/n)
 strip_comments=lambda t:re.sub(r'/\*.*?\*/','',t,flags=re.S).strip()
 assert strip_comments((frozen/'local_find.h').read_text())==strip_comments((REPO/'game/find-local-cache/local_find.h').read_text())
 s=(frozen/'plugin.c').read_text();start=s.index(' wchar_t actual[');end=s.index(' if(!lcEnabled)',start)
 s=s[:start]+''' UINT threads;BYTE*gateway;DWORD old,ignored;INT delta;
 if(!h||h->api!=1)return 1;host=h;base=h->exeBase;threads=*(UINT*)(base+0x5ef728);
 if(!readable(threads,0x4c)||(lcViewThread=*(UINT*)(threads+0x48))==0)return 1;
 lcEnabled=1;metrics=0;
''' + s[end:]
 s=replace(s,' if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(LPCSTR)lc_find,&pinned))return 1;\n','')
 start=s.index('__declspec(dllexport) int __cdecl K2Plugin_Start(')
 s=s[:start]+'''int __cdecl PawFindStart(const Host*h){return install(h);}
'''
 s=s.replace('PRIVATE_FIND_READY','FIND_READY')
 assert 'PRIVATE_ROOT' not in s and '.marker' not in s
 (out/'find.c').write_text(s);shutil.copy2(REPO/'game/presentation-runtime/runtime.c',out/'runtime.c')
 args=[str(TCC),'-shared','-Wall','-Werror',str(out/'runtime.c'),str(out/'ui.c'),str(out/'find.c'),'-o',str(out/'PawsPresentation1372.dll'),'-lkernel32','-luser32'];subprocess.run(args,check=True)
 pe=pefile.PE(str(out/'PawsPresentation1372.dll'));exports={x.name.decode().lstrip('_').split('@')[0]:x.address for x in pe.DIRECTORY_ENTRY_EXPORT.symbols};assert set(exports)=={'PawPresentationFrame','PawPresentationQueued'},exports
 (out/'runtime.json').write_text(json.dumps(dict(sha256=sha(out/'PawsPresentation1372.dll'),exports=exports,compiler=args,sources={p.name:sha(p) for p in out.iterdir() if p.suffix in ['.c','.h']}),indent=2))
 # Same callback bodies, with software-only test exports in a separate fixture.
 shutil.copy2(REPO/'game/ui-scout-test/qa.h',out/'qa.h')
 (out/'ui-qa.c').write_text((out/'ui.c').read_text().replace('#define X\n','#define X __declspec(dllexport)\n'))
 subprocess.run([str(TCC),'-shared','-DPAW_QA','-Wall','-Werror',str(out/'ui-qa.c'),'-o',str(out/'PawUiScoutQA.dll'),'-lkernel32','-luser32'],check=True)
def build_cache(out):
 native=out/'cache';native.mkdir();s=(REPO/'game/resource-cache/cache.c').read_text()
 s=replace(s,'U lastWorkMs,totalWorkMs,lastRun,phase,scanNodes,busy,complete,limitsRevision;','U lastWorkMs,totalWorkMs,lastRun,phase,scanNodes,busy,complete,limitsRevision;\n U callback,animationPolicy;')
 anchor=' U totalRam=R(manager,0x38),totalVram=R(manager,0x44);'
 s=replace(s,anchor,anchor+'\n if(R(s->image,0x5fc924)&&R(target,4)==R(s->image,0x5fc924)){ram=100;vram=100;}')
 old=' if(!s->limitsRevision&&manager&&R(manager+0x9c,0x24)&&R(s->image,0x5f9480)){\n  ((RcLockFn)(s->image+0x1b546d))(manager+0x9c,0);s->limitsRevision=1;\n }'
 new=''' if(!s->animationPolicy&&manager&&R(manager+0x9c,0x24)&&R(s->image,0x5f9480)&&R(R(s->image,0x5f9480),0x100)){
  RcMemory m;m.length=sizeof(m);
  if(((RcMemoryFn)s->memory)(&m)&&m.availableVirtual>=512ull*1024*1024&&m.availablePhysical>=384ull*1024*1024&&m.load<90){
   R(R(s->image,0x5f9480),0x100);R(R(R(s->image,0x5f9480),0x100),0)=80;
   ((RcLockFn)(s->image+0x1b546d))(manager+0x9c,0);s->animationPolicy=s->limitsRevision=1;
  }
 }'''
 new=new.replace('   R(R(s->image,0x5f9480),0x100);','   ')
 s=replace(s,old,new)
 s=replace(s,'RC_OUT void rc_tick(RcState*s){if(s->busy)return;s->busy=1;rc_tick_impl(s);s->busy=0;}','RC_OUT void rc_tick(RcState*s){if(s->busy)return;s->busy=1;rc_tick_impl(s);if(s->callback)((void(*)(void))s->callback)();s->busy=0;}')
 (native/'cache.c').write_text(s)
 # Reuse the tested ASLR/FP/GPR-preserving emitter with this explicit source.
 builder=(REPO/'game/resource-cache/build_native.py').read_text();builder=builder[:builder.index("if __name__=='__main__':")]
 builder=replace(builder,"HERE=Path(__file__).resolve().parent",'HERE=Path('+repr(str(native))+')')
 builder=replace(builder,'WS=HERE.parents[3]','WS=Path('+repr(str(WS))+')')
 script=out/'build-cache.py';script.write_text(builder+"\nif __name__=='__main__':main()\n")
 subprocess.run([sys.executable,str(script),'--out',str(out/'cache-build')],check=True)
def build_graphics(out):
 # State blocks retain implicit resource references that are not reflected in
 # the public Release count. Product builds must use native buffer ownership.
 import importlib.util
 spec=importlib.util.spec_from_file_location('native_buffers',REPO/'game/graphics-guard/build_native_buffers.py')
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 module.build(out/'graphics')

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--reuse-graphics',type=Path);a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 build_runtime(out);build_cache(out)
 if a.reuse_graphics:
  proof=json.loads((a.reuse_graphics/'product.json').read_text());assert proof['warmAlwaysDisabled'] and proof['fixtureNotShipped'] and proof.get('nativeBufferOwnership') is True and proof.get('bufferReuseRevision')==0
  assert sha(a.reuse_graphics/'d3d9.dll')==proof['sha256']
  for name,h in proof['sources'].items():assert sha(a.reuse_graphics/name)==h,name
  shutil.copytree(a.reuse_graphics,out/'graphics')
 else:build_graphics(out)
 print('PRODUCT_RUNTIME_CACHE_AND_BUFFERS_BUILT',out,flush=True)
if __name__=='__main__':main()
