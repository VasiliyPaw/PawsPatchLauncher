/* Matched lab protocol revision 2. A complete checkpoint is acknowledged in
 * the native reliable request/decree channel before either peer starts loading.
 * Ordinary status values keep their native codec and processing. This extra
 * field never changes the stock enum range or disables native checksum checks. */
typedef void (__cdecl *StatusWriteFn)(void*,int);
typedef void (__cdecl *StatusReadFn)(void*,void*);
typedef uintptr_t (FC *SenderFn)(void*,void*);
typedef struct {unsigned magic,control,count,ids[16];HJPauseState pause;} HJControlWire;
typedef struct {uintptr_t order;HJControlWire wire;} HJControl;
static HJControl loadControls[32];
static unsigned loadControlCursor,loadRequestControl;
static HJControlWire loadRequestWire;
static int loadReadySending,loadReadySent,loadBarrierReady;
static unsigned loadParticipant;
static unsigned loadReadyIds[40],loadReadyCount;
static int loadStartSent;
static unsigned loadAdmittedIds[16],loadAdmittedCount;
static void control_reset(unsigned participant) {
 loadParticipant=participant;loadReadySent=loadBarrierReady=loadStartSent=0;loadReadyCount=0;
 loadAdmittedCount=0;memset(loadAdmittedIds,0,sizeof(loadAdmittedIds));
 memset(loadReadyIds,0,sizeof(loadReadyIds));
}
static void control_admitted(unsigned id) {
 unsigned i;for(i=0;i<loadAdmittedCount;i++)if(loadAdmittedIds[i]==id)return;
 if(id&&loadAdmittedCount<16)loadAdmittedIds[loadAdmittedCount++]=id;
}
static int control_has_ready(unsigned id) {
 unsigned i;for(i=0;i<loadReadyCount;i++)if(loadReadyIds[i]==id)return 1;return 0;
}
static int control_human_sender(uintptr_t sender) {
 uintptr_t node,p,s=word(base+0x5f3fe4);unsigned n=0;
 for(node=word(s+0xc8);node&&n++<40;node=word(node+4)){
  p=word(node);if(word(p+4)==sender&&!byte(p+0xc))return 1;
 }
 return 0;
}
static int control_all_ready(void) {
 uintptr_t node,p,s=word(base+0x5f3fe4);unsigned n=0,count=0;
 for(node=word(s+0xc8);node&&n++<40;node=word(node+4)){
  p=word(node);if(byte(p+0xc))continue;count++;
  if(!control_has_ready(word(p+0x20)))return 0;
 }
 return count>0;
}
#define HJ_CONTROL_MAGIC 0x35434a48u
static void control_remember(uintptr_t order,const HJControlWire *wire) {
 unsigned i;HJControl *p;
 for(i=0;i<32;i++)if(loadControls[i].order==order){loadControls[i].wire=*wire;return;}
 p=loadControls+(loadControlCursor++%32);p->order=order;p->wire=*wire;
}
static HJControlWire *control_find(uintptr_t order) {
 unsigned i;for(i=0;i<32;i++)if(loadControls[i].order==order)return &loadControls[i].wire;return 0;
}
static void control_write(void *stream,unsigned kind,const HJControlWire *source) {
 HJControlWire blob;memset(&blob,0,sizeof(blob));blob.magic=HJ_CONTROL_MAGIC;blob.control=kind;
 if(source)blob=*source;
 else if(kind==2){blob.count=loadAdmittedCount;memcpy(blob.ids,loadAdmittedIds,sizeof(blob.ids));blob.pause=joinPause;}
 else if(kind==3||kind==4)blob.pause=joinPause;
 ticket_write_blob(stream,&blob,sizeof(blob));
}
static void control_read(void *stream,HJControlWire *blob) {
 if(!ticket_read_blob(stream,blob,sizeof(*blob))||blob->magic!=HJ_CONTROL_MAGIC||blob->control>6||blob->count>16||blob->pause.paused>1)memset(blob,0,sizeof(*blob));
}
static void __cdecl control_request_write(void *stream,int status) {
 ((StatusWriteFn)(base+0x148d89))(stream,status);control_write(stream,(unsigned)loadReadySending,loadReadySending>=5?&loadRequestWire:0);
}
static void __cdecl control_decree_write(void *stream,int status) {
 ((StatusWriteFn)(base+0x148d89))(stream,status);control_write(stream,loadRequestControl,&loadRequestWire);
}
static void __cdecl control_request_read(void *stream,void *status) {
 ((StatusReadFn)(base+0x148d9c))(stream,status);control_read(stream,&loadRequestWire);loadRequestControl=loadRequestWire.control;
 control_remember((uintptr_t)status-4,&loadRequestWire);
}
static void __cdecl control_decree_read(void *stream,void *status) {
 HJControlWire wire;((StatusReadFn)(base+0x148d9c))(stream,status);control_read(stream,&wire);
 control_remember((uintptr_t)status-4,&wire);
}
static void FC control_process(void *order,void *unused) {
 HJControlWire *wire=control_find((uintptr_t)order);
 uintptr_t a=word(base+0x5f3fec),sender;unsigned kind=wire?wire->control:0;(void)unused;
 if(!kind){((SessionFn)(base+0x156f03))(order,0);return;}
 sender=((SenderFn)(base+0x14a8de))((void*)a,0);
 if(kind>=5){safety_control(kind,sender,wire);return;}
 if(kind==4&&sender==word(a+0x2e4)&&(hostJoinPending||clientSnapshot||word(word(base+0x5f3fe4)+0xf0)==2)){
  joinPause=wire->pause;
  host->log("hotjoin-lab","MANUAL_PAUSE_POLICY_RECEIVED paused=%u ownerId=%u; shared host metadata only",joinPause.paused,joinPause.owner);return;
 }
 if(kind==3&&sender==word(a+0x2e4)&&word(word(base+0x5f3fe4)+0xf0)==2&&!hostJoinPending&&!clientSnapshot&&!byte(word(base+0x5f3fe8)+0x29)){
  joinPause=wire->pause;pause_commit();
  host->log("hotjoin-lab","CANCEL_PRIOR_PAUSE_RESTORED shared host decree; no world reload or vote/cooldown changes");return;
 }
 if(multiMode&&kind==1&&(clientSnapshot||hostJoinPending)&&control_human_sender(sender)){
  /* The local host node keeps connection +74 at zero. The authoritative
   * ordering SessionPlayer supplies the actual player id for every peer. */
  unsigned id=word(word(a+0x2a4)+0x20);if(!control_has_ready(id)&&loadReadyCount<40)loadReadyIds[loadReadyCount++]=id;
  host->log("hotjoin-lab","PEER_CHECKPOINT_READY participant=%u count=%u",id,loadReadyCount);return;
 }
 if(multiMode&&kind==2&&sender==word(a+0x2e4)&&(clientSnapshot||hostJoinPending)){
  uintptr_t s=word(base+0x5f3fe4),node,p;unsigned i,n;
  joinPause=wire->pause;
  for(i=0;i<wire->count;i++)control_admitted(wire->ids[i]);
  /* Every peer may become host. Remember that this shared generation has
   * already started, otherwise election reissues BeginTasks and discards
   * genuine ready statuses received before the previous host disappeared. */
  loadStartSent=1;
  if(loadBarrierReady){host->log("hotjoin-lab","DUPLICATE_SHARED_BARRIER_IGNORED; native ready generation retained");return;}
  /* Every new member receives the whole admission group, including a peer
   * whose Join decree preceded its private session view. Deduplication keeps
   * native role notices once per actual admission on every participant. */
  for(i=0;i<wire->count;i++)for(node=word(s+0xc8),n=0;node&&n++<40;node=word(node+4)){
   p=word(node);if(word(p+0x20)==wire->ids[i]&&!byte(p+0xc)){notice_join(p);break;}
  }
  ((BoolFn)(base+0x14c958))((void*)a,0,1);loadBarrierReady=1;
  host->log("hotjoin-lab","SHARED_CHECKPOINT_READY authoritative host barrier starts all peer loads");return;
 }
 if(multiMode){host->log("hotjoin-lab","LOAD_CONTROL_REFUSED kind=%u senderId=%u human=%d client=%d host=%d",kind,word(word(sender+0xc)+0x20),control_human_sender(sender),clientSnapshot,hostJoinPending);return;}
 if(kind==1&&loadParticipant&&word(sender+0x74)==loadParticipant&&(clientSnapshot||hostJoinPending)){
  /* Start the native task-status generation at this shared decree. A peer
   * may finish its local load before another peer starts allocating the world. */
  ((BoolFn)(base+0x14c958))((void*)a,0,1);
  loadBarrierReady=1;
  host->log("hotjoin-lab","SHARED_CHECKPOINT_READY participant=%u; verified native decree starts both loads",loadParticipant);
 }else host->log("hotjoin-lab","LOAD_CONTROL_REFUSED participant=%u sender=%u",loadParticipant,word(sender+0x74));
}
static void FC control_begin_local_tasks(void *admin,void *unused,int visual) {
 uintptr_t a=(uintptr_t)admin,node,conn,peers[40];unsigned states[40],n=0,i;(void)unused;
 if(!coordinatedMode||!loadBarrierReady||!(clientSnapshot||hostJoinPending)){
  ((BoolFn)(base+0x14c958))(admin,0,visual);return;
 }
 /* Native BeginTasks resets EVERY connection to "loading". During a local
  * hot-join restore this can erase a remote peer's already received success.
  * Keep genuine remote statuses from the shared generation; own loading state
  * and the native visual-ready requirement are still initialized normally. */
 for(node=word(a+0x2cc);node&&n<40;node=word(node+4)){
  conn=word(node);if(conn==a)continue;peers[n]=conn;states[n++]=word(conn+0x38);
 }
 ((BoolFn)(base+0x14c958))(admin,0,visual);
 for(i=0;i<n;i++)*(unsigned*)(peers[i]+0x38)=states[i];
 host->log("hotjoin-lab","LOCAL_TASK_BEGIN preserved %u remote statuses from shared checkpoint generation",n);
}
static void control_send_kind(unsigned kind) {
 uintptr_t a=word(base+0x5f3fec);unsigned old=word(a+0xa0);
 loadReadySending=(int)kind;*(unsigned*)(a+0xa0)=1;
 ((SessionFn)(base+0x14af6e))((void*)a,0);
 *(unsigned*)(a+0xa0)=old;loadReadySending=0;
}
static void control_send_ready(void) {
 if(test_hold("crc"))return;
 control_send_kind(1);loadReadySent=1;
 host->log("hotjoin-lab","CHECKPOINT_READY_REQUESTED after complete native file CRC verification");
}
static int control_install(void) {
 return redirect(0x155e26,0x148d89,control_request_write)&&
  redirect(0x155793,0x148d89,control_decree_write)&&
  redirect(0x1556d1,0x148d9c,control_request_read)&&
  redirect(0x1547a2,0x148d9c,control_decree_read)&&
  redirect(0x1557db,0x156f03,control_process)&&
  redirect(0x1547e9,0x156f03,control_process)&&
  redirect(0x16a919,0x14c958,control_begin_local_tasks);
}
