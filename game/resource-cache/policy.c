/* Product policy: repair native per-class quotas and retain the existing
 * animation cache settings. No resource enumeration, loading or GPU precache.
 * The state layout remains compatible with helper diagnostics and UI callback. */
typedef unsigned U;
typedef unsigned long long U64;
#define FC __attribute__((fastcall))
#define RC_OUT __attribute__((dllexport))
#define R(p,o) (*(U*)((p)+(o)))
typedef void(FC *RcSizeFn)(U,U,U,U);
typedef void(FC *RcLockFn)(U,U);
typedef int(__attribute__((stdcall))*RcMemoryFn)(void*);
typedef struct {U length,load;U64 totalPhysical,availablePhysical,totalPage,availablePage,totalVirtual,availableVirtual,availableExtended;} RcMemory;
typedef struct {
 U image,clock,memory,enabled,weightCalls,frames,world,bucket,skip,passes;
 U warmed,models,sequences,failures,pressureSkips,budgetStops,slowLoads,maxLoadMs;
 U lastWorkMs,totalWorkMs,lastRun,phase,scanNodes,busy,complete,limitsRevision;
 U callback,animationPolicy;
} RcState;
static U rc_share(U total,U weight,U sum){return sum?(U)((U64)total*weight/sum):0;}
RC_OUT void rc_weights(RcState*s,U manager,U target,U ram,U vram){
 U n,p,i,found=0,table=R(manager,0x20),count=R(manager,0x24),caches[64],used=0;
 U totalRam=R(manager,0x38),totalVram=R(manager,0x44);
 if(R(s->image,0x5fc924)&&R(target,4)==R(s->image,0x5fc924)){ram=100;vram=100;}
 for(i=0;i<count;i++)for(n=R(table,i*4);n;n=R(n,8))if(R(n,4)==target)found=1;
 if(found){totalRam-=R(target,0x14);totalVram-=R(target,0x24);}
 totalRam+=ram;totalVram+=vram;
 R(target,0x14)=ram;R(target,0x24)=vram;R(manager,0x38)=totalRam;R(manager,0x44)=totalVram;
 for(i=0;i<count;i++)for(n=R(table,i*4);n;n=R(n,8))if(used<64)caches[used++]=R(n,4);
 for(i=0;i<used;i++){
  p=caches[i];
  ((RcSizeFn)(s->image+0x1b61c8))(p,0,rc_share(R(manager,0x34),R(p,0x14),R(manager,0x38)),rc_share(R(manager,0x40),R(p,0x24),R(manager,0x44)));
 }
 if(!found)((RcSizeFn)(s->image+0x1b61c8))(target,0,rc_share(R(manager,0x34),ram,totalRam),rc_share(R(manager,0x40),vram,totalVram));
 s->weightCalls++;
}
static void rc_tick_impl(RcState*s){
 U manager;
 if(!s->enabled||!s->memory)return;
 s->frames++;s->world=R(s->image,0x5f3fb8);s->phase=R(s->image,0x5f92f4);
 manager=R(s->image,0x5f3fd4);
 if(!s->animationPolicy&&manager&&R(manager+0x9c,0x24)&&R(s->image,0x5f9480)&&R(R(s->image,0x5f9480),0x100)){
  RcMemory m;m.length=sizeof(m);
  if(((RcMemoryFn)s->memory)(&m)&&m.availableVirtual>=512ull*1024*1024&&m.availablePhysical>=384ull*1024*1024&&m.load<90){
   R(R(R(s->image,0x5f9480),0x100),0)=80;
   ((RcLockFn)(s->image+0x1b546d))(manager+0x9c,0);s->animationPolicy=s->limitsRevision=1;
  }
 }
}
RC_OUT void rc_tick(RcState*s){
 if(s->busy)return;s->busy=1;
 rc_tick_impl(s);
 if(s->callback)((void(*)(void))s->callback)();
 s->busy=0;
}
