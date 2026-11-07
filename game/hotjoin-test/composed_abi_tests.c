#include <stdint.h>
#include <assert.h>
#include <stdio.h>
#define FC __attribute__((fastcall))
typedef void (FC *AppendFn)(void*,void*);
typedef void (FC *ReaderFn)(void*,void*,void*);
static uintptr_t appendTarget,readerTarget;
static void FC append(void *session,void *stream){*(unsigned*)session+=*(unsigned*)stream;}
static void FC reader(void *session,void *unused,void *stream){assert(!unused);*(unsigned*)session^=*(unsigned*)stream;}
int main(void){
 unsigned session=17,stream=39;AppendFn a;ReaderFn r;
 appendTarget=(uintptr_t)append;readerTarget=(uintptr_t)reader;
 a=(AppendFn)appendTarget;r=(ReaderFn)readerTarget;
 a(&session,&stream);assert(session==56);r(&session,0,&stream);assert(session==(56^39));
 puts("PASS: global native addresses materialized as typed x86 fastcall pointers; two-register append and stacked reader argument");return 0;
}
