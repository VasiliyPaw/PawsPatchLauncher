/* Local diagnostic for Kohan II. No networking, game-logic edits or DRM changes.
 * The real system d3d9 remains responsible for rendering and Steam integration.
 * Only demonstrably out-of-bounds indexed draws are skipped and recorded.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <stdint.h>
#include <string.h>
#include "d3d_abi_slots.h"

typedef struct { void **vt; } Com;
/* D3DINDEXBUFFER_DESC, as specified by the public Direct3D 9 ABI. */
typedef struct { DWORD format, type, usage, pool, size; } IndexDesc;
typedef HRESULT (WINAPI *DrawFn)(Com*,UINT,INT,UINT,UINT,UINT,UINT);
typedef HRESULT (WINAPI *CreateFn)(Com*,UINT,UINT,HWND,DWORD,void*,Com**);
typedef HRESULT (WINAPI *CreateExFn)(Com*,UINT,UINT,HWND,DWORD,void*,void*,Com**);
typedef struct { void **vt; void *original; } Hook;
static Hook devices[16], factories[16], factoriesEx[16];
static unsigned deviceCount,factoryCount,factoryExCount;
static HMODULE selfModule,realModule;
static CRITICAL_SECTION initLock,logLock;
static LONG draws,skipped,unchecked;
static DWORD lastSummary;
static HANDLE logFile=INVALID_HANDLE_VALUE;
static int testing;
static DrawFn systemDraw;
static void *systemDrawEntry;
static LONGLONG exchange8(volatile LONGLONG *address,LONGLONG value,LONGLONG expected) {
    DWORD lo=(DWORD)expected,hi=(DWORD)((uint64_t)expected>>32);
    __asm__ __volatile__("lock cmpxchg8b %2"
        : "+a"(lo), "+d"(hi), "+m"(*address)
        : "b"((DWORD)value), "c"((DWORD)((uint64_t)value>>32))
        : "cc", "memory");
    return (LONGLONG)(((uint64_t)hi<<32)|lo);
}
/* A bounded history is retained in memory for the next full dump, without
 * writing every draw to disk. Exported names make it easy to locate in CDB. */
typedef struct {
    LONG sequence; DWORD tick,thread,type; INT base;
    UINT min,vertices,first,primitives,format,size;
    uint64_t required; int valid; Com *buffer;
} DrawRecord;
__declspec(dllexport) volatile LONG PawGuardRecentCursor;
__declspec(dllexport) volatile DrawRecord PawGuardRecentDraws[256];

static void log_line(const char *format,...) {
    char line[1800]; SYSTEMTIME st; va_list args; DWORD bytes;
    if(testing) return;
    EnterCriticalSection(&logLock);
    if(logFile==INVALID_HANDLE_VALUE) {
        wchar_t path[MAX_PATH],*slash;
        GetModuleFileNameW(selfModule,path,MAX_PATH);
        slash=wcsrchr(path,L'\\');
        if(slash) wcscpy(slash+1,L"paws_graphics_guard.log");
        logFile=CreateFileW(path,FILE_APPEND_DATA,FILE_SHARE_READ|FILE_SHARE_WRITE,NULL,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
    }
    GetLocalTime(&st);
    int n=snprintf(line,sizeof(line),"%04u-%02u-%02u %02u:%02u:%02u pid=%lu ",st.wYear,st.wMonth,st.wDay,st.wHour,st.wMinute,st.wSecond,GetCurrentProcessId());
    va_start(args,format); vsnprintf(line+n,sizeof(line)-n-3,format,args); va_end(args);
    strcat(line,"\r\n");
    if(logFile!=INVALID_HANDLE_VALUE) WriteFile(logFile,line,(DWORD)strlen(line),&bytes,NULL);
    LeaveCriticalSection(&logLock);
}

static FARPROC resolve(const char *name) {
    EnterCriticalSection(&initLock);
    if(!realModule) {
        wchar_t path[MAX_PATH]; UINT n=GetSystemDirectoryW(path,MAX_PATH);
        if(n && n<MAX_PATH-11) { wcscat(path,L"\\d3d9.dll"); realModule=LoadLibraryW(path); }
        log_line("guard-v2 system_d3d9=%p",realModule);
    }
    FARPROC result=realModule?GetProcAddress(realModule,name):NULL;
    LeaveCriticalSection(&initLock);
    return result;
}

static void *original(Hook *table,unsigned count,Com *object) {
    unsigned i;
    for(i=0;i<count;++i) if(table[i].vt==object->vt) return table[i].original;
    return NULL;
}

static int patch(Hook *table,unsigned *count,Com *obj,unsigned slot,void *replacement) {
    DWORD oldProtect,ignored; unsigned i; int result=0;
    EnterCriticalSection(&initLock);
    for(i=0;i<*count;++i) if(table[i].vt==obj->vt) { result=1; goto done; }
    if(*count>=16 || obj->vt[slot]==replacement) goto done;
    if(!VirtualProtect(&obj->vt[slot],sizeof(void*),PAGE_READWRITE,&oldProtect)) goto done;
    table[*count].vt=obj->vt; table[*count].original=obj->vt[slot];
    ++*count;
    InterlockedExchangePointer(&obj->vt[slot],replacement);
    VirtualProtect(&obj->vt[slot],sizeof(void*),oldProtect,&ignored);
    result=1;
done:
    LeaveCriticalSection(&initLock);
    return result;
}

static int range_valid(UINT type,UINT count,UINT first,UINT format,UINT size,uint64_t *required) {
    uint64_t indices;
    if(!count) { *required=0; return 1; }
    switch(type) {
        case 2: indices=(uint64_t)count*2; break; /* LINELIST */
        case 3: indices=(uint64_t)count+1; break; /* LINESTRIP */
        case 4: indices=(uint64_t)count*3; break; /* TRIANGLELIST */
        case 5: case 6: indices=(uint64_t)count+2; break;
        default: *required=0; return -1;
    }
    if(format!=101 && format!=102) { *required=0; return -1; }
    *required=((uint64_t)first+indices)*(format==101?2:4);
    return *required<=size;
}

static void log_stack(void) {
    typedef USHORT (WINAPI *CaptureFn)(ULONG,ULONG,PVOID*,PULONG);
    CaptureFn capture=(CaptureFn)GetProcAddress(GetModuleHandleA("kernel32.dll"),"RtlCaptureStackBackTrace");
    void *frames[18]; USHORT n,i;
    if(!capture)return;
    n=capture(1,18,frames,NULL);
    for(i=0;i<n;++i) {
        MEMORY_BASIC_INFORMATION info;
        if(VirtualQuery(frames[i],&info,sizeof(info)))
            log_line("  stack[%u]=%p module=%p offset=0x%lx",i,frames[i],info.AllocationBase,(DWORD)((char*)frames[i]-(char*)info.AllocationBase));
    }
}

static HRESULT WINAPI guarded_draw(Com *dev,UINT type,INT base,UINT min,UINT vertices,UINT first,UINT count) {
    typedef HRESULT (WINAPI *GetFn)(Com*,Com**);
    typedef HRESULT (WINAPI *DescFn)(Com*,IndexDesc*);
    typedef ULONG (WINAPI *ReleaseFn)(Com*);
    DrawFn next=testing?(DrawFn)original(devices,deviceCount,dev):systemDraw;
    Com *indices=NULL; IndexDesc desc; HRESULT status;
    uint64_t required=0; int valid=-1; DWORD now;
    memset(&desc,0,sizeof(desc));
    InterlockedIncrement(&draws);
    status=((GetFn)dev->vt[SLOT_IDirect3DDevice9_GetIndices])(dev,&indices);
    if(SUCCEEDED(status) && indices) {
        memset(&desc,0,sizeof(desc));
        status=((DescFn)indices->vt[SLOT_IDirect3DIndexBuffer9_GetDesc])(indices,&desc);
        if(SUCCEEDED(status)) valid=range_valid(type,count,first,desc.format,desc.size,&required);
        ((ReleaseFn)indices->vt[2])(indices); /* GetIndices adds a reference. */
    }
    now=GetTickCount();
    LONG sequence=InterlockedIncrement(&PawGuardRecentCursor);
    volatile DrawRecord *record=&PawGuardRecentDraws[(sequence-1)&255];
    record->sequence=0;record->tick=now;record->thread=GetCurrentThreadId();
    record->type=type;record->base=base;record->min=min;record->vertices=vertices;
    record->first=first;record->primitives=count;record->format=desc.format;
    record->size=desc.size;record->required=required;record->valid=valid;record->buffer=indices;
    InterlockedExchange(&record->sequence,sequence);
    if(valid==0) {
        LONG number=InterlockedIncrement(&skipped);
        if(number<=12 || now-lastSummary>=5000) {
            log_line("INVALID_DRAW #%ld type=%u base=%d min=%u vertices=%u first=%u primitives=%u format=%lu buffer_bytes=%lu required_bytes=%llu buffer=%p",number,type,base,min,vertices,first,count,desc.format,desc.size,(unsigned long long)required,indices);
            if(number<=12)log_stack();
        }
    } else if(valid<0) InterlockedIncrement(&unchecked);
    if(now-lastSummary>=5000) {
        lastSummary=now;
        log_line("summary indexed_draws=%ld skipped=%ld unchecked=%ld",draws,skipped,unchecked);
    }
    if(valid==0)return S_OK;
    return next?next(dev,type,base,min,vertices,first,count):(HRESULT)0x8876086c;
}

static int hook_draw_entry(void *entry) {
    /* The game changes its per-device vtable after the first two draws. Patch
     * the verified system method entry instead. No DLL on disk is modified.
     * Its five-byte prologue has no relative operands. An aligned 8-byte CAS
     * prevents another thread from seeing a partially written branch. */
    static const BYTE prologue[5]={0x8b,0xff,0x55,0x8b,0xec};
    MEMORY_BASIC_INFORMATION info;DWORD oldProtect,ignored;
    BYTE *trampoline;BYTE branch[8];LONGLONG oldBytes,newBytes;
    HMODULE pinned=NULL;int result=0;
    EnterCriticalSection(&initLock);
    if(systemDrawEntry) { result=systemDrawEntry==entry;goto done; }
    if(((uintptr_t)entry&7)!=0 || !VirtualQuery(entry,&info,sizeof(info)) || info.AllocationBase!=realModule)goto done;
    if(memcmp(entry,prologue,sizeof(prologue))!=0)goto done;
    if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(LPCSTR)selfModule,&pinned))goto done;
    trampoline=(BYTE*)VirtualAlloc(NULL,16,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);
    if(!trampoline)goto done;
    memcpy(trampoline,entry,5);trampoline[5]=0xe9;
    *(DWORD*)(trampoline+6)=(DWORD)((uintptr_t)entry+5-((uintptr_t)trampoline+10));
    if(!VirtualProtect(trampoline,16,PAGE_EXECUTE_READ,&ignored)) {VirtualFree(trampoline,0,MEM_RELEASE);goto done;}
    FlushInstructionCache(GetCurrentProcess(),trampoline,10);
    memcpy(&oldBytes,entry,8);memcpy(branch,entry,8);branch[0]=0xe9;
    *(DWORD*)(branch+1)=(DWORD)((uintptr_t)guarded_draw-((uintptr_t)entry+5));
    memcpy(&newBytes,branch,8);
    if(!VirtualProtect(entry,8,PAGE_EXECUTE_READWRITE,&oldProtect)) {VirtualFree(trampoline,0,MEM_RELEASE);goto done;}
    systemDraw=(DrawFn)trampoline;
    if(exchange8((volatile LONGLONG*)entry,newBytes,oldBytes)!=oldBytes) {
        systemDraw=NULL;VirtualProtect(entry,8,oldProtect,&ignored);VirtualFree(trampoline,0,MEM_RELEASE);goto done;
    }
    systemDrawEntry=entry;
    FlushInstructionCache(GetCurrentProcess(),entry,8);
    VirtualProtect(entry,8,oldProtect,&ignored);
    result=1;
done:
    LeaveCriticalSection(&initLock);
    return result;
}
static void hook_device(Com *dev) {
    if(!dev)return;
    if(testing) {patch(devices,&deviceCount,dev,SLOT_IDirect3DDevice9_DrawIndexedPrimitive,(void*)guarded_draw);return;}
    void *entry=dev->vt[SLOT_IDirect3DDevice9_DrawIndexedPrimitive];
    log_line("device=%p DrawIndexedPrimitive_entry=%p entry_guard=%d",dev,entry,hook_draw_entry(entry));
}
static HRESULT WINAPI create_device(Com *d3d,UINT adapter,UINT type,HWND window,DWORD flags,void *params,Com **out) {
    CreateFn fn=(CreateFn)original(factories,factoryCount,d3d);
    HRESULT result=fn?fn(d3d,adapter,type,window,flags,params,out):E_FAIL;
    if(SUCCEEDED(result) && out)hook_device(*out);
    return result;
}
static HRESULT WINAPI create_device_ex(Com *d3d,UINT adapter,UINT type,HWND window,DWORD flags,void *params,void *mode,Com **out) {
    CreateExFn fn=(CreateExFn)original(factoriesEx,factoryExCount,d3d);
    HRESULT result=fn?fn(d3d,adapter,type,window,flags,params,mode,out):E_FAIL;
    if(SUCCEEDED(result) && out)hook_device(*out);
    return result;
}
__declspec(dllexport) Com* WINAPI Direct3DCreate9(UINT version) {
    typedef Com* (WINAPI *Fn)(UINT); Fn fn=(Fn)resolve("Direct3DCreate9");
    Com *obj=fn?fn(version):NULL;
    if(obj)log_line("Direct3DCreate9 factory_guard=%d",patch(factories,&factoryCount,obj,16,(void*)create_device));
    return obj;
}
__declspec(dllexport) HRESULT WINAPI Direct3DCreate9Ex(UINT version,Com **out) {
    typedef HRESULT (WINAPI *Fn)(UINT,Com**); Fn fn=(Fn)resolve("Direct3DCreate9Ex");
    HRESULT hr=fn?fn(version,out):E_FAIL;
    if(SUCCEEDED(hr)&&out&&*out) {
        patch(factories,&factoryCount,*out,16,(void*)create_device);
        patch(factoriesEx,&factoryExCount,*out,20,(void*)create_device_ex);
    }
    return hr;
}
__declspec(dllexport) int WINAPI D3DPERF_BeginEvent(DWORD color,LPCWSTR name) { typedef int(WINAPI*Fn)(DWORD,LPCWSTR); Fn f=(Fn)resolve("D3DPERF_BeginEvent");return f?f(color,name):-1; }
__declspec(dllexport) int WINAPI D3DPERF_EndEvent(void) { typedef int(WINAPI*Fn)(void); Fn f=(Fn)resolve("D3DPERF_EndEvent");return f?f():-1; }
__declspec(dllexport) void WINAPI D3DPERF_SetMarker(DWORD color,LPCWSTR name) { typedef void(WINAPI*Fn)(DWORD,LPCWSTR); Fn f=(Fn)resolve("D3DPERF_SetMarker");if(f)f(color,name); }
__declspec(dllexport) void WINAPI D3DPERF_SetRegion(DWORD color,LPCWSTR name) { typedef void(WINAPI*Fn)(DWORD,LPCWSTR); Fn f=(Fn)resolve("D3DPERF_SetRegion");if(f)f(color,name); }
__declspec(dllexport) void WINAPI D3DPERF_SetOptions(DWORD value) { typedef void(WINAPI*Fn)(DWORD); Fn f=(Fn)resolve("D3DPERF_SetOptions");if(f)f(value); }
__declspec(dllexport) DWORD WINAPI D3DPERF_GetStatus(void) { typedef DWORD(WINAPI*Fn)(void); Fn f=(Fn)resolve("D3DPERF_GetStatus");return f?f():0; }
__declspec(dllexport) BOOL WINAPI D3DPERF_QueryRepeatFrame(void) { typedef BOOL(WINAPI*Fn)(void); Fn f=(Fn)resolve("D3DPERF_QueryRepeatFrame");return f?f():FALSE; }
__declspec(dllexport) void* WINAPI Direct3DShaderValidatorCreate9(void) { typedef void*(WINAPI*Fn)(void); Fn f=(Fn)resolve("Direct3DShaderValidatorCreate9");return f?f():NULL; }
__declspec(dllexport) void WINAPI DebugSetMute(void) { typedef void(WINAPI*Fn)(void); Fn f=(Fn)resolve("DebugSetMute");if(f)f(); }
__declspec(dllexport) void WINAPI DebugSetLevel(DWORD level) { typedef void(WINAPI*Fn)(DWORD); Fn f=(Fn)resolve("DebugSetLevel");if(f)f(level); }

/* Offline fake-COM validation, never calls the user's game or graphics driver. */
static void *fakeDevVt[119],*fakeIndexVt[14];
static Com fakeDev={fakeDevVt},fakeIndex={fakeIndexVt};
static UINT fakeSize,fakeFormat; static LONG refs,forwarded;
static HRESULT WINAPI fake_get(Com*d,Com**out) { *out=&fakeIndex;++refs;return S_OK; }
static HRESULT WINAPI fake_desc(Com*i,IndexDesc*out) { memset(out,0,sizeof(*out));out->size=fakeSize;out->format=fakeFormat;return S_OK; }
static ULONG WINAPI fake_release(Com*i) { return --refs; }
static HRESULT WINAPI fake_draw(Com*d,UINT t,INT b,UINT m,UINT v,UINT f,UINT c) { ++forwarded;return 123; }
__declspec(dllexport) int WINAPI PawGuardSelfTest(void) {
    UINT i;uint64_t required;int errors=0;
    struct { UINT type,count,first,format,size;int expected; } cases[]={
        {4,2,0,101,12,1},{4,3,0,101,12,0},{4,2,1,101,12,0},
        {4,2,0,102,24,1},{4,2,0,102,23,0},{5,4,0,101,12,1},
        {6,4,0,101,11,0},{2,3,0,101,12,1},{3,5,0,101,12,1},
        {4,0xffffffffu,0xffffffffu,102,0xffffffffu,0},
        {4,0,0,101,0,1},{1,1,0,101,12,-1},{4,2,0,0,12,-1},
        {4,43708,0,101,120,0},{4,436,0,101,2616,1}
    };
    testing=1;
    volatile LONGLONG cell=0x1122334455667788LL;
    if(exchange8(&cell,0x1234567890abcdefLL,0x1122334455667788LL)!=0x1122334455667788LL || cell!=0x1234567890abcdefLL)++errors;
    if(exchange8(&cell,0,7)!=0x1234567890abcdefLL || cell!=0x1234567890abcdefLL)++errors;
    for(i=0;i<sizeof(cases)/sizeof(cases[0]);++i)
        if(range_valid(cases[i].type,cases[i].count,cases[i].first,cases[i].format,cases[i].size,&required)!=cases[i].expected)++errors;
    fakeDevVt[82]=(void*)fake_draw;fakeDevVt[SLOT_IDirect3DDevice9_GetIndices]=(void*)fake_get;
    fakeIndexVt[13]=(void*)fake_desc;fakeIndexVt[2]=(void*)fake_release;
    hook_device(&fakeDev);fakeSize=12;fakeFormat=101;
    if(((DrawFn)fakeDev.vt[82])(&fakeDev,4,0,0,4,0,2)!=123 || forwarded!=1 || refs!=0)++errors;
    if(((DrawFn)fakeDev.vt[82])(&fakeDev,4,0,0,4,0,3)!=S_OK || forwarded!=1 || refs!=0 || skipped!=1)++errors;
    fakeFormat=0;
    if(((DrawFn)fakeDev.vt[82])(&fakeDev,4,0,0,4,0,2)!=123 || forwarded!=2 || refs!=0)++errors;
    return errors;
}
BOOL WINAPI DllMain(HINSTANCE module,DWORD reason,LPVOID reserved) {
    if(reason==DLL_PROCESS_ATTACH) {
        selfModule=module;InitializeCriticalSection(&initLock);InitializeCriticalSection(&logLock);DisableThreadLibraryCalls(module);
    } else if(reason==DLL_PROCESS_DETACH) {
        if(logFile!=INVALID_HANDLE_VALUE)CloseHandle(logFile);
    }
    return TRUE;
}
