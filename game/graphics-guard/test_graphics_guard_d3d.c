/* Hidden, independent D3D9 test window. Does not start or attach to Kohan II. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include "d3d_abi_slots.h"
typedef struct {void **vt;} Com;
typedef struct { UINT width,height,format,count,multi,quality,swap;HWND window;BOOL windowed,depth;UINT depthFormat,flags,refresh,interval;} Params;
typedef HRESULT(WINAPI*DrawFn)(Com*,UINT,INT,UINT,UINT,UINT,UINT);
typedef ULONG(WINAPI*ReleaseFn)(Com*);
typedef struct {float x,y,z,rhw;DWORD color;} Vertex;
int main(int argc,char**argv) {
    HRESULT hr;Com *api=NULL,*dev=NULL,*vb=NULL,*ib=NULL;void *memory=NULL;
    HMODULE dll;HWND window;Params params;WNDCLASSA wc;Vertex vertices[3]={{10,10,0,1,0xffffffff},{80,10,0,1,0xffffffff},{10,80,0,1,0xffffffff}};WORD indices[3]={0,1,2};
    if(argc!=2)return 2;
    dll=LoadLibraryA(argv[1]);if(!dll)return 3;
    typedef Com*(WINAPI*Factory)(UINT);
    Factory create=(Factory)GetProcAddress(dll,"Direct3DCreate9");if(!create)return 4;
    memset(&wc,0,sizeof(wc));wc.lpfnWndProc=DefWindowProcA;wc.hInstance=GetModuleHandleA(NULL);wc.lpszClassName="PawGuardHiddenValidation";
    RegisterClassA(&wc);
    window=CreateWindowExA(0,wc.lpszClassName,"Hidden diagnostic validation",WS_OVERLAPPEDWINDOW,0,0,128,128,NULL,NULL,wc.hInstance,NULL);
    if(!window)return 5;
    api=create(32);if(!api)return 6;
    memset(&params,0,sizeof(params));params.width=128;params.height=128;params.count=1;params.swap=1;params.window=window;params.windowed=TRUE;
    typedef HRESULT(WINAPI*CreateDev)(Com*,UINT,UINT,HWND,DWORD,Params*,Com**);
    hr=((CreateDev)api->vt[16])(api,0,1,window,0x20,&params,&dev);if(FAILED(hr)){printf("CreateDevice failed %lx\n",hr);return 7;}
    typedef HRESULT(WINAPI*CreateBuffer)(Com*,UINT,DWORD,UINT,UINT,Com**,HANDLE*);
    hr=((CreateBuffer)dev->vt[26])(dev,sizeof(vertices),0,0x44,1,&vb,NULL);if(FAILED(hr))return 8;
    hr=((CreateBuffer)dev->vt[27])(dev,sizeof(indices),0,101,1,&ib,NULL);if(FAILED(hr))return 9;
    typedef HRESULT(WINAPI*Lock)(Com*,UINT,UINT,void**,DWORD);
    typedef HRESULT(WINAPI*Simple)(Com*);
    hr=((Lock)vb->vt[11])(vb,0,sizeof(vertices),&memory,0);if(FAILED(hr))return 10;
    memcpy(memory,vertices,sizeof(vertices));((Simple)vb->vt[12])(vb);
    hr=((Lock)ib->vt[11])(ib,0,sizeof(indices),&memory,0);if(FAILED(hr))return 11;
    memcpy(memory,indices,sizeof(indices));((Simple)ib->vt[12])(ib);
    typedef HRESULT(WINAPI*Stream)(Com*,UINT,Com*,UINT,UINT);
    typedef HRESULT(WINAPI*SetFvf)(Com*,DWORD);
    typedef HRESULT(WINAPI*SetIb)(Com*,Com*);
    ((Stream)dev->vt[100])(dev,0,vb,0,sizeof(Vertex));
    ((SetFvf)dev->vt[89])(dev,0x44);((SetIb)dev->vt[SLOT_IDirect3DDevice9_SetIndices])(dev,ib);
    ((Simple)dev->vt[41])(dev);
    hr=((DrawFn)dev->vt[82])(dev,4,0,0,3,0,1);if(FAILED(hr)){printf("Valid draw failed %lx\n",hr);return 12;}
    hr=((DrawFn)dev->vt[82])(dev,4,0,0,3,0,2);if(hr!=S_OK)return 13;
    /* Reproduce the game's changed per-device table and a direct method call.
     * A vtable-only guard would not protect a restored original method entry. */
    void **initialTable=dev->vt;
    void **copiedTable=(void**)VirtualAlloc(NULL,119*sizeof(void*),MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);
    if(!copiedTable)return 14;
    memcpy(copiedTable,initialTable,119*sizeof(void*));
    DrawFn directDraw=(DrawFn)initialTable[82];
    dev->vt=copiedTable;
    hr=((DrawFn)dev->vt[82])(dev,4,0,0,3,0,2);if(hr!=S_OK)return 15;
    hr=directDraw(dev,4,0,0,3,0,2);if(hr!=S_OK)return 16;
    hr=directDraw(dev,4,0,0,3,0,1);if(FAILED(hr))return 17;
    dev->vt=initialTable;
    VirtualFree(copiedTable,0,MEM_RELEASE);
    ((Simple)dev->vt[42])(dev);
    ((SetIb)dev->vt[SLOT_IDirect3DDevice9_SetIndices])(dev,NULL);((Stream)dev->vt[100])(dev,0,NULL,0,0);
    ((ReleaseFn)ib->vt[2])(ib);((ReleaseFn)vb->vt[2])(vb);
    ((ReleaseFn)dev->vt[2])(dev);((ReleaseFn)api->vt[2])(api);
    DestroyWindow(window);
    puts("PASS: system D3D9 factory/device, valid draw, invalid draw guard, changed vtable, direct entry calls, resource release.");
    return 0;
}
