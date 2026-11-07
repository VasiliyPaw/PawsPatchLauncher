#include <assert.h>
#include <stdio.h>
#include "ticket_policy.h"
int main(void) {
 HJTicket table[HJ_TICKETS];unsigned a[8]={1,2,3,4,5,6,7,8},b[8],zero[8]={0};unsigned i;
 memset(table,0,sizeof(table));
 assert(!hj_find_token(table,zero));assert(!hj_find_token(table,a));assert(!hj_find_conn(table,0));
 table[0].used=1;memcpy(table[0].token,a,sizeof(a));table[0].conn=123;
 wcscpy(table[0].kingdom,L"kingdom02");
 assert(hj_find_token(table,a)==table);assert(hj_find_conn(table,123)==table);
 memcpy(table[0].verifier,a,sizeof(a));assert(hj_find_verifier(table,a)==table);
 assert(!hj_find_verifier(table,zero));
 memset(table[0].token,0,sizeof(table[0].token));
 assert(!hj_find_token(table,a));assert(hj_find_verifier(table,a)==table); /* migrated peers keep no bearer secret */
 memcpy(table[0].token,a,sizeof(a));
 for(i=0;i<8;i++){memcpy(b,a,sizeof(a));b[i]^=1;assert(!hj_token_equal(a,b));assert(!hj_find_token(table,b));assert(!hj_find_verifier(table,b));}
 assert(!hj_can_reclaim(0,1,0));
 assert(!hj_can_reclaim(table,1,0)); /* existing connected owner */
 table[0].conn=0;table[0].departed=1;
 assert(hj_can_reclaim(table,1,0));
 assert(!hj_can_reclaim(table,0,0)); /* no replacement AI */
 assert(!hj_can_reclaim(table,1,1)); /* human already owns it */
 table[0].kingdom[0]=0;assert(!hj_can_reclaim(table,1,0)); /* departed observer */
 memset(table,0,sizeof(table));assert(!hj_find_token(table,a)); /* new match invalidates old credentials */
 puts("PASS: credential lookup, all credential words, missing credential, connected owner, AI availability, occupied kingdom, observer and match reset");return 0;
}
