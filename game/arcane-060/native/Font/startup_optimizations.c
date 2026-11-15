/* Local opt-in prototype for Kohan II 1.3.72. No disk EXE changes. */
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>
#define FC __attribute__((fastcall))
typedef struct {unsigned api;uintptr_t exeBase;const wchar_t*gameDir,*modsDir;void(__cdecl*log)(const char*,const char*,...);} Host;
static uintptr_t base;
#include "startup_memory.h"
#include "startup_trim.h"
#include "startup_tokens.h"
#include "startup_fields.h"
#include "startup_lookup.h"
__declspec(dllexport) unsigned FC PawsStartupMemory(void*s,void*d){typedef unsigned(FC*Original)(void*,void*);if(memory_try(s))return 0;return((Original)(base+0x18aef6))(s,d);}
__declspec(dllexport) unsigned FC PawsStartupTrim(void*s,void*d){return trim_line(s,d);}
__declspec(dllexport) unsigned FC PawsStartupValue(void*s,void*d,unsigned a){return token_extract(s,d,a,0);}
__declspec(dllexport) unsigned FC PawsStartupNode(void*s,void*d,unsigned a){return token_extract(s,d,a,1);}
__declspec(dllexport) unsigned FC PawsStartupFieldName(void*s,void*d,unsigned a){return field_name(s,d,a);}
__declspec(dllexport) unsigned FC PawsStartupFieldRelease(void*s,void*d){return field_release(s,d);}
__declspec(dllexport) unsigned __cdecl PawsStartupFieldHash(unsigned a){return field_hash(a);}
__declspec(dllexport) void __cdecl PawsStartupReadStats(unsigned*p){p[0]=tokensEnabled;p[1]=tokensFast[0];p[2]=tokensFast[1];p[3]=tokensFallback[0];p[4]=tokensFallback[1];p[5]=tokensCompared;p[6]=tokensMismatch;p[7]=tokenDigest;p[8]=fieldsEnabled;p[9]=fieldsNames;p[10]=fieldsCompared;p[11]=fieldsHits;p[12]=fieldsMismatch;}
__declspec(dllexport) unsigned FC PawsStartupCloneAdd(void*s,void*d,unsigned node){return lookup_clone_add(s,d,node);}
__declspec(dllexport) void __cdecl PawsStartupLookupStats(unsigned*p){unsigned i;p[0]=lookupEnabled;p[1]=lookupChecks;p[2]=lookupSkipped;p[3]=lookupCompared;p[4]=lookupMismatch;p[5]=lookupFallback;p[6]=lookupTypeCount;for(i=0;i<lookupTypeCount;i++){p[7+i*2]=lookupTypes[i];p[8+i*2]=lookupTypeCounts[i];}}
static int patch_call(unsigned rva,void*fn){DWORD old,unused;int rel=(uintptr_t)fn-base-rva-5;if(!VirtualProtect((void*)(base+rva),5,PAGE_EXECUTE_READWRITE,&old))return 0;memcpy((void*)(base+rva+1),&rel,4);VirtualProtect((void*)(base+rva),5,old,&unused);FlushInstructionCache(GetCurrentProcess(),(void*)(base+rva),5);return 1;}
static int patch_clone(void){DWORD old,unused;unsigned char code[11]={0x57,0xe8,0,0,0,0,0x90,0x90,0x90,0x90,0x90};int rel=(uintptr_t)PawsStartupCloneAdd-base-0x1b90fc-6;
 memcpy(code+2,&rel,4);if(!VirtualProtect((void*)(base+0x1b90fc),11,PAGE_EXECUTE_READWRITE,&old))return 0;memcpy((void*)(base+0x1b90fc),code,11);VirtualProtect((void*)(base+0x1b90fc),11,old,&unused);FlushInstructionCache(GetCurrentProcess(),(void*)(base+0x1b90fc),11);return 1;}
__declspec(dllexport) int __cdecl K2Plugin_Start(const Host*h){
 wchar_t marker[MAX_PATH];unsigned i,j;const unsigned sites[]={0x188df1,0x2f775d,0x1bf7e3,0x1bf871,0x1b90c1,0x1b9114,0x2ebd1,0x2ea37},targets[]={0x18aef6,0x497cd,0x1bf21d,0x1bf075,0x205de,0x21375,0x211db,0x211db};
 void*fns[]={PawsStartupMemory,PawsStartupTrim,PawsStartupValue,PawsStartupNode,PawsStartupFieldName,PawsStartupFieldRelease,PawsStartupFieldHash,PawsStartupFieldHash};
 if(!h||h->api!=1||wcslen(h->gameDir)>MAX_PATH-40)return 1;
 swprintf(marker,L"%ls\\startup-optimizations.enabled",h->gameDir);if(GetFileAttributesW(marker)==INVALID_FILE_ATTRIBUTES)return 1;
 base=h->exeBase;
 for(i=0;i<8;i++)if(*(unsigned char*)(base+sites[i])!=0xe8||sites[i]+5+*(int*)(base+sites[i]+1)!=targets[i]){h->log("startup-optimizations","GUARD_REJECT site=%x",sites[i]);return 1;}
 if(memcmp((void*)(base+0x497cd),"\x53\x56\x57\x8b\xf9\x33\xf6",7)||memcmp((void*)(base+0x4981b),"\x56\x57\x8b\x7c\x24\x0c",6))return 1;
 if(memcmp((void*)(base+0x4bef4),"\x51\x8b\x54\x24\x10\x53\x55",7)||memcmp((void*)(base+0x1bf227),"\x51\x53\x56\x8b\xf1",5))return 1;
 if(memcmp((void*)(base+0x1b90fc),"\xff\x50\x50\x50\x8b\xcf\xe8\xe5\xf7\xff\xff",11))return 1;
 if(memcmp((void*)(base+0x1b90c6),"\x8b\x03\x8b\xcf\xff\x75\x08\xc7\x45\xfc\x03\x00\x00\x00\x89\x45\xf0\xe8\x26\x4c\xe9\xff\x84\xc0\x75\x27\x38\x45\x0c\x74\x12\xf6\x47\x20\x01\x75\x0c\x8b\x4d\xf0\x8b\x01\xff\x50\x4c\x84\xc0\x75\x4e\x8b\x4d\xf0\x8b\x01",54))return 1;
 trim_init();tokens_init();fields_init();lookup_init();
 for(i=0;i<8;i++)if(!patch_call(sites[i],fns[i])){for(j=0;j<i;j++)if(!patch_call(sites[j],(void*)(base+targets[j])))h->log("startup-optimizations","ROLLBACK_FAILED site=%x",sites[j]);return 1;}
 if((lookupEnabled||lookupDiagnostic)&&!patch_clone()){for(j=0;j<8;j++)if(!patch_call(sites[j],(void*)(base+targets[j])))h->log("startup-optimizations","ROLLBACK_FAILED site=%x",sites[j]);return 1;}
 h->log("startup-optimizations","READY stage4; memory/trim/tokens/fields/lookup require explicit per-process opt-in; no file patches");return 0;
}
