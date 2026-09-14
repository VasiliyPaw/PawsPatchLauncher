/* Local review: extends the native pre-admission version comparison.
 * Stock depot/data checks, password checks, Steam and simulation remain native.
 * No worker thread, sockets, polling or files are used by the game-side code.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <string.h>
#include <wchar.h>
#include <stdio.h>

#define TOKEN_MAX 256
#define MAGIC 0x31434C50u
typedef void *(__attribute__((fastcall)) *Ctor)(void*,void*,const wchar_t*);
typedef void *(__attribute__((fastcall)) *Assign)(void*,void*,const void*);
typedef void (__attribute__((fastcall)) *Release)(void*,void*);
typedef void (__cdecl *ReasonWrite)(void*,int);
typedef void (__cdecl *ReasonRead)(void*,int*);
typedef void (__cdecl *Bits)(void*,void*,int);
typedef struct { uint32_t magic; int russian; char token[TOKEN_MAX]; } Config;
static uintptr_t image;
static Config local;
static wchar_t localWide[TOKEN_MAX], remoteWide[TOKEN_MAX];
static int remoteValid;
static void *formatThunk;
static Ctor ctor;
static Assign assign;
static Release releaseString;
static ReasonWrite writeReason;
static ReasonRead readReason;
static Bits writeBits,readBits;
__declspec(dllexport) volatile LONG PawLobbyVersionsSent;
__declspec(dllexport) volatile LONG PawLobbyRequirementsSent;
__declspec(dllexport) volatile LONG PawLobbyRequirementsRead;
__declspec(dllexport) volatile LONG PawLobbyMismatchDialogs;
__declspec(dllexport) volatile LONG PawLobbyInstallStatus;

/* Canonical ASCII identity: protocol|game|mod|modVersion|patchVersion|digest.
 * The digest covers actual executable/helper bytes and the applied non-language
 * package manifest/settings. Native game checks still validate the loaded data.
 * Input limits are independent of C string terminators and network allocation.
 */
static int valid_token(const char *s, unsigned n) {
    unsigned i,start=0,field=0;
    if(n<80 || n>=TOKEN_MAX || memcmp(s,"PWLC1|",6)) return 0;
    for(i=0;i<n;i++) {
        unsigned char c=s[i];
        if(c=='|') {
            if(i==start || i-start>48 || ++field>5) return 0;
            if(field==3 && !((i-start==7&&!memcmp(s+start,"vanilla",7)) ||
                (i-start==9&&!memcmp(s+start,"immortals",9)) ||
                (i-start==11&&!memcmp(s+start,"arcane-wars",11)))) return 0;
            start=i+1;
        } else if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='.'||c=='-'||c=='_'||c=='+')) return 0;
    }
    if(field!=5 || n-start!=64) return 0;
    for(i=start;i<n;i++) if(!((s[i]>='0'&&s[i]<='9')||(s[i]>='A'&&s[i]<='F'))) return 0;
    return 1;
}
static void widen(wchar_t *dst,const char *src,unsigned n) {
    unsigned i;for(i=0;i<n;i++) dst[i]=(unsigned char)src[i];dst[n]=0;
}
static void describe(const wchar_t *token,wchar_t *out) {
    wchar_t copy[TOKEN_MAX],*fields[6],*p; unsigned i=1;
    wcscpy(copy,token); fields[0]=copy;
    for(p=copy;*p;p++) if(*p==L'|') {*p=0;fields[i++]=p+1;}
    const wchar_t *mod=!wcscmp(fields[2],L"vanilla")?L"Vanilla":!wcscmp(fields[2],L"immortals")?L"Immortals":L"Arcane Wars";
    const wchar_t *patch=!wcscmp(fields[4],L"off")?(local.russian?L"выключен":L"off"):fields[4];
    /* All fields were bounded and restricted to printable ASCII by valid_token. */
    wsprintfW(out,local.russian?L"Игра: %s\n%s %s\nPaw's Patch: %s":L"Game: %s\n%s %s\nPaw's Patch: %s",fields[1],mod,fields[3],patch);
}
static void build_message(wchar_t *out) {
    wchar_t mine[240],required[240];
    describe(localWide,mine);
    if(remoteValid) describe(remoteWide,required);
    else wcscpy(required,local.russian?L"Хозяин не передал версии мода и патча.\nВозможно, новая проверка ещё не установлена.":L"The host did not provide mod and patch versions.\nThe new compatibility check may not be installed.");
    wsprintfW(out,local.russian?
        L"Несовместимая конфигурация лобби\n\nУ вас:\n%s\n\nДля этого лобби:\n%s\n\nВерсии и компоненты должны совпадать.\nВыберите нужный мод и примените настройки в лаунчере.":
        L"Incompatible lobby configuration\n\nYour installation:\n%s\n\nRequired for this lobby:\n%s\n\nVersions and components must match.\nSelect the required mod and apply settings in the launcher.",mine,required);
}

/* Original version getter is __thiscall with one stack argument; __stdcall
 * has the same stack cleanup here, and the old ECX receiver is not needed. */
static void * WINAPI version_string(void *out) {
    remoteValid=0;
    InterlockedIncrement(&PawLobbyVersionsSent);
    return ctor(out,0,localWide);
}
static void __cdecl write_disconnect(void *stream,int reason) {
    writeReason(stream,reason);
    if(reason==2) {
        uint32_t magic=MAGIC; uint16_t length=(uint16_t)strlen(local.token);
        writeBits(stream,&magic,32); writeBits(stream,&length,16);
        writeBits(stream,local.token,length*8);
        InterlockedIncrement(&PawLobbyRequirementsSent);
    }
}
static int available_bits(void *stream,unsigned bits) {
    uint32_t *s=stream,bytes=s[2],bit=s[3];
    const unsigned char *buffer=(const unsigned char*)(uintptr_t)s[1];
    /* Native TGC byte buffer stores its readable size at data-4. */
    if(!buffer || bit>8) return 0;
    uint32_t size=*(const uint32_t*)(buffer-4);
    if(size>65536 || bytes>size) return 0;
    return (uint64_t)bytes*8+bit+bits<=(uint64_t)size*8;
}
static void __cdecl read_disconnect(void *stream,int *reason) {
    remoteValid=0;
    readReason(stream,reason);
    if(*reason!=2 || !available_bits(stream,48)) return;
    uint32_t magic=0; uint16_t length=0; char token[TOKEN_MAX]={0};
    readBits(stream,&magic,32);
    if(magic!=MAGIC) return;
    readBits(stream,&length,16);
    if(length==0 || length>=TOKEN_MAX || !available_bits(stream,length*8)) return;
    readBits(stream,token,length*8);
    if(!valid_token(token,length)) return;
    widen(remoteWide,token,length); remoteValid=1;
    InterlockedIncrement(&PawLobbyRequirementsRead);
}
static void *__cdecl format_disconnect(void *dst,const void *src,int reason) {
    if(reason!=2) return assign(dst,0,src);
    wchar_t message[1024]; void *text=0;
    build_message(message);
    ctor(&text,0,message);
    void *result=assign(dst,0,&text);
    releaseString((char*)text-16,0);
    remoteValid=0;
    InterlockedIncrement(&PawLobbyMismatchDialogs);
    return result;
}

static const uint32_t sites[]={0x151092,0x150e40,0x151c8a,0x1519ef,0x151bf3};
static const uint32_t originals[]={0x7c92f,0x7c92f,0x149033,0x149046,0x23fb6};
static void call_bytes(unsigned char *out,uintptr_t site,uintptr_t dest) {
    out[0]=0xe8;uint32_t delta=(uint32_t)(dest-site-5);memcpy(out+1,&delta,4);
}
/* Called by the fresh-launch installer (or explicit menu review tool) while
 * pre-existing game threads are suspended. Guard every site before writing. */
__declspec(dllexport) DWORD WINAPI PawInstall(void *raw) {
    Config *cfg=raw;unsigned i;int failed=0;DWORD old;unsigned char expect[5],branch[5];
    if(PawLobbyInstallStatus) return 10;
    if(!cfg||cfg->magic!=MAGIC||(cfg->russian!=0&&cfg->russian!=1)) return 11;
    unsigned n=0;while(n<TOKEN_MAX&&cfg->token[n])n++;
    if(!valid_token(cfg->token,n)) return 12;
    /* Read the main image from the x86 PEB without taking the loader lock:
       other game threads are paused during this short transaction. */
    uintptr_t peb;
    __asm__("movl %%fs:0x30, %0":"=r"(peb));
    image=*(uintptr_t*)(peb+8);
    if(*(uint16_t*)image!=0x5a4d) return 13;
    for(i=0;i<5;i++) {
        call_bytes(expect,image+sites[i],image+originals[i]);
        if(memcmp((void*)(image+sites[i]),expect,5)) return 20+i;
    }
    memcpy(&local,cfg,sizeof local); widen(localWide,local.token,n);
    ctor=(Ctor)(image+0x205de);assign=(Assign)(image+0x23fb6);releaseString=(Release)(image+0x21375);
    writeReason=(ReasonWrite)(image+0x149033);readReason=(ReasonRead)(image+0x149046);
    writeBits=(Bits)(image+0x518fe);readBits=(Bits)(image+0x517cc);
    formatThunk=VirtualAlloc(0,64,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);
    if(!formatThunk) return 30;
    /* push ESI (reason), push original source, push ECX (target), call cdecl;
       pop arguments, ret 4 to preserve the replaced thiscall. */
    unsigned char thunk[]={0x56,0xff,0x74,0x24,0x08,0x51,0xe8,0,0,0,0,0x83,0xc4,0x0c,0xc2,0x04,0};
    call_bytes(thunk+6,(uintptr_t)formatThunk+6,(uintptr_t)format_disconnect);
    memcpy(formatThunk,thunk,sizeof thunk);
    if(!VirtualProtect(formatThunk,64,PAGE_EXECUTE_READ,&old)) return 31;
    FlushInstructionCache(GetCurrentProcess(),formatThunk,64);
    void *targets[]={version_string,version_string,write_disconnect,read_disconnect,formatThunk};
    for(i=0;i<5;i++) {
        void *site=(void*)(image+sites[i]);
        if(!VirtualProtect(site,5,PAGE_EXECUTE_READWRITE,&old)) {failed=1;break;}
        call_bytes(branch,(uintptr_t)site,(uintptr_t)targets[i]);memcpy(site,branch,5);
        DWORD ignored;
        if(!VirtualProtect(site,5,old,&ignored)) {failed=1;i++;break;}
        FlushInstructionCache(GetCurrentProcess(),site,5);
    }
    if(failed) {
        while(i) {--i;void *site=(void*)(image+sites[i]);
            if(VirtualProtect(site,5,PAGE_EXECUTE_READWRITE,&old)) {
                call_bytes(expect,(uintptr_t)site,image+originals[i]);memcpy(site,expect,5);
                DWORD ignored;VirtualProtect(site,5,old,&ignored);FlushInstructionCache(GetCurrentProcess(),site,5);
            }
        }
        PawLobbyInstallStatus=-1;return 40;
    }
    PawLobbyInstallStatus=1; return 0;
}
BOOL WINAPI DllMain(HINSTANCE instance,DWORD reason,LPVOID unused) {return TRUE;}

/* Finish Windows DLL_THREAD_ATTACH before the launcher pauses other threads.
 * The ready/go rendezvous avoids suspending a thread that owns the loader lock. */
typedef struct {volatile LONG ready;volatile LONG go;DWORD result;Config config;} InstallRequest;
__declspec(dllexport) DWORD WINAPI PawInstallQueued(void *raw) {
    InstallRequest *request=raw;
    if(!request)return 50;
    InterlockedExchange(&request->ready,1);
    while(!request->go)Sleep(1);
    DWORD result=PawInstall(&request->config);request->result=result;
    InterlockedExchange(&request->ready,2);
    return result;
}

#ifdef PAW_TEST
int main(void) {
    const char *token="PWLC1|1.3.72|arcane-wars|0.82.1.8|0.3.0-beta.6|0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF";
    unsigned n=strlen(token),checks=0,i;
    if(!valid_token(token,n)) return 1;checks++;
    for(i=0;i<n;i++) {char bad[TOKEN_MAX];memcpy(bad,token,n);bad[i]='\n';if(valid_token(bad,n))return 2;checks++;}
    for(i=0;i<n;i++) {if(valid_token(token,i))return 3;checks++;}
    strcpy(local.token,token);widen(localWide,token,n);widen(remoteWide,token,n);remoteValid=1;
    for(i=0;i<2;i++){local.russian=i;wchar_t out[1024];build_message(out);if(wcslen(out)>900||!wcsstr(out,L"0.3.0-beta.6"))return 4;checks++;}
    printf("PASS %u protocol/parser/format checks\n",checks);return 0;
}
#endif
