#include <stdio.h>
#include <assert.h>
#include <math.h>
#include "policy.h"
int main(void){Alert a;unsigned checks=0,i;float cap;
 for(i=0;i<200;i++){
  float origin=47.f+(float)i*.4f;
  a.home=1;a.target=2;a.limit2=sq(origin+RETREAT_ALLOWANCE);a.last=10.f;
  assert(alert_position(&a,0,0,origin,0,10.f));checks++;
  assert(alert_position(&a,0,0,origin+RETREAT_ALLOWANCE-.01f,0,10.f));checks++;
  assert(!alert_position(&a,0,0,origin+RETREAT_ALLOWANCE+.01f,0,10.f));checks++;
  assert(!alert_position(&a,0,0,origin,0,40.01f));checks++;
  assert(!alert_position(&a,0,0,origin,0,9.f));checks++;
  cap=a.limit2;a.last=20.f;
  assert(a.limit2==cap&&!alert_position(&a,0,0,origin+RETREAT_ALLOWANCE+1,0,20.f));checks++;
  assert(alert_position(&a,0,0,origin-20,0,21.f));checks++;
 }
 a.last=0;a.limit2=100;
 assert(!alert_position(&a,0,0,(float)sqrt(-1.),0,1));checks++;
 assert(!alert_position(&a,0,0,1,1,100001));checks++;
 printf("{\"passed\":true,\"checks\":%u}\n",checks);return 0;
}
