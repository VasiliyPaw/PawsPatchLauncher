#include <assert.h>
#include <stdio.h>
#include "safety_policy.h"
int main(void) {
 unsigned ids[16]={0},count=0,cycle,i,j;
 /* Long match: a submitted/retired intent frees its slot. The seventeenth
  * admission must still accept another request, without duplicate intents. */
 for(cycle=1;cycle<=1000;cycle++){
  assert(hj_pending_add(ids,&count,cycle));assert(hj_pending_add(ids,&count,cycle));
  j=0;for(i=0;i<count;i++)if(ids[i]==cycle){j++;ids[i]=0;}assert(j==1);
 }
 for(i=1;i<=16;i++)assert(hj_pending_add(ids,&count,i));
 assert(!hj_pending_add(ids,&count,17));
 ids[7]=0;assert(hj_pending_add(ids,&count,17));assert(count==16);
 j=0;for(i=0;i<16;i++)if(ids[i]==17)j++;assert(j==1);
 assert(!hj_pending_add(ids,&count,0));
 puts("PASS: 1000 retired admissions, duplicate requests, 16 concurrent intents and vacancy reuse");return 0;
}
