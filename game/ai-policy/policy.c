/* Local AI experiment. Decision callbacks run on the native AI thread;
 * route callbacks use the engine's serialized synchronous path-query scope.
 * No OS calls, RNG, ownership or health writes. Surplus civilian companies
 * use the native Disband command transport on the AI thread. Native resource
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
#include "routing_types.h"
typedef struct { U world,kingdom,camp,cities; float time,strength; } Expansion;
typedef struct { U world,kingdom,id,city; float since,last,cooldown; U destination; } DefenseUnit;
typedef struct { U world,kingdom; float last,dispatch; } DefensePlayer;
typedef struct { U world,kingdom,id; float time,x,y; } DefenseDamage;
typedef struct { U world,kingdom; float last; U camp; } ClearingPlayer;
typedef struct { U world,kingdom,camp,goal; float time,x,y; } ClearingRally;
typedef struct { U world,kingdom,target,site,recruit,layout; float time,observed; } Economy;
typedef struct { U world,kingdom; float last; } ExpansionPulse;
typedef struct { U world,kingdom,city,recipient; float last; } CityGift;

/* Mirror only native owned-field registration, never denizen registration.
 * Keys encode an immutable definition pointer plus the property-table bit. */
typedef struct { U key,count; } RecruitCountEntry;
typedef struct { U id,definition; } RecruitCountMember;
typedef struct { U player,ready; RecruitCountEntry entries[2048]; RecruitCountMember members[4096]; } RecruitCounts;
typedef struct { U world,kingdom,target,valid,count,sites[512]; float time; U counted,owned[2],queued[2],unscored; } BuilderSites;
typedef struct { U world,kingdom,id,camp,goal; float surplusSince,last,sent; } BuilderWork;
typedef struct { U kingdom,actor,job,target,site,assigned; float x,y; } BuilderClaim;
typedef struct { U sequence,mask,counts[30]; Event events[EVENTS]; Seen seen[8192]; Budget budget[2]; U query; Route route; Expansion expansion[96]; DefenseUnit defenders[4096]; DefensePlayer defensePlayers[96]; DefenseDamage damage[4096]; ClearingPlayer clearing[96]; U constructionBusy; ClearingRally rallies[96]; Economy economy[192]; U economyBusy; } Data;
typedef struct { Data base; ExpansionPulse pulses[96]; U fastPlayer; U pulseGoals[4096]; U commandCount,commandGoals[64],expansionRegions[2048]; U noticeWorld,noticeTime,noticeSeen; U recruitWorld,recruitScope; RecruitCounts recruitCounts[96]; BuilderSites builderSites[192]; BuilderWork builderWork[4096]; U builderBusy,recruitDefinition;
 U claimWorld,claimBusy,claimValid,claimCount,claimSiteCount; float claimTime;
 BuilderClaim claims[2048],oldClaims[2048]; U claimSites[512];
 CityGift cityGifts[96];
} FastData;
static void expansion_changed(Data*d,U pl,U goal){
 FastData*f=(FastData*)d;U i;if(!f->fastPlayer||f->fastPlayer!=pl)return;
 for(i=0;i<f->commandCount;i++)if(f->commandGoals[i]==goal)return;
 if(i<64)f->commandGoals[f->commandCount++]=goal;
}
__attribute__((dllexport)) U policy_data_size=sizeof(FastData);
__attribute__((dllexport)) U routing_size=sizeof(Route);
__attribute__((dllexport)) U routing_report_offset=sizeof(Route)-sizeof(RouteReport);
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
 /* The registry holds all KKC objects, not only gameplay actors. A valid
  * registered ID does not authorize reading the larger GActor layout.
  * Check its exact 1.3.7.2 primary vtable before any actor-specific field.
  * Also reject a recycled ID using the native registry generation array. */
 if(P(actor,0)!=image+0x4e5c58)return 0;
 id=P(actor,0x14);return id&&P(reg,0x20004+4*(id&65535))==actor
  &&*(W*)(reg+4+2*(id&65535))==(W)(id>>16);
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
 if(((mode>=33&&mode<=35)||mode==39||mode==51||mode==53)&&obj)e->capacity=(float)P(obj,0x4c);
 if(mode==9&&P(obj,0x14)){e->capacity=(float)P(P(obj,0x14),0x14);}
 if(k){U pr=P(k,0x1a8),up=P(k,0x1c0),st=P(k,0x1cc);
  if(pr&&up){e->income=F(pr,0)-F(up,0);}
  if(st&&P(k,0x1d0))e->gold=F(st,0);
 }
 name(e->name,def);e->commit=n;e->serial=n;d->sequence=n;
}
#include "routing.c"
#include "expansion.c"
#include "opening_capture.c"
static int clearing_reserved(U image,Data*d,U pl,U sa);
#include "defense.c"
#include "clearing.c"
static int builder_site_claimed(U image,U pl,U goal,U sa);
#include "construction.c"
#include "militia.c"
static int builder_missing(U image,Data*d,U pl,U target);
#include "economy.c"
#include "builder_fleet.c"
#include "scouting.c"
#include "city_sharing.c"
#include "supply.c"
#include "army_upgrade.c"
#include "expansion_pulse.c"
#include "notice.c"
#include "recruit_counts.c"
__attribute__((dllexport)) void evaluate(U image,Data*d,U mode,U obj,U*args,float*result) {
 if(mode==51){if(d->mask&8)builder_recruit_hero(image,d,obj,args[0],result);return;}
 if(mode==50){if((d->mask&8)&&(*(U*)result&255)){U a=P(obj,4),pl=live_actor(image,a)?ai_for_kingdom(image,P(a,0xe8)):0;if(builder_enabled(image,pl)&&route_builder(image,a))*(U*)result&=0xffffff00;}return;}
 if(mode==49){if(d->mask&8)builder_hero_score(image,d,obj,args,result);return;}
 if(mode>=40&&mode<=48){if(mode==48){U i;for(i=0;i<96;i++)((FastData*)d)->cityGifts[i].world=0;}if(mode==46||mode==47||mode==48)builder_invalidate(d,mode==48?0:obj,mode==48);recruit_counts_evaluate(image,d,mode,obj,args,result);return;}
 if(mode==39){goal_notice(image,d,result);return;}
 if(mode==34){if(d->mask&8)expansion_pulse(image,d,obj);return;}
 if(mode==35||mode==36||mode==37||mode==38){expansion_fast_dispatch(image,d,mode,obj,args,result);return;}
 if(mode==33){if(d->mask&8)scouting_reveal(image,d,obj,args,result);return;}
 /* At 5B738 args[5] is the caller's saved enemy CV, consumed by FDIVR
  * at 5B73D. Only an empty/empty region gets a neutral ratio of zero.
  * All nonzero, negative and nonfinite inputs retain native behavior. */
 if(mode==25){if((d->mask&8)&&*result==0&&*(float*)&args[5]==0)*result=1;return;}
 if(mode==29){
  U pl=player(obj);
  if(supply_capped(image,d,pl,P(obj,0x44))){*(U*)result=1;return;}
  if(builder_recruit_capped(image,d,pl,P(obj,0x44),P(obj,0x48))){*(U*)result=1;return;}
  if((d->mask&8)&&pl&&args[0]&&args[1]&&economy_slot(image,d,pl,P(obj,0x44),P(obj,0x48),P(args[0],4),P(args[1],4))) *(U*)result=1;
  return;
 }
 if(mode==30){if((d->mask&8)&&(*(U*)result&255)&&economy_spend(image,d,obj,args[0]))*(U*)result&=0xffffff00;return;}
 if(mode==31){if(d->mask&8){U g=args[0];if(g&&economy_center(P(g,0x44),P(g,0x48),0))economy_replace(image,d,g,result);else army_replace(image,d,g,result);}return;}
 if(mode==32){
  U g=obj-0xc,pl;
  if((d->mask&8)&&(*(U*)result&255)&&P(g,0)==image+0x4d9274&&args[0]==g+0x50){
   pl=player(g);
   if(economy_center(P(g,0x44),P(g,0x48),0)){
    if(!pl||!economy_swap_ready(image,d,pl,g)||!economy_swap_safe(image,d,pl,P(g,0x50),g,1))*(U*)result&=0xffffff00;
   }else {U valid=pl?army_validate(image,d,pl,g):0;U sa=P(g,0x50),a=sa?actor_id(image,P(sa,8)):0;
    if(!valid)*(U*)result&=0xffffff00;
    emit(image,d,60,g,pl,P(g,0x44),valid,0,0,0,0,a,0);
   }
  }
  return;
 }
 if(mode==24){if((d->mask&8)&&!opening_large_candidate(image,d,obj,args[0],result))expansion_candidate(image,d,obj,args[0],result);return;}
 if(mode==23){if(d->mask&8){construction_recruit(image,d,obj,args);clearing_recruit(image,d,obj,args);builder_wait(image,d,obj,args);clearing_rally_recruit(image,d,obj,args);scouting_evaluate(image,d,obj,args);}return;}
 if(mode==18&&(d->mask&8)){army_admission(image,d,obj,args[0],result);builder_admission(image,d,obj,args[0],result);opening_capture_admission(image,d,obj,args[0],result);construction_admission(image,d,obj,args[0],result);clearing_staffed_admission(image,d,obj,args[0],result);}
 if(mode==22){if(d->mask&8){construction_recruit(image,d,obj,args);clearing_evaluate(image,d,obj,args);builder_wait(image,d,obj,args);clearing_rally_recruit(image,d,obj,args);}return;}
 if(mode==17||mode==18||mode==20||mode==21){if(d->mask&8)defense_evaluate(image,d,mode,obj,args,result);return;}
 if(mode>=11){if(d->mask&8)route_evaluate(image,d,mode,obj,args,result);return;}
 U pl=0,def=0;float before=0,after=0;
 if(mode>=4){
  U k=0,code=*(U*)result,actor=0;Limit hit={0,0,0,0};
  if(mode==4||mode==5){pl=player(obj);k=pl?P(pl,8):0;def=mode==4?args[0]:P(obj,0x44);}
  else {actor=mode==8?args[0]:P(obj,4);k=actor?P(actor,0xe8):0;pl=ai_for_kingdom(image,k);def=mode==8?args[1]:args[0];}
  if(mode==4){
   U target=0,layout=(P(def,0x174)&128)?P(def,0x2f0):0;
   if((code&255)&&k&&(d->mask&8))target=economy_need(image,d,pl,def,layout);
   if((code&255)&&k&&(d->mask&2)){
    limit_check(image,d,k,def,layout,P(k,0x1a8),P(k,0x1c0),0,&hit);
    /* A feasible single-company upgrade must reach the final planner.
     * It still has to pass actual-layout, money and pre-disband checks. */
    if(hit.resource&&!(target&&hit.resource==economy_unit_resource(image))&&!army_early(image,d,pl,def,layout)){*(U*)result=code&0xffffff00;d->counts[28]++;}
   }
   if((*(U*)result&255)&&k&&(d->mask&8)&&economy_slot(image,d,pl,def,layout,P(k,0x1a8),P(k,0x1c0))){*(U*)result=code&0xffffff00;}
   if((*(U*)result&255)&&supply_capped(image,d,pl,def)){*(U*)result=code&0xffffff00;emit(image,d,54,obj,pl,def,1,2,2,0,0,0,0);}
   if((*(U*)result&255)&&builder_recruit_capped(image,d,pl,def,layout)){*(U*)result=code&0xffffff00;}
   code=(*(U*)result&255)?0:hit.resource?hit.resource:(code&255)?0xfffffffdu:0xffffffffu;
  }else if(mode==5){
   /* Original function has already reserved the candidate's limited upkeep
    * on success (AL=0); a rejection (AL=1) leaves the two vectors unchanged. */
   if(k)limit_check(image,d,k,def,P(obj,0x48),P(args[0],4),P(args[1],4),(code&255)==0,&hit);
   code=hit.resource?hit.resource:(code&255)?0xfffffffeu:0;
  }else if(mode==6){builder_invalidate(d,pl,0);code=1;}
  else if(mode==7||mode==10){
   if(mode==10)builder_invalidate(d,pl,0);
   /* Common recruitment execution must preserve native admission on every
    * peer. Host-only demand/cap policy runs before AI budget reservation
    * (modes 4/29), never after an order reaches the simulation. */
   code=*(U*)result&255;
  }
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
 if(mode==0&&(d->mask&8)){
  U reason=5,blocked=finite(before)&&before>0?opening_large_target(image,obj,pl):0;
  if(!blocked){reason=4;blocked=finite(before)&&before>0?opening_capture_target(image,obj,pl):0;}
  if(blocked){
   after=0;F(obj,0x38)=0;d->counts[19]++;
   emit(image,d,31,obj,pl,P(blocked,4),reason,before,0,F(blocked,0x20),F(blocked,0x24),blocked,0);
  }else {after=expansion_priority(image,d,obj,pl,before);after=militia_priority(image,d,obj,pl,after);}
 }
 /* Allies compete for settlement markers again. Native occupancy and the
  * bot's own builder/site assignments remain authoritative. */
 /* result is not an EAX return for void callees. Publish goal vtable RVA
  * there instead; preparation reports whether a city was selected. */
 emit(image,d,mode,obj,pl,def,mode>=2?*(U*)result:mode==1?(P(obj,0x4c)?1:0):P(obj,0)-image,before,after,mode==2?*(float*)&args[1]:0,mode==2?*(float*)&args[2]:0,0,0);
}
