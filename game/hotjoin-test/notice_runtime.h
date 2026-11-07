/* Native type 0x20 system/chat notices, once per authoritative admission.
 * No chat command or peer-supplied role claim generates a notification. */
typedef unsigned char (__cdecl *NoticeFn)(void*,unsigned,const wchar_t*,...);
typedef uintptr_t (FC *NoticeTextFn)(void*,void*,void*,void*);
typedef uintptr_t (FC *NoticeLookupFn)(void*,void*,void*);
typedef struct {unsigned id;uintptr_t session;int ready;wchar_t nick[80],kingdom[80],label[160];} HJNotice;
static HJNotice notices[32];
static unsigned noticeSeen[64],noticeSeenCursor;
static CRITICAL_SECTION noticeLock;
static void notice_init(void){InitializeCriticalSection(&noticeLock);}
static void notice_reset(void){EnterCriticalSection(&noticeLock);memset(notices,0,sizeof(notices));memset(noticeSeen,0,sizeof(noticeSeen));noticeSeenCursor=0;LeaveCriticalSection(&noticeLock);}
static unsigned char __cdecl notice_stock_join(void *sys,unsigned category,const wchar_t *format,const wchar_t *text) {
 if(noticeJoiningLive){
  /* MessageSystem takes its TGString format BY VALUE and destroys that
   * owned reference. Suppression must consume the caller's copy as well. */
  ((ReleaseFn)(base+0x21375))((char*)format-16,0);return 1;
 }
 return ((NoticeFn)(base+0x1378e2))(sys,category,format,text);
}
static const wchar_t *notice_text(const wchar_t *key,const wchar_t *fallback) {
 wchar_t *id=0;uintptr_t ref,value,db=word(base+0x5f3fd8);
 ((StringFn)(base+0x205de))(&id,0,key);
 if(!((NoticeLookupFn)(base+0x71f7f))((void*)(db+0x4c),0,&id)){
  ((ReleaseFn)(base+0x21375))((char*)id-16,0);host->log("hotjoin-lab","ROLE_NOTICE_LOCALE_MISSING; fallback used");return fallback;
 }
 ref=((NoticeTextFn)(base+0x71800))((void*)db,0,&id,(void*)(base+0xa029c4));
 value=word(ref);((ReleaseFn)(base+0x21375))((char*)id-16,0);
 if(readable(value,2)&&word(value-12)&&wcsstr((wchar_t*)value,key)==0)return (wchar_t*)value;
 host->log("hotjoin-lab","ROLE_NOTICE_LOCALE_MISSING; fallback used");return fallback;
}
static void notice_join(uintptr_t player) {
 unsigned id=word(player+0x20),i;HJNotice *n=0;
 if(!player||byte(player+0xc)||!id)return;
 EnterCriticalSection(&noticeLock);
 for(i=0;i<64;i++)if(noticeSeen[i]==id){LeaveCriticalSection(&noticeLock);return;}
 for(i=0;i<32;i++)if(!notices[i].ready){n=notices+i;break;}
 if(n){
  memset(n,0,sizeof(*n));n->id=id;n->session=word(base+0x5f3fe4);
  ticket_copy_name(n->nick,word(player+8));ticket_copy_name(n->kingdom,word(player+0x24));
  n->ready=1;noticeSeen[noticeSeenCursor++%64]=id;
  host->log("hotjoin-lab","ROLE_NOTICE_QUEUED playerId=%u observer=%d",id,!n->kingdom[0]);
 }
 LeaveCriticalSection(&noticeLock);
}
static void notice_committed(void) {
 uintptr_t s=word(base+0x5f3fe4),node,p,k,meta,label;unsigned i,count;HJNotice *n;
 EnterCriticalSection(&noticeLock);
 for(i=0;i<32;i++){
  n=notices+i;if(n->ready!=1||n->session!=s)continue;
  for(node=word(s+0xc8),count=0,p=0;node&&count++<40;node=word(node+4)){
   uintptr_t candidate=word(node);if(word(candidate+0x20)==n->id&&!byte(candidate+0xc)){p=candidate;break;}
  }
  if(!p){n->ready=0;host->log("hotjoin-lab","ROLE_NOTICE_CANCELLED playerId=%u; participant left before admission committed",n->id);continue;}
  if(n->kingdom[0]){
   unsigned number=!wcsncmp(n->kingdom,L"kingdom",7)?wcstoul(n->kingdom+7,0,10):0;
   if(number>16)number=0;
   for(node=word(s+0xc8),count=0;node&&count++<40;node=word(node+4)){
    p=word(node);if(word(p+0x20)!=n->id||byte(p+0xc))continue;
    k=word(p+0x28);meta=word(k+0x240);label=word(meta+0x10);
    /* Native PrepareSessionPlayersForBeginPlaying uses this immutable map
     * kingdom label, separately from the live nickname assigned to +0xc. */
    if(readable(label,2)&&word(label-12)>0&&word(label-12)<159){
     const wchar_t *display=(wchar_t*)label;
     if(display[0]==L'#')display=notice_text(display+1,L"");
     if(wcslen(display)<160)wcscpy(n->label,display);
    }
    break;
   }
   if(n->label[0]&&number){
    wchar_t named[160];
    _snwprintf(named,159,notice_text(L"paws_hotjoin_kingdom_named|ds",L"Kingdom %d (%s)"),number,n->label);named[159]=0;
    wcscpy(n->label,named);
   }else if(!n->label[0]){
    if(number)swprintf(n->label,notice_text(L"paws_hotjoin_kingdom|d",L"Kingdom %d"),number);
    else wcscpy(n->label,n->kingdom);
   }
  }
  n->ready=2;
 }
 LeaveCriticalSection(&noticeLock);
}
static void notice_tick(void) {
 HJNotice copy;unsigned i;uintptr_t s=word(base+0x5f3fe4);
 if(word(base+0x5f92f4)!=4||word(s+0xf0)!=2||byte(word(base+0x5f3fe8)+0x29))return;
 for(i=0;i<32;i++){
  EnterCriticalSection(&noticeLock);
  if(notices[i].ready!=2||notices[i].session!=s){LeaveCriticalSection(&noticeLock);continue;}
  copy=notices[i];notices[i].ready=0;LeaveCriticalSection(&noticeLock);
  {
   const wchar_t *format=copy.kingdom[0]?notice_text(L"paws_hotjoin_return|ss",L"%s returned to the game as %s."):notice_text(L"paws_hotjoin_observer|s",L"%s joined as an observer.");
   wchar_t *ownedFormat=0;unsigned result;
   /* GetDisplayString returns a borrowed reference. Native MessageSystem
    * consumes a TGString value (137966 -> 21375), so give it its own copy;
    * consuming the table's borrowed string corrupts TextData at shutdown. */
   ((StringFn)(base+0x205de))(&ownedFormat,0,format);
   result=((NoticeFn)(base+0x1378e2))((void*)(base+0x5f94f0),0x20,ownedFormat,copy.nick,copy.label);
   host->log("hotjoin-lab","ROLE_NOTICE_SHOWN playerId=%u observer=%d nativeResult=%u",copy.id,!copy.kingdom[0],result);
  }
 }
}
