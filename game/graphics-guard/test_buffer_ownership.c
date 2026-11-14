/* Real D3D9 regression: a state block restores bindings without SetStreamSource. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
typedef struct{void**vt;}Com;
typedef struct{UINT w,h,f,count,multi,quality,swap;HWND window;BOOL windowed,depth;UINT df,flags,refresh,interval;}Params;
typedef ULONG(WINAPI*Ref)(Com*);
typedef HRESULT(WINAPI*Buffer)(Com*,UINT,DWORD,UINT,UINT,Com**,HANDLE*);
typedef void(WINAPI*Tick)(UINT,UINT,UINT,UINT);
typedef UINT(WINAPI*Stats)(UINT*,UINT);
typedef HRESULT(WINAPI*Stream)(Com*,UINT,Com*,UINT,UINT);
typedef HRESULT(WINAPI*GetStream)(Com*,UINT,Com**,UINT*,UINT*);
typedef HRESULT(WINAPI*Block)(Com*,UINT,Com**);
typedef HRESULT(WINAPI*Apply)(Com*);
static UINT indexKind;
static HRESULT set(Com*d,Com*p){typedef HRESULT(WINAPI*Set)(Com*,Com*);return indexKind?((Set)d->vt[104])(d,p):((Stream)d->vt[100])(d,0,p,0,p?32:0);}
static HRESULT get(Com*d,Com**p){typedef HRESULT(WINAPI*Get)(Com*,Com**);UINT offset,stride;return indexKind?((Get)d->vt[105])(d,p):((GetStream)d->vt[101])(d,0,p,&offset,&stride);}
#define CHECK(x) if(!(x)){printf("FAIL line=%u error=%lx\n",__LINE__,GetLastError());return 2;}
int main(int argc,char**argv){HMODULE dll;Com*api,*device,*a,*b,*state,*actual;Params pp;WNDCLASSA wc;HWND window;Tick tick;Stats stats;UINT values[10],i,flags=0x24;ULONG refs;
 typedef Com*(WINAPI*Factory)(UINT);typedef HRESULT(WINAPI*Create)(Com*,UINT,UINT,HWND,DWORD,Params*,Com**);
 CHECK(argc>=2);SetEnvironmentVariableA("PAWS_BUFFER_REUSE_TEST","1");dll=LoadLibraryA(argv[1]);CHECK(dll);Factory factory=(Factory)GetProcAddress(dll,"Direct3DCreate9");tick=(Tick)GetProcAddress(dll,"PawGpuTick");stats=(Stats)GetProcAddress(dll,"PawBufferPoolStats");CHECK(factory&&tick&&stats);
 memset(&wc,0,sizeof(wc));wc.lpfnWndProc=DefWindowProcA;wc.hInstance=GetModuleHandleA(NULL);wc.lpszClassName="GraphicsStateblockRegression";RegisterClassA(&wc);window=CreateWindowExA(0,wc.lpszClassName,"Owned stateblock test",WS_OVERLAPPEDWINDOW,0,0,128,128,NULL,NULL,wc.hInstance,NULL);CHECK(window);
 if(argc>3)indexKind=!strcmp(argv[3],"ib");if(argc>4)flags=strtoul(argv[4],NULL,0);printf("kind=%s vertexProcessingFlags=%x\n",indexKind?"IB":"VB",flags);
 api=factory(32);CHECK(api);memset(&pp,0,sizeof(pp));pp.w=pp.h=128;pp.count=1;pp.swap=1;pp.window=window;pp.windowed=TRUE;CHECK(SUCCEEDED(((Create)api->vt[16])(api,0,1,window,flags,&pp,&device)));tick(11,4,1,0);
 CHECK(SUCCEEDED(((Buffer)device->vt[indexKind?27:26])(device,128,8,indexKind?101:0xc02c2,1,&a,NULL)));CHECK(SUCCEEDED(set(device,a)));refs=((Ref)a->vt[2])(a);printf("after-client-release refs=%u pointer=%p\n",refs,a);
 if(argc>2&&!strcmp(argv[2],"record")){typedef HRESULT(WINAPI*Begin)(Com*);typedef HRESULT(WINAPI*End)(Com*,Com**);CHECK(SUCCEEDED(((Begin)device->vt[60])(device)));CHECK(SUCCEEDED(set(device,NULL)));CHECK(SUCCEEDED(((End)device->vt[61])(device,&state)));printf("record-only stateblock\n");}
 else{CHECK(SUCCEEDED(((Block)device->vt[59])(device,1,&state)));((Ref)a->vt[1])(a);refs=((Ref)a->vt[2])(a);printf("captured-state refs=%u\n",refs);CHECK(SUCCEEDED(set(device,NULL)));if(argc==2||(argc>2&&!strcmp(argv[2],"apply")))CHECK(SUCCEEDED(((Apply)state->vt[5])(state)));}
 CHECK(SUCCEEDED(get(device,&actual)));if(argc>2&&!strcmp(argv[2],"retained")){CHECK(!actual);printf("stateblock keeps old buffer while device binding is NULL\n");}else CHECK(actual==a);if(actual)((Ref)actual->vt[2])(actual);
 for(i=0;i<4;i++)tick(11,4,1,0);
 CHECK(SUCCEEDED(((Buffer)device->vt[indexKind?27:26])(device,128,8,indexKind?101:0xc02c2,1,&b,NULL)));stats(values,sizeof(values));printf("returned=%p protectedOriginal=%p reusedProtected=%u hits=%u busy=%u\n",b,a,b==a,values[1],values[7]);
 ((Ref)b->vt[2])(b);set(device,NULL);((Ref)state->vt[2])(state);tick(0,3,0,0);((Ref)device->vt[2])(device);((Ref)api->vt[2])(api);DestroyWindow(window);return b==a?1:0;
}
