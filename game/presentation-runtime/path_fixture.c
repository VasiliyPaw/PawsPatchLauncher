/* Owned Win32 executable: real queued validator, fake engine guard pages.
 * The validator must accept equivalent game roots, then decline at the first
 * intentionally absent engine prologue (result6), never patching a game. */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <wchar.h>
typedef struct {UINT api,image,viewThread,magic;wchar_t gameDir[260],modsDir[260];}Config;
typedef struct {volatile LONG go,phase;UINT result;Config config;}Request;
typedef DWORD(WINAPI*Queue)(void*);
static UINT run(Queue queue,Config*c){Request r;memset(&r,0,sizeof(r));r.go=1;r.config=*c;queue(&r);if(r.phase!=2)return 99;return r.result;}
int main(int argc,char**argv){
 HMODULE dll;Queue queue;Config c,base;wchar_t exe[260],*slash;UINT image=(UINT)(uintptr_t)GetModuleHandleW(NULL),*manager;unsigned checks=0,value;void*pages,*code;
 if(argc!=3)return 90;dll=LoadLibraryA(argv[1]);if(!dll)return 91;
 queue=(Queue)GetProcAddress(dll,"PawPresentationQueued");if(!queue)queue=(Queue)GetProcAddress(dll,"_PawPresentationQueued@4");if(!queue)return 92;
 pages=VirtualAlloc((void*)(uintptr_t)(image+0x5e0000),0x20000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
 code=VirtualAlloc((void*)(uintptr_t)(image+0x50000),0x10000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
 manager=VirtualAlloc(NULL,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);if(!pages||!code||!manager)return 93;
 *(UINT*)(uintptr_t)(image+0x5ef728)=(UINT)(uintptr_t)manager;manager[0x48/4]=GetCurrentThreadId();
 memset(&c,0,sizeof(c));c.api=1;c.image=image;c.viewThread=GetCurrentThreadId();c.magic=0x50574150;
 GetModuleFileNameW(NULL,exe,260);slash=wcsrchr(exe,L'\\');if(!slash)return 94;*slash=0;lstrcpyW(c.gameDir,exe);swprintf(c.modsDir,L"%ls\\Mods",exe);base=c;
#define CHECK(expected,label) value=run(queue,&c);if(value!=(expected)){printf("PATH_FIXTURE_FAIL %s got=%u expected=%u\n",label,value,(unsigned)(expected));return 1;}checks++
 CHECK(6,"normal root reaches exact engine guard");
 lstrcatW(c.gameDir,L"\\");CHECK(atoi(argv[2])?6:3,"helper default trailing separator");
 c=base;lstrcatW(c.gameDir,L"\\\\");CHECK(atoi(argv[2])?6:3,"repeated trailing separators");
 c=base;CharUpperBuffW(c.gameDir,lstrlenW(c.gameDir));CHECK(6,"case-equivalent root");
 c=base;lstrcatW(c.gameDir,L"-other");CHECK(3,"different root rejected");
 c=base;c.api=0;CHECK(1,"API rejected");c=base;c.magic=0;CHECK(1,"contract rejected");
 c=base;c.image+=0x10000;CHECK(1,"other image rejected");c=base;c.viewThread++;CHECK(4,"other VIEW rejected");
 c=base;*(UINT*)(uintptr_t)(image+0x5f92f4)=4;CHECK(5,"active match rejected");
 *(UINT*)(uintptr_t)(image+0x5f92f4)=6;CHECK(5,"loading match rejected");
 printf("PRODUCT_PATH_WIN32_FIXTURE_PASS %u; fixed=%s; validator reached then exact native guard declined\n",checks,argv[2]);return 0;
}
