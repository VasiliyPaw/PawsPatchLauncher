#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
typedef unsigned U;
#include "prewarm_budget.h"
static ULONGLONG available;static int valid=1;
static BOOL WINAPI fake(LPMEMORYSTATUSEX m){m->ullAvailVirtual=available;return valid;}
int main(void){PrewarmBudget b;prewarm_budget_begin(&b);assert(b.available);prewarm_memory_status=fake;
 b.available=4ULL*1024*1024*1024;available=2ULL*1024*1024*1024;assert(prewarm_budget_allow(&b));
 /* More than a GiB of consumption remains allowed; no physical-RAM quota. */
 available=129ULL*1024*1024;assert(prewarm_budget_allow(&b));available=127ULL*1024*1024;assert(!prewarm_budget_allow(&b)&&b.limited);
 b.limited=0;available=2ULL*1024*1024*1024;valid=0;assert(!prewarm_budget_allow(&b)&&b.limited);
 puts("PASS: full preload allowed; only native address-space reserve and API failure stop it");return 0;}
