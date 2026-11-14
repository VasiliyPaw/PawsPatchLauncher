/* Owned executable only: real native UI installation into fake engine pages.
 * Never opens or writes another process. Seeds only documented patch guards. */
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>
typedef struct {UINT api,image,viewThread,magic;wchar_t gameDir[260],modsDir[260];}Config;
typedef struct {volatile LONG go,phase;UINT result;Config config;}Request;
typedef DWORD(WINAPI*Queue)(void*);
static UINT image;
static void pointer(UINT site,UINT target){*(UINT*)(uintptr_t)(image+site)=image+target;}
static void call(UINT site,UINT target){BYTE*p=(BYTE*)(uintptr_t)(image+site);p[0]=0xe8;*(UINT*)(p+1)=target-site-5;}
int main(int argc,char**argv){
 HMODULE dll;Queue queue;Request r;UINT*manager,i;wchar_t*slash;
 const UINT inverses[]={0xd5000,0xd5785,0x2a4570,0x2a47ee},projections[]={0x2a43fa,0x2a4430,0x2a4466,0x2a449c},stats[]={0x206917,0x2069d2,0x22a8c1,0x22ebf0,0x25e75c};
 if(argc!=3)return 90;image=(UINT)(uintptr_t)GetModuleHandleW(NULL);
 /* High fixture base avoids the Win32 low heap; this range excludes its PE. */
 if(!VirtualAlloc((void*)(uintptr_t)(image+0x10000),0x6f0000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE))return 91;
 dll=LoadLibraryA(argv[1]);if(!dll)return 92;
 queue=(Queue)GetProcAddress(dll,"PawPresentationQueued");if(!queue)queue=(Queue)GetProcAddress(dll,"_PawPresentationQueued@4");if(!queue)return 93;
 manager=VirtualAlloc(NULL,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);if(!manager)return 94;
 pointer(0x5ef728,(UINT)(uintptr_t)manager-image);manager[0x48/4]=GetCurrentThreadId();
 memset(&r,0,sizeof(r));r.go=1;r.config.api=1;r.config.image=image;r.config.viewThread=GetCurrentThreadId();r.config.magic=0x50574150;
 GetModuleFileNameW(NULL,r.config.gameDir,260);slash=wcsrchr(r.config.gameDir,L'\\');if(!slash)return 95;*slash=0;lstrcpyW(r.config.modsDir,r.config.gameDir);
 /* Original Find code is a canary. Only the deleted optimization used it. */
 memset((void*)(uintptr_t)(image+0x18e3c8),0xa7,32);
 pointer(0x500894+0xc,0x2a45de);
 for(i=0;i<4;i++){call(inverses[i],0x2a42aa);call(projections[i],0x2a495a);}
 call(0x2b1ae6,0x17844b);
 if(!strcmp(argv[2],"arcane")){
  BYTE*p=(BYTE*)(uintptr_t)(image+0x5cee6);p[0]=0xb8;*(UINT*)(p+1)=image+0x4191f5;
  pointer(0x4d79e8+0x58,0x1d3d29);pointer(0x4d79e8+0x78,0x1d4094);
  for(i=0;i<5;i++)call(stats[i],0x25e971);
 }
 queue(&r);if(r.phase!=2||r.result){printf("INSTALL_FAIL phase=%u result=%u\n",(unsigned)r.phase,r.result);return 1;}
 for(i=0;i<32;i++)if(*(BYTE*)(uintptr_t)(image+0x18e3c8+i)!=0xa7)return 2;
 if(*(UINT*)(uintptr_t)(image+0x500894+0xc)==image+0x2a45de)return 3;
 if(*(BYTE*)(uintptr_t)(image+0x2b1ae6)!=0xe8)return 4;
 printf("NATIVE_INSTALL_FIXTURE_PASS %s; UI installed, Find untouched; owned process only\n",argv[2]);return 0;
}
