/* Kohan II 1.3.72: capture knowledge follows observation. The former
 * owner, new owner and kingdoms seeing the building BEFORE ChangeKingdom
 * learn the new owner. Other players retain their last observed ownership.
 * Only existing ownership records are refreshed; native fog stays intact. */
#include <windows.h>
#include <stdint.h>
#include <string.h>
#include <wchar.h>
#define U unsigned
#define P(a,o) (*(U*)((uintptr_t)(a)+(o)))
#define FC __attribute__((fastcall))
typedef U(FC*ChangeFn)(U,U,U);
typedef U(FC*RememberFn)(U,U,U,U);
typedef U(FC*VisibleFn)(U,U,U,U);
typedef struct {U api;uintptr_t exeBase;const wchar_t*gameDir,*modsDir;void(__cdecl*log)(const char*,const char*,...);} Host;
static const Host*host;static U image,installed;static ChangeFn original;
static int readable(U a,U n){MEMORY_BASIC_INFORMATION m;return a&&a+n>=a&&VirtualQuery((void*)a,&m,sizeof(m))&&m.State==MEM_COMMIT&&!(m.Protect&(PAGE_GUARD|PAGE_NOACCESS))&&a+n<=(U)m.BaseAddress+m.RegionSize;}
static U FC change(U a,U unused,U next){
 U old=P(a,0xe8),id=P(a,0x14),building=P(a,0x94)||P(a,0x98),result,registry;
 U informed[32],n=0,world,list,count,i;
 if(building&&old!=next&&next){
  world=P(image,0x5f3fb8);
  if(world){list=P(world,0x150);count=P(world,0x154);
   if(list&&count<=96)for(i=0;i<count&&n<32;i++){U k=P(list,i*4);
    if(k&&!P(k,0x198)&&P(k,0x194)<32&&
       (k==old||k==next||(((VisibleFn)P(P(a,0),0x70))(a,0,k,1)&255)))
     informed[n++]=k;
   }
  }
 }
 result=original(a,0,next);
 if(!n)return result;
 registry=P(image,0x5ef72c);
 /* Native ChangeKingdom may destroy a duplicate recruit. Resolve the saved
  * ID before dereferencing the returned actor. Locals also survive recursion. */
 if(!registry||((ChangeFn)(image+0x21117))(registry,0,id)!=a||!readable(a,0xec)||P(a,0x14)!=id||(P(a,8)&3)||P(a,0xe8)!=next)return result;
 for(i=0;i<n;i++)((RememberFn)(image+0x23bcc1))(a,0,informed[i],1);
 return result;
}
static int patch(U at,const unsigned char*bytes){DWORD old,tmp;if(!VirtualProtect((void*)at,5,PAGE_EXECUTE_READWRITE,&old))return 0;memcpy((void*)at,bytes,5);FlushInstructionCache(GetCurrentProcess(),(void*)at,5);VirtualProtect((void*)at,5,old,&tmp);return !memcmp((void*)at,bytes,5);}
static int install(void){U at=image+0x228b6c;unsigned char expected[10],jump[5],*trampoline;DWORD old;
 expected[0]=0xb8;P(expected,1)=image+0x43d60f;expected[5]=0xe8;P(expected,6)=0x3e15dc-(0x228b6c+10);
 if(memcmp((void*)at,expected,10)){host->log("capture-knowledge","guard rejected ChangeKingdom");return 0;}
 trampoline=VirtualAlloc(0,16,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);if(!trampoline)return 0;
 memcpy(trampoline,expected,5);trampoline[5]=0xe9;P(trampoline,6)=at+5-(U)(trampoline+10);
 if(!VirtualProtect(trampoline,16,PAGE_EXECUTE_READ,&old)){VirtualFree(trampoline,0,MEM_RELEASE);return 0;}
 FlushInstructionCache(GetCurrentProcess(),trampoline,16);original=(ChangeFn)trampoline;jump[0]=0xe9;P(jump,1)=(U)change-at-5;
 if(!patch(at,jump)){if(patch(at,expected)){original=0;VirtualFree(trampoline,0,MEM_RELEASE);}return 0;}
 host->log("capture-knowledge","READY observed capture knowledge; former/new owner and pre-change viewers; native fog unchanged");return 1;
}
__declspec(dllexport)int __cdecl K2Plugin_Start(const Host*h){wchar_t marker[MAX_PATH];
 if(!h||h->api!=1||wcslen(h->gameDir)>MAX_PATH-40)return 1;swprintf(marker,L"%ls\\paws_runtime.marker",h->gameDir);
 if(GetFileAttributesW(marker)==INVALID_FILE_ATTRIBUTES)return 1;host=h;image=h->exeBase;return 0;
}
__declspec(dllexport)void __cdecl K2Plugin_Tick(void){if(!installed)installed=install()?1:2;}
#ifdef CAPTURE_KNOWLEDGE_TEST
__declspec(dllexport)U __cdecl TestChange(U a,U next){return change(a,0,next);}
__declspec(dllexport)void __cdecl TestBind(U base,U fn){image=base;original=(ChangeFn)fn;}
#endif
