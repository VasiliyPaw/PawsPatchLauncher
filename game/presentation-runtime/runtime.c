/* Helper-owned product runtime. Installation is queued while the verified
 * fresh game's threads are suspended. Only its native VIEW frame ticks UI/GPU.
 * No private loader, laboratory markers, observer or network automation. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <string.h>
#include <wchar.h>
typedef uintptr_t U;
typedef struct {UINT api;U exeBase;const wchar_t*gameDir,*modsDir;void(__cdecl*log)(const char*,const char*,...);} Host;
typedef struct {UINT api,image,viewThread,magic;wchar_t gameDir[260],modsDir[260];} Config;
typedef struct {volatile LONG go,phase;UINT result;Config config;} Request;
extern int __cdecl PawUiStart(const Host*);
extern int __cdecl PawUiInstall(void);
extern void __cdecl PawUiUndo(void);
extern void __cdecl PawUiTick(void);
extern int __cdecl PawFindStart(const Host*);
static Host host;
static Config config;
static UINT ready,frames,busy;
static void __cdecl log_quiet(const char*group,const char*format,...){(void)group;(void)format;}
static int readable(U p,UINT n){MEMORY_BASIC_INFORMATION m;return p&&p+n>=p&&VirtualQuery((void*)p,&m,sizeof(m))&&m.State==MEM_COMMIT&&!(m.Protect&(PAGE_GUARD|PAGE_NOACCESS))&&p+n<=(U)m.BaseAddress+m.RegionSize;}
typedef void(__attribute__((fastcall))*NativeLock)(U,U);
typedef void(WINAPI*GpuTick)(UINT,UINT,UINT,UINT);
static void gpu_frame(void){
 static GpuTick tick;
 U renderer,mutex,simulation;UINT phase,world,paused=0;
 if(!tick){HMODULE d=GetModuleHandleW(L"d3d9.dll");if(d)tick=(GpuTick)GetProcAddress(d,"PawGpuTick");}
 if(!tick)return;
 renderer=*(U*)(config.image+0x5f3f98);if(!readable(renderer,0x44)||!*(U*)(renderer+0x40))return;
 mutex=renderer+0x18;phase=*(UINT*)(config.image+0x5f92f4);world=*(UINT*)(config.image+0x5f3fb8);simulation=*(U*)(config.image+0x5f3fe8);
 if(readable(simulation,0x29))paused=*(BYTE*)(simulation+0x28);
 ((NativeLock)*(U*)(*(U*)mutex+4))(mutex,0);
 tick(world,phase,paused,0);
 ((NativeLock)*(U*)(*(U*)mutex+8))(mutex,0);
}
__declspec(dllexport) void __cdecl PawPresentationFrame(void){
 if(!ready||busy||GetCurrentThreadId()!=config.viewThread)return;
 busy=1;frames++;PawUiTick();gpu_frame();busy=0;
}
static UINT validate(const Config*c){
 wchar_t actual[260],expected[260],*slash;U threads;UINT length;
 if(ready||c->api!=1||c->magic!=0x50574150||c->image!=(U)GetModuleHandleW(NULL)||!c->viewThread)return 1;
 if(!GetModuleFileNameW(NULL,actual,260)||(slash=wcsrchr(actual,L'\\'))==NULL)return 2;
 *slash=0;if(c->gameDir[259]||c->modsDir[259])return 3;
 lstrcpynW(expected,c->gameDir,260);length=lstrlenW(expected);
 while(length&&(expected[length-1]==L'\\'||expected[length-1]==L'/'))expected[--length]=0;
 if(lstrcmpiW(actual,expected))return 3;
 threads=*(U*)(c->image+0x5ef728);if(!readable(threads,0x4c)||*(UINT*)(threads+0x48)!=c->viewThread)return 4;
 if(*(UINT*)(c->image+0x5f92f4)==4||*(UINT*)(c->image+0x5f92f4)==6)return 5;
 return 0;
}
static UINT install(const Config*c){
 config=*c;host.api=1;host.exeBase=c->image;host.gameDir=config.gameDir;host.modsDir=config.modsDir;host.log=log_quiet;
 if(PawUiStart(&host)||PawUiInstall())return 6;
 if(PawFindStart(&host)){PawUiUndo();return 7;}
 ready=1;return 0;
}
__declspec(dllexport) DWORD WINAPI PawPresentationQueued(void*arg){
 Request*r=arg;HMODULE pinned=NULL;
 /* Finish loader work before the helper suspends any original thread. */
 if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(LPCSTR)PawPresentationFrame,&pinned)){r->result=8;r->phase=2;return 8;}
 r->result=validate(&r->config);if(r->result){r->phase=2;return r->result;}
 r->phase=1;while(!r->go)Sleep(1);
 r->result=install(&r->config);r->phase=2;
 return 0; /* Never touch r again: the helper can now release its request. */
}
BOOL WINAPI DllMain(HINSTANCE h,DWORD reason,void*unused){(void)unused;if(reason==DLL_PROCESS_ATTACH)DisableThreadLibraryCalls(h);return TRUE;}
