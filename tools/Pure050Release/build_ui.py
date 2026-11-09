"""Pure presentation only: wheel/camera minimap and native simulation clock."""
import re,shutil,subprocess
from context import *
def once(text,old,new):assert text.count(old)==1,old[:100];return text.replace(old,new)
def main():
 out=OUT/'ui-native-r2';out.mkdir(exist_ok=False);frozen=REPO/'outputs/ui-scout-20261109/build-r26';text=(frozen/'runtime.c').read_text();assert sha(frozen/'runtime.c')==sha(REPO/'game/ui-scout-test/runtime.c')
 # Remove all actor/AI/statistics bodies and their dispatcher installation.
 start=text.index('typedef struct {float x,y,time;U region;} ReconVisit;');end=text.index('static WNDPROC previousProc',start);text=text[:start]+text[end:]
 start=text.index('static Cooldown*clock_for(');end=text.index('static LRESULT CALLBACK window_proc',start);text=text[:start]+text[end:]
 text=text.replace('#include "dispatch.h"','');text=once(text,'#define X __declspec(dllexport)','#define X')
 text=once(text,'static float clamp(', 'void __cdecl PawPresentationFrame(void);\nvoid __cdecl PawUiTick(void);\nstatic float clamp(')
 text=once(text,'}\nstatic U FC project',' PawPresentationFrame();\n}\nstatic U FC project')
 start=text.index('static int install(void)');end=text.index('X int __cdecl K2Plugin_Start',start)
 text=text[:start]+'''static int install(void){unsigned i;static const U inverses[]={0xd5000,0xd5785,0x2a4570,0x2a47ee};static const U projections[]={0x2a43fa,0x2a4430,0x2a4466,0x2a449c};
 if(!pointer(0x500894+0xc,0x2a45de,(U)mini_update))return 1;
 for(i=0;i<4;i++)if(!call(inverses[i],0x2a42aa,(U)inverse)||!call(projections[i],0x2a495a,(U)project))return 1;
 if(!call(0x2b1ae6,0x17844b,(U)map_draw)||!commit())return 1;
 return 0;
}
'''+text[end:]
 start=text.index('X int __cdecl K2Plugin_Start');end=text.index('#ifdef PAW_QA\n#include',start)
 text=text[:start]+'''int __cdecl PawUiStart(const Host*h){U threads;if(!h||h->api!=1)return 1;host=h;base=h->exeBase;threads=P(base,0x5ef728);mainThread=P(threads,0x48);return mainThread?0:1;}
int __cdecl PawUiInstall(void){return install();}
void __cdecl PawUiUndo(void){unsigned i=writeCount;DWORD old;while(i){Write*w=&writes[--i];if(!memcmp((void*)w->at,w->after,w->size)&&VirtualProtect((void*)w->at,w->size,PAGE_EXECUTE_READWRITE,&old)){memcpy((void*)w->at,w->before,w->size);VirtualProtect((void*)w->at,w->size,old,&old);FlushInstructionCache(GetCurrentProcess(),(void*)w->at,w->size);}}}
'''+text[end:]
 start=text.index('X void __cdecl K2Plugin_Tick');end=text.index('busy=1;',start)
 text=text[:start]+'''void __cdecl PawUiTick(void){if(busy||GetCurrentThreadId()!=mainThread)return;'''+text[end:]
 assert '.marker'not in text and 'air_orders'not in text and 'classify('not in text and 'clock_for'not in text
 # QA entry points are supplied separately, never included in production.
 text=text.replace('#ifdef PAW_QA\n#include "qa.h"\n#endif','').replace('#ifdef PAW_QA\n qa_tick();\n#endif','')
 (out/'ui.c').write_text(text);header=(frozen/'day_clock.h').read_text().replace('L"sun_default"','L"sun_afternoon"');(out/'day_clock.h').write_text(header)
 # Pin the current transport architecture without importing its Find/GPU work.
 factory=(REPO/'game/presentation-runtime/runtime.c').read_text();start=factory.index('typedef void(__attribute__((fastcall))*NativeLock)');end=factory.index('__declspec(dllexport) void __cdecl PawPresentationFrame',start);factory=factory[:start]+factory[end:]
 factory=factory.replace('PawUiTick();gpu_frame();','PawUiTick();').replace(' if(PawFindStart(&host)){PawUiUndo();return 7;}\n','')
 factory=factory.replace('extern int __cdecl PawFindStart(const Host*);\n','')
 assert 'gpu_frame'not in factory and 'if(PawFindStart'not in factory
 (out/'runtime.c').write_text(factory)
 args=[TCC,'-shared','-Wall','-Werror',out/'runtime.c',out/'ui.c','-o',out/'PawsPurePresentation1372.dll','-lkernel32','-luser32'];subprocess.run(list(map(str,args)),check=True)
 import pefile
 pe=pefile.PE(str(out/'PawsPurePresentation1372.dll'));exports={x.name.decode().lstrip('_').split('@')[0]:x.address for x in pe.DIRECTORY_ENTRY_EXPORT.symbols};assert set(exports)=={'PawPresentationFrame','PawPresentationQueued'}
 # Reuse the notification-safe queued loader and paused-thread PC checks.
 managed=(REPO/'game/presentation-runtime/PresentationRuntimePatch.cs').read_text();start=managed.index('        if(ReleaseStartup.Hash(Path.Combine(root,"d3d9.dll"))');end=managed.index('        string folder=',start);managed=managed[:start]+managed[end:]
 start=managed.index('        void Guard()');end=managed.index('        void CheckThreads(',start)
 managed=managed[:start]+'''        void Guard(){game.Refresh();if(game.HasExited||game.StartTime.ToUniversalTime()!=started||U(game.MainModule.BaseAddress)!=image)throw new IOException("Fresh Pure presentation process identity changed.");}
'''+managed[end:]
 managed=once(managed,'                Write(ResourceCachePatch.StateAddress+104,BitConverter.GetBytes(module+PresentationRuntimePayload.FrameRva));','                // Native minimap update calls the view-thread frame directly.')
 managed=re.sub(r'static readonly uint\[\] CodeSites=\{[^}]+\};','static readonly uint[] CodeSites={0xd5000,0xd5785,0x2a4570,0x2a47ee,0x2a43fa,0x2a4430,0x2a4466,0x2a449c,0x2b1ae6};',managed)
 managed=managed.replace('PresentationRuntimePatch','PurePresentationRuntimePatch').replace('PresentationRuntimePayload','PurePresentationRuntimePayload').replace('PawPresentationNative','PawPurePresentationNative').replace('PawsPresentation1372.dll','PawsPurePresentation1372.dll')
 managed=re.sub(r'log\("PRESENTATION_READY[^\n]+','log("PURE_PRESENTATION_READY revision=1; minimapZoom=1..4; step=0.1; dayClock=true; noActorHooks=true");',managed)
 assert 'ResourceCache'not in managed and 'GraphicsSha256'not in managed and 'reconRevision'not in managed
 (out/'PurePresentationRuntimePatch.cs').write_text(managed)
 digest=sha(out/'PawsPurePresentation1372.dll');(out/'PurePresentationRuntimePayload.cs').write_text('internal static class PurePresentationRuntimePayload { internal const string Sha256="'+digest+'";internal const uint QueuedRva='+str(exports['PawPresentationQueued'])+'; }\n')
 write(out/'build.json',dict(sha256=digest,exports=exports,sources={p.name:sha(p)for p in out.iterdir()if p.suffix in ['.c','.h','.cs']},compiler=list(map(str,args)),scope=['minimap','day-clock'],actorHooks=False,performanceHooks=False))
 print('PURE_PRESENTATION_NATIVE_BUILT',digest)
if __name__=='__main__':main()
