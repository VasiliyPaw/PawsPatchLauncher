/* Visual cache only: original world tiles, height, flags, native variation
 * definitions, saved IDs and terrain rules are never modified. */
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <wchar.h>
#include <string.h>
#define U unsigned
#define P(a,o) (*(U*)((U)(a)+(o)))
#define F(a,o) (*(float*)((U)(a)+(o)))
#define FC __attribute__((fastcall))
typedef struct{U api;uintptr_t exeBase;const wchar_t*gameDir,*modsDir;void(__cdecl*log)(const char*,const char*,...);}Host;
typedef U(FC*M0)(U,U);typedef U(FC*M1)(U,U,U);typedef U(FC*M2)(U,U,U,U);
#include "biome_sources.h"
#include "wide_stub.h"
static const Host*host;static U base,installed,worldSeen,tilesSeen,width,height,cloneCount,changed,blocks;
static unsigned char*recipes;static U*integrals;
typedef struct {U original,target,step;unsigned char definition[0x44];}Clone;
static Clone clones[65536];
static U prewarmEnabled=1,prewarmed;static void prewarm_land(U map);
#include "prewarm_budget.h"
#include "recipe_cache.h"
static RecipeCacheEntry variantCache[131072],definitionCache[2048];
static int readable(U a,U n){MEMORY_BASIC_INFORMATION m;return a&&a+n>=a&&VirtualQuery((void*)a,&m,sizeof(m))&&m.State==MEM_COMMIT&&!(m.Protect&(PAGE_NOACCESS|PAGE_GUARD))&&a+n<=(U)m.BaseAddress+m.RegionSize;}
static int slot(U def){const wchar_t*s=def?(wchar_t*)P(def,8):0;if(!s)return -1;if(!wcsncmp(s,L"temperate_",10))return 0;if(!wcsncmp(s,L"arctic_",7))return 1;if(!wcsncmp(s,L"desert_",7))return 2;if(!wcsncmp(s,L"cursed_",7))return 3;return -1;}
static int known(U def){U i;const wchar_t*s=(wchar_t*)P(def,8);for(i=0;i<sizeof(sources)/sizeof(sources[0]);i++)if(!wcscmp(s,sources[i].id))return 1;return 0;}
static U definition_info(U original){RecipeCacheEntry*e=recipe_cache_find(definitionCache,2047,original,0);U info;if(e&&e->original)return e->value;if(!readable(original,0x44))return 0;info=0x100u|((U)(slot(original)+1))|((U)known(original)<<4);recipe_cache_publish(e,original,0,info);return info;}
static U sum(U*b,int x0,int y0,int x1,int y1){U stride=width+1;return b[y1*stride+x1]-b[y0*stride+x1]-b[y1*stride+x0]+b[y0*stride+x0];}
static void prepare(U world,U map){U x,y,k,n,w=P(map,0x1c),h=P(map,0x20),tiles=P(map,0x28),stride=w+1;int s;
 if(integrals){VirtualFree(integrals,0,MEM_RELEASE);integrals=0;}if(recipes){VirtualFree(recipes,0,MEM_RELEASE);recipes=0;}
 worldSeen=world;tilesSeen=tiles;width=w;height=h;prewarmed=0;if(!w||!h||w>1024||h>1024||!tiles)return;
 n=(w+1)*(h+1);integrals=VirtualAlloc(0,n*16,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);recipes=VirtualAlloc(0,w*h*2,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);if(!integrals||!recipes)return;
 for(k=0;k<4;k++)for(y=0;y<h;y++){U run=0,*b=integrals+k*n;for(x=0;x<w;x++){s=slot(P(tiles+(y*w+x)*48,0));run+=s==(int)k;b[(y+1)*stride+x+1]=b[y*stride+x+1]+run;}}
 for(y=0;y<h;y++)for(x=0;x<w;x++){U total=0,counts[4],q[4],previous=0,hash=x*0x9e3779b9u+y*0x85ebca6bu,code;float cumulative=0,dither;int x0=x>BIOME_RADIUS?(int)x-BIOME_RADIUS:0,y0=y>BIOME_RADIUS?(int)y-BIOME_RADIUS:0,x1=x+BIOME_RADIUS+1<w?(int)x+BIOME_RADIUS+1:(int)w,y1=y+BIOME_RADIUS+1<h?(int)y+BIOME_RADIUS+1:(int)h;s=slot(P(tiles+(y*w+x)*48,0));if(s<0)continue;
  for(k=0;k<4;k++){counts[k]=sum(integrals+k*n,x0,y0,x1,y1);total+=counts[k];}
  if(!total||counts[s]==total)continue;hash^=hash>>16;hash*=0x7feb352du;hash^=hash>>15;dither=(float)(hash&65535)/65536.f;
  for(k=0;k<3;k++){U next;cumulative+=(float)counts[k]*8/total;next=(U)(cumulative+dither);if(next>8)next=8;q[k]=next-previous;previous=next;}q[3]=8-previous;
  if(q[s]==8)continue;code=palette_index[q[0]*81+q[1]*9+q[2]];((unsigned short*)recipes)[y*w+x]=(unsigned short)code;
 }
 VirtualFree(integrals,0,MEM_RELEASE);integrals=0;host->log("biome-wide","WORLD visual recipes %ux%u; radius %u cells, continuous four-biome field",w,h,BIOME_RADIUS);if(prewarmEnabled)prewarm_land(map);
}
static U variant(U original,U target,U step){U key=0,resource,load,info;wchar_t path[220];Clone*c;RecipeCacheEntry*cached;
 info=definition_info(original);if(!info)return original;if(step&&!(info&0x10)){step=0;target=0;}
 cached=recipe_cache_find(variantCache,131071,original,step);if(cached&&cached->original)return cached->value;
 if(cloneCount==65536)return original;
 if(!step){resource=P(original,0x20);step=0;target=0;goto copy_definition;}
 if(!palette[step-1][(info&15)-1])swprintf(path,L"Textures/PawsBiomeMix/shared/%u.png",step);
 else swprintf(path,L"Textures/PawsBiomeMix/%ls_%u.png",(wchar_t*)P(original,8),step);
 ((M1)(base+0x205de))((U)&key,0,(U)path);resource=((U(__cdecl*)(U,U))(base+0x1c586f))((U)&key,0);if(key)((M0)(base+0x21375))(key-16,0);if(!resource)return original;
 load=P(P(resource,0),0x10);((M2)load)(resource,0,1,1);
copy_definition:
 c=&clones[cloneCount++];c->original=original;c->target=target;c->step=step;memcpy(c->definition,(void*)original,0x44);P(c->definition,0x20)=resource;P(c->definition,0x18)=P(original,0x18)*1024+step;recipe_cache_publish(cached,original,step,(U)c->definition);return (U)c->definition;
}
/* Prepare just the (variation, recipe) pairs occurring on this map. */
static void prewarm_land(U map){U i,n=width*height,tiles=P(map,0x28),before=cloneCount,failures=0;DWORD began=GetTickCount();PrewarmBudget budget;if(prewarmed||!recipes)return;prewarmed=1;prewarm_budget_begin(&budget);
 for(i=0;i<n;i++){U cell=tiles+i*48,original=P(cell,0),recipe=((unsigned short*)recipes)[i],info;RecipeCacheEntry*e;if(!original)continue;if(P(cell,0x20)&0x100)recipe=0;info=definition_info(original);if(!info)continue;if(recipe&&!(info&0x10))recipe=0;e=recipe_cache_find(variantCache,131071,original,recipe);if(e&&e->original)continue;if(recipe&&!prewarm_budget_allow(&budget))break;if(variant(original,0,recipe)==original)failures++;}
 host->log("biome-wide","PREWARM land %u new clones, %u failures, %lu ms, memoryLimited=%u",cloneCount-before,failures,GetTickCount()-began,budget.limited);
}
static void __cdecl apply(U chunk){U world=P(base,0x5f3fb8),map,grid,n,ox,oy,x,y,cell,entry,original,r,v;
 if(!world||!chunk||!(map=P(world,0x30))||P(map,4)!=1)return;if(worldSeen!=world||tilesSeen!=P(map,0x28)||width!=P(map,0x1c)||height!=P(map,0x20))prepare(world,map);if(!recipes)return;
 grid=P(chunk,0x88);n=P(chunk,0xd0);if(!grid||!n||n>64)return;ox=P(chunk,0xac)*n;oy=P(chunk,0xb0)*n;
 for(y=0;y<n+2;y++)for(x=0;x<n+2;x++){int gx=(int)ox+(int)x-1,gy=(int)oy+(int)y-1;if(gx<0||gy<0||gx>=(int)width||gy>=(int)height)continue;entry=grid+(y*(n+2)+x)*20;cell=P(entry,4);if(!cell)continue;original=P(cell,0);P(entry,0)=original;
  if(!original)continue;r=((unsigned short*)recipes)[gy*width+gx];if((P(cell,0x20)&0x100)||!r)v=variant(original,0,0);else v=variant(original,0,r);P(entry,0)=v;if(v!=original)changed++;
 }blocks++;
}
static int ready(void){FILETIME c,e,k,u;ULARGE_INTEGER t;wchar_t name[160];HANDLE h;int ok;if(!GetProcessTimes(GetCurrentProcess(),&c,&e,&k,&u))return 0;t.LowPart=c.dwLowDateTime;t.HighPart=c.dwHighDateTime;t.QuadPart+=504911232000000000ULL;swprintf(name,L"Local\\PawPresentationReady-%lu-%I64u",GetCurrentProcessId(),t.QuadPart);h=OpenEventW(SYNCHRONIZE,FALSE,name);if(!h)return 0;ok=WaitForSingleObject(h,0)==WAIT_OBJECT_0;CloseHandle(h);return ok;}
__declspec(dllexport)int __cdecl K2Plugin_Start(const Host*h){wchar_t marker[MAX_PATH];char option[8];if(!h||h->api!=1)return 1;swprintf(marker,L"%ls\\paws_runtime.marker",h->gameDir);if(GetFileAttributesW(marker)==INVALID_FILE_ATTRIBUTES)return 1;host=h;base=h->exeBase;if(GetEnvironmentVariableA("PAWS_BIOME_PREWARM",option,sizeof(option))&&option[0]=='0')prewarmEnabled=0;return 0;}
__declspec(dllexport)void __cdecl K2Plugin_Tick(void){U site=base+0x19c302,stub;DWORD old,tmp;unsigned char jump[5];FILE*f;wchar_t path[MAX_PATH];if(installed){if(installed==1&&!P(base,0x5f3fb8))worldSeen=0;return;}if(!ready())return;
 if(!readable(site,10)||*(unsigned char*)site!=0xb8||P(site,1)!=base+0x43484e){installed=2;host->log("biome-wide","GUARD REFUSED");return;}
 stub=(U)VirtualAlloc(0,256,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);if(!stub)return;memcpy((void*)stub,wide_stub,sizeof(wide_stub));P(stub,STUB_APPLY)=(U)apply-(stub+STUB_APPLY+4);memcpy((void*)(stub+128),(void*)site,5);*(unsigned char*)(stub+133)=0xe9;P(stub+133,1)=site+5-(stub+138);P(stub,STUB_TAIL)=stub+128-(stub+STUB_TAIL+4);
 if(!VirtualProtect((void*)site,5,PAGE_EXECUTE_READWRITE,&old))return;jump[0]=0xe9;P(jump,1)=stub-site-5;memcpy((void*)site,jump,5);FlushInstructionCache(GetCurrentProcess(),(void*)site,5);VirtualProtect((void*)site,5,old,&tmp);installed=1;
 swprintf(path,L"%ls\\Mods\\biome-wide-state.txt",host->gameDir);f=_wfopen(path,L"w");if(f){fprintf(f,"%u %u %u %u\n",(U)&blocks,(U)&changed,(U)&cloneCount,(U)&worldSeen);fclose(f);}host->log("biome-wide","READY render-cache-only wide biome blend");
}
