/* Opt-in revision 6/7 experiment. An authenticated returning owner may ask
 * remaining peers to resolve its native dead connection without a UI click.
 * Actual removal still requires the game's ordinary majority vote. No vote
 * is sent for a live owner, an unknown credential or a display-name match. */
#define HJ_RECOVERY_MAGIC 0x31524850u
static int recovery_preconnect(uintptr_t conn,const unsigned *secret) {
 uintptr_t a=word(base+0x5f3fec),old,p;unsigned digest[8];HJTicket *t;
 /* A backup server cannot enter the stock new-connection parser until native
  * election has settled. A timed-out owner's proof can request native recovery;
  * its normal quorum may remove every already-unresponsive peer. It grants no
  * admission or kingdom, and never votes against a healthy connection.
  * The retried connection must still pass the entire stock parser afterward. */
 if(word(word(base+0x5f3fe4)+0xf0)!=2||word(a+0x2e8)!=a||!byte(a+0x2f4)||!hj_token_present(secret)||!ticket_digest(secret,digest))return 0;
 t=hj_find_verifier(tickets,digest);
 if(!t||t->departed||!t->playerId)return 0;
 old=t->conn;p=word(old+0xc);
 if(!old||old==a||old==conn||!p||word(p+0x20)!=t->playerId||byte(old+0x98))return 0;
 if(recoveryIntent!=t->playerId){
  recoveryIntent=t->playerId;memcpy(recoveryVerifier,t->verifier,32);
  recoveryVoteId=t->playerId;recoveryVoteSent=0;
  host->log("hotjoin-lab","DEAD_OWNER_PROOF playerId=%u; native cleanup only; full admission deferred until original identity is released",t->playerId);
 }
 /* Do not enter Connect(I) until native cleanup releases the old Steam/client
  * identity. Retried packets then pass ALL ordinary auth/content/password
  * checks. No duplicate-identity rejection is bypassed or forged. */
 return 1;
}
static void recovery_write(void *stream) {
 unsigned blob[10];memset(blob,0,sizeof(blob));blob[0]=HJ_RECOVERY_MAGIC;blob[1]=recoveryIntent;
 if(recoveryIntent)memcpy(blob+2,recoveryVerifier,32);
 ticket_write_blob(stream,blob,sizeof(blob));
}
static void recovery_read(uintptr_t conn,void *stream,unsigned stamp) {
 unsigned blob[10];uintptr_t a=word(base+0x5f3fec),node=word(conn+0x42c),p;HJTicket *t;
 if(!ticket_read_blob(stream,blob,sizeof(blob))||blob[0]!=HJ_RECOVERY_MAGIC||!blob[1])return;
 if((conn!=word(a+0x2e4)&&conn!=word(a+0x2e8))||word(node+0x34)!=stamp)return;
 t=hj_find_verifier(tickets,blob+2);
 if(!t||t->departed||t->playerId!=blob[1]||!t->conn||t->conn==a)return;
 p=word(t->conn+0xc);
 if(!p||word(p+0x20)!=blob[1]||byte(t->conn+0x98)||!byte(a+0x2f4))return;
 if(recoveryVoteId!=blob[1]){
  recoveryVoteId=blob[1];recoveryVoteSent=0;
  host->log("hotjoin-lab","AUTHORITATIVE_RETURN_INTENT playerId=%u; local native connection also timed out",blob[1]);
 }
}
static void FC recovery_server_out(void *conn,void *unused,void *stream,unsigned stamp) {
 (void)unused;((NetSerialFn)(base+0x15189f))(conn,0,stream,stamp);recovery_write(stream);
}
static void FC recovery_backup_out(void *conn,void *unused,void *stream,unsigned stamp) {
 (void)unused;((NetSerialFn)(base+0x152021))(conn,0,stream,stamp);recovery_write(stream);
}
static void FC recovery_server_in(void *conn,void *unused,void *stream,unsigned stamp) {
 (void)unused;((NetSerialFn)(base+0x151689))(conn,0,stream,stamp);recovery_read((uintptr_t)conn,stream,stamp);
}
static void FC recovery_backup_in(void *conn,void *unused,void *stream,unsigned stamp) {
 (void)unused;((NetSerialFn)(base+0x151ecd))(conn,0,stream,stamp);recovery_read((uintptr_t)conn,stream,stamp);
}
static int recovery_install(void) {
 return redirect(0x1502c7,0x15189f,recovery_server_out)&&
  redirect(0x1502e1,0x152021,recovery_backup_out)&&
  redirect(0x1503a9,0x151689,recovery_server_in)&&
  redirect(0x1503c3,0x151ecd,recovery_backup_in);
}
