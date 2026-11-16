/* Local Arcane Wars candidate. Native command transport and visibility retained. */
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>
#define FC __attribute__((fastcall))
#define X
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
static WNDPROC previousProc;static HWND gameWindow;
void __cdecl PawUiTick(void);
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

#ifdef PAW_QA
static unsigned char FC qa_recon_cast(U self,U unused,U x,U y);
#endif
static int install(void){unsigned i;static const U inverses[]={0xd5000,0xd5785,0x2a4570,0x2a47ee};static const U projections[]={0x2a43fa,0x2a4430,0x2a4466,0x2a449c};
 if(!pointer(0x500894+0xc,0x2a45de,(U)mini_update))return 1;
 for(i=0;i<4;i++)if(!call(inverses[i],0x2a42aa,(U)inverse)||!call(projections[i],0x2a495a,(U)project))return 1;
 if(!call(0x2b1ae6,0x17844b,(U)map_draw)||!commit())return 1;
 return 0;
}
int __cdecl PawUiStart(const Host*h){U threads;if(!h||h->api!=1)return 1;host=h;base=h->exeBase;threads=P(base,0x5ef728);mainThread=P(threads,0x48);return mainThread?0:1;}
int __cdecl PawUiInstall(void){return install();}
void __cdecl PawUiUndo(void){unsigned i=writeCount;DWORD old;while(i){Write*w=&writes[--i];if(!memcmp((void*)w->at,w->after,w->size)&&VirtualProtect((void*)w->at,w->size,PAGE_EXECUTE_READWRITE,&old)){memcpy((void*)w->at,w->before,w->size);VirtualProtect((void*)w->at,w->size,old,&old);FlushInstructionCache(GetCurrentProcess(),(void*)w->at,w->size);}}}

void __cdecl PawUiTick(void){if(busy||GetCurrentThreadId()!=mainThread)return;busy=1;if(!previousProc){EnumWindows(find_window,(LPARAM)&gameWindow);if(gameWindow){previousProc=(WNDPROC)SetWindowLongPtrW(gameWindow,GWLP_WNDPROC,(LONG_PTR)window_proc);}}
 day_clock_tick();

 busy=0;
}
