/* Synchronous renderer-thread loading, with room left for the native engine. */
typedef struct{ULONGLONG available;U limited;}PrewarmBudget;
static BOOL(WINAPI*prewarm_memory_status)(LPMEMORYSTATUSEX);
static void prewarm_budget_begin(PrewarmBudget*b){MEMORYSTATUSEX m;memset(&m,0,sizeof(m));m.dwLength=sizeof(m);b->limited=0;if(!prewarm_memory_status)prewarm_memory_status=(void*)GetProcAddress(GetModuleHandleA("kernel32.dll"),"GlobalMemoryStatusEx");b->available=prewarm_memory_status&&prewarm_memory_status(&m)?m.ullAvailVirtual:0;}
/* No RAM quota or artificial per-map MB cap. Preserve a small native VA reserve. */
static int prewarm_budget_allow(PrewarmBudget*b){MEMORYSTATUSEX m;memset(&m,0,sizeof(m));m.dwLength=sizeof(m);if(!b->available||!prewarm_memory_status||!prewarm_memory_status(&m)||m.ullAvailVirtual<128ULL*1024*1024){b->limited=1;return 0;}return 1;}
