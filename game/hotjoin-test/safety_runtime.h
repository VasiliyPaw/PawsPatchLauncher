/* Private admission transaction safeguards. Host loss cancels uncommitted
 * arrivals; election, PlayerLeave, task completion and checksums stay native.
 * Resign is retried by its original local human after the shared commit. */
#include "safety_policy.h"
static uintptr_t safetySession,safetyHost;
static unsigned safetyHostId,safetyMeta[6];
static wchar_t *safetyName;
static int safetyActive,safetyAborting,safetyAbortSent,safetyClientLeave;
static unsigned safetyResignIds[16],safetyResignCount;
static uintptr_t safetyResignOriginal;
static uintptr_t safetyResignSession;
static int safetyResignPublish;
static void safety_end(void) {
 safetyActive=safetyAborting=safetyAbortSent=0;safetyHost=safetyHostId=0;
 if(safetyName){((ReleaseFn)(base+0x21375))((char*)safetyName-16,0);safetyName=0;}
}
static void safety_begin(void) {
 uintptr_t a=word(base+0x5f3fec),s=word(base+0x5f3fe4);
 if(safetyActive&&safetySession==s)return;
 safety_end();safetySession=s;safetyHost=word(a+0x2e4);safetyHostId=pause_player_id(safetyHost);
 safetyActive=1;safetyClientLeave=0;
 safetyMeta[0]=word(s+0x60);safetyMeta[1]=word(s+0x64);safetyMeta[2]=word(s+0x6c);
 safetyMeta[3]=word(s+0x108);safetyMeta[4]=word(s+0x164);safetyMeta[5]=word(s+0x10c);
 if(readable(word(s+0x68),2))((StringFn)(base+0x205de))(&safetyName,0,(wchar_t*)word(s+0x68));
 host->log("hotjoin-lab","ADMISSION_TRANSACTION_BEGIN hostId=%u incoming=%d",safetyHostId,clientSnapshot);
}
static void safety_send(unsigned kind,const unsigned *ids,unsigned count) {
 uintptr_t a=word(base+0x5f3fec);unsigned old=word(a+0xa0);
 /* The same native request serializer can carry a host-only control with an
  * explicit body. Save/restore the transient buffer for nested local orders. */
 HJControlWire saved=loadRequestWire;unsigned savedKind=loadRequestControl;
 HJControlWire wire;memset(&wire,0,sizeof(wire));wire.magic=HJ_CONTROL_MAGIC;wire.control=kind;
 wire.count=count;if(count)memcpy(wire.ids,ids,count*4);wire.pause=joinPause;
 loadRequestWire=wire;loadRequestControl=kind;loadReadySending=(int)kind;
 *(unsigned*)(a+0xa0)=1;
 ((SessionFn)(base+0x14af6e))((void*)a,0);
 *(unsigned*)(a+0xa0)=old;loadReadySending=0;loadRequestWire=saved;loadRequestControl=savedKind;
}
static void safety_resign_remember(unsigned id) {
 unsigned i;uintptr_t p,conn;if(!id)return;
 if(safetyResignSession!=word(base+0x5f3fe4)){safetyResignSession=word(base+0x5f3fe4);safetyResignCount=0;}
 for(i=0;i<safetyResignCount;i++)if(safetyResignIds[i]){
  conn=pause_connection(safetyResignIds[i]);p=word(conn+0xc);
  if(!p||byte(p+0x1c))safetyResignIds[i]=0;
 }
 conn=pause_connection(id);p=word(conn+0xc);
 /* Staging has no GKingdom yet. Its native serialized vote and membership
  * suffice here; a zero world pointer must not discard a legitimate intent. */
 if(!p||byte(p+0x1c))return;
 if(!hj_pending_add(safetyResignIds,&safetyResignCount,id))
  host->log("hotjoin-lab","RESIGN_QUEUE_FULL; native human ceiling reached");
}
static void safety_rollback(void *session,int nativeCompletion) {
 uintptr_t s=(uintptr_t)session;
 *(unsigned*)(s+0x60)=safetyMeta[0];*(unsigned*)(s+0x64)=safetyMeta[1];*(unsigned*)(s+0x6c)=safetyMeta[2];
 *(unsigned*)(s+0x108)=safetyMeta[3];*(unsigned*)(s+0x164)=safetyMeta[4];*(unsigned*)(s+0x10c)=safetyMeta[5];
 if(safetyName)((CreatorSettingsFn)(base+0x23fb6))((void*)(s+0x68),0,&safetyName);
 joinPause.paused=1;joinPause.owner=joinPause.previous=0;joinPause.stamp=0xc61c3c00u;pause_commit();
 if(nativeCompletion)((BoolFn)(base+0x162816))(session,0,1);
 else ((BoolFn)(base+0x1612ac))((void*)word(base+0x5f3fe8),0,0);
 hostJoinPending=clientSnapshot=hostReloadPending=snapshotReady=multiSnapshotPending=0;
 InterlockedExchange(&autoStage,0);autoQueueCount=autoInFlightCount=0;
 notice_committed();control_reset(0);safety_end();
 host->log("hotjoin-lab","ADMISSION_HOST_LOSS_ROLLBACK_COMMITTED nativeCompletion=%d; original world retained paused, retry allowed",nativeCompletion);
}
static int safety_pre_tasks(void *session,int success) {
 uintptr_t a=word(base+0x5f3fec);
 /* Native PlayerLeave can finish an otherwise idle task generation before
  * Maintain runs again. Complete the rollback at that same shared callback,
  * rather than mislabelling it as a successful admission and losing metadata. */
 if(!success||!safetyActive||clientSnapshot||loadBarrierReady||!hostJoinPending||
    (uintptr_t)session!=safetySession||word(a+0x2e4)==safetyHost)return 0;
 safety_rollback(session,1);return 1;
}
static int safety_control(unsigned kind,uintptr_t sender,const void *body) {
 const HJControlWire *wire=body;uintptr_t a=word(base+0x5f3fec),s=word(base+0x5f3fe4);unsigned i;
 if(sender!=word(a+0x2e4))return 0;
 if(kind==5){
  for(i=0;i<wire->count;i++)safety_resign_remember(wire->ids[i]);
  host->log("hotjoin-lab","RESIGN_DEFERRED_SHARED count=%u; original human retries after admission",wire->count);return 1;
 }
 if(kind!=6||!safetyActive||clientSnapshot||loadBarrierReady||word(s+0xf0)!=2)return 0;
 /* No world was replaced before the shared load barrier. Restore only the
  * checkpoint-selection metadata, then unfreeze through this shared decree. */
 safety_rollback((void*)s,0);return 1;
}
static void safety_leave_incoming(void) {
 unsigned char data[0x34];uintptr_t str;
 if(safetyClientLeave)return;safetyClientLeave=1;
 /* Exact native staging exit ConnectData, queued through RequestLeave.
  * A not-yet-loaded participant has no world for the Scoring screen used by
  * RequestLeaveGame. Return to its original LAN/Internet lobby instead. */
 memset(data,0,sizeof(data));((SessionFn)(base+0x14900a))(data,0);
 ((BoolFn)(base+0x172d54))(data,0,(int)byte(word(base+0x5f3fe0)+0xac));
 ((CreatorSettingsFn)(base+0x14cf50))((void*)word(base+0x5f3fec),0,data);
 str=word((uintptr_t)data+8);if(str)((ReleaseFn)(base+0x21375))((char*)str-16,0);
 host->log("hotjoin-lab","ADMISSION_CANCELLED_HOST_CHANGED; native leave queued before new host world orders; credential retained for retry");
}
static void FC safety_packet(void *connection,void *unused,void *stream,unsigned stamp) {
 uintptr_t c=(uintptr_t)connection,a=word(base+0x5f3fec),node=word(c+0x42c);unsigned kind=0;
 (void)unused;
 if(clientSnapshot&&safetyActive&&safetySession==word(base+0x5f3fe4)){
  /* Inspect the native fixed-width packet kind without consuming input.
   * Cancel only an authenticated current-server successor's fresh packet;
   * ordinary backup traffic while the original host lives is not a loss. */
  unsigned pos=word((uintptr_t)stream+8),bits=word((uintptr_t)stream+12);
  if(ticket_has_bits(stream,4)){
   ((StatusReadFn)(base+0x15ad83))(stream,&kind);
   *(unsigned*)((uintptr_t)stream+8)=pos;*(unsigned*)((uintptr_t)stream+12)=bits;
  }
  if(safetyClientLeave)return;
  if(c!=safetyHost&&word(node+0x34)==stamp&&
     ((kind==5&&c==word(a+0x2e8))||
      (kind==7&&c==word(a+0x2e8)&&(!byte(safetyHost+0x98)||byte(a+0x2f4)))||
      (word(a+0x2e4)!=safetyHost&&(c==word(a+0x2e4)||c==word(a+0x2e8))))){
   safety_leave_incoming();return;
  }
 }
 ((NetSerialFn)(base+0x150343))(connection,0,stream,stamp);
}
static int safety_maintain(void) {
 uintptr_t a=word(base+0x5f3fec),s=word(base+0x5f3fe4),node,p;unsigned i,n;
 if(safetyResignPublish&&word(a+0x2e4)==a){safetyResignPublish=0;safety_send(5,safetyResignIds,safetyResignCount);}
 if(!safetyActive)return 0;
 if(s!=safetySession){safety_end();return 0;}
 if(!clientSnapshot&&word(s+0xf0)!=2){
  /* The local host/player can also leave through the ordinary menu during
   * an admission. Discard held work before that same process opens a match. */
  auto_release_order();
  for(i=0;i<autoQueueCount;i++){
   if(autoQueue[i].held)((SessionFn)(base+0x153443))(autoQueue[i].order+8,0);
   memset(autoQueue+i,0,sizeof(autoQueue[i]));
  }
  autoQueueCount=autoInFlightCount=0;InterlockedExchange(&autoStage,0);
  hostJoinPending=hostReloadPending=snapshotReady=multiSnapshotPending=0;
  safetyResignCount=safetyResignPublish=0;control_reset(0);safety_end();
  host->log("hotjoin-lab","LOCAL_ADMISSION_CANCELLED_SESSION_LEFT; held work cleared, private credential retained");return 0;
 }
 if(safetyClientLeave)return 1;
 if(word(a+0x2e4)==safetyHost)return 0;
 if(clientSnapshot){safety_leave_incoming();return 1;}
 if(!hostJoinPending)return 0;
 if(!safetyAborting){safetyAborting=1;joinPause.paused=1;joinPause.owner=joinPause.previous=0;joinPause.stamp=0xc61c3c00u;
  host->log("hotjoin-lab","ADMISSION_COORDINATOR_LOST; cancel uncommitted arrivals, preserve native election and existing match");}
 if(word(a+0x2e4)!=a||byte(a+0x2f4))return 0;
 for(i=0;i<loadAdmittedCount;i++)for(node=word(s+0xc8),n=0;node&&n++<40;node=word(node+4)){
  p=word(node);if(word(p+0x20)==loadAdmittedIds[i]&&!byte(p+0xc)&&word(p+4)!=a){
   unsigned order[3];order[0]=(unsigned)(base+0x4b6288);order[1]=(unsigned)p;order[2]=10;
   host->log("hotjoin-lab","HOST_LOSS_CANCEL_NATIVE_PLAYER_LEAVE playerId=%u barrier=%d",loadAdmittedIds[i],loadBarrierReady);
   ((SessionFn)(base+0x155ea9))(order,0);return 0;
  }
 }
 if(!loadBarrierReady&&!safetyAbortSent){safetyAbortSent=1;safety_send(6,0,0);}
 return 0;
}
static void FC safety_resign_request(void *order,void *unused) {
 typedef uintptr_t (__cdecl *GetFn)(void);
 typedef unsigned char (__cdecl *ValidFn)(void);
 uintptr_t a=word(base+0x5f3fec),p=word(a+0x2a4);SessionFn original=(SessionFn)safetyResignOriginal;(void)unused;
 if((hostJoinPending||clientSnapshot||autoStage)&&word(a+0x2e4)==a&&
    ((GetFn)(base+0x15da89))()&&((ValidFn)(base+0x15da94))()&&!((ValidFn)(base+0x15dab3))()&&
    p&&!byte(p+0xc)&&word(p+0x28)){
  safety_resign_remember(word(p+0x20));safetyResignPublish=1;
  host->log("hotjoin-lab","RESIGN_DEFERRED_REQUEST playerId=%u; no native vote issued during load",word(p+0x20));return;
 }
 original(order,0);
}
static void safety_tick(void) {
 uintptr_t s=word(base+0x5f3fe4),a=word(base+0x5f3fec);unsigned own=pause_player_id(a),i;
 if(safetyResignSession!=s){safetyResignCount=0;safetyResignSession=s;}
 if(safetyClientLeave){
  InterlockedExchange(&autoUiReady,0);InterlockedExchange(&autoUiCandidate,0);
  if(!word(s+0xf0)&&word(base+0x5f92f4)==10){safety_end();safetyClientLeave=0;clientSnapshot=0;hostJoinPending=0;hostReloadPending=0;control_reset(0);}
  return;
 }
 if(safetyActive||autoStage||hostJoinPending||clientSnapshot||word(s+0xf0)!=2||word(base+0x5f92f4)!=4)return;
 for(i=0;i<safetyResignCount;i++)if(safetyResignIds[i]==own){
  uintptr_t p=word(a+0xc);
  if(!p||byte(p+0x1c)||!word(p+0x28)){
   safetyResignIds[i]=0;host->log("hotjoin-lab","RESIGN_DEFERRED_ALREADY_RESOLVED playerId=%u; no duplicate native vote",own);return;
  }
  if(run(L"RequestResign")){safetyResignIds[i]=0;host->log("hotjoin-lab","RESIGN_DEFERRED_REISSUED playerId=%u through original local native request",own);}return;
 }
}
static int safety_install(void) {
 unsigned char *trampoline;unsigned char patch[5]={0xe9,0,0,0,0};DWORD old,ignored;uintptr_t site=base+0xd199b;
 if(byte(site)!=0xb8||word(site+1)!=base+0x41c87e)return 0;
 trampoline=VirtualAlloc(0,10,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);if(!trampoline)return 0;
 memcpy(trampoline,(void*)site,5);trampoline[5]=0xe9;*(int*)(trampoline+6)=site+5-(uintptr_t)trampoline-10;
 if(!VirtualProtect(trampoline,10,PAGE_EXECUTE_READ,&old))return 0;
 FlushInstructionCache(GetCurrentProcess(),trampoline,10);safetyResignOriginal=(uintptr_t)trampoline;
 *(int*)(patch+1)=(uintptr_t)safety_resign_request-site-5;
 if(!VirtualProtect((void*)site,5,PAGE_EXECUTE_READWRITE,&old))return 0;
 memcpy((void*)site,patch,5);VirtualProtect((void*)site,5,old,&ignored);FlushInstructionCache(GetCurrentProcess(),(void*)site,5);
 return redirect(0x15c7bb,0x150343,safety_packet);
}
