/* Runs the actual 1.3.72 bit codec in an isolated test process, never in k2. */
#include "lobby_compatibility.c"
#include <stdlib.h>
static unsigned checks;
#define CHECK(x) do {checks++;if(!(x)){printf("FAIL line %d check %u\n",__LINE__,checks);exit(1);}}while(0)
static void rw(void *s,int r){writeBits(s,&r,4);}
static void rr(void *s,int *r){*r=0;readBits(s,r,4);}
static void patch_call(unsigned char *code,unsigned offset,void *fn) {call_bytes(code+offset,(uintptr_t)(code+offset),(uintptr_t)fn);}
int main(int argc,char **argv) {
    CHECK(sizeof(InstallRequest)==276);
    InstallRequest request;memset(&request,0,sizeof request);
    HANDLE worker=CreateThread(0,0,PawInstallQueued,&request,0,0);CHECK(worker!=0);
    DWORD startTime=GetTickCount();
    while(!request.ready&&GetTickCount()-startTime<5000)Sleep(1);
    CHECK(request.ready==1&&request.go==0);
    InterlockedExchange(&request.go,1);
    CHECK(WaitForSingleObject(worker,5000)==WAIT_OBJECT_0);CloseHandle(worker);
    CHECK(request.ready==2&&request.result==11); /* invalid config rejected */
    CHECK(argc==2);FILE *f=fopen(argv[1],"rb");CHECK(f!=0);
    unsigned char *code=VirtualAlloc(0,4096,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);CHECK(code!=0);
    CHECK(fseek(f,0x4b17cc-0x460000,SEEK_SET)==0);CHECK(fread(code,1,0x252,f)==0x252);fclose(f);
    patch_call(code,0x4b185d-0x4b17cc,memcpy);patch_call(code,0x4b1992-0x4b17cc,memcpy);
    /* Allocation is pre-sized in this harness. Preserve the native grow ABI. */
    code[0x300]=0xc2;code[0x301]=4;code[0x302]=0;
    patch_call(code,0x4b190e - 0x4b17cc,code+0x300);
    readBits=(Bits)code;writeBits=(Bits)(code+0x4b18fe - 0x4b17cc);writeReason=rw;readReason=rr;
    const char *t="PWLC1|1.3.72|arcane-wars|0.82.1.8|0.3.0-beta.6|0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF";
    strcpy(local.token,t);widen(localWide,t,strlen(t));
    unsigned char storage[1028],copy[1028];uint32_t s[4]={0,(uint32_t)(uintptr_t)(storage+4),0,0};
    unsigned start,reason,cut;
    for(start=0;start<=8;start++) for(reason=0;reason<14;reason++) {
        memset(storage,0,sizeof storage);*(uint32_t*)storage=1024;s[2]=0;s[3]=start;
        write_disconnect(s,reason);unsigned end=s[2]*8+s[3],size=(end+7)/8;
        *(uint32_t*)storage=size;memcpy(copy,storage,sizeof storage);
        s[2]=0;s[3]=start;int got=-1;remoteValid=1;
        read_disconnect(s,&got);CHECK(got==reason);CHECK(remoteValid==(reason==2));
        CHECK(s[2]*8+s[3]==end);
        if(reason==2) {
            CHECK(!wcscmp(localWide,remoteWide));
            for(cut=(start+4+7)/8;cut<size;cut++) {
                memcpy(storage,copy,sizeof storage);*(uint32_t*)storage=cut;s[2]=0;s[3]=start;remoteValid=1;
                read_disconnect(s,&got);CHECK(got==2);CHECK(!remoteValid);
            }
        }
    }
    /* Malicious extension lengths, magic and invalid tokens; no stale host. */
    for(start=0;start<=8;start++) for(cut=0;cut<6;cut++) {
        memset(storage,0,sizeof storage);*(uint32_t*)storage=1024;s[2]=0;s[3]=start;rw(s,2);
        uint32_t magic=cut==0?0:MAGIC;uint16_t len=cut==1?0:cut==2?256:cut==3?65535:(uint16_t)strlen(t);
        writeBits(s,&magic,32);writeBits(s,&len,16);char bad[256];strcpy(bad,t);bad[cut==4?0:20]='\n';writeBits(s,bad,strlen(t)*8);
        *(uint32_t*)storage=(s[2]*8+s[3]+7)/8;s[2]=0;s[3]=start;remoteValid=1;int got=0;
        read_disconnect(s,&got);CHECK(got==2);CHECK(!remoteValid);
    }
    /* TinyCC fastcall must place receiver in ECX and the third arg on stack,
       as required by the game's thiscall string functions. */
    unsigned char abi[]={0x8b,0x44,0x24,0x04,0x89,0x01,0x8b,0xc1,0xc2,0x04,0};
    memcpy(code+0x400,abi,sizeof abi);Ctor c=(Ctor)(code+0x400);void *got=0;
    CHECK(c(&got,0,localWide)==&got);CHECK(got==localWide);
    printf("PASS %u native codec, truncation, legacy reason and x86 ABI checks\n",checks);return 0;
}
