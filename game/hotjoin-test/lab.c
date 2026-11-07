/* Private 1.3.72 live-join prototype. NOT a shipping reconnect component.
 * Never load in a user installation. Native version/content/auth checks remain.
 * Admission-only mode is deliberately incomplete and confined to a marked lab.
 */
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>
#define FC __attribute__((fastcall))
#ifdef PAWS_HOTJOIN_RELEASE
#define EXPORT static
#else
#define EXPORT __declspec(dllexport)
#endif
typedef struct { unsigned api; uintptr_t exeBase; const wchar_t *gameDir,*modsDir; void (__cdecl *log)(const char*,const char*,...); } Host;
typedef void *(FC *StringFn)(void*,void*,const wchar_t*);
typedef void (FC *ReleaseFn)(void*,void*);
typedef void (FC *RunFn)(void*,void*,void*,int);
typedef void (FC *DisconnectFn)(void*,void*,int,int);
typedef void (FC *SerializeFn)(void*,void*,void*);
typedef void (FC *PrivateAppendFn)(void*,void*);
typedef int (FC *AssignFn)(void*,void*,void*);
typedef uintptr_t (__cdecl *ResourceFn)(void*);
typedef void *(FC *CreatorCtor)(void*,void*,int);
typedef void (FC *CreatorSettingsFn)(void*,void*,void*);
typedef void (FC *FrozenFn)(void*,void*,int);
typedef void (FC *SessionFn)(void*,void*);
typedef void (FC *BoolFn)(void*,void*,int);
typedef void (FC *ResetFn)(void*,void*,int,int);
typedef void (FC *WorldSyncFn)(void*,void*,const wchar_t*);
typedef uintptr_t (FC *LookupFn)(void*,void*,void*);
typedef void (FC *HistoryFn)(void*,void*,void*,int);
static const Host *host;
static uintptr_t base;
static uintptr_t sessionWriteTarget,sessionReadTarget,sessionAppendTarget;
static int composedMode,startPrepared,startPending,startFailed;
static int testLegacyProtocol;
static DWORD mainThread,lastSample,lastPoll;
static unsigned commandId;
static int busy;
static wchar_t commandPath[MAX_PATH],statePath[MAX_PATH],syncPath[MAX_PATH];
static unsigned lastSyncTick;
static int snapshotMode,snapshotReady,coordinatedMode,hostReloadPending;
static wchar_t *snapshotName;
static uintptr_t snapshotCreator;
static uintptr_t snapshotResource;
static unsigned char snapshotLoadCreator[0x54];
static int loadCreatorConstructed;
static unsigned snapshotCrc;
static int clientSnapshot,clientLaunchStarted;
static int hostJoinPending;
static int actorTraceActive;
static unsigned selectionActor,selectionKingdom,selectionSally,selectionRecall;
static DWORD selectionPoll;
static DWORD clientFilePoll;
static wchar_t clientSnapshotPath[MAX_PATH];
static int automaticMode;
static int multiMode;
static int recoveryMode;
static int controlProbeMode;
static volatile LONG departurePauseRequested;
static volatile LONG testBackupVoteRequested;
static int noticeJoiningLive;
static int ticketApplyingLiveRole;
/* Authoritative pre-admission pause state. Connection addresses are local to
 * each process, so only native SessionPlayer IDs cross the wire. */
typedef struct {unsigned paused,owner,previous,stamp;} HJPauseState;
static HJPauseState joinPause={1,0,0,0xc61c3c00u};
static void pause_capture(void);
static void pause_commit(void);
static void notice_init(void);
static void notice_reset(void);
static void notice_join(uintptr_t player);
static void notice_committed(void);
static void notice_tick(void);
static unsigned char __cdecl notice_stock_join(void*,unsigned,const wchar_t*,const wchar_t*);
static int recovery_preconnect(uintptr_t conn,const unsigned *secret);
static int transfer_settings_ok(void);
static void multi_receive_checkpoint(const wchar_t *name,unsigned crc);
static void multi_maintain(void *session);
static void auto_committed(void);
static int auto_admission_ok(void);
static int auto_batch_window(void);
static int auto_batch_waiting(void);
static void auto_batch_assigned(uintptr_t conn);
static void auto_maintain(void *session);
static void auto_tick(void);
static void auto_saved(int success);
static void auto_prepare_load(void);
static void FC auto_join_send(void *order,void *unused,int destination);
static void FC serialize_view(void *session,void *unused,void *stream);
static int FC assign_probe(void *session,void *unused,void *player);
static void FC read_snapshot(void *session,void *unused,void *stream);
static void FC maintain_session(void *session,void *unused);
static void safety_begin(void);
static void safety_end(void);
static int safety_maintain(void);
static int safety_pre_tasks(void *session,int success);
static int safety_control(unsigned kind,uintptr_t sender,const void *wire);
static void safety_tick(void);
static void pause_for_departure(const char *why) {
 uintptr_t sim=*(uintptr_t*)(base+0x5f3fe8),world=*(uintptr_t*)(base+0x5f3fb8);
 if(!sim||!world)return;
 joinPause.paused=1;joinPause.owner=joinPause.previous=0;joinPause.stamp=0xc61c3c00u;
 ((BoolFn)(base+0x1612a2))((void*)sim,0,1);
 host->log("hotjoin-lab","MATCH_PAUSE_RETAINED reason=%s tick=%u; players resume manually",why,*(unsigned*)(world+0xe4));
}
static void FC keep_checkpoint_rng(void *rng,void *unused,int seed) {
 (void)unused;
 if(!coordinatedMode&&clientSnapshot&&clientLaunchStarted){
  host->log("hotjoin-lab","RESTORE_KEEP_RNG serialized=%x; ignoring new-game seed override",*(unsigned*)rng);return;
 }
 ((BoolFn)(base+0x302374))(rng,0,seed);
}
static void * FC keep_checkpoint_rules(void *rules,void *unused,void *override) {
 (void)unused;
 if(!coordinatedMode&&clientSnapshot&&clientLaunchStarted){
  host->log("hotjoin-lab","RESTORE_KEEP_RULES serializedMapType=%u; ignoring lobby rule override",*((unsigned*)rules+1));return rules;
 }
 return ((CreatorSettingsFn)(base+0x11c2da))(rules,0,override),rules;
}
static void FC tasks_probe(void *session,void *unused,int success) {
 uintptr_t s=(uintptr_t)session,net=*(uintptr_t*)(base+0x5f3ff0);(void)unused;
 success&=255;
 if(automaticMode&&safety_pre_tasks(session,success))return;
 host->log("hotjoin-lab","ALL_TASKS success=%d; clientSnapshot=%d phase2=%d netIndex=%u netCrc=%u",success,clientSnapshot,*(unsigned char*)(s+0x17a),*(unsigned*)(net+0x14),*(unsigned*)(net+8));
#ifndef PAWS_HOTJOIN_RELEASE
 if(coordinatedMode&&(clientSnapshot||hostJoinPending)){
  wchar_t path[MAX_PATH],*name=0;swprintf(path,L"%ls\\Mods\\before-commit-trace.txt",host->gameDir);
  ((StringFn)(base+0x205de))(&name,0,path);
  ((HistoryFn)(base+0x16e375))((void*)net,0,&name,*(unsigned*)(net+0x14));
  ((ReleaseFn)(base+0x21375))((char*)name-16,0);
 }
#endif
 if(!coordinatedMode&&success&&(clientSnapshot||hostJoinPending)){
  /* Native phase 2 assumes every peer has recreated the world from identical
   * launch settings. A late observer instead restored it privately. Shared
   * task completion still unfreezes both peers and preserves network tracing.
   * Validate the actual full world on BOTH peers at this shared order barrier. */
  *(unsigned char*)(s+0x17a)=0;
  ((BoolFn)(base+0x162816))(session,0,success);
  ((ResetFn)(base+0x16dfca))((void*)*(uintptr_t*)(base+0x5f3ff4),0,0,0);
  ((WorldSyncFn)(base+0x241e46))((void*)*(uintptr_t*)(base+0x5f3fb8),0,L"hotjoin_checkpoint");
  host->log("hotjoin-lab","CHECKPOINT_WORLD_COMPARED netIndex=%u netCrc=%u",*(unsigned*)(net+0x14),*(unsigned*)(net+8));
  hostJoinPending=0;clientSnapshot=0;
  return;
 }
 /* The native local load clears pause while frozen. Restore it at the shared
  * completion barrier BEFORE native completion can unfreeze the simulation. */
 if(coordinatedMode&&success&&(clientSnapshot||hostJoinPending))pause_commit();
 ((BoolFn)(base+0x162816))(session,0,success);
 if(automaticMode)auto_saved(success);
 if(coordinatedMode&&success&&(clientSnapshot||hostJoinPending)){
  host->log("hotjoin-lab","COORDINATED_NATIVE_COMMIT netIndex=%u netCrc=%u",*(unsigned*)(net+0x14),*(unsigned*)(net+8));
  /* Keep the native sender-player prefix explicit after restoring a world.
   * This cache can still name the pre-load sender, while a newly arrived peer
   * has no such actor context. Reusing it can omit SetPlayer before the first
   * AI selection order. Invalidate only the send optimization; the ordinary
   * native request/decree writes and checks the actual player identity. */
  *(uintptr_t*)(*(uintptr_t*)(base+0x5f3fec)+0x230)=0;
#ifndef PAWS_HOTJOIN_RELEASE
  actorTraceActive=1;
#endif
  notice_committed();
  host->log("hotjoin-lab","SENDER_PREFIX_INVALIDATED next native order must identify its sender");
  hostJoinPending=0;clientSnapshot=0;
  if(automaticMode)auto_committed();
  safety_end();
 }
}
static void FC disconnect_probe(void *conn,void *unused,int notify,int reason) {
 (void)unused;host->log("hotjoin-lab","NATIVE_REJECT reason=%d; notify=%d",reason,notify);
 ((DisconnectFn)(base+0x152379))(conn,0,notify,reason);
}
static int redirect(unsigned rva,unsigned target,void *replacement) {
 DWORD old,ignored;uintptr_t site=base+rva;int delta=(uintptr_t)replacement-site-5;
 if((*(unsigned char*)site!=0xe8 && *(unsigned char*)site!=0xe9) || site+5+*(int*)(site+1)!=base+target)return 0;
 if(!VirtualProtect((void*)(site+1),4,PAGE_EXECUTE_READWRITE,&old))return 0;
 memcpy((void*)(site+1),&delta,4);VirtualProtect((void*)(site+1),4,old,&ignored);
 FlushInstructionCache(GetCurrentProcess(),(void*)site,5);return 1;
}
static int readable(uintptr_t p,unsigned n) {
 MEMORY_BASIC_INFORMATION m;
 return p && p+n>=p && VirtualQuery((void*)p,&m,sizeof(m)) && m.State==MEM_COMMIT &&
 !(m.Protect&(PAGE_GUARD|PAGE_NOACCESS)) && p+n<=(uintptr_t)m.BaseAddress+m.RegionSize;
}
static unsigned word(uintptr_t p) { return readable(p,4)?*(unsigned*)p:0; }
static unsigned byte(uintptr_t p) { return readable(p,1)?*(unsigned char*)p:0; }
static int test_hold(const char *stage) {
#ifdef PAWS_HOTJOIN_RELEASE
 (void)stage;return 0;
#else
 wchar_t path[MAX_PATH];char value[24]={0};FILE *f;static char shown[24];
 swprintf(path,L"%ls\\Mods\\lab-hold.flag",host->gameDir);f=_wfopen(path,L"rb");
 if(f){fread(value,1,sizeof(value)-1,f);fclose(f);}
 if(strcmp(value,stage)){if(!value[0])shown[0]=0;return 0;}
 if(strcmp(shown,stage)){
  char upper[24];unsigned i;for(i=0;stage[i]&&i<23;i++)upper[i]=(stage[i]>='a'&&stage[i]<='z')?stage[i]-32:stage[i];upper[i]=0;
  strcpy(shown,stage);host->log("hotjoin-lab","TEST_HOLD_%s private QA delay; native validation remains required",upper);
 }
 return 1;
#endif
}
static unsigned pause_player_id(uintptr_t conn) {return word(word(conn+0xc)+0x20);}
static uintptr_t pause_connection(unsigned id) {
 uintptr_t s=word(base+0x5f3fe4),node,p;unsigned n=0;
 if(!id)return 0;
 for(node=word(s+0xc8);node&&n++<40;node=word(node+4)){
  p=word(node);if(word(p+0x20)==id&&!byte(p+0xc))return word(p+4);
 }
 return 0;
}
static void pause_capture(void) {
 uintptr_t a=word(base+0x5f3fec);
 joinPause.paused=!!byte(word(base+0x5f3fe8)+0x28);
 joinPause.owner=pause_player_id(word(a+0x2c0));
 joinPause.previous=pause_player_id(word(a+0x2c4));joinPause.stamp=word(a+0x2c8);
 host->log("hotjoin-lab","JOIN_PRIOR_PAUSE captured=%u ownerId=%u",joinPause.paused,joinPause.owner);
}
static void pause_commit(void) {
 uintptr_t a=word(base+0x5f3fec),owner=pause_connection(joinPause.owner);
 /* Native session serialization omits pause owner and votes. Restore the
  * authoritative owner on EVERY peer before unfreezing; otherwise a Resume
  * can bypass voting on the old peer while remaining a vote on the new one. */
 ((BoolFn)(base+0x14c7fa))((void*)a,0,(int)owner);
 *(uintptr_t*)(a+0x2c4)=pause_connection(joinPause.previous);
 *(unsigned*)(a+0x2c8)=joinPause.stamp;
 ((SessionFn)(base+0x14c887))((void*)a,0);
 ((BoolFn)(base+0x1612a2))((void*)word(base+0x5f3fe8),0,(int)joinPause.paused);
 host->log("hotjoin-lab","JOIN_PAUSE_COMMITTED paused=%u ownerId=%u; native resume votes reset",joinPause.paused,pause_player_id(owner));
}
static void ascii(uintptr_t p,char *s,unsigned cap) {
 unsigned n=0,c; while(n+1<cap && readable(p+n*2,2) && (c=*(unsigned short*)(p+n*2))){
 s[n++]=(c>=32&&c<127&&c!='"'&&c!='\\')?(char)c:'?'; } s[n]=0;
}
#include "ticket_runtime.h"
#include "load_barrier.h"
#include "notice_runtime.h"
static void FC actor_context_probe(void *order,void *unused) {
 uintptr_t a=word(base+0x5f3fec),s=word(base+0x5f3fe4);(void)unused;
 ((SessionFn)(base+0x156628))(order,0);
 if(actorTraceActive)host->log("hotjoin-lab","NATIVE_SENDER_PREFIX id=%u playback=%u resolved=%x",word((uintptr_t)order+4),byte(s+0x24),word(a+0x2a4));
}
static unsigned ai_controllers(uintptr_t kingdom) {
 uintptr_t sai=word(base+0x5f3fc8),array=word(sai+0x6c),brain;unsigned i,count=0,size=word(sai+0x70);
 if(!kingdom||size>40)return 0;
 for(i=0;i<size;i++){brain=word(array+i*4);if(brain&&word(brain+8)==kingdom)count++;}
 return count;
}
static void observe_own_selection(void) {
 typedef uintptr_t (FC *OwnerFn)(void*,void*);
 typedef unsigned char (FC *CanFn)(void*,void*,unsigned);
 uintptr_t a=word(base+0x5f3fec),p=word(a+0xc),mgr=word(p+0x58),node=word(mgr+4),actor=word(node),vtable=word(actor);
 DWORD now=GetTickCount();if(now-selectionPoll<500)return;selectionPoll=now;
 selectionActor=selectionKingdom=selectionSally=selectionRecall=0;
 if(word(base+0x5f92f4)!=4||!word(base+0x5f3fb8)||word(word(base+0x5f3fe4)+0x134)||!readable(actor,0x104)||!readable(vtable,0x10c))return;
 selectionKingdom=((OwnerFn)word(vtable+0x108))((void*)actor,0);
 if(!selectionKingdom||selectionKingdom!=word(p+0x28)){selectionKingdom=0;return;}
 selectionActor=word(actor+0x14);
 selectionSally=((CanFn)word(vtable+0x34))((void*)actor,0,23);
 selectionRecall=((CanFn)word(vtable+0x34))((void*)actor,0,24);
}
static void FC preserve_implicit_players(void *session,void *unused) {
 (void)unused;
 if(coordinatedMode&&(hostJoinPending||clientSnapshot)){
  /* A normal in-game reload removes implicit AIs and recreates their session
   * identities in FinalizeLaunchSettings. A fresh arriving peer is in staging
   * and retains the identities from its authoritative session view instead.
   * Preserve the SAME roster on existing peers: native world unbinding and
   * controller teardown still run, and FinalizeLaunchSettings sees each
   * reserved kingdom already represented, so no new AI identity is invented. */
  host->log("hotjoin-lab","COORDINATED_AI_ROSTER_PRESERVED; native world/controller cleanup retained");return;
 }
 ((SessionFn)(base+0x16adee))(session,0);
}
static void FC world_ready(void *session,void *unused) {
 uintptr_t s=(uintptr_t)session,w=word(base+0x5f3fb8),node,p,k,sai=word(base+0x5f3fc8);unsigned n=0;(void)unused;
 if(coordinatedMode&&(hostJoinPending||clientSnapshot)&&w){
  /* Saved world parameters retain the old AI marker independently of session
   * assignments. Human ownership is authoritative at the restore barrier.
   * Retire any restored AI brain through its native destructor before SAI
   * InitForGame can start thinking; do this on every peer, before full sync. */
  for(node=word(s+0xc8);node&&n++<40;node=word(node+4)){
   p=word(node);if(byte(p+0xc)||!word(word(p+0x24)-12))continue;
   k=((LookupFn)(base+0x24270a))((void*)w,0,(void*)(p+0x24));
   if(!readable(k,0x24a))continue;
   host->log("hotjoin-lab","HUMAN_RESTORE playerId=%u oldAi=%u oldBrains=%u",word(p+0x20),byte(k+0x249),ai_controllers(k));
   ((CreatorSettingsFn)(base+0x1e04b4))((void*)sai,0,(void*)k);
   *(unsigned char*)(k+0x249)=0;
  }
 }
 ((SessionFn)(base+0x16a091))(session,0);
}
static int __cdecl gate_reject(void) {
 HJConn *c;uintptr_t s=word(base+0x5f3fe4);
 if(coordinatedMode){
  c=ticket_conn(ticketIncomingConn,0);
  if(!c||!c->capable||(c->duplicate&&!ticket_can_replace(c))){host->log("hotjoin-lab","PROTOCOL_ADMISSION_REFUSED capable=%d duplicate=%d",c?c->capable:0,c?c->duplicate:0);return 1;}
 }
 if(word(s+0xf0)!=2)return 0;
 if(!snapshotMode)return 0;
 if(!coordinatedMode)return !snapshotReady;
 c=ticket_conn(ticketIncomingConn,0);
 if(automaticMode)return !auto_admission_ok();
 if(!snapshotReady||hostJoinPending||!c||!c->capable||c->duplicate){
  host->log("hotjoin-lab","HOT_ADMISSION_REFUSED ready=%d busy=%d capable=%d duplicate=%d",snapshotReady,hostJoinPending,c?c->capable:0,c?c->duplicate:0);return 1;
 }
 return 0;
}
static int install_admission_gate(void) {
 unsigned char code[]={0x9c,0x60,0xe8,0,0,0,0,0x85,0xc0,0x75,7,0x61,0x9d,0xe9,0,0,0,0,0x61,0x9d,0xe9,0,0,0,0};
 unsigned char patch[]={0xe9,0,0,0,0,0x90};unsigned char *cave;
 DWORD old,ignored;uintptr_t site=base+0x150e19;
 cave=VirtualAlloc(0,sizeof(code),MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);if(!cave)return 0;
 *(int*)(code+3)=(uintptr_t)gate_reject-(uintptr_t)cave-7;
 *(int*)(code+14)=base+0x150e1f-(uintptr_t)cave-18;
 *(int*)(code+21)=base+0x150fda-(uintptr_t)cave-25;
 memcpy(cave,code,sizeof(code));
 if(!VirtualProtect(cave,sizeof(code),PAGE_EXECUTE_READ,&old))return 0;
 FlushInstructionCache(GetCurrentProcess(),cave,sizeof(code));
 *(int*)(patch+1)=(uintptr_t)cave-site-5;
 if(!VirtualProtect((void*)site,6,PAGE_EXECUTE_READWRITE,&old))return 0;
 memcpy((void*)site,patch,6);VirtualProtect((void*)site,6,old,&ignored);
 FlushInstructionCache(GetCurrentProcess(),(void*)site,6);return 1;
}
static void prepare_snapshot(unsigned crc) {
 uintptr_t resource;
 if(!snapshotName)((StringFn)(base+0x205de))(&snapshotName,0,L"Save/HotJoinSnapshot.RSG");
 resource=((ResourceFn)(base+0x1c2f25))(&snapshotName);
 if(!readable(resource,0x94)||!readable(word(resource+0x90),0x68)) {
  host->log("hotjoin-lab","SNAPSHOT_NOT_READY resource=%x",(unsigned)resource);return;
 }
 snapshotCreator=word(resource+0x90);snapshotResource=resource;
 if(!loadCreatorConstructed){
  ((CreatorCtor)(base+0x297e9c))(snapshotLoadCreator,0,0);loadCreatorConstructed=1;
 }
 ((CreatorSettingsFn)(base+0x297548))(snapshotLoadCreator,0,(void*)snapshotCreator);
 *(uintptr_t*)(snapshotLoadCreator+0x50)=resource;
 snapshotCrc=crc;snapshotReady=1;
 host->log("hotjoin-lab","SNAPSHOT_READY resource=%x creator=%x crc=%x",(unsigned)resource,(unsigned)snapshotCreator,crc);
}
static void FC serialize_view(void *session,void *unused,void *stream) {
 unsigned char view[0x188];uintptr_t s=(uintptr_t)session;
 (void)unused;
 if(snapshotMode&&snapshotReady&&word(s+0xf0)==2&&word(base+0x5f3fb8)&&readable(s,sizeof(view))&&readable(snapshotCreator,0x68)){
  memcpy(view,session,sizeof(view));
  *(unsigned*)(view+0x60)=2; /* Request loading only on the arriving peer. */
  *(unsigned*)(view+0x64)=2; /* WorldCreatorLoad */
  *(wchar_t**)(view+0x68)=snapshotName;
  *(unsigned*)(view+0x6c)=3; /* Native saved-game load role. */
  *(uintptr_t*)(view+0x74)=snapshotCreator;
  *(uintptr_t*)(view+0x7c)=(uintptr_t)snapshotLoadCreator;
  *(unsigned*)(view+0x108)=snapshotCrc;
  host->log("hotjoin-lab","SERIALIZE_SNAPSHOT_VIEW world=%x; host session unchanged",word(base+0x5f3fb8));
  ((SerializeFn)(base+0x16775c))(view,0,stream);
 }else ((SerializeFn)(base+0x16775c))(session,0,stream);
 /* The existing color extension must see the REAL session identity. Passing
  * the temporary loading view would reset its session-local palette state. */
 if(sessionAppendTarget){PrivateAppendFn append=(PrivateAppendFn)sessionAppendTarget;append(session,stream);}
 if(coordinatedMode)ticket_append_private(stream);
}
static void FC serialize_order_cursor(void *conn,void *unused,void *stream) {
 uintptr_t a=word(base+0x5f3fec),s=word(base+0x5f3fe4),previous=word(a+0x228),active=word(a+0x2a4),node;
 unsigned n=0;int valid=0;(void)unused;
 if(coordinatedMode&&hostJoinPending&&word(s+0xf0)==2&&active){
  for(node=word(s+0xc8);node&&n++<40;node=word(node+4))if(word(node)==active){valid=1;break;}
 }
 /* Private admission can start in the middle of a native request batch.
  * Its bit/decree cursor already points past PlayerJoin, but +228 is only
  * updated at END of that batch. Serialize the actual in-flight sender for
  * the continuation, then restore the native previous-batch field. The
  * unmodified native reader maps that player ID to the new peer's objects. */
 if(valid)*(uintptr_t*)(a+0x228)=active;
 ((SerializeFn)(base+0x152926))(conn,0,stream);
 if(valid){
  *(uintptr_t*)(a+0x228)=previous;
  host->log("hotjoin-lab","PRIVATE_ORDER_CONTEXT previousId=%u activeId=%u; native cursor preserved",word(previous+0x20),word(active+0x20));
 }
}
static int FC assign_probe(void *session,void *unused,void *player) {
 HJTicket *ticket=0;int returned=0;
 (void)unused;
 if(coordinatedMode)ticket=ticket_register(word((uintptr_t)player+4),(uintptr_t)player);
 if(snapshotMode&&word((uintptr_t)session+0xf0)==2&&word(base+0x5f3fb8)){
  uintptr_t sim=word(base+0x5f3fe8);
  if(readable(sim,0x40)&&word(sim+0x3c)==word(base+0x5f3fb8)){
   if(!hostJoinPending){
    ((FrozenFn)(base+0x1612ac))((void*)sim,0,1);
    host->log("hotjoin-lab","JOIN_BARRIER native simulation frozen on network thread; no sync reset");
    control_reset(word((uintptr_t)player+0x20));
   }else host->log("hotjoin-lab","JOIN_GROUP_EXTENDED existing native freeze retained; no duplicate recorded freeze");
   hostJoinPending=1;control_admitted(word((uintptr_t)player+0x20));
   if(automaticMode)auto_batch_assigned(word((uintptr_t)player+4));
   if(coordinatedMode)hostReloadPending=1;
   else ((BoolFn)(base+0x14b305))((void*)word(base+0x5f3fec),0,1);
  }else host->log("hotjoin-lab","JOIN_BARRIER_REFUSED sim=%x world=%x",(unsigned)sim,word(base+0x5f3fb8));
  if(coordinatedMode)returned=ticket_apply_return(session,(uintptr_t)player);
  if(ticket){ticket->departed=0;if(!returned)ticket->kingdom[0]=0;}
  host->log("hotjoin-lab","JOIN_ROLE player=%x; returning=%d; visitor has no kingdom auto-assignment",(unsigned)player,returned);return 1;
 }
 if(coordinatedMode&&clientSnapshot&&word((uintptr_t)session+0xf0)==1){
  /* Another authenticated member can join the SAME checkpoint while this
   * peer is receiving it. Respect the host's role decree in staging as well;
   * stock staging auto-assignment must not take an AI kingdom for a visitor. */
  ticket_apply_return(session,(uintptr_t)player);return 1;
 }
 return ((AssignFn)(base+0x168042))(session,0,player);
}
static void FC read_snapshot(void *session,void *unused,void *stream) {
 uintptr_t s=(uintptr_t)session;const wchar_t *name;SerializeFn reader=(SerializeFn)sessionReadTarget;(void)unused;
 reader(session,0,stream);
 if(coordinatedMode)ticket_accept_private(stream);
 name=(const wchar_t*)word(s+0x68);
 if(snapshotMode&&readable((uintptr_t)name,48)&&(!wcscmp(name,L"Save/HotJoinSnapshot.RSG")||(automaticMode&&!wcsncmp(name,L"Save/PawHotJoin-",16)))&&word(s+0x60)==2&&word(s+0x64)==2){
  if(automaticMode){
   wchar_t docs[MAX_PATH];GetEnvironmentVariableW(L"PAWS_TEST_DOCUMENTS",docs,MAX_PATH);
   if(wcslen(name)>95||wcsspn(name,L"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789/-.")!=wcslen(name))return;
   swprintf(clientSnapshotPath,L"%ls\\Kohan2\\data\\%ls",docs,name);
  }
  if(snapshotName)((ReleaseFn)(base+0x21375))((char*)snapshotName-16,0);
  snapshotName=0;((StringFn)(base+0x205de))(&snapshotName,0,name);
  clientSnapshot=1;host->log("hotjoin-lab","CLIENT_SNAPSHOT_SESSION accepted native snapshot metadata");
  clientLaunchStarted=0;control_reset(word(word(base+0x5f3fec)+0x74));
  safety_begin();
  notice_join(word(word(base+0x5f3fec)+0xc));
 }
}
static int file_crc(unsigned *crc) {
 FILE *f;unsigned c=0;unsigned char data[8192];size_t n,i;unsigned bytes=0;
 f=_wfopen(clientSnapshotPath,L"rb");if(!f)return 0;
 while((n=fread(data,1,sizeof(data),f))!=0){for(i=0;i<n;++i)c=c*7+data[i];bytes+=(unsigned)n;}
 fclose(f);if(bytes<1000)return 0;*crc=c;return 1;
}
static void FC maintain_session(void *session,void *unused) {
 uintptr_t s=(uintptr_t)session;unsigned crc;DWORD now=GetTickCount();(void)unused;
 ((SessionFn)(base+0x16203e))(session,0);
 if(coordinatedMode)ticket_update();
 if(automaticMode&&safety_maintain())return;
 if(automaticMode)auto_maintain(session);
 if(multiMode)multi_maintain(session);
 if(controlProbeMode)observe_own_selection();
 #ifndef PAWS_HOTJOIN_RELEASE
 {
  uintptr_t w=word(base+0x5f3fb8),net=word(base+0x5f3ff0),ws=word(base+0x5f3ff4);unsigned tick=word(w+0xe4);FILE *f;
  if(w&&word(s+0xf0)==2&&tick!=lastSyncTick&&!(tick%16)){
   lastSyncTick=tick;f=_wfopen(syncPath,L"a");if(f){
    fprintf(f,"{\"world\":%u,\"tick\":%u,\"seconds\":%.4f,\"worldIndex\":%u,\"worldCrc\":%u,\"netIndex\":%u,\"netCrc\":%u,\"netDepth\":%u}\n",(unsigned)w,tick,*(float*)(w+0xe8),word(ws+0x14),word(ws+8),word(net+0x14),word(net+8),word(net+4));fclose(f);
   }
  }
 }
 #endif
 if(coordinatedMode&&hostReloadPending&&snapshotReady&&loadBarrierReady&&word(s+0xf0)==2){
  uintptr_t load=word(s+0x7c);
  hostReloadPending=0;
  ((CreatorSettingsFn)(base+0x1c2355))((void*)word(s+0x74),0,(void*)snapshotCreator);
  ((CreatorSettingsFn)(base+0x297548))((void*)load,0,(void*)snapshotCreator);
  *(uintptr_t*)(load+0x50)=snapshotResource;
  ((CreatorSettingsFn)(base+0x23fb6))((void*)(s+0x68),0,&snapshotName);
  *(unsigned*)(s+0x60)=2;*(unsigned*)(s+0x64)=2;*(unsigned*)(s+0x6c)=3;
  *(unsigned*)(s+0x10c)=snapshotCrc;
  host->log("hotjoin-lab","COORDINATED_RESTORE host session retained; native in-game checkpoint reload");
  if(automaticMode)auto_prepare_load();
  ((BoolFn)(base+0x16e788))((void*)word(base+0x5f3ff0),0,0);
  ((SessionFn)(base+0x1626da))(session,0);
  ((BoolFn)(base+0x16e788))((void*)word(base+0x5f3ff0),0,1);
  return;
 }
 if(!clientSnapshot||clientLaunchStarted||word(s+0xf0)!=1||word(base+0x5f3fb8)||(!loadBarrierReady&&now-clientFilePoll<1000))return;
 clientFilePoll=now;
 if(!file_crc(&crc)||crc!=word(s+0x108))return;
 if(coordinatedMode&&!loadReadySent){control_send_ready();return;}
 if(coordinatedMode&&!loadBarrierReady)return;
 if(test_hold("load"))return;
 clientLaunchStarted=1;
 if(coordinatedMode)*(unsigned*)(s+0x10c)=crc;
 host->log("hotjoin-lab","CLIENT_CHECKPOINT_VERIFIED crc=%x; invoking native load on network thread",crc);
 if(automaticMode)auto_prepare_load();
 /* A private restore is a local operation, like native CreateLaunchTask's
  * scoped destruction. Exclude only this synchronous setup from the shared
  * order trace. The scope ends before the next network order/tick; neither
  * checksum state nor the native failure handler is reset or patched. */
 ((BoolFn)(base+0x16e788))((void*)word(base+0x5f3ff0),0,0);
 ((SessionFn)(base+0x1626da))(session,0);
 ((BoolFn)(base+0x16e788))((void*)word(base+0x5f3ff0),0,1);
 host->log("hotjoin-lab","LOCAL_RESTORE_SCOPE_END netDisableDepth=%u",word(word(base+0x5f3ff0)+4));
}
static int run(const wchar_t *command) {
 wchar_t *text=0;uintptr_t console;
 /* Console global is decoded from a hash-verified instruction, not guessed. */
 console=word(word(base+0x13df08));
 if(!console||GetCurrentThreadId()!=mainThread)return 0;
 ((StringFn)(base+0x205de))(&text,0,command);
 if(!text)return 0;
 ((RunFn)(base+0x1f9963))((void*)console,0,&text,0);
 ((ReleaseFn)(base+0x21375))((char*)text-16,0);return 1;
}
#include "auto_runtime.h"
#include "multi_runtime.h"
#include "recovery_runtime.h"
#include "transfer_runtime.h"
#include "safety_runtime.h"
static void sample(void) {
 uintptr_t s=word(base+0x5f3fe4),a=word(base+0x5f3fec),w=word(base+0x5f3fb8),node,p,conn;
 FILE *f;unsigned n=0,k=0;char name[100],kingdom[100];float seconds=0;
 if(readable(w+0xe8,4))seconds=*(float*)(w+0xe8);
 f=_wfopen(statePath,L"a");if(!f)return;
 fprintf(f,"{\"ms\":%lu,\"phase\":%u,\"session\":%u,\"mode\":%u,\"desired\":%u,\"mapType\":%u,\"world\":%u,\"seconds\":%.4f,\"host\":%u,\"decree\":%u,\"request\":%u,\"players\":[",GetTickCount(),word(base+0x5f92f4),(unsigned)s,word(s+0xf0),word(s+0x60),word(s+0x64),(unsigned)w,seconds,a&&word(a+0x2e4)==a,word(a+0x238),word(a+0x220));
 for(node=word(s+0xc8);node&&n<40;node=word(node+4)) {
  p=word(node);if(!readable(p,0x5c))break;
  conn=word(p+4);
  ascii(word(p+8),name,sizeof(name));ascii(word(p+0x24),kingdom,sizeof(kingdom));
  fprintf(f,"%s{\"id\":%u,\"ai\":%u,\"implicit\":%u,\"conn\":%u,\"kingdomPtr\":%u,\"kingdomAi\":%u,\"aiControllers\":%u,\"name\":\"%s\",\"kingdom\":\"%s\",\"fileState\":%u,\"sendFirst\":%u,\"sendLast\":%u,\"sendBytes\":%u,\"receiveBytes\":%u}",n?",":"",word(p+0x20),byte(p+0xc),byte(p+0xd),(unsigned)conn,word(p+0x28),byte(word(p+0x28)+0x249),ai_controllers(word(p+0x28)),name,kingdom,conn!=a?word(conn+0x3c):0,conn!=a?word(conn+0x3b4+0x2c):0,conn!=a?word(conn+0x3b4+0x30):0,conn!=a?word(conn+0x3b4+0x48):0,conn!=a?word(conn+0x400+0x24):0);++n;
 }
 fprintf(f,"],\"selectionActor\":%u,\"selectionKingdom\":%u,\"selectionSally\":%u,\"selectionRecall\":%u",selectionActor,selectionKingdom,selectionSally,selectionRecall);
 fprintf(f,",\"mapWidth\":%u,\"mapHeight\":%u",word(word(w+0x30)+0x1c)*2,word(word(w+0x30)+0x20)*2);
 fprintf(f,",\"pauseOwnerId\":%u,\"pausePreviousOwnerId\":%u",pause_player_id(word(a+0x2c0)),pause_player_id(word(a+0x2c4)));
 fprintf(f,",\"passwordConfigured\":%u",word(word(s+0xdc)-12)!=0);
 fprintf(f,",\"incomingReceiveExpected\":%u,\"incomingReceiveFirst\":%u",word(a+0x2e4)!=a?word(word(a+0x2e4)+0x424):0,word(a+0x2e4)!=a?word(word(a+0x2e4)+0x408):0);
 fprintf(f,",\"resignVoteIds\":[");n=0;
 for(node=word(s+0xc8);node&&k++<40;node=word(node+4)){
  p=word(node);if(byte(p+0x1c))fprintf(f,"%s%u",n++?",":"",word(p+0x20));
 }
 fprintf(f,"]");
 fprintf(f,",\"backupHost\":%u,\"paused\":%u,\"backup\":%u,\"frozen\":%u,\"worldTicks\":%u,\"netIndex\":%u,\"netCrc\":%u,\"netDepth\":%u,\"worldIndex\":%u,\"worldCrc\":%u,\"task\":%u}\n",a&&word(a+0x2e8)==a,byte(word(base+0x5f3fe8)+0x28),byte(a+0x2f4),byte(word(base+0x5f3fe8)+0x29),word(w+0xe4),word(word(base+0x5f3ff0)+0x14),word(word(base+0x5f3ff0)+8),word(word(base+0x5f3ff0)+4),word(word(base+0x5f3ff4)+0x14),word(word(base+0x5f3ff4)+8),word(a+0xa0));fclose(f);
}
#ifdef PAWS_HOTJOIN_MONITOR
static SessionFn monitorMaintain;
static void FC monitor_session(void *session,void *unused) {
 uintptr_t a=word(base+0x5f3fec),w,net,ws;unsigned tick;FILE *f;(void)unused;
 monitorMaintain(session,0);
 if(testBackupVoteRequested&&byte(a+0x2f4)){
  ((BoolFn)(base+0x14aab6))((void*)a,0,1);InterlockedExchange(&testBackupVoteRequested,0);
  host->log("hotjoin-monitor","TEST_PLAYER_NATIVE_BACKUP_VOTE; explicit fixture action");
 }
 w=word(base+0x5f3fb8);net=word(base+0x5f3ff0);ws=word(base+0x5f3ff4);tick=word(w+0xe4);
 if(w&&word((uintptr_t)session+0xf0)==2&&tick!=lastSyncTick&&!(tick%16)){
  lastSyncTick=tick;f=_wfopen(syncPath,L"a");if(f){
   fprintf(f,"{\"world\":%u,\"tick\":%u,\"seconds\":%.4f,\"worldIndex\":%u,\"worldCrc\":%u,\"netIndex\":%u,\"netCrc\":%u,\"netDepth\":%u}\n",(unsigned)w,tick,*(float*)(w+0xe8),word(ws+0x14),word(ws+8),word(net+0x14),word(net+8),word(net+4));fclose(f);
  }
 }
}
#endif
EXPORT int __cdecl K2Plugin_Start(const Host *h) {
 wchar_t marker[MAX_PATH],mode[40];
 static const unsigned char gate[]={0x0f,0x84,0xbb,0x01,0x00,0x00};
 if(!h||h->api!=1||wcslen(h->gameDir)>MAX_PATH-40)return 1;
 host=h;base=h->exeBase;mainThread=GetCurrentThreadId();
 if(!startPrepared){
  notice_init();startPrepared=1;sessionWriteTarget=base+0x16775c;sessionReadTarget=base+0x16797a;
  mode[0]=0;GetEnvironmentVariableW(L"PAWS_HOTJOIN_COMPOSED",mode,40);
  if(!wcscmp(mode,L"1")){composedMode=1;startPending=1;host->log("hotjoin-lab","COMPOSED_WAITING_FOR_OWNED_HELPER; no native hooks installed yet");return 0;}
 }
 swprintf(marker,L"%ls\\hotjoin-lab.marker",h->gameDir);
#ifndef PAWS_HOTJOIN_RELEASE
 if(GetFileAttributesW(marker)==INVALID_FILE_ATTRIBUTES)return 1;
#endif
#ifdef PAWS_HOTJOIN_MONITOR
 {
  HMODULE runtime=GetModuleHandleW(L"paws_hotjoin.dll");MEMORY_BASIC_INFORMATION region;uintptr_t target;
  if(!runtime||byte(base+0x14cb6a)!=0xe8)return 1;
  target=base+0x14cb6f+(int)word(base+0x14cb6b);
  if(!VirtualQuery((void*)target,&region,sizeof(region))||region.AllocationBase!=runtime)return 1;
  swprintf(commandPath,L"%ls\\Mods\\lab-command.txt",h->gameDir);
  swprintf(statePath,L"%ls\\Mods\\lab-state.jsonl",h->gameDir);
  swprintf(syncPath,L"%ls\\Mods\\lab-sync.jsonl",h->gameDir);
  monitorMaintain=(SessionFn)target;
  if(!redirect(0x14cb6a,(unsigned)(target-base),monitor_session))return 1;
  host->log("hotjoin-monitor","PRODUCTION_RUNTIME_OBSERVER_READY; native product owns all hot-join logic; fixture commands and CRC sampling only");return 0;
 }
#endif
 if(composedMode&&!composed_prepare())return 1;
 if(*(unsigned short*)(base+0x13df06)!=0x0d8b || memcmp((void*)(base+0x150e19),gate,6))return 1;
 if(!redirect(0x150fe0,0x152379,disconnect_probe))return 1;
 swprintf(commandPath,L"%ls\\Mods\\lab-command.txt",h->gameDir);
 swprintf(statePath,L"%ls\\Mods\\lab-state.jsonl",h->gameDir);
 swprintf(syncPath,L"%ls\\Mods\\lab-sync.jsonl",h->gameDir);
 mode[0]=0;GetEnvironmentVariableW(L"PAWS_HOTJOIN_LAB",mode,40);coordinatedMode=!wcscmp(mode,L"coordinated");snapshotMode=!wcscmp(mode,L"snapshot")||coordinatedMode;
 automaticMode=GetEnvironmentVariableW(L"PAWS_HOTJOIN_AUTO",mode,40)&&!wcscmp(mode,L"1");
 multiMode=GetEnvironmentVariableW(L"PAWS_HOTJOIN_MULTI",mode,40)&&!wcscmp(mode,L"1");
 recoveryMode=GetEnvironmentVariableW(L"PAWS_HOTJOIN_RECOVER",mode,40)&&!wcscmp(mode,L"1");
 controlProbeMode=GetEnvironmentVariableW(L"PAWS_HOTJOIN_CONTROL",mode,40)&&!wcscmp(mode,L"1");
 testLegacyProtocol=GetEnvironmentVariableW(L"PAWS_HOTJOIN_TEST_LEGACY",mode,40)&&!wcscmp(mode,L"1");
 if(multiMode&&!automaticMode)return 1;
 if(recoveryMode&&(!automaticMode||!multiMode))return 1;
 if(automaticMode&&!coordinatedMode)return 1;
 mode[0]=0;GetEnvironmentVariableW(L"PAWS_HOTJOIN_TEST_CAPTURE_TIMEOUT_MS",mode,40);
 if(mode[0]){unsigned value=wcstoul(mode,0,10);if(value>=5000&&value<=120000)autoDeadlineMs=value;}
 if(snapshotMode){
  wchar_t docs[MAX_PATH];unsigned count=GetEnvironmentVariableW(L"PAWS_TEST_DOCUMENTS",docs,MAX_PATH);
  if(!count||count>MAX_PATH-50)return 1;
  swprintf(clientSnapshotPath,L"%ls\\Kohan2\\data\\Save\\HotJoinSnapshot.RSG",docs);
  swprintf(ticketPath,L"%ls\\Kohan2\\data\\User\\HotJoinTicket.bin",docs);
  if(coordinatedMode){FILE *t=_wfopen(ticketPath,L"rb");if(t){if(fread(clientTicket,1,sizeof(clientTicket),t)!=sizeof(clientTicket))memset(clientTicket,0,sizeof(clientTicket));fclose(t);}}
  if(!redirect(0x152b5a,(unsigned)(sessionWriteTarget-base),serialize_view)||!redirect(0x14b77c,0x168042,assign_probe)||!redirect(0x152b86,(unsigned)(sessionReadTarget-base),read_snapshot)||!redirect(0x14cb6a,0x16203e,maintain_session)||!redirect(0x14aed1,0x162816,tasks_probe)||!redirect(0x2413fb,0x302374,keep_checkpoint_rng)||!redirect(0x2414d5,0x11c2da,keep_checkpoint_rules))return 1;
  if(coordinatedMode&&(!redirect(0x1502a0,0x151031,ticket_connect_out)||!redirect(0x150382,0x150c78,ticket_connect_in)||!redirect(0x150d87,0x6ac79,ticket_connect_flag)||!redirect(0x14b7a7,0x152400,ticket_private_out)||!redirect(0x155af8,0x16d265,ticket_join_send)||!redirect(0x154e32,0x16d265,ticket_join_decree)||!redirect(0x154478,0x16d212,ticket_join_read)||!redirect(0x154d77,0x16d212,ticket_join_read)||!redirect(0x156fb4,0x14b50b,ticket_player_join)||!redirect(0x15708c,0x14b7c5,ticket_player_leave)||!redirect(0x16a6d4,0x16a091,world_ready)))return 1;
  if(automaticMode&&!redirect(0x150fc8,0x155a95,auto_join_send))return 1;
  if(automaticMode&&!redirect(0x156d10,0x14bb3f,auto_pause_order))return 1;
  if(automaticMode&&!redirect(0x156cd4,0x162a74,auto_player_save))return 1;
  if(coordinatedMode&&!ticket_install_departure())return 1;
  if(coordinatedMode&&!redirect(0x1688cf,0x16adee,preserve_implicit_players))return 1;
  if(coordinatedMode&&!redirect(0x14b742,0x1378e2,notice_stock_join))return 1;
  if(coordinatedMode&&!redirect(0x1524c3,0x152926,serialize_order_cursor))return 1;
  if(coordinatedMode&&!redirect(0x14b56c,0x16205a,ticket_live_capacity))return 1;
  if(coordinatedMode&&!transfer_boundary_install())return 1;
  if(recoveryMode&&!recovery_install())return 1;
  if(automaticMode&&!redirect(0x1190dc,0x16882b,auto_visual_ready))return 1;
  if(coordinatedMode&&!control_install())return 1;
  if(automaticMode&&!safety_install())return 1;
  if(coordinatedMode&&(!redirect(0x15489c,0x156628,actor_context_probe)||!redirect(0x156194,0x156628,actor_context_probe)))return 1;
 }
 if(!wcscmp(mode,L"admission-only")||snapshotMode) {
  if(!install_admission_gate())return 1;
  host->log("hotjoin-lab","PRIVATE_LAB_GATE installed; coordinated mode requires matching capability and ready checkpoint");
 }
 host->log("hotjoin-lab","START pid=%lu; mainThread=%lu; base=%x",GetCurrentProcessId(),mainThread,(unsigned)base);return 0;
}
EXPORT void __cdecl K2Plugin_Tick(void) {
 DWORD now,n;HANDLE f;char data[1024],*end;unsigned id;wchar_t command[1000];
 if(startFailed)return;
 if(startPending){
  wchar_t marker[MAX_PATH];swprintf(marker,L"%ls\\Mods\\hotjoin-helper-ready.marker",host->gameDir);
  if(GetFileAttributesW(marker)==INVALID_FILE_ATTRIBUTES)return;
  startPending=0;if(K2Plugin_Start(host)){startFailed=1;host->log("hotjoin-lab","COMPOSED_INSTALL_REFUSED; no fallback to incompatible private wire");return;}
 }
 if(busy||GetCurrentThreadId()!=mainThread)return;busy=1;now=GetTickCount();
 if(automaticMode)safety_tick();
 if(automaticMode)auto_tick();
 if(coordinatedMode)notice_tick();
#ifdef PAWS_HOTJOIN_RELEASE
 busy=0;return;
#else
 if(now-lastSample>=1000){lastSample=now;sample();}
 if(now-lastPoll<100){busy=0;return;}lastPoll=now;
 f=CreateFileW(commandPath,GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,0,OPEN_EXISTING,0,0);
 if(f!=INVALID_HANDLE_VALUE){
  if(ReadFile(f,data,sizeof(data)-1,&n,0)){
   data[n]=0;id=(unsigned)strtoul(data,&end,10);
   if(id>commandId&&id<100000&&*end==' '){
    commandId=id;mbstowcs(command,end+1,999);command[999]=0;
    host->log("hotjoin-lab","COMMAND %u: %s",id,end+1);
    if(!strncmp(end+1,"!snapshot ",10))prepare_snapshot((unsigned)strtoul(end+11,0,10));
    else if(!strcmp(end+1,"!backup-vote"))InterlockedExchange(&testBackupVoteRequested,1);
    else if(!strcmp(end+1,"!transfer-fixture"))transfer_select_fixture();
    else if(!strncmp(end+1,"!password ",10)){
     unsigned order[2];wchar_t *text=0;
     ((StringFn)(base+0x205de))(&text,0,command+10);
     order[0]=(unsigned)(base+0x4a1d24);order[1]=(unsigned)text;
     ((BoolFn)(base+0x10c88d))(order,0,0);
     ((ReleaseFn)(base+0x21375))((char*)text-16,0);
     host->log("hotjoin-lab","TEST_PASSWORD_NATIVE_REQUEST_SENT; ordinary native host/version permission checks retained");
    }
    else if(!strncmp(end+1,"!port ",6)){
     unsigned port=(unsigned)strtoul(end+7,0,10);uintptr_t config=word(base+0x5f9a0c);
     if(port>=5000&&port<=65000&&word(word(base+0x5f3fe4)+0xf0)==0&&readable(config,0x64)){
      *(unsigned*)(config+0x48)=port;host->log("hotjoin-lab","TEST_NATIVE_HOST_PORT %u; normal host constructor follows",port);
     }
    }
    else host->log("hotjoin-lab","COMMAND_QUEUED %u result=%d",id,run(command));
   }
  }CloseHandle(f);
 }busy=0;
#endif
}
