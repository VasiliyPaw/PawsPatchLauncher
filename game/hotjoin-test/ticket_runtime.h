/* PRIVATE LAB PROTOCOL. Both copies must run the same marked lab build.
 * Credentials are never placed in player names, game logs, or shared saves.
 * Not installed or shipped by the launcher. */
#include "ticket_policy.h"
typedef void (FC *NetSerialFn)(void*,void*,void*,unsigned);
typedef void (__cdecl *BitsFn)(void*,void*,int);
typedef void (__cdecl *BodySerialFn)(void*,void*);
typedef uintptr_t (FC *FindConnFn)(void*,void*,void*);
typedef void (FC *LeaveFn)(void*,void*,void*,int);
typedef struct {uintptr_t conn;HJTicket *ticket;int capable,duplicate;} HJConn;
typedef struct {unsigned verifier[8],playerId,used,departed;wchar_t kingdom[80];} HJPublicTicket;
typedef struct {uintptr_t body;wchar_t kingdom[80];wchar_t checkpoint[96];unsigned checkpointCrc;HJPublicTicket manifest[HJ_TICKETS];unsigned peerVerifier[8];HJPauseState pause;} HJRole;
static HJTicket tickets[HJ_TICKETS];
static HJConn ticketConns[HJ_TICKETS];
static HJRole ticketRoles[HJ_TICKETS];
static unsigned ticketRoleCursor,clientTicket[HJ_TICKET_WORDS];
static uintptr_t ticketIncomingConn,ticketPrivateConn;
static const wchar_t *ticketCurrentRole;
static wchar_t ticketPath[MAX_PATH];
static uintptr_t ticketSession;
static unsigned ticketPreviousMode;
#define HJ_MAGIC 0x324a4850u
/* Revision O/P and recovery Q/R add cancelled-host admission and deferred resign.
 * Earlier layouts must not silently connect. A public verifier cannot
 * reconnect: the handshake hashes the supplied secret again. */
static unsigned ticket_magic(void){unsigned value=recoveryMode?(multiMode?0x524a4850u:0x514a4850u):(multiMode?0x504a4850u:0x4f4a4850u);return value^(testLegacyProtocol?0x1000000u:0);}
static int ticket_digest(const unsigned *secret,unsigned *digest) {
 typedef LONG (WINAPI *OpenFn)(void**,const wchar_t*,const wchar_t*,ULONG);
 typedef LONG (WINAPI *HashFn)(void*,unsigned char*,ULONG,unsigned char*,ULONG,unsigned char*,ULONG);
 typedef LONG (WINAPI *CloseFn)(void*,ULONG);
 HMODULE dll=LoadLibraryW(L"bcrypt.dll");void *alg=0;LONG status;OpenFn open;HashFn hash;CloseFn close;
 if(!dll)return 0;
 open=(OpenFn)GetProcAddress(dll,"BCryptOpenAlgorithmProvider");hash=(HashFn)GetProcAddress(dll,"BCryptHash");close=(CloseFn)GetProcAddress(dll,"BCryptCloseAlgorithmProvider");
 if(!open||!hash||!close){FreeLibrary(dll);return 0;}
 status=open(&alg,L"SHA256",0,0);
 if(status>=0){status=hash(alg,0,0,(unsigned char*)secret,32,(unsigned char*)digest,32);close(alg,0);}
 FreeLibrary(dll);return status>=0;
}
static void ticket_cache_local(const unsigned *secret) {
 FILE *f;memcpy(clientTicket,secret,sizeof(clientTicket));
 f=_wfopen(ticketPath,L"wb");if(f){fwrite(clientTicket,1,sizeof(clientTicket),f);fclose(f);}
}
static void ticket_manifest_make(HJPublicTicket *out) {
 unsigned i;memset(out,0,sizeof(HJPublicTicket)*HJ_TICKETS);
 for(i=0;i<HJ_TICKETS;i++)if(tickets[i].used){
  memcpy(out[i].verifier,tickets[i].verifier,32);out[i].used=1;
  out[i].playerId=tickets[i].playerId;out[i].departed=tickets[i].departed;
  wcscpy(out[i].kingdom,tickets[i].kingdom);
 }
}
static void ticket_manifest_accept(const HJPublicTicket *in) {
 unsigned i,j,count=0;HJTicket *t;
 for(i=0;i<HJ_TICKETS;i++)if(in[i].used&&hj_token_present(in[i].verifier)){
  t=hj_find_verifier(tickets,in[i].verifier);
  if(!t){for(j=0;j<HJ_TICKETS&&tickets[j].used;j++);if(j==HJ_TICKETS)continue;t=tickets+j;memset(t,0,sizeof(*t));}
  t->used=1;memcpy(t->verifier,in[i].verifier,32);t->playerId=in[i].playerId;t->departed=!!in[i].departed;
  memcpy(t->kingdom,in[i].kingdom,sizeof(t->kingdom));t->kingdom[79]=0;
  count++;
 }
 host->log("hotjoin-lab","PUBLIC_OWNERSHIP_MANIFEST accepted=%u; no remote bearer credentials",count);
}
static void ticket_copy_name(wchar_t *to,uintptr_t from) {
 unsigned n=word(from-12);
 to[0]=0;if(!from||n>79||!readable(from,(n+1)*2))return;
 memcpy(to,(void*)from,n*2);to[n]=0;
}
static int ticket_has_bits(void *input,unsigned bits) {
 uintptr_t p=(uintptr_t)input,data=word(p+4);
 /* +0 is a vtable, +4 is the native ref-counted byte buffer. The native
  * capacity accessor 15dcfd reads data[-4]; never treat the vtable as data. */
 unsigned cap=word(data-4),pos=word(p+8)*8+word(p+12);
 return cap>0&&cap<1048576&&pos<=cap*8&&bits<=cap*8-pos&&readable(data,cap);
}
static int ticket_read_blob(void *input,void *output,unsigned bytes) {
 if(!ticket_has_bits(input,bytes*8))return 0;
 memset(output,0,bytes);((BitsFn)(base+0x517cc))(input,output,bytes*8);return 1;
}
static void ticket_write_blob(void *output,void *input,unsigned bytes) {
 ((BitsFn)(base+0x518fe))(output,input,bytes*8);
}
static HJConn *ticket_conn(uintptr_t conn,int create) {
 unsigned i;HJConn *empty=0;
 for(i=0;i<HJ_TICKETS;i++){
  if(ticketConns[i].conn==conn)return ticketConns+i;
  if(!ticketConns[i].conn&&!empty)empty=ticketConns+i;
 }
 if(create&&empty){memset(empty,0,sizeof(*empty));empty->conn=conn;return empty;}
 return 0;
}
static int ticket_can_replace(HJConn *c) {
 uintptr_t old,p,a=word(base+0x5f3fec);
 if(!recoveryMode||!c||!c->capable||!c->ticket||!c->duplicate)return 0;
 old=c->ticket->conn;p=word(old+0xc);
 return old&&old!=a&&old!=c->conn&&readable(old,0x43c)&&p&&!byte(p+0xc)&&
  word(p+0x20)==c->ticket->playerId&&!byte(old+0x98)&&byte(a+0x2f4);
}
static HJRole *ticket_role(uintptr_t body,int create) {
 unsigned i;HJRole *r;
 for(i=0;i<HJ_TICKETS;i++)if(ticketRoles[i].body==body)return ticketRoles+i;
 if(!create)return 0;r=ticketRoles+(ticketRoleCursor++%HJ_TICKETS);
 memset(r,0,sizeof(*r));r->body=body;return r;
}
static uintptr_t ticket_find_ai(const wchar_t *name,int *human) {
 uintptr_t node,p,s=word(base+0x5f3fe4),found=0;unsigned n=0;
 *human=0;
 for(node=word(s+0xc8);node&&n++<40;node=word(node+4)){
  p=word(node);
  if(!readable(word(p+0x24),2)||wcscmp((wchar_t*)word(p+0x24),name))continue;
  if(byte(p+0xc)&&byte(p+0xd))found=p;else *human=1;
 }
 return found;
}
static void ticket_remember(HJTicket *t,uintptr_t player) {
 if(t&&word(player+0x28)&&!byte(player+0xc))ticket_copy_name(t->kingdom,word(player+0x24));
}
static HJTicket *ticket_register(uintptr_t conn,uintptr_t player) {
 HJConn *c=ticket_conn(conn,0);HJTicket *t;unsigned i;
 typedef BOOLEAN (WINAPI *RandomFn)(void*,unsigned long);
 RandomFn random;
 if(!c||!c->capable)return 0;
 if(c->ticket){c->ticket->conn=conn;c->ticket->playerId=word(player+0x20);return c->ticket;}
 for(i=0;i<HJ_TICKETS;i++)if(!tickets[i].used)break;
 if(i==HJ_TICKETS)return 0;
 random=(RandomFn)GetProcAddress(LoadLibraryA("advapi32.dll"),"SystemFunction036");
 t=tickets+i;memset(t,0,sizeof(*t));
 if(!random||!random(t->token,sizeof(t->token))||!hj_token_present(t->token)||!ticket_digest(t->token,t->verifier))return 0;
 t->used=1;t->conn=conn;t->playerId=word(player+0x20);c->ticket=t;
 host->log("hotjoin-lab","TICKET_ISSUED playerId=%u; private recipient only",t->playerId);return t;
}
static void ticket_ensure_host_credential(void) {
 uintptr_t a=word(base+0x5f3fec);HJConn *c;HJTicket *t;
 if(word(a+0x2e4)!=a||!word(a+0xc)||hj_find_conn(tickets,a))return;
 c=ticket_conn(a,1);if(!c)return;c->capable=1;t=ticket_register(a,word(a+0xc));
 if(t&&hj_token_present(t->token))ticket_cache_local(t->token);
}
static void FC ticket_connect_out(void *conn,void *unused,void *stream,unsigned stamp) {
 unsigned blob[1+HJ_TICKET_WORDS];(void)unused;
 blob[0]=ticket_magic();memcpy(blob+1,clientTicket,sizeof(clientTicket));
 if(recoveryMode)ticket_write_blob(stream,blob,sizeof(blob));
 ((NetSerialFn)(base+0x151031))(conn,0,stream,stamp);
 blob[0]=ticket_magic();memcpy(blob+1,clientTicket,sizeof(clientTicket));ticket_write_blob(stream,blob,sizeof(blob));
 host->log("hotjoin-lab","TICKET_CONNECT_SENT size0=%u cursor=%u bits=%u",word((uintptr_t)stream),word((uintptr_t)stream+8),word((uintptr_t)stream+12));
}
static void FC ticket_connect_in(void *conn,void *unused,void *stream,unsigned stamp) {
 unsigned prefix[1+HJ_TICKET_WORDS];
 if(recoveryMode){
  if(!ticket_read_blob(stream,prefix,sizeof(prefix))||prefix[0]!=ticket_magic())return;
  if(recovery_preconnect((uintptr_t)conn,prefix+1))return;
 }
 (void)unused;ticketIncomingConn=(uintptr_t)conn;
 ((NetSerialFn)(base+0x150c78))(conn,0,stream,stamp);ticketIncomingConn=0;
}
static void __cdecl ticket_connect_flag(void *stream,void *flag,int bits) {
 unsigned blob[1+HJ_TICKET_WORDS],digest[8];HJConn *c;
 typedef void (__cdecl *FlagFn)(void*,void*,int);
 ((FlagFn)(base+0x6ac79))(stream,flag,bits);
 c=ticket_conn(ticketIncomingConn,1);if(!c)return;
 /* The native unaligned bit-array codec preserves field boundaries. Read
  * exactly the same 36-byte field written by connect_out, not two slices. */
 if(!ticket_read_blob(stream,blob,sizeof(blob))||blob[0]!=ticket_magic()){
  host->log("hotjoin-lab","TICKET_PROTOCOL_MISSING; hot admission must be refused; capacity=%u cursor=%u bits=%u",word(word((uintptr_t)stream+4)-4),word((uintptr_t)stream+8),word((uintptr_t)stream+12));return;
 }
 c->capable=1;c->ticket=hj_token_present(blob+1)&&ticket_digest(blob+1,digest)?hj_find_verifier(tickets,digest):0;
 if(c->ticket)memcpy(c->ticket->token,blob+1,32); /* Verified owner reveals its own secret to the new host only. */
 c->duplicate=c->ticket&&c->ticket->conn&&c->ticket->conn!=ticketIncomingConn;
 host->log("hotjoin-lab","TICKET_CONNECT capable=1 recognized=%d duplicate=%d",c->ticket!=0,c->duplicate);
}
static void FC ticket_private_out(void *conn,void *unused) {
 (void)unused;ticketPrivateConn=(uintptr_t)conn;
 ((SessionFn)(base+0x152400))(conn,0);ticketPrivateConn=0;
}
static void ticket_append_private(void *stream) {
 HJTicket *t=hj_find_conn(tickets,ticketPrivateConn);unsigned blob[1+HJ_TICKET_WORDS];HJPublicTicket manifest[HJ_TICKETS];
 memset(blob,0,sizeof(blob));blob[0]=ticket_magic();if(t)memcpy(blob+1,t->token,sizeof(t->token));
 ticket_write_blob(stream,blob,sizeof(blob));
 ticket_manifest_make(manifest);ticket_write_blob(stream,manifest,sizeof(manifest));
 ticket_write_blob(stream,&joinPause,sizeof(joinPause));
}
static void ticket_accept_private(void *stream) {
 unsigned blob[1+HJ_TICKET_WORDS];HJPublicTicket manifest[HJ_TICKETS];uintptr_t s=word(base+0x5f3fe4);
 if(!ticket_read_blob(stream,blob,sizeof(blob))||blob[0]!=ticket_magic()||!hj_token_present(blob+1))return;
 if(!ticket_read_blob(stream,manifest,sizeof(manifest)))return;
 if(!ticket_read_blob(stream,&joinPause,sizeof(joinPause))||joinPause.paused>1){joinPause.paused=1;joinPause.owner=joinPause.previous=0;joinPause.stamp=0xc61c3c00u;}
 if(ticketSession!=s){memset(tickets,0,sizeof(tickets));memset(ticketConns,0,sizeof(ticketConns));notice_reset();}
 ticketSession=s;ticketPreviousMode=word(s+0xf0);
 ticket_cache_local(blob+1);ticket_manifest_accept(manifest);
 host->log("hotjoin-lab","TICKET_CACHED in isolated private profile; value omitted");
}
static void __cdecl ticket_join_send(void *stream,void *body) {
 wchar_t empty[80];HJPublicTicket manifest[HJ_TICKETS];unsigned digest[8];memset(empty,0,sizeof(empty));
 ((BodySerialFn)(base+0x16d265))(stream,body);ticket_write_blob(stream,empty,sizeof(empty));
 if(multiMode){wchar_t name[96];unsigned crc=0;memset(name,0,sizeof(name));ticket_write_blob(stream,name,sizeof(name));ticket_write_blob(stream,&crc,sizeof(crc));}
 memset(manifest,0,sizeof(manifest));memset(digest,0,sizeof(digest));ticket_write_blob(stream,manifest,sizeof(manifest));ticket_write_blob(stream,digest,sizeof(digest));
 {HJPauseState ignored={1,0,0,0xc61c3c00u};ticket_write_blob(stream,&ignored,sizeof(ignored));}
}
static void __cdecl ticket_join_read(void *stream,void *body) {
 HJRole *role=ticket_role((uintptr_t)body,1);
 ((BodySerialFn)(base+0x16d212))(stream,body);
 if(!ticket_read_blob(stream,role->kingdom,sizeof(role->kingdom)))role->kingdom[0]=0;
 role->kingdom[79]=0;
 if(multiMode){
  if(!ticket_read_blob(stream,role->checkpoint,sizeof(role->checkpoint)))role->checkpoint[0]=0;
  role->checkpoint[95]=0;if(!ticket_read_blob(stream,&role->checkpointCrc,4))role->checkpointCrc=0;
 }
 if(!ticket_read_blob(stream,role->manifest,sizeof(role->manifest)))memset(role->manifest,0,sizeof(role->manifest));
 if(!ticket_read_blob(stream,role->peerVerifier,sizeof(role->peerVerifier)))memset(role->peerVerifier,0,sizeof(role->peerVerifier));
 if(!ticket_read_blob(stream,&role->pause,sizeof(role->pause))||role->pause.paused>1){role->pause.paused=1;role->pause.owner=role->pause.previous=0;role->pause.stamp=0xc61c3c00u;}
}
static void __cdecl ticket_join_decree(void *stream,void *body) {
 uintptr_t conn;HJConn *c;HJRole *role=ticket_role((uintptr_t)body,1);int human;uintptr_t ai;
 ((BodySerialFn)(base+0x16d265))(stream,body);role->kingdom[0]=0;
 conn=((FindConnFn)(base+0x14d092))((void*)word(base+0x5f3fec),0,(void*)word((uintptr_t)body+0x14));
 c=ticket_conn(conn,0);
 /* Only a real peer admission establishes a new hosted match credential.
  * Returning to an empty local staging screen after Leave must never replace
  * the credential for the match that the player just left. */
 ticket_ensure_host_credential();
 if(c&&c->capable&&!c->ticket)ticket_register(conn,0);
 if(c&&c->capable&&!c->duplicate&&c->ticket){
  ai=ticket_find_ai(c->ticket->kingdom,&human);
  if(hj_can_reclaim(c->ticket,ai!=0,human))wcscpy(role->kingdom,c->ticket->kingdom);
 }
 ticket_write_blob(stream,role->kingdom,sizeof(role->kingdom));
 if(multiMode){
  memset(role->checkpoint,0,sizeof(role->checkpoint));role->checkpointCrc=0;
  if(snapshotReady&&snapshotName&&wcslen(snapshotName)<96&&word(word(base+0x5f3fe4)+0xf0)==2){wcscpy(role->checkpoint,snapshotName);role->checkpointCrc=snapshotCrc;}
  ticket_write_blob(stream,role->checkpoint,sizeof(role->checkpoint));ticket_write_blob(stream,&role->checkpointCrc,4);
 }
 ticket_manifest_make(role->manifest);memset(role->peerVerifier,0,sizeof(role->peerVerifier));
 if(c&&c->ticket)memcpy(role->peerVerifier,c->ticket->verifier,32);
 ticket_write_blob(stream,role->manifest,sizeof(role->manifest));ticket_write_blob(stream,role->peerVerifier,sizeof(role->peerVerifier));
 role->pause=joinPause;ticket_write_blob(stream,&role->pause,sizeof(role->pause));
 host->log("hotjoin-lab","AUTHORITATIVE_ROLE return=%d; request role ignored",role->kingdom[0]!=0);
}
static void FC ticket_player_join(void *admin,void *unused,void *body) {
 HJRole *role=ticket_role((uintptr_t)body,0);HJTicket *t;uintptr_t conn,p,oldPlayer;int live,prior=noticeJoiningLive;(void)unused;
 conn=((FindConnFn)(base+0x14d092))(admin,0,(void*)word((uintptr_t)body+0x14));oldPlayer=word(conn+0xc);
 live=coordinatedMode&&((word(word(base+0x5f3fe4)+0xf0)==2&&word(base+0x5f3fb8))||clientSnapshot);
 if(role)ticket_manifest_accept(role->manifest);
 /* This is the authoritative native Join decree, never the request's claim. */
 if(live&&role)joinPause=role->pause;
 if(live&&role)safety_begin();
 if(multiMode&&role)multi_receive_checkpoint(role->checkpoint,role->checkpointCrc);
 ticketCurrentRole=role?role->kingdom:0;
 noticeJoiningLive=live;ticketApplyingLiveRole=live&&role!=0;
 ((CreatorSettingsFn)(base+0x14b50b))(admin,0,body);
 ticketApplyingLiveRole=0;noticeJoiningLive=prior;ticketCurrentRole=0;
 if(role&&(t=hj_find_verifier(tickets,role->peerVerifier))!=0){
  conn=((FindConnFn)(base+0x14d092))(admin,0,(void*)word((uintptr_t)body+0x14));p=word(conn+0xc);
  if(p){t->conn=conn;t->playerId=word(p+0x20);t->departed=0;ticket_remember(t,p);}
 }
 if(live&&!oldPlayer)notice_join(word(conn+0xc));
}
static unsigned char FC ticket_live_capacity(void *session,void *unused) {
 typedef unsigned char (FC *FullFn)(void*,void*);
 uintptr_t s=(uintptr_t)session,node,p;unsigned n=0,humans=0;unsigned char full;(void)unused;
 full=((FullFn)(base+0x16205a))(session,0);
 if(!full||!coordinatedMode||!ticketApplyingLiveRole)return full;
 for(node=word(s+0xc8);node&&n++<40;node=word(node+4)){
  p=word(node);if(!byte(p+0xc))humans++;
 }
 /* The room's launch-player limit counts spectators in the stock PlayerJoin
  * gate. Allow a verified live role's connection after kingdoms are occupied,
  * retaining the ceiling of 16 humans/observers and the same kingdom slots. */
 if(humans<16){host->log("hotjoin-lab","LIVE_CONNECTION_CAPACITY humans=%u; original kingdom slots unchanged",humans);return 0;}
 return full;
}
static int ticket_apply_return(void *session,uintptr_t player) {
 uintptr_t ai,kingdom;int human;wchar_t *name=0;
 if(!ticketCurrentRole||!ticketCurrentRole[0])return 0;
 ai=ticket_find_ai(ticketCurrentRole,&human);if(!ai||human)return 0;
 kingdom=word(ai+0x28);
 ((CreatorSettingsFn)(base+0x16240a))(session,0,(void*)ai);
 ((StringFn)(base+0x205de))(&name,0,ticketCurrentRole);
 ((CreatorSettingsFn)(base+0x15d6d5))((void*)player,0,&name);
 ((ReleaseFn)(base+0x21375))((char*)name-16,0);
 ((CreatorSettingsFn)(base+0x15d71a))((void*)player,0,(void*)kingdom);
 host->log("hotjoin-lab","RETURN_ROLE_APPLIED playerId=%u; implicit AI session player removed",word(player+0x20));return 1;
}
static void FC ticket_player_leave(void *admin,void *unused,void *player,int reason) {
 /* All actual departures pass through ClientLeave below. Invalid/replayed
  * PlayerLeave(NULL) after election must not create another pause event. */
 (void)unused;
 ((LeaveFn)(base+0x14b7c5))(admin,0,player,reason);
}
static void FC ticket_client_leave(void *admin,void *unused,void *connection,int reason,int notify,int votes) {
 typedef void (FC *ClientLeaveFn)(void*,void*,void*,int,int,int);
 uintptr_t conn=(uintptr_t)connection,p=word(conn+0xc),s=word(base+0x5f3fe4);HJTicket *t;HJConn *c;
 int playing=word(s+0xf0)==2&&p&&!byte(p+0xc);(void)unused;
 if(playing){
  pause_for_departure("native-client-leave-before-ai");t=hj_find_conn(tickets,conn);c=ticket_conn(conn,0);
  if(t){ticket_remember(t,p);t->conn=0;t->departed=1;host->log("hotjoin-lab","TICKET_DEPARTED playerId=%u hasKingdom=%d nativeReason=%d",t->playerId,t->kingdom[0]!=0,reason);}
  if(c)memset(c,0,sizeof(*c));
 }
 ((ClientLeaveFn)(base+0x14d42b))(admin,0,connection,reason,notify,votes);
 if(playing&&word(word(base+0x5f3fe4)+0xf0)==2)pause_for_departure("native-client-leave-after-cleanup");
}
static void FC ticket_backup_mode(void *admin,void *unused,int enabled) {
 uintptr_t a=(uintptr_t)admin;(void)unused;
 /* Local timeout detection is asynchronous: changing Sim.pause here strands
  * peers at different pending ticks. Queue the ordinary shared Pause order.
  * Native backup mode already stalls the world while that decree settles. */
 if((enabled&255)&&!byte(a+0x2f4)&&word(word(base+0x5f3fe4)+0xf0)==2&&word(base+0x5f3fb8)&&!hostJoinPending&&!clientSnapshot){
  InterlockedExchange(&departurePauseRequested,1);
  host->log("hotjoin-lab","LOSS_PAUSE_REQUESTED through shared native order; no asynchronous world pause");
 }
 ((BoolFn)(base+0x14f89c))(admin,0,enabled);
}
static unsigned FC ticket_admission_state(void *admin,void *unused) {
 typedef unsigned (FC *StateFn)(void*,void*);uintptr_t a=(uintptr_t)admin,s=word(base+0x5f3fe4);
 unsigned original=((StateFn)(base+0x14d162))(admin,0);HJConn *c=ticket_conn(ticketIncomingConn,0);(void)unused;
 if(ticket_can_replace(c))return 0;
 /* Native state 1 persists after a completed host election. Permit the
  * matching experimental protocol only after the live elected host has left
  * backup mode and has no pending task. Stock authentication follows. */
 if(original==1&&automaticMode&&c&&c->capable&&!c->duplicate&&word(a+0x2e4)==a&&
    word(s+0xf0)==2&&!byte(a+0x2f4)&&((!byte(word(base+0x5f3fe8)+0x29)&&!word(s+0x134))||auto_batch_window())&&auto_admission_ok()){
  host->log("hotjoin-lab","SETTLED_MIGRATED_HOST_ADMISSION; native identity and content checks follow");return 0;
 }
 return original;
}
static unsigned FC ticket_transfer_state(void *admin,void *unused) {
 typedef unsigned (FC *StateFn)(void*,void*);uintptr_t a=(uintptr_t)admin,s=word(base+0x5f3fe4);
 unsigned original=((StateFn)(base+0x14d162))(admin,0);(void)unused;
 /* The stock migrated-host state also disables SetMapTransferStatus. Permit
  * its normal CRC/filename/index-checked transfer for this admitted checkpoint
  * only. Never alter the persistent election state or bypass file validation. */
 if(original==1&&coordinatedMode&&hostJoinPending&&snapshotReady&&snapshotName&&
    word(a+0x2e4)==a&&word(s+0xf0)==2&&!byte(a+0x2f4)&&
    readable(word(s+0x68),2)&&!wcscmp((wchar_t*)word(s+0x68),snapshotName))return 0;
 return original;
}
static int ticket_install_departure(void) {
 static const unsigned calls[]={0x14b84b,0x14c1cf,0x14c3f4,0x14c717,0x14c765,0x14d546,0x14e2cc,0x150955,0x15151c,0x151c1d};
 unsigned i;for(i=0;i<sizeof(calls)/sizeof(calls[0]);i++)if(!redirect(calls[i],0x14d42b,ticket_client_leave))return 0;
 return redirect(0x14fa4a,0x14f89c,ticket_backup_mode)&&redirect(0x15180c,0x14f89c,ticket_backup_mode)&&redirect(0x150de6,0x14d162,ticket_admission_state)&&redirect(0x14b09a,0x14d162,ticket_transfer_state);
}
static void ticket_update(void) {
 unsigned i,n,mode;uintptr_t player,node,s=word(base+0x5f3fe4);HJTicket *t;
 mode=word(s+0xf0);
 if(ticketSession!=s||(ticketPreviousMode==2&&mode==1)){
  memset(tickets,0,sizeof(tickets));memset(ticketConns,0,sizeof(ticketConns));memset(ticketRoles,0,sizeof(ticketRoles));
  notice_reset();
  ticketSession=s;host->log("hotjoin-lab","TICKET_MATCH_RESET credentials from previous match invalidated");
 }
 ticketPreviousMode=mode;
 for(i=0;i<HJ_TICKETS;i++){
  t=tickets+i;if(!t->used||t->departed)continue;
  for(node=word(s+0xc8),n=0;node&&n++<40;node=word(node+4)){
   player=word(node);if(!byte(player+0xc)&&word(player+0x20)==t->playerId){t->conn=word(player+4);break;}
  }
  if(!t->conn)continue;
  player=word(t->conn+0xc);if(player&&!t->departed)ticket_remember(t,player);
 }
}
