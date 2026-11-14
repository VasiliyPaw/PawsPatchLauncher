/* Owned graphics QA only. Select a copied save with the native host order. */
#include <windows.h>
#include <stdint.h>
#include <string.h>
#include <wchar.h>
typedef uintptr_t U;
typedef struct{UINT api;U exeBase;const wchar_t*gameDir,*modsDir;void(__cdecl*log)(const char*,const char*,...);}Host;
typedef void(__attribute__((fastcall))*StringFn)(wchar_t**,void*,const wchar_t*);
typedef void(__attribute__((fastcall))*CtorFn)(void*,void*,wchar_t**);
typedef void(__attribute__((fastcall))*IssueFn)(void*,void*,int);
typedef void(__attribute__((fastcall))*ReleaseFn)(void*,void*);
static const Host*host;static U base;static DWORD thread;static int done;
__declspec(dllexport) int __cdecl K2Plugin_Start(const Host*h){
 if(!h||h->api!=1||wcscmp(h->gameDir,L"G:\\PawGraphicsQA-20261113\\game"))return 1;
 host=h;base=h->exeBase;thread=GetCurrentThreadId();return 0;
}
__declspec(dllexport) void __cdecl K2Plugin_Tick(void){
 U session;wchar_t*text=0;struct{U vtable;wchar_t*name;}order={0,0};wchar_t marker[260];
 if(done||GetCurrentThreadId()!=thread)return;session=*(U*)(base+0x5f3fe4);
 if(!session||*(U*)(session+0xf0)!=1)return;
 swprintf(marker,L"%ls\\select-heavy.flag",host->modsDir);if(GetFileAttributesW(marker)==INVALID_FILE_ATTRIBUTES)return;
 done=1;((StringFn)(base+0x205de))(&text,0,L"Save/QA-expanded-heavy.RSG");if(!text)return;
 ((CtorFn)(base+0x121bd0))(&order,0,&text);((IssueFn)(base+0x122822))(&order,0,0);
 if(order.name)((ReleaseFn)(base+0x21375))((char*)order.name-16,0);
 ((ReleaseFn)(base+0x21375))((char*)text-16,0);host->log("expanded-cache-qa","COPIED_SAVE_SELECTED native host order");
}
