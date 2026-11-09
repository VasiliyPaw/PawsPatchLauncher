/* Kohan II 1.3.72 presentation resources only. No simulation/RNG/network writes.
 * Imported functions are supplied by the checked fresh-process installer.
 * Nothing retains a native resource or graph pointer between frame callbacks. */
typedef unsigned U;
typedef unsigned long long U64;
#define FC __attribute__((fastcall))
#define RC_OUT __attribute__((dllexport))
#define R(p,o) (*(U*)((p)+(o)))
typedef void (FC *RcSizeFn)(U,U,U,U);
typedef void (FC *RcLockFn)(U,U);
typedef void (FC *RcRequestFn)(U,U,U,U);
typedef void (FC *RcReleaseFn)(U,U,U);
typedef void (FC *RcPrecacheFn)(U,U,U);
typedef U (__attribute__((stdcall)) *RcClockFn)(void);
typedef int (__attribute__((stdcall)) *RcMemoryFn)(void*);
typedef struct {U length,load;U64 totalPhysical,availablePhysical,totalPage,availablePage,totalVirtual,availableVirtual,availableExtended;} RcMemory;
typedef struct {
 U image,clock,memory,enabled,weightCalls,frames,world,bucket,skip,passes;
 U warmed,models,sequences,failures,pressureSkips,budgetStops,slowLoads,maxLoadMs;
 U lastWorkMs,totalWorkMs,lastRun,phase,scanNodes,busy,complete,limitsRevision;
} RcState;
static U rc_share(U total,U weight,U sum){return sum?(U)((U64)total*weight/sum):0;}

RC_OUT void rc_weights(RcState*s,U manager,U target,U ram,U vram){
 U n,p,i,found=0,table=R(manager,0x20),count=R(manager,0x24),caches[64],used=0;
 U totalRam=R(manager,0x38),totalVram=R(manager,0x44);
 for(i=0;i<count;i++)for(n=R(table,i*4);n;n=R(n,8))if(R(n,4)==target)found=1;
 if(found){totalRam-=R(target,0x14);totalVram-=R(target,0x24);}
 totalRam+=ram;totalVram+=vram;
 R(target,0x14)=ram;R(target,0x24)=vram;R(manager,0x38)=totalRam;R(manager,0x44)=totalVram;
 /* 1.3.72 has fifteen cache classes. Do not retain bucket-chain addresses
  * across eviction callbacks, which can register another resource class. */
 for(i=0;i<count;i++)for(n=R(table,i*4);n;n=R(n,8))if(used<64)caches[used++]=R(n,4);
 for(i=0;i<used;i++){
  p=caches[i];
  ((RcSizeFn)(s->image+0x1b61c8))(p,0,rc_share(R(manager,0x34),R(p,0x14),R(manager,0x38)),rc_share(R(manager,0x40),R(p,0x24),R(manager,0x44)));
 }
 if(!found)((RcSizeFn)(s->image+0x1b61c8))(target,0,rc_share(R(manager,0x34),ram,totalRam),rc_share(R(manager,0x40),vram,totalVram));
 s->weightCalls++;
}

static U rc_lower(U c){return c>='A'&&c<='Z'?c+32:c;}
static int rc_prefix(const unsigned short *p,const char *s){
 if(!p)return 0;
 for(;*s;s++,p++)if(rc_lower(*p)!=(U)*s)return 0;
 return 1;
}
static int rc_contains(const unsigned short *p,const char*s){
 for(;*p;p++)if(rc_prefix(p,s))return 1;return 0;
}
static int rc_scoped(U resource){
 const unsigned short *p=(const unsigned short*)R(resource,0x38);
 /* UI portraits, terrain and decoration have separate caches/budgets. */
 if(!p||rc_contains(p,"portrait"))return 0;
 return rc_prefix(p,"units/")||rc_prefix(p,"spells/")||rc_prefix(p,"effects/")||rc_prefix(p,"projectiles/")||rc_prefix(p,"globalpowers/")||
        rc_prefix(p,"units\\")||rc_prefix(p,"spells\\")||rc_prefix(p,"effects\\")||rc_prefix(p,"projectiles\\")||rc_prefix(p,"globalpowers\\");
}
static int rc_headroom(RcState*s){
 RcMemory m;m.length=sizeof(m);
 if(!((RcMemoryFn)s->memory)(&m))return 0;
 /* The process is 32 bit: stop speculative loads well before VA exhaustion.
  * Native LRU eviction remains active, with the original global budgets. */
 return m.availablePhysical>=384ull*1024*1024&&m.availableVirtual>=384ull*1024*1024&&m.load<90;
}
static int rc_cache_room(RcState*s,U manager,U type){
 U map=manager+0x9c,table=R(map,0x20),count=R(map,0x24),i,n,c,id;
 if(!table||count>4096)return 0;
 id=R(s->image,type==0x4d34a4?0x5fc910:0x5fc924);
 for(i=0;i<count;i++)for(n=R(table,i*4);n;n=R(n,8))if(R(n,0)==id){
  c=R(n,4);
  return R(c,8)>2u*1024*1024&&R(c,0x18)>2u*1024*1024&&
         (U64)R(c,0xc)*4<(U64)R(c,8)*3&&(U64)R(c,0x1c)*4<(U64)R(c,0x18)*3;
 }
 return 0;
}
static U rc_request_next(RcState*s,U manager){
 U mutex=manager+0x20,table,count,n,p=0,i,visited=0,type;
 ((RcLockFn)R(R(mutex,0),4))(mutex,0);
 table=R(manager,0x60);count=R(manager,0x64);
 if(table&&count&&count<=65536){
  while(s->bucket<count&&visited<256){
   n=R(table,s->bucket*4);for(i=0;n&&i<s->skip;i++)n=R(n,4);
   if(!n){s->bucket++;s->skip=0;continue;}
   s->skip++;s->scanNodes++;visited++;p=R(n,0);if(!p)continue;
   type=R(p,0)-s->image;
   if((type!=0x4d34a4&&type!=0x4d3510)||!R(p,0x14)||R(p,4)||(R(p,8)&0x3f)||!rc_scoped(p)){p=0;continue;}
   if(!s->passes&&!rc_prefix((const unsigned short*)R(p,0x38),"units/")&&!rc_prefix((const unsigned short*)R(p,0x38),"units\\")){p=0;continue;}
   if(!rc_cache_room(s,manager,type)||(R(p,0x20)&&R(R(p,0x20),0x10))){p=0;continue;}
   /* Acquire a native load reference without blocking while holding the
    * metadata lock. The dictionary may rehash as dependencies are loaded. */
   ((RcRequestFn)(s->image+0x1c99f4))(p,0,1,1);break;
  }
  if(s->bucket>=count){s->bucket=s->skip=0;s->passes++;if(s->passes>=2)s->complete=1;}
 }
 ((RcLockFn)R(R(mutex,0),8))(mutex,0);
 return p;
}
static void rc_tick_impl(RcState*s){
 U world,phase,oldPhase,manager,p,start,now,spent,type,root,renderer,loadStart,loadMs;
 if(!s->enabled||!s->clock||!s->memory)return;
 s->frames++;phase=R(s->image,0x5f92f4);world=R(s->image,0x5f3fb8);oldPhase=s->phase;s->phase=phase;
 manager=R(s->image,0x5f3fd4);
 if(!s->limitsRevision&&manager&&R(manager+0x9c,0x24)&&R(s->image,0x5f9480)){
  ((RcLockFn)(s->image+0x1b546d))(manager+0x9c,0);s->limitsRevision=1;
 }
 if(!(s->enabled&2))return;
 if(!world||(phase!=6&&phase!=4)){
  s->world=0;s->bucket=s->skip=s->passes=s->complete=0;return;
 }
 if(world!=s->world||phase!=oldPhase){s->world=world;s->bucket=s->skip=s->passes=s->complete=0;}
 /* Expensive first-time driver work is indivisible. Confine speculation to
  * the loading screen or a pause; never add it to an unpaused battle frame. */
 if(phase==4){U simulation=R(s->image,0x5f3fe8);if(!simulation||!*(unsigned char*)(simulation+0x28))return;}
 /* Two finite scans: world-loading references may be registered during scan 1.
  * New first-use assets subsequently use the repaired native LRU cache. */
 if(s->complete)return;
 now=((RcClockFn)s->clock)();
 if((U)(now-s->lastRun)<16u)return;
 start=now;s->lastRun=now;s->lastWorkMs=0;
 if(!rc_headroom(s)){s->pressureSkips++;return;}
 manager=R(s->image,0x5f3fd4);if(!manager)return;
 if(!R(s->image,0x5f9480)||!R(R(s->image,0x5f9480),0xfc)||!*(unsigned char*)R(R(s->image,0x5f9480),0xfc))return;
 renderer=R(s->image,0x5f3f98);if(!renderer||!R(renderer,0x40))return;
 while(!s->complete){
  p=rc_request_next(s,manager);if(!p)break;
  type=R(p,0)-s->image;
  /* No resource pointer survives this synchronous, VIEW-thread-only operation.
   * Request/Release handle native synchronization, dependency loading and LRU.
   * A pending asynchronous task is never stolen from the native loader. */
  loadStart=((RcClockFn)s->clock)();
  ((RcLockFn)R(R(p,0),0x18))(p,0);
  if(R(p,8)&1){
   root=R(p,0x40);
   if(type==0x4d34a4&&root){((RcPrecacheFn)(s->image+0x18ac10))(renderer,0,root);s->models++;}
   else if(type==0x4d3510)s->sequences++;
   s->warmed++;
  }else s->failures++;
  ((RcReleaseFn)(s->image+0x1c9aea))(p,0,1);
  loadMs=((RcClockFn)s->clock)()-loadStart;
  if(loadMs>s->maxLoadMs)s->maxLoadMs=loadMs;
  if(loadMs>8)s->slowLoads++;
  spent=((RcClockFn)s->clock)()-start;
  if(spent>=(phase==6?40u:2u)){s->budgetStops++;break;}
 }
 spent=((RcClockFn)s->clock)()-start;s->lastWorkMs=spent;s->totalWorkMs+=spent;
}
RC_OUT void rc_tick(RcState*s){if(s->busy)return;s->busy=1;rc_tick_impl(s);s->busy=0;}
