/* Experimental budget calculation. Owned QA only; no resource preloading.
 * base-policy.c is a SHA-bound copy of policy.c with sequence weights 120/120
 * and a 1792 MiB per-class quota ceiling. The original product is unchanged. */
#define rc_tick rc_tick_base
#define rc_weights rc_weights_base
#include "base-policy.c"
#undef rc_tick
#undef rc_weights

#define MIB (1024ull*1024)
#define CEILING (3072ull*MIB)
#define VA_RESERVE (768ull*MIB)
#define PHYS_RESERVE (384ull*MIB)
typedef struct {
 RcState common;
 U budgetCalls,ramBudget,vramBudget,freeVaMiB,freePhysMiB,pressure;
 U probeAt,refreshes,apiFailures,shrinkCalls;
} ExpandedState;
typedef U(__attribute__((stdcall))*BudgetClock)(void);
typedef U(__attribute__((cdecl))*GpuUsed)(void);
static U64 minimum(U64 a,U64 b){return a<b?a:b;}
static U64 room(U64 free,U64 reserve){return free>reserve?free-reserve:0;}
static double fraction(U bits){union {U bits;float value;} f;f.bits=bits;return f.value>=0&&f.value<=1?(double)f.value:0;}
static U bounded(double value){return value>0?(value>CEILING?(U)CEILING:(U)(U64)value):0;}

/* Original thiscall has ECX=cache manager, float RAM/VRAM fractions, bool force.
 * The assembler adapter supplies float bit patterns without signed conversion. */
RC_OUT void rc_budget(RcState*s,U manager,U ramBits,U vramBits,U force){
 ExpandedState*e=(ExpandedState*)s;RcMemory m;U renderer=R(s->image,0x5f3f98);
 U64 headroom,usedRam=R(manager,0x30),usedVram=R(manager,0x3c),video=64*MIB,gpu=0;
 U ram,vram,oldRam=R(manager,0x34),oldVram=R(manager,0x40);double rf=fraction(ramBits),vf=fraction(vramBits);
 m.length=sizeof(m);e->budgetCalls++;
 if(!s->memory||!((RcMemoryFn)s->memory)(&m)){
  e->apiFailures++;e->pressure=4;
  R(manager,0x34)=oldRam<0x7fffffff?oldRam:0x7fffffff;
  R(manager,0x40)=oldVram<0x7fffffff?oldVram:0x7fffffff;
  e->ramBudget=R(manager,0x34);e->vramBudget=R(manager,0x40);return;
 }
 e->freeVaMiB=(U)(m.availableVirtual/MIB);e->freePhysMiB=(U)(m.availablePhysical/MIB);
 headroom=minimum(room(m.availableVirtual,VA_RESERVE),room(m.availablePhysical,PHYS_RESERVE));
 /* Separate statements avoid a TinyCC x86 spill defect with a conditional
  * value kept alive across the short-circuit RHS of a bitwise expression. */
 e->pressure=0;
 if(m.availableVirtual<VA_RESERVE)e->pressure|=1;
 if(m.availablePhysical<PHYS_RESERVE)e->pressure|=2;
 if(m.load>=90)e->pressure|=2;
 ram=bounded((double)(usedRam+headroom)*rf);
 if(renderer){video=R(renderer,0x254);if(!force)gpu=((GpuUsed)(s->image+0x18a946))();}
 video=video+usedVram;video=video>gpu?video-gpu:0;
 vram=bounded((double)video*vf);
 {U guarded=bounded((double)(usedVram+headroom)*rf);if(vram>guarded)vram=guarded;}
 if(e->pressure){
  U r=bounded((double)usedRam*.75),v=bounded((double)usedVram*.75);
  if(ram>r)ram=r;if(vram>v)vram=v;e->shrinkCalls++;
 }else if(m.availableVirtual<1024*MIB){
  if(oldRam&&ram>oldRam)ram=oldRam;if(oldVram&&vram>oldVram)vram=oldVram;
 }
 R(manager,0x34)=ram;R(manager,0x40)=vram;e->ramBudget=ram;e->vramBudget=vram;
}

RC_OUT void rc_tick(RcState*s){
 ExpandedState*e=(ExpandedState*)s;RcMemory m;U now,manager;
 if(s->busy)return;
 rc_tick_base(s);
 if(!s->enabled||!s->clock||!s->memory||s->phase!=4)return;
 now=((BudgetClock)s->clock)();if((U)(now-e->probeAt)<1000)return;e->probeAt=now;
 m.length=sizeof(m);if(!((RcMemoryFn)s->memory)(&m)){e->apiFailures++;return;}
 if(m.availableVirtual>=VA_RESERVE&&m.availablePhysical>=PHYS_RESERVE&&m.load<90)return;
 manager=R(s->image,0x5f3fd4);
 if(manager&&R(manager+0x9c,0x24)){
  /* Native refresh acquires the resource/cache/renderer locks and evicts only
   * through native cache SetSize. No scan or Release loop is introduced. */
  ((RcLockFn)(s->image+0x1b546d))(manager+0x9c,0);e->refreshes++;
 }
}
