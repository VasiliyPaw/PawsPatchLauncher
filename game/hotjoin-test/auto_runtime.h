/* Connection-driven checkpoint experiment, still confined to marked copies.
 * The pending native join is retained only AFTER stock password/version/content
 * checks. The default scope has one remaining human peer; explicitly selected
 * multiparty revisions coordinate existing peers at the native load barrier. */
static volatile LONG autoStage,autoUiReady,autoUiCandidate;
static unsigned char autoOrder[0x40];
static uintptr_t autoSession,autoConn,autoAddress;
static DWORD autoSince,autoUiSince;
static DWORD autoAdmissionSince;
static DWORD autoDeadlineMs=120000;
static unsigned autoPauseStamp;
static HJPauseState autoPriorPause;
static unsigned autoSerial;
static int autoWasPaused,autoOrderHeld;
static int autoInternalPauseQueued;
static wchar_t autoName[96];
static unsigned recoveryIntent,recoveryVoteId,recoveryVoteSent,recoveryVerifier[8];
static HJTicket *recoveryOwner;
static wchar_t *autoDeferredSave;
static uintptr_t autoDeferredSession;

static void FC auto_pause_order(void *admin,void *unused,int enabled) {
 uintptr_t a=(uintptr_t)admin;unsigned before=byte(word(base+0x5f3fe8)+0x28);
 uintptr_t sender=word(word(a+0x2a4)+4);
 int internal=autoInternalPauseQueued&&autoStage==2&&(enabled&255)&&sender==a;
 (void)unused;
 if(internal)autoInternalPauseQueued=0;
 ((BoolFn)(base+0x14bb3f))(admin,0,enabled);
 /* Observe only a native accepted decision. Votes, observer restrictions
  * and pause cooldowns remain unchanged. Broadcast metadata, not a second
  * pause, so late peers retain the players' latest decision at commit. */
 if(!internal&&word(a+0x2e4)==a&&(autoStage||hostJoinPending)&&before!=byte(word(base+0x5f3fe8)+0x28)){
  pause_capture();autoPriorPause=joinPause;control_send_kind(4);
  host->log("hotjoin-lab","MANUAL_PAUSE_POLICY_UPDATED paused=%u ownerId=%u; native decision retained during admission",joinPause.paused,joinPause.owner);
 }
}
typedef struct {unsigned char order[0x40];uintptr_t conn,address;int held;} HJQueuedJoin;
static HJQueuedJoin autoQueue[8];
static unsigned autoQueueCount;
static uintptr_t autoInFlight[16];
static unsigned autoInFlightCount;
static int auto_batch_window(void) {
 uintptr_t a=word(base+0x5f3fec);
 return multiMode&&autoStage&&autoSession==word(base+0x5f3fe4)&&word(a+0x2e4)==a&&!byte(a+0x2f4)&&
  !loadStartSent&&!loadBarrierReady&&autoQueueCount<8&&autoInFlightCount<16;
}
static int auto_batch_waiting(void){
 unsigned i=0;
 while(i<autoInFlightCount){
  if(!readable(autoInFlight[i],0x43c)||byte(autoInFlight[i]+0x99))autoInFlight[i]=autoInFlight[--autoInFlightCount];else i++;
 }
 return autoQueueCount||autoInFlightCount;
}
static void auto_batch_assigned(uintptr_t conn) {
 unsigned i;
 for(i=0;i<autoInFlightCount;i++)if(autoInFlight[i]==conn){
  autoInFlight[i]=autoInFlight[--autoInFlightCount];return;
 }
}
static void auto_batch_flush(void) {
 unsigned i;HJQueuedJoin *q;HJConn *c;
 for(i=0;i<autoQueueCount;i++){
  q=autoQueue+i;c=ticket_conn(q->conn,0);
  if(c&&c->ticket&&c->ticket->departed&&!c->ticket->conn)c->duplicate=0;
  if(readable(word(q->address),0xa4)&&word(word(q->address)+0xa0)==q->conn&&readable(q->conn,0x43c)&&byte(q->conn+0x438)&&!byte(q->conn+0x99)&&c&&c->capable&&!c->duplicate){
   ((BoolFn)(base+0x155a95))(q->order,0,0);
   host->log("hotjoin-lab","BATCH_VERIFIED_JOIN_SENT; same fresh checkpoint, native role assignment follows");
  }else{auto_batch_assigned(q->conn);host->log("hotjoin-lab","BATCH_PENDING_JOIN_CANCELLED disconnected or occupied identity");}
  if(q->held)((SessionFn)(base+0x153443))(q->order+8,0);
  memset(q,0,sizeof(*q));
 }
 autoQueueCount=0;
}

static unsigned auto_humans(uintptr_t s) {
 uintptr_t node,p;unsigned n=0,count=0;
 for(node=word(s+0xc8);node&&n++<40;node=word(node+4)){
  p=word(node);if(!byte(p+0xc))count++;
 }
 return count;
}
static int auto_sources_ready(uintptr_t world,int hydrate) {
 typedef unsigned char (__cdecl *FromFn)(void*);
 typedef unsigned char (FC *HeaderFn)(void*,void*);
 uintptr_t res=word(world+0x28),settings,seen[32],net,ws;unsigned i,j;int loaded;
 if(!readable(res,0x8c))return 0;if(!(word(res+8)&0x10))return 1;
 for(i=0;i<32;i++){
  for(j=0;j<i;j++)if(seen[j]==res)return 0;seen[i]=res;
  if(!(word(res+8)&2)){
   /* A coordinated restore normally releases the checkpoint's parsed
    * header, retaining the indexed resource. SaveGame traverses that source
    * and requires IsHeaderLoaded(). Parse it through the native loader before
    * requesting the NEXT save; never fake the flag or skip the save assert. */
   if(!hydrate)return readable(word(res+0x38),2)&&(word(res+8)&8)!=0;
   net=word(base+0x5f3ff0);ws=word(base+0x5f3ff4);
   ((BoolFn)(base+0x16e788))((void*)net,0,0);((BoolFn)(base+0x16e788))((void*)ws,0,0);
   loaded=((HeaderFn)(base+0x1c384a))((void*)res,0);
   ((BoolFn)(base+0x16e788))((void*)ws,0,1);((BoolFn)(base+0x16e788))((void*)net,0,1);
   if(!loaded||!(word(res+8)&2))return 0;
   host->log("hotjoin-lab","CHECKPOINT_SOURCE_HEADER_RELOADED native parser succeeded");
  }
  settings=word(res+0x88);if(!readable(settings,0x54))return 0;
  if(!((FromFn)(base+0x16bf8f))((void*)settings))return 1;
  res=word(settings+0x50);if(!readable(res,0x8c))return 0;
 }
 return 0;
}
static void FC auto_player_save(void *session,void *unused) {
 uintptr_t s=(uintptr_t)session,a=word(base+0x5f3fec),w=word(base+0x5f3fb8);
 (void)unused;
 if(hostJoinPending||clientSnapshot){
  /* GameSave's preceding native filename order has already run. Restore
   * the current checkpoint name on every peer; queue the requested save
   * only on the authoritative host after the admission task has finished. */
  if(word(a+0x2e4)==a&&readable(word(s+0x68),2)){
   if(autoDeferredSave)((ReleaseFn)(base+0x21375))((char*)autoDeferredSave-16,0);
   autoDeferredSave=0;((StringFn)(base+0x205de))(&autoDeferredSave,0,(wchar_t*)word(s+0x68));
   autoDeferredSession=s;
  }
  if(snapshotName)((CreatorSettingsFn)(base+0x23fb6))((void*)(s+0x68),0,&snapshotName);
  host->log("hotjoin-lab","PLAYER_SAVE_DEFERRED_DURING_ADMISSION; current checkpoint retained, normal save queued after shared commit");return;
 }
 if(w&&word(a+0x2e4)==a&&!auto_sources_ready(w,1)){
  host->log("hotjoin-lab","PLAYER_SAVE_SOURCE_UNAVAILABLE; native header hydration failed, save not started");return;
 }
 ((SessionFn)(base+0x162a74))(session,0);
}
static int auto_admission_ok(void) {
 uintptr_t s=word(base+0x5f3fe4);HJConn *c=ticket_conn(ticketIncomingConn,0);
 int ok=transfer_settings_ok()&&c&&c->capable&&(!c->duplicate||ticket_can_replace(c))&&
  (multiMode?auto_humans(s)+autoInFlightCount<16:auto_humans(s)==1)&&
  (auto_batch_window()||(!autoStage&&!hostJoinPending&&!word(s+0x134)&&auto_sources_ready(word(base+0x5f3fb8),0)));
 if(!ok)host->log("hotjoin-lab","AUTO_ADMISSION_REFUSED busy=%ld humans=%u sourceReady=%d",autoStage,auto_humans(s),auto_sources_ready(word(base+0x5f3fb8),0));
 return ok;
}
static void auto_release_order(void) {
 if(autoOrderHeld){((SessionFn)(base+0x153443))(autoOrder+8,0);autoOrderHeld=0;}
}
static int auto_connection_live(void) {
 uintptr_t node=word(autoAddress);
 return word(base+0x5f3fe4)==autoSession&&readable(node,0xa4)&&
  word(node+0xa0)==autoConn&&readable(autoConn,0x43c)&&byte(autoConn+0x438)&&!byte(autoConn+0x99);
}
static void auto_cancel(const char *why) {
 HJConn *c=ticket_conn(autoConn,0);unsigned i;uintptr_t a=word(base+0x5f3fec);
 int restore=autoStage>1&&autoStage<4&&!autoPriorPause.paused&&!joinPause.paused&&!hostJoinPending&&word(base+0x5f3fe4)==autoSession&&word(a+0x2e4)==a&&word(a+0x2c0)==a&&word(a+0x2c8)==autoPauseStamp;
 host->log("hotjoin-lab","AUTO_CAPTURE_CANCELLED %s; no role transfer or world restore",why);
 if(auto_connection_live())((DisconnectFn)(base+0x152379))((void*)autoConn,0,1,10);
 if(c)memset(c,0,sizeof(*c));
 for(i=0;i<autoQueueCount;i++){
  HJQueuedJoin *q=autoQueue+i;
  if(readable(word(q->address),0xa4)&&word(word(q->address)+0xa0)==q->conn&&readable(q->conn,0x43c)&&!byte(q->conn+0x99))((DisconnectFn)(base+0x152379))((void*)q->conn,0,1,10);
  if(q->held)((SessionFn)(base+0x153443))(q->order+8,0);memset(q,0,sizeof(*q));
 }
 autoQueueCount=autoInFlightCount=0;
 auto_release_order();snapshotReady=0;
 recoveryIntent=0;recoveryOwner=0;
 InterlockedExchange(&autoStage,0);
 if(restore){joinPause=autoPriorPause;control_send_kind(3);host->log("hotjoin-lab","CANCEL_PRIOR_PAUSE_REQUESTED through native reliable channel; no admitted player");}
 safety_end();
}
static void FC auto_join_send(void *order,void *unused,int destination) {
 uintptr_t s=word(base+0x5f3fe4);(void)unused;
 if(word(s+0xf0)!=2){((BoolFn)(base+0x155a95))(order,0,destination);return;}
 if(!auto_admission_ok()){((DisconnectFn)(base+0x152379))((void*)ticketIncomingConn,0,1,10);return;}
 if(auto_batch_window()){
  HJQueuedJoin *q;HJConn *incoming=ticket_conn(ticketIncomingConn,0);unsigned i;
  for(i=0;i<autoInFlightCount;i++){
   HJConn *existing=ticket_conn(autoInFlight[i],0);
   if(autoInFlight[i]==ticketIncomingConn)return;
   if(incoming&&incoming->ticket&&existing&&existing->ticket==incoming->ticket){
    ((DisconnectFn)(base+0x152379))((void*)ticketIncomingConn,0,1,10);return;
   }
  }
  q=autoQueue+autoQueueCount++;memset(q,0,sizeof(*q));memcpy(q->order,order,8);
  ((CreatorSettingsFn)(base+0x1531ed))(q->order+8,0,(unsigned char*)order+8);
  q->held=1;q->conn=ticketIncomingConn;q->address=word((uintptr_t)order+8+0x14);
  autoInFlight[autoInFlightCount++]=q->conn;
  host->log("hotjoin-lab","BATCH_AUTHENTICATED_JOIN_QUEUED; stock password/version/content checks passed");return;
 }
 safety_begin();control_reset(0);autoInFlightCount=1;autoInFlight[0]=ticketIncomingConn;
 memcpy(autoOrder,order,8);
 ((CreatorSettingsFn)(base+0x1531ed))(autoOrder+8,0,(unsigned char*)order+8);
 autoOrderHeld=1;autoSession=s;autoConn=ticketIncomingConn;autoAddress=word((uintptr_t)order+8+0x14);
 pause_capture();autoWasPaused=(int)joinPause.paused;autoSince=GetTickCount();snapshotReady=0;
 autoPriorPause=joinPause;autoPauseStamp=0;
 swprintf(autoName,L"Save/PawHotJoin-%lu-%lu-%u.RSG",GetCurrentProcessId(),autoSince,++autoSerial);
 if(ticket_can_replace(ticket_conn(ticketIncomingConn,0))){
  recoveryOwner=ticket_conn(ticketIncomingConn,0)->ticket;recoveryIntent=recoveryOwner->playerId;
  memcpy(recoveryVerifier,recoveryOwner->verifier,32);recoveryVoteId=recoveryIntent;recoveryVoteSent=0;
  InterlockedExchange(&autoStage,5);
  host->log("hotjoin-lab","AUTHENTICATED_RETURN_WAITING_NATIVE_REMOVAL playerId=%u; all native admission checks passed",recoveryIntent);
 }else InterlockedExchange(&autoStage,6);
 host->log("hotjoin-lab","AUTO_CAPTURE_REQUESTED after all native admission checks; priorPaused=%d",autoWasPaused);
}
static void auto_saved(int success) {
 if(autoStage==2){
  autoPauseStamp=word(word(base+0x5f3fec)+0x2c8);
  if(!success){auto_cancel("native save failed");return;}
  InterlockedExchange(&autoStage,3);
  host->log("hotjoin-lab","AUTO_NATIVE_SAVE_COMPLETE; preparing verified current checkpoint");
 }
}
static void auto_committed(void) {
 if(autoStage==4){
  snapshotReady=0;InterlockedExchange(&autoStage,0);
  host->log("hotjoin-lab","AUTO_RETURN_COMMITTED; AUTO_PRIOR_PAUSE_RESTORED paused=%u",joinPause.paused);
  if(joinPause.paused)host->log("hotjoin-lab","AUTO_PAUSE_RETAINED; players resume manually");
 }
}
static void auto_prepare_load(void) {InterlockedExchange(&autoUiCandidate,1);}
static void FC auto_visual_ready(void *session,void *unused,int success) {
 (void)unused;((BoolFn)(base+0x16882b))(session,0,success);
 if((success&255)&&autoUiCandidate){
  InterlockedExchange(&autoUiCandidate,0);autoUiSince=GetTickCount();InterlockedExchange(&autoUiReady,1);
  host->log("hotjoin-lab","AUTO_VISUAL_LOAD_READY; native visual completion retained");
 }
}
static void auto_maintain(void *session) {
 unsigned crc;wchar_t docs[MAX_PATH];uintptr_t a=word(base+0x5f3fec);(void)session;
 /* The CSD widget registers its console commands lazily. Call its native
  * backup-vote API under the existing admin lock, independent of UI focus or
  * whether the dialog has been constructed. This uses the ordinary backup
  * request channel and retains the engine's history/quorum/timeout checks. */
 if(recoveryMode&&recoveryVoteId&&recoveryVoteId!=recoveryVoteSent){
  ((BoolFn)(base+0x14aab6))((void*)a,0,1);recoveryVoteSent=recoveryVoteId;
  host->log("hotjoin-lab","AUTHENTICATED_RETURN_NATIVE_BACKUP_VOTE playerId=%u; native recovery quorum required",recoveryVoteId);
 }
 if(testBackupVoteRequested&&word((uintptr_t)session+0xf0)==2&&byte(a+0x2f4)){
  ((BoolFn)(base+0x14aab6))((void*)a,0,1);InterlockedExchange(&testBackupVoteRequested,0);
  host->log("hotjoin-lab","TEST_PLAYER_NATIVE_BACKUP_VOTE; explicit Continue without absent players");
 }
 if(autoStage==4){
  if(!byte(a+0x2f4)&&word(a+0x2e4)==a){
   uintptr_t node,p,conn;unsigned i,n;
   if(autoQueueCount)auto_batch_flush();
   if(GetTickCount()-autoAdmissionSince>autoDeadlineMs){
    /* Only newly admitted members can expire here. Keep native file CRC,
     * task completion, disconnect order and survivor quorum authoritative. */
    for(i=0;i<loadAdmittedCount;i++)for(node=word(word(base+0x5f3fe4)+0xc8),n=0;node&&n++<40;node=word(node+4)){
     p=word(node);conn=word(p+4);
     if(word(p+0x20)==loadAdmittedIds[i]&&!byte(p+0xc)&&conn!=a&&readable(conn,0xa4)&&!byte(conn+0x99)&&
        (!control_has_ready(loadAdmittedIds[i])||(loadStartSent&&word(conn+0x38)==1))){
      unsigned order[3];order[0]=(unsigned)(base+0x4b6288);order[1]=(unsigned)p;order[2]=10;
      host->log("hotjoin-lab","ADMISSION_DEADLINE_NATIVE_DISCONNECT playerId=%u crcReady=%d task=%u; shared native PlayerLeave decree before transport teardown",loadAdmittedIds[i],control_has_ready(loadAdmittedIds[i]),word(conn+0x38));
      ((SessionFn)(base+0x155ea9))(order,0);
      /* Native execution removes p and its list node. Rescan next tick. */
      return;
     }
    }
   }
  }
  return;
 }
 if(!autoStage)return;
 if(!auto_connection_live()){auto_cancel("arriving connection or match changed");return;}
 if(GetTickCount()-autoSince>autoDeadlineMs){auto_cancel("capture deadline exceeded");return;}
 if(autoStage==5){
  if(recoveryOwner&&recoveryOwner->departed&&!recoveryOwner->conn&&!byte(word(base+0x5f3fec)+0x2f4)){
   HJConn *c=ticket_conn(autoConn,0);if(c)c->duplicate=0;
   recoveryIntent=0;recoveryOwner=0;InterlockedExchange(&autoStage,6);
   host->log("hotjoin-lab","NATIVE_DISCONNECT_RESOLVED_WITHOUT_USER_DELETE; checkpoint capture may begin");
  }
  return;
 }
 if(autoStage==6){
  if(test_hold("capture"))return;
  if(!auto_sources_ready(word(base+0x5f3fb8),1)){auto_cancel("native checkpoint source header unavailable");return;}
  InterlockedExchange(&autoStage,1);return;
 }
 if(autoStage!=3||word(autoSession+0x134))return;
 if(test_hold("saved"))return;
 GetEnvironmentVariableW(L"PAWS_TEST_DOCUMENTS",docs,MAX_PATH);
 swprintf(clientSnapshotPath,L"%ls\\Kohan2\\data\\%ls",docs,autoName);
 if(!file_crc(&crc)){auto_cancel("completed checkpoint unreadable");return;}
 if(snapshotName){((ReleaseFn)(base+0x21375))((char*)snapshotName-16,0);snapshotName=0;}
 ((StringFn)(base+0x205de))(&snapshotName,0,autoName);
 prepare_snapshot(crc);
 if(!snapshotReady){auto_cancel("completed native metadata unavailable");return;}
 InterlockedExchange(&autoStage,4);
 autoAdmissionSince=GetTickCount();
 ((BoolFn)(base+0x155a95))(autoOrder,0,0);auto_release_order();
 host->log("hotjoin-lab","AUTO_VERIFIED_JOIN_SENT; no driver checkpoint preparation");
}
static void auto_tick(void) {
 wchar_t command[MAX_PATH+40];uintptr_t s=word(base+0x5f3fe4);
 if(autoDeferredSave&&(s!=autoDeferredSession||word(s+0xf0)!=2||word(word(base+0x5f3fec)+0x2e4)!=word(base+0x5f3fec)||wcslen(autoDeferredSave)>=MAX_PATH)){
  ((ReleaseFn)(base+0x21375))((char*)autoDeferredSave-16,0);autoDeferredSave=0;
  host->log("hotjoin-lab","PLAYER_DEFERRED_SAVE_CANCELLED session, host or filename changed");
 }
 if(autoDeferredSave&&!autoStage&&!hostJoinPending&&!clientSnapshot&&word(s+0xf0)==2&&word(base+0x5f92f4)==4){
  if(wcslen(autoDeferredSave)<MAX_PATH){
   swprintf(command,L"GameSave \"%ls\"",autoDeferredSave);
   if(run(command)){
    ((ReleaseFn)(base+0x21375))((char*)autoDeferredSave-16,0);autoDeferredSave=0;
    host->log("hotjoin-lab","PLAYER_DEFERRED_SAVE_REQUESTED through ordinary native GameSave command");
   }
  }
 }
 if(departurePauseRequested&&word(s+0xf0)==2&&word(base+0x5f92f4)==4){
  if(run(L"GamePause 1")){InterlockedExchange(&departurePauseRequested,0);host->log("hotjoin-lab","LOSS_NATIVE_PAUSE_SENT; no automatic resume");}
 }
 if(autoStage==1){
  InterlockedExchange(&autoStage,2);
  swprintf(command,L"GameSave \"%ls\"",autoName);
  autoInternalPauseQueued=1;
  if(!run(L"GamePause 1")||!run(command)){
   /* Cancellation itself must execute under the admin lock. */
   autoSince=GetTickCount()-120001;
  }
 }
 if(autoUiReady&&GetTickCount()-autoUiSince>1000&&word(s+0xf0)==2&&word(base+0x5f92f4)==6){
  if(run(L"UserReady")){InterlockedExchange(&autoUiReady,0);host->log("hotjoin-lab","AUTO_USER_READY");}
 }
 if(autoUiReady&&word(s+0xf0)==2&&word(base+0x5f92f4)==4){InterlockedExchange(&autoUiReady,0);host->log("hotjoin-lab","AUTO_UI_ALREADY_READY");}
}
