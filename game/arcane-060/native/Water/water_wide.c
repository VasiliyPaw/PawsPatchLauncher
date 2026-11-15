/* Local visual extension. Owns only temporary renderer group vectors and
 * vertex alpha. World terrain, bodies, heights, rules and paths stay native. */
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>
#define U unsigned
#define P(a,o) (*(U*)((uintptr_t)(a)+(o)))
#define F(a,o) (*(float*)((uintptr_t)(a)+(o)))
#define FC __attribute__((fastcall))
#define TYPES 10
#define RADIUS 24
#include "water_mix_math.h"
typedef struct{U api;uintptr_t exeBase;const wchar_t*gameDir,*modsDir;void(__cdecl*log)(const char*,const char*,...);}Host;
typedef U(FC*M0)(U,U);typedef U(FC*M1)(U,U,U);typedef U(FC*M2)(U,U,U,U);
typedef float(FC*Floor)(U,U,U,U);
static const Host*host;static U base,installed,worldSeen,tilesSeen,width,height,typeCount;
static U defs[TYPES],variations[TYPES],keys[131072],groups,verticesChanged,builds,fallthrough,violations,groupBusy;
static float*field;static unsigned char coverage[4096];
static U prewarmEnabled=1;static void prewarm_floor(U map);
#include "prewarm_budget.h"
static const wchar_t*names[TYPES]={L"temperate_lake",L"arctic_lake",L"desert_lake",L"cursed_lake",L"temperate_river",L"arctic_river",L"paws_river_temperate",L"paws_river_arctic",L"paws_river_desert",L"paws_river_cursed"};
static int readable(U a,U n){MEMORY_BASIC_INFORMATION m;return a&&a+n>=a&&VirtualQuery((void*)a,&m,sizeof(m))&&m.State==MEM_COMMIT&&!(m.Protect&(PAGE_NOACCESS|PAGE_GUARD))&&a+n<=(U)m.BaseAddress+m.RegionSize;}
static int kind(U def){U i;if(!def)return -1;for(i=0;i<TYPES;i++)if(!wcscmp((wchar_t*)P(def,8),names[i]))return i;return -1;}
static int index_of(U def){U i;for(i=0;i<typeCount;i++)if(defs[i]==def)return i;return -1;}
static U chunk_key(U chunk,int add){U i=(chunk>>4)*2654435761u&131071,start=i;if(!chunk)return 0;do{if(keys[i]==chunk)return 1;if(!keys[i]){if(add)keys[i]=chunk;return add;}i=(i+1)&131071;}while(i!=start);return 0;}
static int scope(void){U w=P(base,0x5f3fb8),s=P(base,0x5f3fe4);return w&&s&&P(s,0xf0)==2&&P(w,0xd8)!=6;}
static U rectangle(U*b,int x0,int y0,int x1,int y1){U stride=width+1;return b[y1*stride+x1]-b[y0*stride+x1]-b[y1*stride+x0]+b[y0*stride+x0];}
static int prepare(void){U world,map,tiles,w,h,n,i,k,x,y,available[TYPES]={0},variant[TYPES]={0},*integrals;int slot;
 if(!scope())return 0;world=P(base,0x5f3fb8);map=P(world,0x30);if(!map)return 0;tiles=P(map,0x28);w=P(map,0x1c);h=P(map,0x20);
 if(world==worldSeen&&tiles==tilesSeen&&w==width&&h==height)return field&&typeCount;
 if(field){VirtualFree(field,0,MEM_RELEASE);field=0;}memset(keys,0,sizeof(keys));memset(defs,0,sizeof(defs));memset(variations,0,sizeof(variations));typeCount=0;worldSeen=world;tilesSeen=tiles;width=w;height=h;
 if(!w||!h||w>1024||h>1024||!tiles)return 0;
 for(i=0;i<w*h;i++){U c=tiles+i*48,v=P(c,0),d=v?P(v,0x1c):0;if((P(c,0x20)&0x170)!=0x120||!d)continue;slot=kind(d);if(slot>=0){available[slot]=d;variant[slot]=v;}}
 for(k=0;k<TYPES;k++)if(available[k]){defs[typeCount]=available[k];variations[typeCount++]=variant[k];}
 if(!typeCount)return 0;n=(w+1)*(h+1);integrals=VirtualAlloc(0,n*typeCount*4,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);field=VirtualAlloc(0,w*h*typeCount*4,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);
 if(!integrals||!field){if(integrals)VirtualFree(integrals,0,MEM_RELEASE);if(field){VirtualFree(field,0,MEM_RELEASE);field=0;}return 0;}
 for(k=0;k<typeCount;k++)for(y=0;y<h;y++){U run=0,*b=integrals+k*n;for(x=0;x<w;x++){U c=tiles+(y*w+x)*48,v=P(c,0);run+=v&&(P(c,0x20)&0x170)==0x120&&P(v,0x1c)==defs[k];b[(y+1)*(w+1)+x+1]=b[y*(w+1)+x+1]+run;}}
 for(y=0;y<h;y++)for(x=0;x<w;x++){U counts[TYPES],sum=0;int x0=x>RADIUS?(int)x-RADIUS:0,y0=y>RADIUS?(int)y-RADIUS:0,x1=x+RADIUS+1<w?(int)x+RADIUS+1:(int)w,y1=y+RADIUS+1<h?(int)y+RADIUS+1:(int)h;for(k=0;k<typeCount;k++){counts[k]=rectangle(integrals+k*n,x0,y0,x1,y1);sum+=counts[k];}if(sum)for(k=0;k<typeCount;k++)field[(y*w+x)*typeCount+k]=(float)counts[k]/sum;}
 VirtualFree(integrals,0,MEM_RELEASE);host->log("water-wide","WORLD %ux%u; %u animated materials; radius %u",w,h,typeCount,RADIUS);if(prewarmEnabled)prewarm_floor(map);return 1;
}
static float weight(int x,int y,U k){if(x<0)x=0;if(y<0)y=0;if(x>=(int)width)x=width-1;if(y>=(int)height)y=height-1;return field[(y*width+x)*typeCount+k];}
#include "water_floor.h"
static int reaches(int x,int y,U k){int dx,dy;for(dy=-1;dy<=1;dy++)for(dx=-1;dx<=1;dx++)if(weight(x+dx,y+dy,k)>.000001f)return 1;return 0;}
static void retain_for_chunk(U chunk,U variant){U i,entries=P(chunk,0xa0);for(i=0;i<P(chunk,0xa4);i++)if(P(entries+i*8,4)==variant)return;((M2)(base+0x19e6e2))(chunk,0,variant,1);}
static void __cdecl extend_groups(U self,U container){U map,view,chunk,ratio,ox,oy,i,j,k,oldp,oldn,replacement[3],entry,point,count=0;int x,y;
 if(groupBusy||!self||!container||!prepare()||(oldn=P(container,4))>64||!(oldp=P(container,0)))return;
 map=P(P(base,0x5f3fb8),0x30);view=P(base,0x5f3fa8);chunk=P(self,0);if(!view||!chunk||!P(view,0xb4))return;ratio=P(view,0xa8)/P(view,0xb4);if(!ratio||ratio>64)return;ox=P(chunk,0xac)*ratio;oy=P(chunk,0xb0)*ratio;memset(coverage,0,sizeof(coverage));
 for(i=0;i<oldn;i++){entry=oldp+i*16;U v=P(entry,0),d=v?P(v,0x1c):0;if(index_of(d)<0)continue;for(j=0;j<P(entry,8);j++){point=P(entry,4)+j*8;x=(int)P(point,0);y=(int)P(point,4);if(x<0||y<0||x>=(int)ratio||y>=(int)ratio)return;if(!coverage[y*ratio+x]){coverage[y*ratio+x]=1;count++;}}}
 if(!count)return;groupBusy=1;((M2)(base+0x1b3aa1))((U)replacement,0,1,1);
 /* Preserve special bog/blood/cutout groups and their native cell lists. */
 for(i=0;i<oldn;i++){entry=oldp+i*16;U v=P(entry,0),d=v?P(v,0x1c):0;if(index_of(d)>=0)continue;U out=((M2)(base+0x1b34fb))(0,0,v,(U)replacement);for(j=0;j<P(entry,8);j++){point=P(entry,4)+j*8;((M2)(base+0x1b3d1b))(out,0,P(point,0),P(point,4));}}
 for(k=0;k<typeCount;k++){U out=0;for(y=0;y<(int)ratio;y++)for(x=0;x<(int)ratio;x++)if(coverage[y*ratio+x]&&ox+x<P(map,0x1c)&&oy+y<P(map,0x20)&&reaches(ox+x,oy+y,k)){
  if(!out){retain_for_chunk(chunk,variations[k]);out=((M2)(base+0x1b34fb))(0,0,variations[k],(U)replacement);}((M2)(base+0x1b3d1b))(out,0,x,y);
 }}
 {unsigned short seen[4096];memset(seen,0,sizeof(seen));for(i=0;i<replacement[1];i++){U e=replacement[0]+i*16,v=P(e,0);int index=index_of(P(v,0x1c));if(index<0)continue;for(j=0;j<P(e,8);j++){U p=P(e,4)+j*8,xx=P(p,0),yy=P(p,4);if(xx>=ratio||yy>=ratio||!coverage[yy*ratio+xx]||(seen[yy*ratio+xx]&(1u<<index)))violations++;else seen[yy*ratio+xx]|=1u<<index;}}for(i=0;i<ratio*ratio;i++)if(coverage[i]&&!seen[i])violations++;}
 ((M0)(base+0x1b3ee1))(container,0);memcpy((void*)container,replacement,12);chunk_key(chunk,1);groups++;groupBusy=0;
}
static int __cdecl native_build(U self){builds++;if(!self||!prepare()||index_of(P(self,8))<0||!chunk_key(P(self,0),0)){fallthrough++;return 0;}return 1;}
static float opacity(U profile,float depth){U i,n;float*t;if(!profile||!(n=P(profile,0xc))||n>256||!P(profile,8)){U p=P(base,0x5f94d0),v=p?P(p,0x14):0;float scale=v?*(float*)v:1;return scale>.00001f?depth/scale:0;}t=(float*)P(profile,8);if(depth<=t[0])return t[4];for(i=1;i<n;i++)if(depth<t[i*5]){float q=(depth-t[(i-1)*5])/(t[i*5]-t[(i-1)*5]);return t[(i-1)*5+4]+q*(t[i*5+4]-t[(i-1)*5+4]);}return t[(n-1)*5+4];}
static int integer(float f){int i;__asm__ volatile(".byte 0xf3,0x0f,0x2c,0x00":"=a"(i):"a"(&f));return i;}
static int __cdecl blend_vertices(U self){U world,view,data,count,i,j,profiles[TYPES];int own,x,y;float*positions,*colors;
 if(!self||!prepare()||(own=index_of(P(self,8)))<0||!chunk_key(P(self,0),0)||!P(self,4))return 0;
 world=P(base,0x5f3fb8);view=P(base,0x5f3fa8);data=P(P(self,4),0xcc);if(!data)return 0;count=*(unsigned short*)(data+0xc);positions=(float*)P(data,0x20);colors=(float*)P(data,0x28);if(!positions||!colors)return 0;
 for(j=0;j<typeCount;j++)profiles[j]=((M1)(base+0x70e6f))(P(view,0x70),0,defs[j]);
 for(i=0;i<count;i++){float gx=positions[i*3]*.5f-.5f,gy=positions[i*3+1]*.5f-.5f,tx,ty,w[TYPES],a[TYPES],sum=0,depth,alpha;
  x=integer(gx);if(gx<x)x--;y=integer(gy);if(gy<y)y--;tx=gx-x;ty=gy-y;
  for(j=0;j<typeCount;j++){w[j]=weight(x,y,j)*(1-tx)*(1-ty)+weight(x+1,y,j)*tx*(1-ty)+weight(x,y+1,j)*(1-tx)*ty+weight(x+1,y+1,j)*tx*ty;sum+=w[j];}
  if(sum<.000001f||w[own]>=sum-.000001f)continue;if(w[own]<.000001f){colors[i*4+3]=0;continue;}
  depth=positions[i*3+2]-((Floor)(base+0x2424d0))(world,0,(U)(positions+i*3),0x122);
  for(j=0;j<typeCount;j++){a[j]=0;if(w[j]>.000001f){alpha=(int)j==own?colors[i*4+3]:opacity(profiles[j],depth);if(alpha<0)alpha=0;if(alpha>1)alpha=1;a[j]=alpha;}}
  alpha=water_layer_alpha(w,a,typeCount,own);if(!(alpha>=0&&alpha<=1.00001f)){violations++;continue;}colors[i*4+3]=alpha;verticesChanged++;
 }
 return 1;
}
#include "water_stubs.h"
/* Acquire all four sites before changing any instruction. A protection failure
 * leaves every previous renderer hook intact and the unused stub can be freed. */
static int install_hooks(U group,U build,U colors,U stub){U sites[4]={group,build,colors,base+0x19c307},targets[4]={stub,stub+512,stub+1024,stub+1536},i;DWORD old[4],tmp;unsigned char b[5];
 for(i=0;i<4;i++)if(!VirtualProtect((void*)sites[i],5,PAGE_EXECUTE_READWRITE,old+i)){while(i){i--;VirtualProtect((void*)sites[i],5,old[i],&tmp);}return 0;}
 for(i=0;i<4;i++){b[0]=i?0xe8:0xe9;P(b,1)=targets[i]-sites[i]-5;memcpy((void*)sites[i],b,5);FlushInstructionCache(GetCurrentProcess(),(void*)sites[i],5);}
 /* Two call sites share a page: restore protections in reverse acquisition
  * order so that its original protection wins, rather than the temporary RWX. */
 for(i=4;i;i--)VirtualProtect((void*)sites[i-1],5,old[i-1],&tmp);return 1;
}
__declspec(dllexport)int __cdecl K2Plugin_Start(const Host*h){wchar_t p[MAX_PATH];char option[8];if(!h||h->api!=1)return 1;swprintf(p,L"%ls\\paws_runtime.marker",h->gameDir);if(GetFileAttributesW(p)==INVALID_FILE_ATTRIBUTES)return 1;host=h;base=h->exeBase;if(GetEnvironmentVariableA("PAWS_BIOME_PREWARM",option,sizeof(option))&&option[0]=='0')prewarmEnabled=0;return 0;}
__declspec(dllexport)void __cdecl K2Plugin_Tick(void){U group=base+0x1b33aa,build=base+0x1b25de,colors=base+0x1b2790,priorBuild,priorColors,stub,i;FILE*f;wchar_t p[MAX_PATH];if(installed){if(installed==1&&!P(base,0x5f3fb8))worldSeen=0;return;}
 if(*(unsigned char*)build!=0xe8||*(unsigned char*)colors!=0xe8)return;priorBuild=build+5+P(build,1);priorColors=colors+5+P(colors,1);if(priorBuild==base+0x1b29dc||priorColors==base+0x398e00)return;
 if(!readable(priorBuild,2)||!readable(priorColors,2)||*(unsigned short*)priorBuild!=0x609c||*(unsigned short*)priorColors!=0x609c||memcmp((void*)group,"\x8d\x45\xb8\x33\xf6",5)){installed=2;host->log("water-wide","GUARD REFUSED");return;}
 if(*(unsigned char*)(base+0x19c307)!=0xe8||base+0x19c30c+P(base+0x19c307,1)!=base+0x3e15dc){installed=2;host->log("water-wide","FLOOR GUARD REFUSED");return;}
 stub=(U)VirtualAlloc(0,2048,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);if(!stub)return;memcpy((void*)stub,water_stubs,sizeof(water_stubs));
 for(i=0;i<sizeof(fixups)/sizeof(fixups[0]);i++){U target=0;switch(fixups[i][1]){case 1:target=(U)extend_groups;break;case 2:target=(U)native_build;break;case 3:target=(U)blend_vertices;break;case 4:target=group+5;break;case 5:target=base+0x1b29dc;break;case 6:target=base+0x398e00;break;case 7:target=priorBuild;break;case 8:target=priorColors;break;case 9:target=(U)blend_floor;break;case 10:target=base+0x3e15dc;break;}P(stub,fixups[i][0])=target-(stub+fixups[i][0]+4);}
 if(!install_hooks(group,build,colors,stub)){VirtualFree((void*)stub,0,MEM_RELEASE);return;}installed=1;
 swprintf(p,L"%ls\\Mods\\water-wide-state.txt",host->gameDir);f=_wfopen(p,L"w");if(f){fprintf(f,"%u %u %u %u %u %u %u %u %u %u %u %u %u\n",(U)&groups,(U)&verticesChanged,(U)&builds,(U)&fallthrough,(U)&typeCount,(U)&field,(U)&width,(U)&height,(U)&defs,(U)&violations,(U)&floorEntries,(U)&floorChunks,(U)&floorCloneCount);fclose(f);}host->log("water-wide","READY native animated layers and bottom; 24-cell field; chunk-local ownership");
}
