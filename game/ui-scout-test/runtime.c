/* Local Arcane Wars candidate. Native command transport and visibility retained. */
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>
#define FC __attribute__((fastcall))
#define X __declspec(dllexport)
typedef uintptr_t U;
#define P(a,o) (*(U*)((U)(a)+(o)))
#define F(a,o) (*(float*)((U)(a)+(o)))
typedef struct {unsigned api;U exeBase;const wchar_t*gameDir,*modsDir;void(__cdecl*log)(const char*,const char*,...);} Host;
static const Host*host;static DWORD mainThread;static int busy;static U base,mapWidget,worldSeen;static float zoom=1,cx=.5f,cy=.5f;
static U quadRenderer;static float quadU,quadV,quadUV[8];static int wheelRemainder;
typedef void(FC*Void0)(U,U);
typedef void(FC*Void1)(U,U,U);
typedef U(FC*Get1)(U,U,U);
typedef U(FC*Get0)(U,U);
typedef double(FC*Score)(U,U,U,U);
typedef U(FC*Project)(U,U,float*,float,float);
typedef U(FC*Inverse)(U,U,float*,int,int);
typedef void(FC*Draw)(U,U,U,U);
typedef U(FC*MakeOrder)(U,U,U,U);
typedef struct {float x,y,time;U region;} ReconVisit;
typedef struct {U world,kingdom;float last;unsigned sent;float probe;unsigned probed,sequence,recentCount,recentNext;ReconVisit recent[16];} Cooldown;
static Cooldown cooldowns[96];
static WNDPROC previousProc;static HWND gameWindow;
static float clamp(float v,float lo,float hi){return v<lo?lo:v>hi?hi:v;}
static int match(void){U idx=P(base,0x5f92f4),state;if(idx>16)return 0;state=P(base+0x5f92b4,idx*4);return state&&P(state,0)==base+0x48d0dc&&P(base,0x5f3fb8);}
static void center(void){U ui=P(base,0x5f3fbc),world=P(base,0x5f3fb8),terrain;float half=.5f/zoom;
 if(!ui||!world)return;terrain=P(world,0x30);if(!terrain||F(terrain,0xc)<=0||F(terrain,0x10)<=0)return;
 cx=(F(ui,0x144)+F(ui,0x150)+F(ui,0x15c)+F(ui,0x168))*.25f/F(terrain,0xc);
 cy=(F(ui,0x148)+F(ui,0x154)+F(ui,0x160)+F(ui,0x16c))*.25f/F(terrain,0x10);
 cx=clamp(cx,half,1-half);cy=clamp(cy,half,1-half);
}
/* Native cached quad: vertices at +5c, count at +60, upload-dirty byte +85.
 * Keep the owning render object alive. VE dirty bit 20 destroys this cache;
 * setting it every camera frame leaves the minimap blank while panning. */
static void FC quad_update(U ve,U unused){U holder,renderer;float*v;unsigned i;(void)unused;
 if(!ve||!(holder=P(ve,0xa4))||!(renderer=P(holder,0))||renderer!=quadRenderer||P(renderer,0x60)!=4||!(v=(float*)P(renderer,0x5c)))return;
 if(quadU<=0||quadV<=0)return;
 for(i=0;i<4;i++){float u=((quadUV[i*2]-.5f)/zoom+cx)*quadU,w=((quadUV[i*2+1]-.5f)/zoom+cy)*quadV;
  if(v[i*8+5]!=u||v[i*8+6]!=w){v[i*8+5]=u;v[i*8+6]=w;*(unsigned char*)(renderer+0x85)=1;}
 }
}
static void FC wheel_zoom(U raw,U unused){int step=(int)((zoom-1)*10+.5f);(void)unused;
 wheelRemainder+=(short)raw;step+=wheelRemainder/120;wheelRemainder%=120;
 if(step<0)step=0;if(step>30)step=30;zoom=1+.1f*step;
}
static void FC mini_update(U self,U unused){U world=P(base,0x5f3fb8),ve;(void)unused;
 mapWidget=self;if(worldSeen!=world){zoom=1;cx=cy=.5f;worldSeen=world;quadRenderer=0;wheelRemainder=0;}
 if(match())center();
 ((Void0)(base+0x2a45de))(self,0);
 if(match()&&(ve=P(self,0x74))!=0){quad_update(ve,0);*(unsigned char*)(ve+0xf4)=1;}
}
static U FC project(U matrix,U unused,float*out,float x,float y){(void)unused;
 if(match()&&zoom>1){x=(x-cx)*zoom+.5f;y=(y-cy)*zoom+.5f;}
 return ((Project)(base+0x2a495a))(matrix,0,out,x,y);
}
static U FC inverse(U self,U unused,float*out,int x,int y){U world,terrain,result;(void)unused;
 result=((Inverse)(base+0x2a42aa))(self,0,out,x,y);
 if(self==mapWidget&&match()&&zoom>1){world=P(base,0x5f3fb8);terrain=P(world,0x30);
  out[0]=((out[0]/F(terrain,0xc)-.5f)/zoom+cx)*F(terrain,0xc);
  out[1]=((out[1]/F(terrain,0x10)-.5f)/zoom+cy)*F(terrain,0x10);
 }
 return result;
}
static void FC map_draw(U renderer,U unused,U vertices,U indices){float*v=(float*)P(vertices,0),umax=0,vmax=0;unsigned i;(void)unused;
 if(v&&match()){
  for(i=0;i<4;i++){if(v[i*8+5]>umax)umax=v[i*8+5];if(v[i*8+6]>vmax)vmax=v[i*8+6];}
  quadRenderer=renderer;quadU=umax;quadV=vmax;
  if(umax>0&&vmax>0)for(i=0;i<4;i++){quadUV[i*2]=v[i*8+5]/umax;quadUV[i*2+1]=v[i*8+6]/vmax;}
  if(zoom>1&&umax>0&&vmax>0)for(i=0;i<4;i++){v[i*8+5]=(v[i*8+5]/umax-.5f)/zoom*umax+cx*umax;v[i*8+6]=(v[i*8+6]/vmax-.5f)/zoom*vmax+cy*vmax;}
 }
 ((Draw)(base+0x17844b))(renderer,0,vertices,indices);
}
static Cooldown*clock_for(U kingdom){U world=P(base,0x5f3fb8);float time=world?F(world,0xe8):0;unsigned i;Cooldown*c=0;
 for(i=0;i<96;i++)if(cooldowns[i].world==world&&cooldowns[i].kingdom==kingdom){c=&cooldowns[i];break;}
 if(!c)for(i=0;i<96;i++)if(cooldowns[i].world!=world){c=&cooldowns[i];memset(c,0,sizeof(*c));c->world=world;c->kingdom=kingdom;break;}
 if(c&&(time<c->last||time<c->probe)){c->sent=0;c->probed=0;c->last=time;c->probe=time;c->sequence=c->recentCount=c->recentNext=0;memset(c->recent,0,sizeof(c->recent));}return c;
}
static int black(U kingdom,U region){U index,info;if(!kingdom||!region)return 0;index=P(kingdom,0x194);
 if(index>=P(region,0x14)||!P(region,0x10))return 0;info=P(P(region,0x10),index*4);
 return info&&P(info,0)==region&&P(info,8)==0;
}
static int __cdecl allowed(U kingdom,U region){Cooldown*c=clock_for(kingdom);U world=P(base,0x5f3fb8);
 return world&&c&&(!c->sent||F(world,0xe8)-c->last>=60)&&black(kingdom,region);
}
/* Repeatable random ranking: no wall clock, pointer values or engine RNG. */
static U recon_mix(U v){v^=v>>16;v*=0x7feb352du;v^=v>>15;v*=0x846ca68bu;return v^(v>>16);}
static int recon_recent(Cooldown*c,U region,float now,float radius2){unsigned i;for(i=0;i<c->recentCount;i++){ReconVisit*v=&c->recent[i];float dx,dy;if(now-v->time>=600||now<v->time)continue;
 dx=F(region,0x54)-v->x;dy=F(region,0x58)-v->y;if(P(region,0)==v->region||dx*dx+dy*dy<radius2)return 1;}return 0;}
static void __cdecl remember_recon(Cooldown*c,U region,float now){ReconVisit*v=&c->recent[c->recentNext];v->x=F(region,0x54);v->y=F(region,0x58);v->time=now;v->region=P(region,0);c->recentNext=(c->recentNext+1)%16;if(c->recentCount<16)c->recentCount++;c->sequence++;}
static U far_region(U kingdom,U actor){U map=P(base,0x5f3fcc),world=P(base,0x5f3fb8),terrain,table,n,i,pass,region=0,seed,bestKey=0;float minimum=64,radius=32,best=0,now;Cooldown*c=clock_for(kingdom);
 if(!world||!c||!map)return 0;now=F(world,0xe8);if(!(now>=0&&now<200000000.f))return 0;
 if((terrain=P(world,0x30))!=0){float side=F(terrain,0xc)<F(terrain,0x10)?F(terrain,0xc):F(terrain,0x10);if(side*.2f>minimum)minimum=side*.2f;if(side*.05f>radius)radius=side*.05f;}
 table=P(map,0x14);n=P(map,0x18);if(!table||!n||n>8192)return 0;
 seed=recon_mix(P(world,0xe4)^c->sequence*0x9e3779b9u^(P(kingdom,0x194)+1)*0x85ebca6bu^P(actor,0x14)*0xc2b2ae35u^P(actor,0x20)^recon_mix(P(actor,0x24)));
 /* First establish the distant band, then sample its eligible regions by hash.
  * Never fall back into a recent target area when all alternatives are blocked. */
 for(pass=0;pass<2;pass++)for(i=0;i<n;i++){U candidate=P(table,i*4),key;float dx,dy,distance;
  if(!black(kingdom,candidate)||recon_recent(c,candidate,now,radius*radius))continue;
  dx=F(candidate,0x54)-F(actor,0x20);dy=F(candidate,0x58)-F(actor,0x24);distance=dx*dx+dy*dy;
  if(!(distance>=minimum*minimum&&distance<=1e12f))continue;
  if(!pass){if(distance>best)best=distance;continue;}
  if(distance<best*.4225f)continue; /* At least 65% of the farthest distance. */
  key=recon_mix(seed^P(candidate,0));if(!region||key<bestKey||(key==bestKey&&P(candidate,0)<P(region,0))){region=candidate;bestKey=key;}
 }
 return region;
}
/* City upgrades do not populate the legacy synthetic-air-actor pool in AW.
 * Plan on the serialized AI callback using native owned IDs and command support;
 * never register actors, transfer goals, reveal fog, or alter resources here. */
static void FC air_update(U goal,U unused){U pl,kingdom,world,node,steps=0,actor=0,region,oldTarget,command[6];Cooldown*c;float time;(void)unused;
 ((Void0)(base+0x1d4094))(goal,0);
 world=P(base,0x5f3fb8);if(!world)return;pl=P(P(goal,4),4);kingdom=P(pl,8);c=clock_for(kingdom);time=F(world,0xe8);
 if(!c||(c->sent&&time-c->last<60)||(c->probed&&time-c->probe<10))return;c->probed=1;c->probe=time;
 for(node=P(pl,0x4c);node&&steps++<4096;node=P(node,4)){
  U candidate=((Get1)(base+0x21117))(P(base,0x5ef72c),0,P(node,0)),def,body;
  if(!candidate||P(candidate,0)!=base+0x4e5c58||P(candidate,0xe8)!=kingdom||(P(candidate,8)&1))continue;
  /* Owned settlement IDs refer to the enclosing settlement actor. The actual
   * upgraded center owns the denizens, recon price and native command bit. */
  if(P(candidate,0x98)){U center=P(P(candidate,0x98),0x14);if(center)candidate=center;}
  if(P(candidate,0)!=base+0x4e5c58||P(candidate,0xe8)!=kingdom||(P(candidate,8)&1))continue;
  def=P(candidate,4);body=P(candidate,0x60);if(!def||!body||!(F(body,0x10)>0)||!P(def,0x3fc)||!P(def,0x400)||P(def,0x400)>16)continue;
  if(!(((Get1)P(P(candidate,0),0x34))(candidate,0,0x1a)&255))continue;
  if(!actor||P(candidate,0x14)<P(actor,0x14))actor=candidate;
 }
 if(node||!actor)return;
 region=far_region(kingdom,actor);
 if(!region)return;
 oldTarget=P(goal,0x44);P(goal,0x44)=region;((MakeOrder)(base+0x1d3e82))(goal,0,(U)command,actor);P(goal,0x44)=oldTarget;
 ((Void1)(base+0x1f2c03))(pl,0,(U)command);((Void0)(base+0x1f397b))((U)command,0);
 c->last=time;c->sent=1;remember_recon(c,region,time);host->log("ui-scout-test","AIR_RECON_CITY_QUEUED kingdom=%u actor=%u region=%u time=%.3f cooldown=60",P(kingdom,0x194),P(actor,0x14),P(region,0),time);
}
static void FC air_orders(U goal,U unused,U arg){U pl=P(P(goal,4),4),kingdom=P(pl,8),world=P(base,0x5f3fb8),node,steps=0;Cooldown*c=clock_for(kingdom);(void)unused;(void)arg;
 if(!world||!c||(c->sent&&F(world,0xe8)-c->last<60))return;
 for(node=P(goal,0xc);node&&steps++<4096;node=P(node,4)){
  U sa=P(node,0),actor,region,oldTarget,command[6];
  if(!sa||(((Get0)P(P(sa,0),0xc))(sa,0)&255)||!(((Get0)P(P(sa,0),4))(sa,0)&255))continue;
  actor=((Get1)(base+0x1e2321))(P(sa,0x50),0,0);if(!actor||P(actor,0xe8)!=kingdom||(P(actor,8)&1))continue;
  if(!(((Get0)(base+0x1e392f))(sa,0)&255))continue;
  region=far_region(kingdom,actor);if(!region)continue;
  oldTarget=P(goal,0x44);P(goal,0x44)=region;((MakeOrder)(base+0x1d3e82))(goal,0,(U)command,actor);P(goal,0x44)=oldTarget;
  ((Void1)(base+0x1f2c03))(pl,0,(U)command);
  ((Void0)(base+0x1f397b))((U)command,0);
  c->last=F(world,0xe8);c->sent=1;
  remember_recon(c,region,c->last);
  host->log("ui-scout-test","AIR_RECON_QUEUED kingdom=%u actor=%u region=%u time=%.3f cooldown=60",P(kingdom,0x194),P(actor,0x14),P(region,0),c->last);
  return;
 }
}
static int equal_wide(const wchar_t*a,const wchar_t*b){while(*a&&*a==*b){a++;b++;}return *a==*b;}
static int __cdecl classify(U actor){const wchar_t*name;U def=P(actor,4);int native=((int(__cdecl*)(U))(base+0x25e971))(actor);static const wchar_t*races[]={L"human",L"gauri",L"drauga",L"haroun",L"undead",L"shadow"};unsigned i;
 if(!def||!(name=(const wchar_t*)P(def,8)))return native;
 for(i=0;i<6;i++){const wchar_t*p=name,*r=races[i];while(*r&&*r==*p){r++;p++;}if(!*r&&*p=='_'&&(equal_wide(p+1,L"fort")||equal_wide(p+1,L"keep")||equal_wide(p+1,L"keep_1")))return 3;}
 return native;
}
static LRESULT CALLBACK window_proc(HWND w,UINT msg,WPARAM wp,LPARAM lp){
 if(msg==WM_MOUSEWHEEL&&mapWidget&&match()){
  POINT pt;float out[2];U terrain=P(P(base,0x5f3fb8),0x30),ve=P(mapWidget,0x74);pt.x=(short)LOWORD(lp);pt.y=(short)HIWORD(lp);ScreenToClient(w,&pt);
  if(ve&&pt.x>=F(ve,0x20)&&pt.x<F(ve,0x28)&&pt.y>=F(ve,0x24)&&pt.y<F(ve,0x2c)){
   ((Inverse)(base+0x2a42aa))(mapWidget,0,out,pt.x,pt.y);
   if(out[0]>=0&&out[1]>=0&&out[0]<=F(terrain,0xc)&&out[1]<=F(terrain,0x10)){
    wheel_zoom((U)(short)HIWORD(wp),0);center();quad_update(ve,0);
    host->log("ui-scout-test","MINIMAP_ZOOM %.1f center=%.4f,%.4f",zoom,cx,cy);return 0;
   }
  }
 }
 return CallWindowProcW(previousProc,w,msg,wp,lp);
}
static BOOL CALLBACK find_window(HWND w,LPARAM arg){DWORD pid;GetWindowThreadProcessId(w,&pid);if(pid==GetCurrentProcessId()&&IsWindowVisible(w)&&!GetWindow(w,GW_OWNER)){*(HWND*)arg=w;return FALSE;}return TRUE;}
typedef struct {U at;unsigned char before[8],after[8];unsigned size;} Write;
static Write writes[40];static unsigned writeCount;
static int prepare(U rva,const unsigned char*expected,const void*after,unsigned size){Write*w;if(writeCount>=40||size>8||memcmp((void*)(base+rva),expected,size))return 0;w=&writes[writeCount++];w->at=base+rva;w->size=size;memcpy(w->before,expected,size);memcpy(w->after,after,size);return 1;}
static int pointer(U rva,U expected,U target){U value=base+expected;return prepare(rva,(unsigned char*)&value,&target,4);}
static int call(U rva,U target,U replacement){unsigned char expected[5],after[5];expected[0]=after[0]=0xe8;*(int*)(expected+1)=target-rva-5;*(int*)(after+1)=replacement-(base+rva+5);return prepare(rva,expected,after,5);}
static int commit(void){unsigned i;DWORD old;for(i=0;i<writeCount;i++){Write*w=&writes[i];if(!VirtualProtect((void*)w->at,w->size,PAGE_EXECUTE_READWRITE,&old))break;memcpy((void*)w->at,w->after,w->size);VirtualProtect((void*)w->at,w->size,old,&old);FlushInstructionCache(GetCurrentProcess(),(void*)w->at,w->size);}if(i==writeCount)return 1;
 while(i){Write*w=&writes[--i];if(VirtualProtect((void*)w->at,w->size,PAGE_EXECUTE_READWRITE,&old)){memcpy((void*)w->at,w->before,w->size);VirtualProtect((void*)w->at,w->size,old,&old);FlushInstructionCache(GetCurrentProcess(),(void*)w->at,w->size);}}return 0;
}
/* Generated exact x86 tail dispatch keeps all non-air goals byte-native. */
#include "day_clock.h"
#include "dispatch.h"
#ifdef PAW_QA
static unsigned char FC qa_recon_cast(U self,U unused,U x,U y);
#endif
static int install(void){unsigned i;static const U inverses[]={0xd5000,0xd5785,0x2a4570,0x2a47ee};static const U projections[]={0x2a43fa,0x2a4430,0x2a4466,0x2a449c};static const U stats[]={0x206917,0x2069d2,0x22a8c1,0x22ebf0,0x25e75c};
 const Host*h=host;
 if(!init_dispatch())return 1;
 if(!pointer(0x500894+0xc,0x2a45de,(U)mini_update)||!pointer(0x4d79e8+0x58,0x1d3d29,(U)orders_dispatch)||!pointer(0x4d79e8+0x78,0x1d4094,(U)update_dispatch))return 1;
 for(i=0;i<4;i++)if(!call(inverses[i],0x2a42aa,(U)inverse)||!call(projections[i],0x2a495a,(U)project))return 1;
 for(i=0;i<5;i++)if(!call(stats[i],0x25e971,(U)classify))return 1;
#ifdef PAW_QA
 if(!call(0x2096dd,0x209a4e,(U)qa_recon_cast))return 1;
#endif
 if(!call(0x2b1ae6,0x17844b,(U)map_draw)||!commit())return 1;
 h->log("ui-scout-test","READY r1; minimap=1..4; recon=one/kingdom/60s/black-only; fort-stats=18 explicit ids");return 0;
}
X int __cdecl K2Plugin_Start(const Host*h){wchar_t marker[MAX_PATH];
 if(!h||h->api!=1)return 1;host=h;base=h->exeBase;mainThread=GetCurrentThreadId();swprintf(marker,L"%ls\\ui-scout-test.marker",h->gameDir);if(GetFileAttributesW(marker)==INVALID_FILE_ATTRIBUTES)return 1;
 host->log("ui-scout-test","WAITING for private helper");return 0;
}
#ifdef PAW_QA
#include "qa.h"
#endif
X void __cdecl K2Plugin_Tick(void){static int installed;wchar_t marker[MAX_PATH];if(busy||GetCurrentThreadId()!=mainThread||installed<0)return;if(!installed){swprintf(marker,L"%ls\\ui-scout-helper-ready.marker",host->modsDir);if(GetFileAttributesW(marker)==INVALID_FILE_ATTRIBUTES)return;installed=install()?-1:1;if(installed<0){host->log("ui-scout-test","INSTALL_REFUSED");return;}}busy=1;if(!previousProc){EnumWindows(find_window,(LPARAM)&gameWindow);if(gameWindow){previousProc=(WNDPROC)SetWindowLongPtrW(gameWindow,GWLP_WNDPROC,(LONG_PTR)window_proc);}}
 day_clock_tick();
#ifdef PAW_QA
 qa_tick();
#endif
 busy=0;
}
