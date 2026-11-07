/* Opt-in revision 3 experiment: existing peers receive the same host checkpoint
 * through the unchanged native map transfer. All current human peers, including
 * observers, acknowledge its CRC before the host broadcasts the load barrier.
 * This path is separate from the accepted two-peer revision 2 until tested. */
typedef unsigned char (FC *SelectFileFn)(void*,void*,void*,unsigned,int);
typedef unsigned char (FC *LoadHeaderFn)(void*,void*);
static int multiSnapshotPending;
static DWORD multiFilePoll;
static int multi_name_valid(const wchar_t *name) {
 unsigned n;if(!name)return 0;n=(unsigned)wcslen(name);
 return n>20&&n<96&&!wcsncmp(name,L"Save/PawHotJoin-",16)&&!wcsstr(name,L"..")&&
  wcsspn(name,L"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789/-.")==n;
}
static void multi_receive_checkpoint(const wchar_t *name,unsigned crc) {
 uintptr_t s=word(base+0x5f3fe4),a=word(base+0x5f3fec);wchar_t docs[MAX_PATH];
 if(word(s+0xf0)!=2||word(a+0x2e4)==a||!word(base+0x5f3fb8)||!multi_name_valid(name))return;
 if(snapshotName){((ReleaseFn)(base+0x21375))((char*)snapshotName-16,0);snapshotName=0;}
 ((StringFn)(base+0x205de))(&snapshotName,0,name);
 GetEnvironmentVariableW(L"PAWS_TEST_DOCUMENTS",docs,MAX_PATH);
 swprintf(clientSnapshotPath,L"%ls\\Kohan2\\data\\%ls",docs,name);
 snapshotReady=0;snapshotCrc=crc;multiSnapshotPending=1;multiFilePoll=0;
 ((CreatorSettingsFn)(base+0x23fb6))((void*)(s+0x68),0,&snapshotName);
 *(unsigned*)(s+0x64)=2;*(unsigned*)(s+0x6c)=3;*(unsigned*)(s+0x108)=crc;
 ((SelectFileFn)(base+0x168bff))((void*)s,0,&snapshotName,crc,0);
 host->log("hotjoin-lab","EXISTING_PEER_CHECKPOINT_REQUESTED through native map transfer; live world retained at barrier");
}
static void multi_maintain(void *session) {
 uintptr_t a=word(base+0x5f3fec),res,net,worldSync;unsigned crc;DWORD now=GetTickCount();
 if(!hostJoinPending)return;
 if(multiSnapshotPending&&!snapshotReady&&now-multiFilePoll>=1000){
  multiFilePoll=now;
  if(file_crc(&crc)&&crc==snapshotCrc){
   res=((ResourceFn)(base+0x1c2f25))(&snapshotName);
   if(!readable(res,0x94))return;
   /* Selecting/verifying a file does not parse its map header. Reuse the
    * native header loader, with balanced local read scopes: no world has
    * changed and this private resource read is not a shared simulation order. */
   net=word(base+0x5f3ff0);worldSync=word(base+0x5f3ff4);
   ((BoolFn)(base+0x16e788))((void*)net,0,0);
   ((BoolFn)(base+0x16e788))((void*)worldSync,0,0);
   ((LoadHeaderFn)(base+0x1c384a))((void*)res,0);
   ((BoolFn)(base+0x16e788))((void*)worldSync,0,1);
   ((BoolFn)(base+0x16e788))((void*)net,0,1);
   prepare_snapshot(crc);
   if(snapshotReady){multiSnapshotPending=0;host->log("hotjoin-lab","EXISTING_PEER_CHECKPOINT_VERIFIED crc=%x",crc);}
  }
 }
 if(snapshotReady&&!loadReadySent)control_send_ready();
 if(snapshotReady&&word(a+0x2e4)==a&&!loadStartSent&&!auto_batch_waiting()&&control_all_ready()){
  loadStartSent=1;control_send_kind(2);
  host->log("hotjoin-lab","ALL_PEERS_CHECKPOINT_READY host issued authoritative load barrier");
 }
}
