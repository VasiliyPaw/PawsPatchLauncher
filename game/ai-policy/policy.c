/* Local AI experiment. All callbacks run on the native decision-making thread.
 * No OS calls, RNG, commands, ownership or health writes. Native resource
 * queries use short-lived engine vectors on this same simulation thread. */
typedef unsigned int U;
typedef unsigned short W;
int __attribute__((stdcall)) _dllstart(void*a,U b,void*c){return 1;}
#define P(a,o) (*(U*)((U)(a)+(o)))
#define F(a,o) (*(float*)((U)(a)+(o)))
#define EVENTS 2048
typedef struct { U serial, world; float time; U kind, kingdom, object, definition, result;
 float before,after,gold,income,used,capacity,x,y; char name[60]; U commit; } Event;
typedef struct { U object,world,kind,hash; float time; } Seen;
typedef struct { U world; float time; U used; } Budget;
typedef struct { U sequence,mask,counts[30]; Event events[EVENTS]; Seen seen[8192]; Budget budget[2]; U query; } Data;
typedef U (*Query)(U image,U def,U layout,float* values);
typedef struct { U resource; float need,used,cap; } Limit;
static int finite(float a) { U b=*(U*)&a; return (b&0x7f800000)!=0x7f800000; }
static U ai_for_kingdom(U image,U k) {
 U sai=P(image,0x5f3fc8),i,n,list;if(!sai||!k)return 0;
 n=P(sai,0x70);list=P(sai,0x6c);if(n>96||!list)return 0;
 for(i=0;i<n;i++){U p=P(list,4*i);if(p&&P(p,8)==k)return p;}return 0;
}
/* The paired produced resource comes from the native definition, so Shards
 * and both army/kingdom limits follow the current resource ordering. Ordinary
 * shortages never veto recruitment here. Native payment/admission still runs. */
static void limit_check(U image,Data*d,U k,U def,U layout,U production,U upkeep,int reserved,Limit*hit) {
 float need[16];U table=P(image,0x5efa8c),defs,n,i,count;
 if(!k||!def||!d->query||!table||!production||!upkeep)return;
 n=P(table,0x28);defs=P(table,0x24);if(!defs||!n||n>16)return;
 count=((Query)d->query)(image,def,layout,need);if(count!=n)return;
 for(i=0;i<n;i++){
  U rd=P(defs,4*i),pair,index;float used,cap;
  if(!rd||P(rd,0x18)!=2||need[i]<=0)continue;
  pair=P(rd,0x30);if(!pair)continue;index=P(pair,0xc);if(index>=n)continue;
  used=F(upkeep,4*i);cap=F(production,4*index);
  if(reserved)used-=need[i];
  if(finite(need[i])&&finite(used)&&finite(cap)&&used+need[i]>cap){hit->resource=i+1;hit->need=need[i];hit->used=used;hit->cap=cap;return;}
 }
 return;
}
static int live_actor(U image,U actor) {
 U reg=P(image,0x5ef72c),id;if(!reg||!actor)return 0;
 id=P(actor,0x14);return id&&P(reg,0x20004+4*(id&65535))==actor;
}
static U invalid_center(U image,U component) {
 if(!component)return 1;
 U city=P(component,4),center=P(component,0x14),body;
 if(!live_actor(image,city)||P(city,0x98)!=component)return 1;
 if(!center||!live_actor(image,center))return 2;
 if(!P(city,0xe8)||P(center,0xe8)!=P(city,0xe8))return 3;
 body=P(center,0x60);
 if(!body||P(body,4)!=center||!finite(F(body,0x10))||F(body,0x10)<=0)return 4;
 return 0;
}
static U player(U goal) { U engine=P(goal,4);return engine?P(engine,4):0; }
static int same_spot(float x,float y,U obj,U off) {float dx=x-F(obj,off),dy=y-F(obj,off+4);return finite(dx)&&finite(dy)&&dx*dx+dy*dy<=16;}
static int constructing(U image,U pl,float x,float y) {
 U engine=P(pl,0xc),node=engine?P(engine,0xc):0,i=0;
 for(;node&&i++<4096;node=P(node,4)){U g=P(node,0);if(g&&P(g,0)==image+0x4da6b0&&P(g,4)==engine&&P(g,8)==2&&P(g,0xc)&&same_spot(x,y,g,0x48))return 1;}
 return 0;
}
/* A settlement already started by an ally belongs to that ally. Do not let
 * an expansion goal silently become allied construction assistance. Repair
 * goals and player commands never pass through this filter. */
static int allied_site_busy(U image,U pl,U def,float x,float y) {
 U k=P(pl,8),parent=k?P(k,0x1f8):0,sai=P(image,0x5f3fc8),list,count,i,self=96;
 int committed;
 if(!parent||!sai||!finite(x)||!finite(y))return 0;
 count=P(sai,0x70);list=P(sai,0x6c);if(!list||count>96)return 0;
 for(i=0;i<count;i++)if(P(list,i*4)==pl)self=i;
 if(self==96)return 0;committed=constructing(image,pl,x,y);
 for(i=0;i<count;i++){
  U other=P(list,i*4),otherK,j,cities,n;if(!other||other==pl)continue;
  otherK=P(other,8);if(!otherK||P(otherK,0x1f8)!=parent)continue;
  cities=P(otherK,0x2dc);n=P(otherK,0x2e0);
  if(cities&&n<=256)for(j=0;j<n;j++){
   U city=P(cities,j*4),container,center;
   if(!city||P(city,0xe8)!=otherK||!P(city,0x94))continue;
   container=P(city,0x98);center=container?P(container,0x14):0;
   if(center&&P(center,4)==def&&same_spot(x,y,city,0x20))return 1;
  }
  /* Existing committed plans win over new plans; simultaneous committed
   * plans use native player-list order, never pointer addresses or clocks. */
  if((!committed||i<self)&&constructing(image,other,x,y))return 2;
 }
 return 0;
}
static void name(char* dst,U def) {
 U p=def?P(def,8):0;int i;
 for(i=0;i<59 && p;i++){W c=*(W*)(p+i*2);if(!c)break;dst[i]=(c<128)?(char)c:'?';}
 dst[i]=0;
}
static void emit(U image,Data*d,U mode,U obj,U pl,U def,U result,float before,float after,float x,float y,U actor,Limit* limit) {
 U n=d->sequence+1, world=P(image,0x5f3fb8),k=pl?P(pl,8):0;
 if(!k&&actor)k=P(actor,0xe8);
 float time=world?F(world,0xe8):0;
 U hash=def^result^*(U*)&before^(*(U*)&after<<1)^*(U*)&x^*(U*)&y;
 U key=obj;
 /* Native goal candidates are often ephemeral: object-address deduplication
  * cannot bound their flood. Aggregate ordinary priority observations by
  * kingdom/type/state/eligibility; snapshots retain individual active goals.
  * Recruitment preparation, requirements, and actual policy vetoes are never
  * subjected to the bulk rate budget. All native evaluations remain counted. */
 if(mode==0)hash=def^result^(P(obj,8)*2654435761u)^((F(obj,0x34)>0)?0x80000000u:0);
 if(mode==0)key=k^result;
 if(mode==4||mode==5)key=k^def;
 Seen*s=&d->seen[((key>>4)^(hash>>9)^(mode*997))&8191];
 if(mode<30)d->counts[mode]++;
 /* Retain semantic changes immediately; numeric priority changes and other
  * unchanged evaluations at most once per five game seconds. The cache is
  * diagnostic-only and never drives decisions. */
 if(mode!=6&&mode!=7&&mode!=10&&s->object==key&&s->world==world&&s->kind==mode&&s->hash==hash&&time>=s->time&&time-s->time<5){d->counts[mode<=3?21+mode:27]++;return;}
 if(mode==0||(mode==2&&before==after)){
  Budget*b=&d->budget[mode==0?0:1];
  if(b->world!=world||time<b->time||time-b->time>=1){b->world=world;b->time=time;b->used=0;}
  if(b->used>=64){d->counts[25+(mode==0?0:1)]++;return;}
  b->used++;
 }
 s->object=key;s->world=world;s->kind=mode;s->hash=hash;s->time=time;
 Event* e=&d->events[(n-1)&(EVENTS-1)];
 e->serial=0;e->world=world;e->time=time;e->kind=mode;
 e->kingdom=k;e->object=obj;e->definition=def;e->result=result;e->before=before;e->after=after;e->x=x;e->y=y;
 e->gold=e->income=e->used=e->capacity=0;
 if(mode==0){e->used=(float)P(obj,8);e->capacity=F(obj,0x34);}
 if(mode==1&&P(obj,0x4c)){e->used=(float)P(P(obj,0x4c),8);}
 if(mode==3&&P(obj,4)){e->used=(float)P(P(obj,4),0x14);}
 if(mode==4||mode==5){e->used=limit->used;e->capacity=limit->cap;}
 if(mode>=6&&actor){e->used=(float)P(actor,0x14);}
 if(mode==9&&P(obj,0x14)){e->capacity=(float)P(P(obj,0x14),0x14);}
 if(k){U pr=P(k,0x1a8),up=P(k,0x1c0),st=P(k,0x1cc);
  if(pr&&up){e->income=F(pr,0)-F(up,0);}
  if(st&&P(k,0x1d0))e->gold=F(st,0);
 }
 name(e->name,def);e->commit=n;e->serial=n;d->sequence=n;
}
__attribute__((dllexport)) void evaluate(U image,Data*d,U mode,U obj,U*args,float*result) {
 U pl=0,def=0;float before=0,after=0;
 if(mode>=4){
  U k=0,code=*(U*)result,actor=0;Limit hit={0,0,0,0};
  if(mode==4||mode==5){pl=player(obj);k=pl?P(pl,8):0;def=mode==4?args[0]:P(obj,0x44);}
  else {actor=mode==8?args[0]:P(obj,4);k=actor?P(actor,0xe8):0;pl=ai_for_kingdom(image,k);def=mode==8?args[1]:args[0];}
  if(mode==4){
   if((code&255)&&k&&(d->mask&2)){
    U layout=(P(def,0x174)&128)?P(def,0x2f0):0;
    limit_check(image,d,k,def,layout,P(k,0x1a8),P(k,0x1c0),0,&hit);
    if(hit.resource){*(U*)result=code&0xffffff00;d->counts[28]++;}
   }
   code=hit.resource?hit.resource:(code&255)?0:0xffffffffu;
  }else if(mode==5){
   /* Original function has already reserved the candidate's limited upkeep
    * on success (AL=0); a rejection (AL=1) leaves the two vectors unchanged. */
   if(k)limit_check(image,d,k,def,P(obj,0x48),P(args[0],4),P(args[1],4),(code&255)==0,&hit);
   code=hit.resource?hit.resource:(code&255)?0xfffffffeu:0;
  }else if(mode==6){code=1;}
  else if(mode==7||mode==10){code=code&255;}
  else if(mode==8){U blocked=args[4]?P(args[4],0):0;code=blocked?P(blocked,0xc)+1:0;}
  else if(mode==9){
   code=(d->mask&4)?invalid_center(image,obj):0;
   *(U*)result=code;if(code)d->counts[29]++;
  }
  emit(image,d,mode,obj,pl,def,code,hit.need,hit.cap-hit.used,actor?F(actor,0x20):0,actor?F(actor,0x24):0,actor,&hit);
  return;
 }
 if(mode==3){U actor=P(obj,4),k=actor?P(actor,0xe8):0,sai=P(image,0x5f3fc8),i;
  def=args[0];if(sai&&k&&P(sai,0x70)<=96)for(i=0;i<P(sai,0x70);i++){U q=P(P(sai,0x6c),i*4);if(q&&P(q,8)==k){pl=q;break;}}
 }
 else pl=mode==2?obj:player(obj);
 if(mode==3){}
 else if(mode==2){pl=obj;def=args[0];before=after=*result;}
 else if(mode==1){def=P(obj,0x44);before=after=F(obj,0x38);}
 else {U vt=P(obj,0)-image;if(vt==0x4d9274)def=P(obj,0x44);else if(vt==0x4da6b0)def=P(obj,0x44);else if(vt==0x4da628||vt==0x4da738)def=P(obj,0x40);before=after=F(obj,0x38);}
 if(mode==2&&(d->mask&1)&&finite(before)&&before>0&&allied_site_busy(image,pl,def,*(float*)&args[1],*(float*)&args[2])){after=0;*result=0;d->counts[20]++;}
 /* result is not an EAX return for void callees. Publish goal vtable RVA
  * there instead; preparation reports whether a city was selected. */
 emit(image,d,mode,obj,pl,def,mode>=2?*(U*)result:mode==1?(P(obj,0x4c)?1:0):P(obj,0)-image,before,after,mode==2?*(float*)&args[1]:0,mode==2?*(float*)&args[2]:0,0,0);
}
