/* Private terrain-layer color cache. Native fog, markers and UV zoom stay intact. */
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>
#define U unsigned
#define P(a,o) (*(U*)((uintptr_t)(a)+(o)))
#define FC __attribute__((fastcall))
#define RADIUS 24
typedef struct{U api;uintptr_t exeBase;const wchar_t*gameDir,*modsDir;void(__cdecl*log)(const char*,const char*,...);}Host;
typedef U(FC*ColorGetter)(U,U);
#include "minimap_palette.h"
#include "minimap_stubs.h"
static const Host*host;static U base,installed,worldSeen,tilesSeen,width,height,builds,samples,hits,fallbacks,changed,prepareMs;
static float*colors,*sourceColors;static U*originals;
static float zero[3];
static int readable(U a,U n){MEMORY_BASIC_INFORMATION m;return a&&a+n>=a&&VirtualQuery((void*)a,&m,sizeof(m))&&m.State==MEM_COMMIT&&!(m.Protect&(PAGE_NOACCESS|PAGE_GUARD))&&a+n<=(U)m.BaseAddress+m.RegionSize;}
static int climate(U v){const wchar_t*s=v?(wchar_t*)P(v,8):0;if(!s)return -1;if(!wcsncmp(s,L"temperate_",10))return 0;if(!wcsncmp(s,L"arctic_",7))return 1;if(!wcsncmp(s,L"desert_",7))return 2;if(!wcsncmp(s,L"cursed_",7))return 3;return -1;}
static int water(U v,U flags){const wchar_t*s;U d;if((flags&0x170)!=0x120||!(d=P(v,0x1c)))return 0;s=(wchar_t*)P(d,8);return s&&(!wcscmp(s,L"temperate_lake")||!wcscmp(s,L"arctic_lake")||!wcscmp(s,L"desert_lake")||!wcscmp(s,L"cursed_lake")||!wcscmp(s,L"temperate_river")||!wcscmp(s,L"arctic_river")||!wcscmp(s,L"paws_river_temperate")||!wcscmp(s,L"paws_river_arctic")||!wcscmp(s,L"paws_river_desert")||!wcscmp(s,L"paws_river_cursed"));}
static float*native_color(U v){return v?(float*)((ColorGetter)(base+0x6f74c))(v,0):zero;}
static U rectangle(U*b,U stride,U x0,U y0,U x1,U y1){return b[y1*stride+x1]-b[y0*stride+x1]-b[y1*stride+x0]+b[y0*stride+x0];}
static void clear_cache(void){if(colors)VirtualFree(colors,0,MEM_RELEASE);if(sourceColors)VirtualFree(sourceColors,0,MEM_RELEASE);if(originals)VirtualFree(originals,0,MEM_RELEASE);colors=sourceColors=0;originals=0;}
static void prepare(U world,U map){U w=P(map,0x1c),h=P(map,0x20),tiles=P(map,0x28),count=w*h,n=(w+1)*(h+1),*integrals=0,x,y,i,k,j,stride=w+1;float refs[8][3];unsigned char*classes=0;DWORD began=GetTickCount();static const wchar_t*canonical[4]={L"temperate_grass01",L"arctic_snow01",L"desert_sand01",L"cursed_grass01"};U waterRef[4]={0};
 clear_cache();worldSeen=world;tilesSeen=tiles;width=w;height=h;changed=0;if(!w||!h||w>1024||h>1024||!tiles)return;
 colors=VirtualAlloc(0,count*12,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);sourceColors=VirtualAlloc(0,count*12,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);originals=VirtualAlloc(0,count*4,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);integrals=VirtualAlloc(0,n*32,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);classes=VirtualAlloc(0,count,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);
 if(!colors||!sourceColors||!originals||!integrals||!classes)goto failed;memcpy(refs,minimap_palette,sizeof(refs));
 for(i=0;i<count;i++){U cell=tiles+i*48,v=P(cell,0),flags=P(cell,0x20);int s=climate(v);float*c=native_color(v);originals[i]=v;memcpy(sourceColors+i*3,c,12);memcpy(colors+i*3,c,12);classes[i]=255;if(s<0)continue;
  if(!(flags&0x100)){classes[i]=(unsigned char)s;if(!wcscmp((wchar_t*)P(v,8),canonical[s]))memcpy(refs[s],c,12);}
  else if(water(v,flags)){classes[i]=(unsigned char)(s+4);if(!waterRef[s]){memcpy(refs[s+4],c,12);waterRef[s]=1;}}
 }
 /* Land proportions include the surrounding climate, while water proportions
  * use only supported water cells. The shoreline is never averaged into water. */
 for(k=0;k<8;k++)for(y=0;y<h;y++){U run=0,*b=integrals+k*n;for(x=0;x<w;x++){i=y*w+x;run+=k<4?climate(originals[i])==(int)k:classes[i]==k;b[(y+1)*stride+x+1]=b[y*stride+x+1]+run;}}
 for(y=0;y<h;y++)for(x=0;x<w;x++){U group,own,total=0,counts[4],x0=x>RADIUS?x-RADIUS:0,y0=y>RADIUS?y-RADIUS:0,x1=x+RADIUS+1<w?x+RADIUS+1:w,y1=y+RADIUS+1<h?y+RADIUS+1:h;i=y*w+x;if(classes[i]==255)continue;group=classes[i]>=4?4:0;own=classes[i]-group;
  for(k=0;k<4;k++){counts[k]=rectangle(integrals+(group+k)*n,stride,x0,y0,x1,y1);total+=counts[k];}if(!total||counts[own]==total)continue;
  for(j=0;j<3;j++){float value=0;for(k=0;k<4;k++)value+=(k==own?sourceColors[i*3+j]:refs[group+k][j])*((float)counts[k]/total);colors[i*3+j]=value;}
  if(memcmp(colors+i*3,sourceColors+i*3,12))changed++;
 }
 VirtualFree(integrals,0,MEM_RELEASE);VirtualFree(classes,0,MEM_RELEASE);prepareMs=GetTickCount()-began;builds++;host->log("minimap-biomes","CACHE %ux%u; %u blended cells; %u ms; terrain layer only",w,h,changed,prepareMs);return;
failed:
 if(integrals)VirtualFree(integrals,0,MEM_RELEASE);if(classes)VirtualFree(classes,0,MEM_RELEASE);clear_cache();host->log("minimap-biomes","CACHE unavailable; original minimap colors retained");
}
static U __cdecl sample(U cell,U original){U world=P(base,0x5f3fb8),map,index;float*c=native_color(original);samples++;if(!world||!(map=P(world,0x30))||P(map,4)!=1){fallbacks++;return (U)c;}
 if(worldSeen!=world||tilesSeen!=P(map,0x28)||width!=P(map,0x1c)||height!=P(map,0x20))prepare(world,map);
 if(!colors||cell<tilesSeen||(cell-tilesSeen)%48||(index=(cell-tilesSeen)/48)>=width*height||originals[index]!=original||memcmp(c,sourceColors+index*3,12)){fallbacks++;return (U)c;}hits++;return (U)(colors+index*3);
}
#ifdef PAWS_MINIMAP_QA
__declspec(dllexport)void __cdecl Test_Init(U image,const Host*h){base=image;host=h;}
__declspec(dllexport)U __cdecl Test_Sample(U cell,U original){return sample(cell,original);}
__declspec(dllexport)U __cdecl Test_Value(U which){switch(which){case 0:return builds;case 1:return samples;case 2:return hits;case 3:return fallbacks;case 4:return changed;}return 0;}
#endif
static int ready(void){FILETIME c,e,k,u;ULARGE_INTEGER t;wchar_t name[160];HANDLE h;int ok;if(!GetProcessTimes(GetCurrentProcess(),&c,&e,&k,&u))return 0;t.LowPart=c.dwLowDateTime;t.HighPart=c.dwHighDateTime;t.QuadPart+=504911232000000000ULL;swprintf(name,L"Local\\PawPresentationReady-%lu-%I64u",GetCurrentProcessId(),t.QuadPart);h=OpenEventW(SYNCHRONIZE,FALSE,name);if(!h)return 0;ok=WaitForSingleObject(h,0)==WAIT_OBJECT_0;CloseHandle(h);return ok;}
__declspec(dllexport)int __cdecl K2Plugin_Start(const Host*h){if(!h||h->api!=1)return 1;host=h;base=h->exeBase;return 0;}
__declspec(dllexport)void __cdecl K2Plugin_Tick(void){U sites[4]={base+0x2d5343,base+0x2d5352,base+0x2d5364,base+0x2d5376},i,stub;DWORD old[4],tmp;FILE*f;wchar_t path[MAX_PATH];if(installed){if(!P(base,0x5f3fb8))worldSeen=0;return;}if(!ready())return;
 for(i=0;i<4;i++)if(!readable(sites[i],5)||*(unsigned char*)sites[i]!=0xe8||sites[i]+5+P(sites[i],1)!=base+0x6f74c){installed=2;host->log("minimap-biomes","GUARD REFUSED");return;}
 stub=(U)VirtualAlloc(0,sizeof(minimap_stubs),MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);if(!stub)return;memcpy((void*)stub,minimap_stubs,sizeof(minimap_stubs));for(i=0;i<4;i++)P(stub,minimap_fixups[i])=(U)sample-(stub+minimap_fixups[i]+4);
 for(i=0;i<4;i++)if(!VirtualProtect((void*)sites[i],5,PAGE_EXECUTE_READWRITE,old+i)){while(i){i--;VirtualProtect((void*)sites[i],5,old[i],&tmp);}VirtualFree((void*)stub,0,MEM_RELEASE);return;}
 for(i=0;i<4;i++){P(sites[i],1)=stub+i*128-sites[i]-5;FlushInstructionCache(GetCurrentProcess(),(void*)sites[i],5);}for(i=4;i;i--)VirtualProtect((void*)sites[i-1],5,old[i-1],&tmp);VirtualProtect((void*)stub,sizeof(minimap_stubs),PAGE_EXECUTE_READ,&tmp);installed=1;
 swprintf(path,L"%ls\\Mods\\minimap-biomes-state.txt",host->gameDir);f=_wfopen(path,L"w");if(f){fprintf(f,"%u %u %u %u %u %u %u %u %u %u\n",(U)&builds,(U)&samples,(U)&hits,(U)&fallbacks,(U)&changed,(U)&prepareMs,(U)&colors,(U)&width,(U)&height,(U)&sourceColors);fclose(f);}host->log("minimap-biomes","READY cached terrain palette; radius 24 cells; native fog/markers/zoom");
}
