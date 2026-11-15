
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>
#define FC __attribute__((fastcall))
typedef struct {unsigned api;uintptr_t exeBase;const wchar_t*gameDir,*modsDir;void(__cdecl*log)(const char*,const char*,...);} Host;
static uintptr_t base;static DWORD thread;static wchar_t trace[MAX_PATH];
#include "font_metrics_cache.h"
typedef unsigned(FC*Stage0)(void*,void*);
typedef unsigned(FC*Stage1)(void*,void*,unsigned);
static unsigned FC setup(void*s,void*d){unsigned r;fmc_begin();r=((Stage0)(base+0x183972))(s,d);fmc_end();return r;}
static unsigned FC onefont(void*s,void*d,unsigned x){fmc_font_begin(s);return((Stage1)(base+0x1815d9))(s,d,x);}
__declspec(dllexport) int __cdecl K2Plugin_Start(const Host*h){
 unsigned i,j;DWORD protections[5],unused;int rel;
 const unsigned sites[]={0x18197e,0x1819fc,0x1821c3,0x1825f6,0x183a51},targets[]={0x181dfc,0x181dfc,0x184432,0x183972,0x1815d9};
 void*fn[]={fmc_glyphs,fmc_glyphs,fmc_measure,setup,onefont};char key[65];
 if(!h||h->api!=1||wcslen(h->modsDir)>MAX_PATH-30||GetEnvironmentVariableA("PAWS_FONT_CACHE_KEY",key,65)!=64)return 1;
 base=h->exeBase;thread=GetCurrentThreadId();swprintf(trace,L"%ls\\font-cache-status.jsonl",h->modsDir);
 for(i=0;i<5;i++)if(*(unsigned char*)(base+sites[i])!=0xe8||sites[i]+5+*(int*)(base+sites[i]+1)!=targets[i]){h->log("font-metrics","GUARD_REJECT %x",sites[i]);return 1;}
 for(i=0;i<5;i++)if(!VirtualProtect((void*)(base+sites[i]),5,PAGE_EXECUTE_READWRITE,&protections[i])){
  for(j=i;j>0;j--)VirtualProtect((void*)(base+sites[j-1]),5,protections[j-1],&unused);return 1;
 }
 for(i=0;i<5;i++){rel=(uintptr_t)fn[i]-base-sites[i]-5;memcpy((void*)(base+sites[i]+1),&rel,4);}
 for(i=5;i>0;i--)VirtualProtect((void*)(base+sites[i-1]),5,protections[i-1],&unused);
 FlushInstructionCache(GetCurrentProcess(),0,0);h->log("font-metrics","READY native metrics only, automatic record/replay; no QA window/quit/input hooks");return 0;
}
