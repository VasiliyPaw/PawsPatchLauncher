/* Opt-in experiment: bounded quality test plus D3D's memory estimate.
 * The estimate also feeds CacheManager::SetSize; it is NOT merely a boolean.
 * Keep unsupported cutoffs/zero estimates on the original path.
 */
typedef unsigned(WINAPI*MemoryEstimate)(void*);
typedef HRESULT(WINAPI*MemoryTexture)(void*,unsigned,unsigned,unsigned,unsigned,unsigned,unsigned,void**,void*);
typedef unsigned(WINAPI*MemoryRelease)(void*);
typedef struct {unsigned estimate,cutoff,allocated,bytes,used;} MemoryResult;
static MemoryResult memoryResult;
static int memory_bounded(void*dev,int cutoff,MemoryResult*out){
 void*textures[256];unsigned n=0,estimate,i;HRESULT hr;
 MemoryTexture make=(MemoryTexture)(*(void***)dev)[23];
 memset(out,0,sizeof(*out));
 if(cutoff<1||cutoff>256)return 0;
 estimate=((MemoryEstimate)(*(void***)dev)[4])(dev);
 out->estimate=estimate;out->cutoff=cutoff;
 if(estimate<((unsigned)cutoff<<20))return 0;
 while(n<(unsigned)cutoff){void*t=0;hr=make(dev,512,512,1,1,21,0,&t,0);if(FAILED(hr))break;textures[n++]=t;}
 for(i=0;i<n;i++)((MemoryRelease)(*(void***)textures[i])[2])(textures[i]);
 out->allocated=n;out->bytes=n==(unsigned)cutoff?estimate:n<<20;out->used=1;return 1;
}
static int memory_try(void*s){
 char flag[4];int*cutoff;void*dev;
 typedef int*(FC*GetVar)(void*,void*,const wchar_t*,unsigned);
 if(GetEnvironmentVariableA("PAWS_STARTUP_MEMORY_ESTIMATE",flag,4)!=1||flag[0]!='1')return 0;
 cutoff=((GetVar)(base+0x65a44))((void*)(base+0x5f94c8),0,L"RendererLowMemoryCutoff",3);
 dev=*(void**)(*(uintptr_t*)((char*)s+0x40)+0x80);
 if(!memory_bounded(dev,*cutoff,&memoryResult))return 0;
 *(unsigned*)((char*)s+0x254)=memoryResult.bytes;return 1;
}
