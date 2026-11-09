/* Private prototype: read-only predicate results scoped to one native Find.
 * No retained object references, persistent index, or lifecycle interception.
 * Only occupied positive shader(3)/unique-texture(5) prefixes are eligible.
 * Native kinds 1..28 and both polarities are cached in four stack bitsets;
 * complete non-strict condition chains still run in their original order.
 * Occupied keys guarantee strict failure without changing condition bytes.
 * All allocation, condition updates and unusual cases run in native Find. */
typedef void*(FC*LcFind)(void*,void*,void*);
typedef BYTE(FC*LcPredicate)(void*,void*,void*,UINT);
static LcFind lcNativeFind;static LcPredicate lcNativePredicate;static DWORD lcViewThread;
static unsigned long long lcCalls,lcEligible,lcSkipped,lcFallback,lcPredicates,lcStopped;static UINT lcEnabled;
#ifndef LC_THREAD_ID
#define LC_THREAD_ID GetCurrentThreadId
#endif
static UINT lc_shape(const UINT*p){
 if(!p)return 0;
 if(p[1]==1||p[1]==2){if(p[0]!=1&&p[0]!=2)return 0;p=(const UINT*)(uintptr_t)p[2];if(!p)return 0;}
 if(p[0]!=1||p[1]!=3||!p[3])return 0;
 p=(const UINT*)(uintptr_t)p[2];
 if(!p||p[0]!=1||p[1]!=5||!p[3])return 0;
 return 1;
}
static int lc_eligible(const UINT*p,void*unused,void*object,UINT*known,UINT*passed){
 UINT count=0,kind,index,mask;
 while(p&&count++<32){
  kind=p[1];if(kind<1||kind>28||(p[0]!=1&&p[0]!=2))return -1;
  index=p[0]-1;mask=1u<<kind;
  if(!(known[index]&mask)){lcPredicates++;if(lcNativePredicate((void*)p,unused,object,0))passed[index]|=mask;known[index]|=mask;}
  if(!(passed[index]&mask))return 0;
  p=(const UINT*)(uintptr_t)p[2];
 }
 return p?-1:1;
}
static void*FC lc_find(void*self,void*unused,void*object){
 UINT*p=self,*next,*conditions,n=0,known[2]={0,0},passed[2]={0,0};int eligible;void*result;
 if(!lcEnabled||LC_THREAD_ID()!=lcViewThread)return lcNativeFind(self,unused,object);
 lcCalls++;
 /* The last occupied bin must reach native Find: its strict rejection can
  * allocate and initialise the next bin. Never bypass that native work. */
 next=(UINT*)(uintptr_t)p[6];conditions=(UINT*)(uintptr_t)p[4];
 while(next&&n<16384&&lc_shape(conditions)){
  if(!n)lcEligible++;
  /* Strict=0 on these exact kinds is read-only. This same object cannot be
   * changed by a predicate or group allocation; no allocation occurs here. */
  eligible=lc_eligible(conditions,unused,object,known,passed);
  if(eligible<0)break;
  if(!eligible){lcStopped++;lcSkipped+=n;return NULL;}
  n++;p=next;next=(UINT*)(uintptr_t)p[6];conditions=(UINT*)(uintptr_t)p[4];
 }
 lcSkipped+=n;lcFallback++;result=lcNativeFind(p,unused,object);return result;
}
