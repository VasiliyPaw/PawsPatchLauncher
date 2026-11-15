/* The player setting CameraScaleZoom includes the engine's +0.1 offset.
 * Cap that setting at 2.0 (native distance scale 1.9), including loaded views. */
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>
#define U unsigned
#define P(a,o) (*(U*)((uintptr_t)(a)+(o)))
#define F(a,o) (*(float*)((uintptr_t)(a)+(o)))
typedef struct{U api;uintptr_t exeBase;const wchar_t*gameDir,*modsDir;void(__cdecl*log)(const char*,const char*,...);}Host;
static const Host*host;static U base,installed,updates,lastCamera;
#define MAX_DISTANCE 1.9f
typedef U(__attribute__((fastcall))*NativeZoom)(U,U,U);
static int readable(U a,U n){MEMORY_BASIC_INFORMATION m;return a&&VirtualQuery((void*)a,&m,sizeof(m))&&m.State==MEM_COMMIT&&!(m.Protect&(PAGE_NOACCESS|PAGE_GUARD))&&a+n<=(U)m.BaseAddress+m.RegionSize;}
static int __cdecl apply(U camera){U p;if(!P(base,0x5f3fb8)||!(p=P(base,0x5fafe0))||camera!=P(p,0)||P(camera,0)!=base+0x4c385c)return 0;
 if(!(F(camera,0x20c)>=.1f&&F(camera,0x20c)<=1)||!(F(camera,0x210)>1&&F(camera,0x210)<=16))return 0;
 F(camera,0x210)=MAX_DISTANCE;if(F(camera,0x14c)==512)F(camera,0x14c)=1024;updates++;lastCamera=camera;return 1;
}
static void __cdecl render_limit(U camera){U value;if(!apply(camera)||!(F(camera,0x208)>MAX_DISTANCE))return;
 {float maximum=MAX_DISTANCE;memcpy(&value,&maximum,4);}((NativeZoom)(base+0x174a3c))(camera,0,value);
}
#include "range_stub.h"
__declspec(dllexport)int __cdecl K2Plugin_Start(const Host*h){if(!h||h->api!=1)return 1;host=h;base=h->exeBase;return 0;}
__declspec(dllexport)void __cdecl K2Plugin_Tick(void){U site=base+0x175d2d,render=base+0x1738ce,previous,stub;DWORD old,renderOld,tmp;unsigned char code[8];FILE*f;wchar_t path[MAX_PATH];if(installed)return;
 if(*(unsigned char*)site!=0xe9)return;previous=site+5+P(site,1);if(!readable(previous,3)||memcmp((void*)previous,"\x9c\x81\x3f",3))return;
 if(*(unsigned char*)render!=0xb8||P(render,1)!=base+0x432705){installed=2;host->log("camera-range","RENDER GUARD REFUSED");return;}
 stub=(U)VirtualAlloc(0,256,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);if(!stub)return;memcpy((void*)stub,range_stub,sizeof(range_stub));P(stub,RANGE_APPLY)=(U)apply-(stub+RANGE_APPLY+4);P(stub,RANGE_TAIL)=previous-(stub+RANGE_TAIL+4);
 P(stub,RENDER_APPLY)=(U)render_limit-(stub+RENDER_APPLY+4);P(stub,RENDER_TAIL)=stub+160-(stub+RENDER_TAIL+4);memcpy((void*)(stub+160),(void*)render,5);*(unsigned char*)(stub+165)=0xe9;P(stub,166)=render+5-(stub+170);
 if(!VirtualProtect((void*)site,8,PAGE_EXECUTE_READWRITE,&old)){VirtualFree((void*)stub,0,MEM_RELEASE);return;}
 if(!VirtualProtect((void*)render,5,PAGE_EXECUTE_READWRITE,&renderOld)){VirtualProtect((void*)site,8,old,&tmp);VirtualFree((void*)stub,0,MEM_RELEASE);return;}
 memset(code,0x90,8);code[0]=0xe9;P(code,1)=stub-site-5;memcpy((void*)site,code,8);P(code,1)=stub+64-render-5;memcpy((void*)render,code,5);FlushInstructionCache(GetCurrentProcess(),(void*)site,8);FlushInstructionCache(GetCurrentProcess(),(void*)render,5);VirtualProtect((void*)render,5,renderOld,&tmp);VirtualProtect((void*)site,8,old,&tmp);installed=1;
 swprintf(path,L"%ls\\Mods\\camera-range-state.txt",host->gameDir);f=_wfopen(path,L"w");if(f){fprintf(f,"%u %u\n",(U)&updates,(U)&lastCamera);fclose(f);}host->log("camera-range","READY player setting cap 2.0; native distance cap 1.9; saved views and wheel bounded");
}
