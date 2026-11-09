/* Standalone private proof build. No game networking or frame timing. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>
#define FC __attribute__((fastcall))
typedef struct{UINT api;uintptr_t exeBase;const wchar_t*gameDir,*modsDir;void(__cdecl*log)(const char*,const char*,...);}Host;
static uintptr_t base;static const Host*host;static UINT ready,declined,metrics;static DWORD lastFlush;
#include "local_find.h"
#include "native_contract.h"
static int readable(uintptr_t p,UINT n){MEMORY_BASIC_INFORMATION m;return p&&VirtualQuery((void*)p,&m,sizeof(m))&&m.State==MEM_COMMIT&&!(m.Protect&(PAGE_GUARD|PAGE_NOACCESS))&&p+n<=(uintptr_t)m.BaseAddress+m.RegionSize;}
static int install(const Host*h){
 wchar_t actual[MAX_PATH],env[MAX_PATH],expected[MAX_PATH],marker[MAX_PATH],*slash;char mode[16]={0};UINT threads;BYTE*gateway;DWORD old,ignored;INT delta;HMODULE pinned=NULL;
 if(!h||h->api!=1||!GetEnvironmentVariableW(L"PAWS_FIND_PRIVATE_ROOT",env,MAX_PATH))return 1;
 if(!GetModuleFileNameW(NULL,actual,MAX_PATH)||!GetFullPathNameW(env,MAX_PATH,expected,NULL))return 1;slash=wcsrchr(actual,L'\\');if(!slash)return 1;*slash=0;
 if(lstrcmpiW(actual,expected)||wcslen(actual)>MAX_PATH-48)return 1;swprintf(marker,L"%ls\\find-local-cache-test.marker",actual);if(GetFileAttributesW(marker)==INVALID_FILE_ATTRIBUTES)return 1;
 host=h;base=h->exeBase;threads=*(UINT*)(base+0x5ef728);if(!readable(threads,0x4c)||*(UINT*)(threads+0x48)!=GetCurrentThreadId())return 2;
 lcViewThread=GetCurrentThreadId();GetEnvironmentVariableA("PAWS_FIND_LOCAL_CACHE",mode,sizeof(mode));lcEnabled=atoi(mode)==1;mode[0]=0;GetEnvironmentVariableA("PAWS_FIND_METRICS",mode,sizeof(mode));metrics=atoi(mode)==1;
 if(!lcEnabled){ready=1;host->log("find-local","PRIVATE_FIND_READY mode=0; native Find entry unchanged");return 0;}
 lc_rebase_contract();
 if(!lc_contract_matches())return 1;
 gateway=VirtualAlloc(NULL,64,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);if(!gateway)return 1;memcpy(gateway,(void*)(base+0x18e3c8),5);gateway[5]=0xe9;delta=base+0x18e3cd-(uintptr_t)(gateway+10);memcpy(gateway+6,&delta,4);
 if(!VirtualProtect(gateway,64,PAGE_EXECUTE_READ,&ignored))return 1;FlushInstructionCache(GetCurrentProcess(),gateway,10);lcNativeFind=(LcFind)gateway;lcNativePredicate=(LcPredicate)(base+0x18de9d);
 if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(LPCSTR)lc_find,&pinned))return 1;
 if(!VirtualProtect((void*)(base+0x18e3c8),5,PAGE_EXECUTE_READWRITE,&old))return 1;*(BYTE*)(base+0x18e3c8)=0xe9;delta=(uintptr_t)lc_find-base-0x18e3cd;memcpy((void*)(base+0x18e3c9),&delta,4);VirtualProtect((void*)(base+0x18e3c8),5,old,&ignored);FlushInstructionCache(GetCurrentProcess(),(void*)(base+0x18e3c8),5);
 ready=1;host->log("find-local","PRIVATE_FIND_READY mode=1; per-call eligibility, original order/allocation/key writes; no index");return 0;
}
__declspec(dllexport) int __cdecl K2Plugin_Start(const Host*h){int r=install(h);if(r==2){h->log("find-local","PRIVATE_FIND_WAITING_FOR_VIEW");return 0;}return r;}
__declspec(dllexport) void __cdecl K2Plugin_Tick(void){if(host&&!ready&&!declined){int r=install(host);if(r==1){declined=1;host->log("find-local","PRIVATE_FIND_DECLINED");}}if(ready&&metrics&&GetCurrentThreadId()==lcViewThread&&GetTickCount()-lastFlush>1000){wchar_t p[MAX_PATH];FILE*f;lastFlush=GetTickCount();swprintf(p,L"%ls\\find-local.jsonl",host->modsDir);f=_wfopen(p,L"a");if(f){fprintf(f,"{\"ms\":%u,\"mode\":%u,\"calls\":%llu,\"eligible\":%llu,\"skipped\":%llu,\"fallback\":%llu,\"predicates\":%llu,\"stopped\":%llu}\n",lastFlush,lcEnabled,lcCalls,lcEligible,lcSkipped,lcFallback,lcPredicates,lcStopped);fclose(f);}}}
__declspec(dllexport) void __cdecl K2Plugin_Stop(void){}
BOOL WINAPI DllMain(HINSTANCE h,DWORD reason,void*p){if(reason==DLL_PROCESS_ATTACH)DisableThreadLibraryCalls(h);return TRUE;}
