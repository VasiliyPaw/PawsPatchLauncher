/* Match-local reconnect credentials. No display-name based ownership. */
#ifndef PAW_HOTJOIN_TICKET_POLICY_H
#define PAW_HOTJOIN_TICKET_POLICY_H
#include <string.h>
#include <stdint.h>
#include <wchar.h>
#define HJ_TICKETS 32
#define HJ_TICKET_WORDS 8
typedef struct {
 unsigned token[HJ_TICKET_WORDS];
 unsigned verifier[HJ_TICKET_WORDS]; /* Public SHA-256 proof verifier; never a bearer credential. */
 uintptr_t conn;
 unsigned playerId;
 wchar_t kingdom[80];
 int used, departed;
} HJTicket;
static int hj_token_equal(const unsigned *a,const unsigned *b) {
 unsigned diff=0,i;for(i=0;i<HJ_TICKET_WORDS;i++)diff|=a[i]^b[i];return diff==0;
}
static int hj_token_present(const unsigned *a) {
 unsigned value=0,i;for(i=0;i<HJ_TICKET_WORDS;i++)value|=a[i];return value!=0;
}
static HJTicket *hj_find_token(HJTicket *table,const unsigned *token) {
 unsigned i;HJTicket *result=0;if(!hj_token_present(token))return 0;
 for(i=0;i<HJ_TICKETS;i++)if(table[i].used&&hj_token_equal(table[i].token,token))result=table+i;
 return result;
}
static HJTicket *hj_find_conn(HJTicket *table,uintptr_t conn) {
 unsigned i;if(!conn)return 0;
 for(i=0;i<HJ_TICKETS;i++)if(table[i].used&&table[i].conn==conn)return table+i;
 return 0;
}
static HJTicket *hj_find_verifier(HJTicket *table,const unsigned *digest) {
 unsigned i;if(!hj_token_present(digest))return 0;
 for(i=0;i<HJ_TICKETS;i++)if(table[i].used&&hj_token_equal(table[i].verifier,digest))return table+i;
 return 0;
}
static int hj_can_reclaim(const HJTicket *t,int implicitAiExists,int humanOwnsKingdom) {
 return t&&t->used&&t->departed&&t->kingdom[0]&&implicitAiExists&&!humanOwnsKingdom;
}
#endif
