/* Only pending local-human intents belong in this bounded wire queue. */
static int hj_pending_add(unsigned ids[16],unsigned *count,unsigned id) {
 unsigned i,empty=16;if(!id||*count>16)return 0;
 for(i=0;i<*count;i++){
  if(ids[i]==id)return 1;
  if(!ids[i]&&empty==16)empty=i;
 }
 if(empty<16){ids[empty]=id;return 1;}
 if(*count==16)return 0;
 ids[(*count)++]=id;return 1;
}
