/* Local SP prototype: explicit drag plan, engineer-only construction. Native
 * mouse events, movement commands, terrain properties and serialization. */
#include <stddef.h>
#include "road_text.h"
typedef unsigned int U;
typedef unsigned short W;
#define P(a,o) (*(U*)((U)(a)+(o)))
#define F(a,o) (*(float*)((U)(a)+(o)))
#define B(a,o) (*(unsigned char*)((U)(a)+(o)))
#define FAST __attribute__((fastcall))
#define EXPORT __attribute__((dllexport))
typedef U (FAST *M0)(U,U);
typedef U (FAST *M1)(U,U,U);
typedef U (FAST *M2)(U,U,U,U);
typedef U (*C2)(U,U);
typedef U (*C5)(U,U,U,U,U);
typedef U (*NativeCall)(U,U,U,U*);
#define JOBS 8
#define POINTS 512
#define QUEUE 32
typedef struct {U id,kingdom,lastCell,moved;float x,y,lastWork,lastMove; U count,index,issued,points[POINTS];} Job;
#ifdef PAWS_BRIDGES
typedef struct {U id;float x0,x1,y0,y1,level;U opened,originalCount,originalPoints[256],originalVariants[256];float ux,uy,half;} BridgeSpan;
#include "../engineer-bridges/ai_types.h"
#endif
typedef struct {
 U image,call,language,world,tick,completed,painted,rejected;
 U read,write,requests[QUEUE],button,label,uiStatus,uiId,vt[54];
 float lastTime;
 Job jobs[JOBS];
 U armed,dragging,pending,count,valid,cancel,drawTick,startX,startY,points[POINTS];
#ifdef PAWS_BRIDGES
 U bridgeButton,bridgeLabel,bridgeStatus,bridgeTip,tool,pendingTool,jobTools[JOBS],fixture;
 float workStarted[JOBS];
 U bridgeWorld,bridgeCount,bridgeBuilt,bridgeFailed;
 BridgeSpan spans[128];
 U moveRequest;float moveX,moveY;
 U bridgeError;
 U ownerRequest,ownerCount,ownerPoints[32];
 U previewCount,previewValid,previewPoints[32],construction[JOBS];
 U nativeStarted,nativeFinished,gameInterface;
 U previewFixture;float previewFixtureX,previewFixtureY;
 U previewMaterial,pendingMaterial,jobMaterials[JOBS];
 W metadataScratch[32768];
 U attackRequest,attackTarget;
 float siteHealth[JOBS];
 U siteCommitted[JOBS];
 U decalSelf,decalOwner,decalCalls,decalMatches;
 U islandCount,islandKeys[256],islandValues[256];
 U routeMemory,routeCells,routeStamp,routeBusy,routeCalls,routeExpanded,routeQueued,routeFallback,routeRestoreCursor;
 float bridgeDeathTime[128];
 BridgeAI ai;
#ifdef PAWS_BRIDGE_MULTIPLAYER
 U netWorld,netJobs[JOBS],netSent,netReceived,netRejected,netCancelled,netRestored;
#endif
#endif
} Roads;
static Roads* current;
EXPORT void roads_bind(Roads*d){current=d;}
#ifdef PAWS_BRIDGES
EXPORT const U bridge_route_layout[]={offsetof(Roads,routeMemory),9};
#endif
static U m0(Roads*d,U r,U s){return ((M0)(d->image+r))(s,0);}
static U m1(Roads*d,U r,U s,U a){return ((M1)(d->image+r))(s,0,a);}
static U str(Roads*d,const W*s){U v=0;m1(d,0x205de,(U)&v,(U)s);return v;}
static void release(Roads*d,U s){if(s)m0(d,0x21375,s-16);}
static U invoke(Roads*d,U r,U self,U n,U a,U b){U v[2];v[0]=a;v[1]=b;return ((NativeCall)d->call)(d->image+r,self,n,v);}
static int finite(float f){union{float f;U u;}v;v.f=f;return (v.u&0x7f800000)!=0x7f800000;}
static int integer(float f){int i;__asm__ volatile(".byte 0xf3,0x0f,0x2c,0x00":"=a"(i):"a"(&f));return i;}
static int eq(const W*w,const char*a){int i;U x,y;if(!w)return 0;for(i=0;i<80;i++){x=w[i];y=(unsigned char)a[i];if(x>='A'&&x<='Z')x+=32;if(y>='A'&&y<='Z')y+=32;if(x!=y)return 0;if(!x)return 1;}return 0;}
static U actor(Roads*d,U id){U reg=P(d->image,0x5ef72c),a;if(!reg||!id)return 0;a=P(reg,0x20004+4*(id&65535));return a&&P(a,0x14)==id&&P(a,0)==d->image+0x4e5c58&&!(P(a,8)&1)?a:0;}
static U local(Roads*d){U m=P(d->image,0x5f3fc0);return m?m0(d,0x2be624,m):0;}
static U game_interface(Roads*d){U ui=P(d->image,0x5f3fc0),game=ui?P(ui,0x60):0,i;for(i=0;game&&i<16;i++){U parent;if(P(game,0)==d->image+0x48e090)return game;parent=P(game,8);if(parent==game)break;game=parent;}return 0;}
static int bridge_networked(Roads*d){
#ifdef PAWS_BRIDGE_MULTIPLAYER
 U s=P(d->image,0x5f3fe4);return s&&B(s,0x100);
#else
 (void)d;return 0;
#endif
}
static int bridge_authority(Roads*d){U a=P(d->image,0x5f3fec);return !bridge_networked(d)||(a&&P(a,0x2e4)==a);}
#ifdef PAWS_BRIDGES
static int bridge_net_send(Roads*d,U a,U*pts,U n,U wood);
static int bridge_net_normal(Roads*d,U a,U kind,float x,float y,U target);
#endif
static int allowed(Roads*d){U s=P(d->image,0x5f3fe4),w=P(d->image,0x5f3fb8);return s&&w&&P(d->image,0x5f9218)==2&&(!B(s,0x100)||bridge_networked(d))&&P(s,0xf0)==2&&P(w,0xd8)!=6;}
static int engineer(U a){const W*id=P(a,4)?(W*)P(P(a,4),8):0,*tail=id;U i;if(!id)return 0;for(i=0;i<80&&id[i];i++)if(id[i]=='_')tail=id+i+1;return eq(tail,"engineer")||eq(tail,"caretaker")||eq(tail,"forge")||eq(tail,"crafter")||eq(tail,"nightbringer")||eq(tail,"boneweaver");}
static int alive_worker(Roads*d,U a){U b=P(a,0xa8),body=P(a,0x60);return engineer(a)&&b&&P(b,0)==d->image+0x4df830&&P(b,4)==a&&body&&P(body,4)==a&&finite(F(body,0x10))&&F(body,0x10)>0;}
static U worker(Roads*d,U a){U o=P(a,0x7c),i,n,list;if(!o||P(o,4)!=a)return 0;n=P(o,0x2c);list=P(o,0x28);if(!n||n>64||!list)return 0;
 for(i=0;i<n;i++){U u=P(list,i*4),e;if(!u||actor(d,P(u,0x14))!=u||P(u,0xe8)!=P(a,0xe8)||!alive_worker(d,u))continue;e=P(u,0x80);if(e&&P(e,4)==u&&P(e,0x10)==a)return u;}return 0;}
static U selected(Roads*d){U ui=P(d->image,0x5f3fbc),s,a,k;if(!ui||!allowed(d))return 0;s=P(ui,0x13c);s=s?P(s,8):0;s=s?P(s,0):0;a=s?P(s,0x14):0;
 if(!a||actor(d,P(a,0x14))!=a)return 0;k=local(d);return k&&P(a,0xe8)==k&&worker(d,a)?a:0;}
static Job* job(Roads*d,U id){U i;for(i=0;i<JOBS;i++)if(d->jobs[i].id==id)return &d->jobs[i];return 0;}
static int fighting(Roads*d,U a){U ai=P(a,0x70),s=ai?P(ai,0x14):0,v;s=s?P(s,0):0;v=s?P(s,0)-d->image:0;return v==0x4f4dc4||v==0x4f4e20||v==0x4f4e4c||v==0x4f4e78||v==0x4f4ea4||v==0x4f4fb4||(P(a,0x100)&0x6000);}
static int moving(Roads*d,U a){U ai=P(a,0x70),s=ai?P(ai,0x14):0;s=s?P(s,0):0;return s&&P(s,0)==d->image+0x4f4df0;}
static U road_variant(Roads*d,U cell){U mgr=P(d->image,0x5f0030),n,i;if(!mgr)return 0;
 n=P(mgr,0x28);if(n>4096)return 0;for(i=0;i<n;i++){U p=P(P(mgr,0x24),i*4);if(p&&eq((W*)P(p,8),"paws_engineer_road01"))return p;}return 0;}
static U tile(Roads*d,int x,int y){U map=d->world?P(d->world,0x30):0,w,h;if(!map||P(map,4)!=1)return 0;w=P(map,0x1c);h=P(map,0x20);
 if(!w||!h||w>1024||h>1024||x<2||y<2||x+2>=(int)w||y+2>=(int)h||!P(map,0x28))return 0;return P(map,0x28)+(y*w+x)*0x30;}
static int passable(Roads*d,int x,int y){int xx,yy;U c;for(yy=y-2;yy<=y+2;yy++)for(xx=x-2;xx<=x+2;xx++){c=tile(d,xx,yy);if(!c||(P(c,0x20)&0x100))return 0;}return 1;}
#ifdef PAWS_BRIDGES
static int command_target(Roads*d,U a,U target);
static int command_target_kind(Roads*d,U a,U target,U kind);
static int command(Roads*d,U a,const char*name,float x,float y);
#include "../engineer-bridges/bridge.h"
#include "../engineer-bridges/navigation.h"
#include "../engineer-bridges/routing.h"
#include "../engineer-bridges/placement.h"
#include "../engineer-bridges/combat.h"
#include "../engineer-bridges/decommission.h"
/* A native site is provisional until a worker actually adds construction
 * health. Replacing an approach must not leave an invisible reservation. */
static void bridge_abandon(Roads*d,U i){U a=actor(d,d->construction[i]);
 if(a&&!d->siteCommitted[i]&&(P(a,0x100)&0x200000)){
  U company=actor(d,d->jobs[i].id),body=P(a,0x60);
  if(!body||F(body,0x10)<=d->siteHealth[i]||bridge_occupied(d,d->jobs[i].points,d->jobs[i].count,d->jobs[i].id)||!bridge_funds(d,P(a,4),company,a))invoke(d,0x24338e,d->world,1,a,0);
 }
 d->construction[i]=0;d->jobs[i].id=0;
}
#endif
static int build(Roads*d,U point){U cell,variant,ctx[8],xy[2],i,count=0;int x=point&65535,y=point>>16,xx,yy;
 if(!passable(d,x,y))return -1;cell=tile(d,x,y);variant=road_variant(d,cell);if(!variant)return -1;
 for(yy=y-1;yy<=y+1;yy++)for(xx=x-1;xx<=x+1;xx++)if(P(tile(d,xx,yy),0)!=variant)count++;
 if(!count)return 0;
 for(i=0;i<8;i++)ctx[i]=0;invoke(d,0x2517a3,(U)ctx,0,0,0);
 for(yy=y-1;yy<=y+1;yy++)for(xx=x-1;xx<=x+1;xx++){xy[0]=xx;xy[1]=yy;invoke(d,0x2517f9,(U)ctx,2,(U)xy,variant);}
 invoke(d,0x25185b,(U)ctx,1,0,0);invoke(d,0x20d4b,(U)(ctx+3),0,0,0);invoke(d,0x20d4b,(U)(ctx+5),0,0,0);
 d->painted+=count;return 1;
}
/* Bound the line to the map grid. Recompute from endpoints, rather than sampling
 * mouse motion: slow and fast drags produce the same continuous route. */
static void plan(Roads*d,int x,int y){int ax=d->startX,ay=d->startY,dx=x-ax,dy=y-ay,sx=dx<0?-1:1,sy=dy<0?-1:1,err,e;
#ifdef PAWS_BRIDGES
 if(d->tool){bridge_plan(d,x,y);return;}
#endif
 d->count=0;d->valid=1;if(dx<0)dx=-dx;if(dy<0)dy=-dy;err=dx-dy;
 for(;;){if(d->count==POINTS||!passable(d,ax,ay)){d->valid=0;return;}d->points[d->count++]=(U)ax|((U)ay<<16);
 if(ax==x&&ay==y)break;e=2*err;if(e>-dy){err-=dy;ax+=sx;}if(e<dx){err+=dx;ay+=sy;}}
}
static int cursor(Roads*d,int*x,int*y){U ui=P(d->image,0x5f3fbc),mgr=P(d->image,0x5f3fc0);float a,b;
 if(!ui||!mgr||P(mgr,0x60)!=ui)return 0;a=F(ui,0x184);b=F(ui,0x188);if(!finite(a)||!finite(b)||a<0||b<0||a>1024||b>1024)return 0;
 *x=integer(a)>>1;*y=integer(b)>>1;return tile(d,*x,*y)!=0;}
static int command(Roads*d,U a,const char*name,float x,float y){U defs=P(d->image,0x5f3fb4),id,def=0,c,held,v[3],ok,queued=name[0]=='q';if(queued)name++;
 if(!defs||!P(defs,0x298))return 0;for(id=0;id<39;id++){def=P(P(defs,0x298),id*4);if(def&&eq((W*)P(def,8),name))break;}if(id==39)return 0;
 if(!(((M1)P(P(a,0),0x34))(a,0,id)&255))return 0;
 c=((U(*)(U))(d->image+0x2ef03c))(0x40);if(!c)return 0;held=m1(d,0x22f4e9,c,id);if(!held)return 0;P(held,4)++;
 if(queued)B(held,0x3c)=1;
 if(name[0]=='m'){P(held,0xc)|=4;F(held,0x18)=x;F(held,0x1c)=y;}
 /* Already on the simulation thread in local SP. Use the same validation
  * and ActorCommand execution as UIGameActionActorCommand, not SAIPlayer
  * queue offsets (HumanPlayer has a different layout). */
 v[0]=0;v[1]=(U)&held;v[2]=0;
 ok=((NativeCall)d->call)(P(P(a,0),0x150),a,3,v)&255;
 if(ok)ok=m1(d,0x22f651,held,a)&255;
 m0(d,0x42fca,(U)&held);return ok;
}
#ifdef PAWS_BRIDGES
static int command_target_kind(Roads*d,U a,U target,U kind){U c,held,v[3],ok;
 d->bridgeError=91;if(!(((M1)P(P(a,0),0x34))(a,0,kind)&255))return 0;
 c=((U(*)(U))(d->image+0x2ef03c))(0x40);if(!c)return 0;
 held=m1(d,0x22f4e9,c,kind);if(!held)return 0;P(held,4)++;
 P(held,0xc)|=1;P(held,0x10)=target;
 v[0]=0;v[1]=(U)&held;v[2]=0;
 ok=((NativeCall)d->call)(P(P(a,0),0x150),a,3,v)&255;
 d->bridgeError=93;
 /* Mind::TellCommand returns false for a valid queued transition as well as
  * for an immediate failure. Keep the real construction site alive while
  * native AI leaves the approach state and processes its command queue. */
 if(ok){m1(d,0x22f651,held,a);d->bridgeError=0;}
 m0(d,0x42fca,(U)&held);if(ok)d->bridgeError=0;return ok;
}
static int command_target(Roads*d,U a,U target){return command_target_kind(d,a,target,3);}
#include "../engineer-bridges/ai.h"
#include "../engineer-bridges/network.h"
#endif
static void clear(Roads*d){U i;for(i=0;i<JOBS;i++)d->jobs[i].id=0;d->armed=d->dragging=d->pending=d->count=d->cancel=0;d->read=d->write;
#ifdef PAWS_BRIDGES
 d->moveRequest=d->ownerRequest=d->attackRequest=0;bridge_cache_clear(d);d->bridgeWorld=0;d->previewCount=d->previewValid=d->previewFixture=0;
 for(i=0;i<JOBS;i++)d->construction[i]=0;
 bridge_ai_clear(d);
#ifdef PAWS_BRIDGE_MULTIPLAYER
 d->netWorld=0;for(i=0;i<JOBS;i++)d->netJobs[i]=0;
#endif
#endif
}
EXPORT void roads_tick(Roads*d,U world){U i,a,u;float now,dt;int dirty=0;d->tick++;
#ifdef PAWS_INSTALLED_RIVERS
 current=d;d->gameInterface=game_interface(d);
#endif
 if(!world||!allowed(d)){clear(d);d->world=0;return;}now=F(world,0xe8);if(!finite(now))return;
 dt=d->world==world&&now>=d->lastTime?now-d->lastTime:0;
 if(d->world!=world||now<d->lastTime){clear(d);d->world=world;
#ifdef PAWS_BRIDGES
 d->bridgeWorld=0;d->routeRestoreCursor=1;
#endif
 }d->lastTime=now;
#ifdef PAWS_BRIDGES
 bridge_restore(d);
 bridge_net_restore(d);
 bridge_health_tick(d,dt);
 if(bridge_maintenance(d))dirty=1;
 if(bridge_sync(d)){dirty=1;d->routeRestoreCursor=1;}
 bridge_navigation_refresh(d);
 bridge_route_restore(d);
 if(d->ownerRequest){U id=d->ownerRequest,k=0,kn=P(world,0x154),ki;d->ownerRequest=0;
  if(kn<=96)for(ki=0;ki<kn;ki++){U kp=P(P(world,0x150),ki*4);if(kp&&P(kp,0x14)==id){k=kp;break;}}
  if(k){U material=d->ownerCount>>8,n=d->ownerCount&255;if(material){if(bridge_build_material(d,d->ownerPoints,n,k,material==2))dirty=1;}else if(bridge_build(d,d->ownerPoints,n,k))dirty=1;}
 }
 if(d->moveRequest){a=actor(d,d->moveRequest);d->moveRequest=0;if(a&&P(a,0xe8)==local(d)&&finite(d->moveX)&&finite(d->moveY)){if(bridge_networked(d))bridge_net_normal(d,a,5,d->moveX,d->moveY,0);else command(d,a,"move",d->moveX,d->moveY);}}
 if(d->attackRequest){a=actor(d,d->attackRequest);d->attackRequest=0;if(a&&P(a,0xe8)==local(d)&&actor(d,d->attackTarget)){if(bridge_networked(d))bridge_net_normal(d,a,0,0,0,d->attackTarget);else command_target_kind(d,a,d->attackTarget,0);}}
 if(d->fixture){U fixture=d->fixture;d->fixture=0;if(fixture==11){a=actor(d,d->ownerPoints[0]);if(a)command(d,a,"qmove",F(d->ownerPoints,4),F(d->ownerPoints,8));}else if(fixture==10){a=actor(d,d->ownerPoints[0]);if(a)command_target_kind(d,a,(U)integer(F(d->ownerPoints,4)),3);}else if(fixture==9){a=actor(d,d->ownerPoints[0]);if(bridge_actor(d,a))command(d,a,"raze",0,0);}else if(fixture==8)bridge_rapid_fixture_tick(d);else if(fixture==7)bridge_site_fixture_tick(d);else if(fixture==5){a=actor(d,d->ownerPoints[0]);if(a)command_target_kind(d,a,(U)integer(F(d->ownerPoints,4)),0);}else if(fixture==6){float pos[3];a=actor(d,d->ownerPoints[0]);pos[0]=F(d->ownerPoints,4);pos[1]=F(d->ownerPoints,8);pos[2]=bridge_height(d,integer(pos[0])>>1,integer(pos[1])>>1);if(a&&finite(pos[2])&&pos[2]>=0)bridge_group_relocate(d,a,pos);}else if(fixture==4)bridge_health_fixture_tick(d);else if(fixture==3){a=actor(d,d->ownerPoints[0]);if(a)command(d,a,"move",F(d->ownerPoints,4),F(d->ownerPoints,8));}else if(fixture==2)bridge_peace_fixture(d);else bridge_fixture(d);}
#endif
#ifdef PAWS_BRIDGES
 if(d->cancel&&bridge_networked(d)){a=actor(d,d->cancel);if(a&&P(a,0xe8)==local(d))bridge_net_normal(d,a,6,0,0,0);d->cancel=0;}
#endif
 if(d->cancel){Job*j=job(d,d->cancel);if(j){a=actor(d,j->id);if(a&&P(a,0xe8)==local(d))command(d,a,"stop",0,0);
#ifdef PAWS_BRIDGES
 bridge_abandon(d,j-d->jobs);
#else
 j->id=0;
#endif
 d->completed++;}d->cancel=0;}
#ifdef PAWS_BRIDGES
 if(d->pending&&bridge_networked(d)){a=actor(d,d->pending);if(a&&P(a,0xe8)==local(d)&&d->pendingTool&&d->valid)bridge_net_send(d,a,d->points,d->count,d->pendingMaterial);d->pending=0;}
#endif
 if(d->pending){Job*j;U k,id=d->pending;d->pending=0;a=actor(d,id);
  if(!a||P(a,0xe8)!=local(d)||!worker(d,a)||!d->valid||!d->count){d->rejected++;}
  else{j=job(d,id);if(!j){for(i=0;i<JOBS;i++)if(!d->jobs[i].id)break;j=i<JOBS?&d->jobs[i]:0;}
   if(j){
#ifdef PAWS_BRIDGES
    bridge_abandon(d,j-d->jobs);
#endif
    j->id=id;j->kingdom=P(P(a,0xe8),0x14);j->index=j->issued=0;j->count=d->count;j->lastMove=j->lastWork=now;
    for(k=0;k<j->count;k++)j->points[k]=d->points[k];
#ifdef PAWS_BRIDGES
    d->jobTools[j-d->jobs]=d->pendingTool;d->workStarted[j-d->jobs]=0;d->construction[j-d->jobs]=0;d->siteCommitted[j-d->jobs]=0;
    d->jobMaterials[j-d->jobs]=d->pendingMaterial;
    if(d->pendingTool){U approach=bridge_approach(d,a,j->points,j->count);
     if(!approach){j->id=0;d->rejected++;}
     else if(approach==2)for(k=0;k<j->count/2;k++){U swap=j->points[k];j->points[k]=j->points[j->count-k-1];j->points[j->count-k-1]=swap;}
    }
#endif
   }else d->rejected++;}
 }
 for(i=0;i<JOBS;i++){Job*j=&d->jobs[i];float dx,dy,x,y;int painted;if(!j->id)continue;a=actor(d,j->id);
  if(!a||!P(a,0xe8)||P(P(a,0xe8),0x14)!=j->kingdom||!(u=worker(d,a))||
#ifdef PAWS_BRIDGES
    (P(a,0xe8)!=local(d)&&!bridge_net_job_owned(d,i,a)&&!bridge_ai_job_owned(d,i,a))
#else
    P(a,0xe8)!=local(d)
#endif
    ){
#ifdef PAWS_BRIDGES
   bridge_abandon(d,i);
#else
   j->id=0;
#endif
   continue;}
  if(fighting(d,a)||fighting(d,u)){
#ifdef PAWS_BRIDGES
   bridge_abandon(d,i);
#else
   j->id=0;
#endif
   d->completed++;continue;}
  if(j->index==j->count){j->id=0;d->completed++;continue;}
  x=(j->points[j->index]&65535)*2+1;y=(j->points[j->index]>>16)*2+1;
#ifdef PAWS_BRIDGES
  if(d->jobTools[i]){
   if(d->construction[i]){U site=actor(d,d->construction[i]);
    if(!site){j->id=0;d->rejected++;continue;}
    if(!d->siteCommitted[i]){U body=P(site,0x60);
     if(body&&F(body,0x10)>d->siteHealth[i]){
      /* Another company may have started a crossing during the approach.
       * Only the first actual construction wins; queued sites do not block. */
      if(bridge_occupied(d,j->points,j->count,j->id)||!bridge_funds(d,P(site,4),a,site)){invoke(d,0x24338e,d->world,1,site,0);command(d,a,"stop",0,0);d->construction[i]=j->id=0;d->rejected++;continue;}
      d->siteCommitted[i]=1;bridge_clear_doodads(d,site);
     }else if(now-j->lastWork>12){bridge_abandon(d,i);command(d,a,"stop",0,0);d->rejected++;continue;}
    }
    if(!(P(site,0x100)&0x200000)){U variant=bridge_variant(d,"paws_engineer_bridge01");
     if(variant&&bridge_paint(d,j->points,j->count,variant)){
      d->completed++;d->nativeFinished++;dirty=1;
     }j->id=0;
    }continue;
   }
   if(!bridge_valid(d,j->points,j->count,0)||(!j->issued&&bridge_occupied(d,j->points,j->count,j->id))){j->id=0;d->rejected++;continue;}
   if(!j->issued){if(!command(d,a,"move",x,y)){j->id=0;d->rejected++;continue;}j->issued=1;j->lastMove=now;}
   dx=F(a,0x20)-x;dy=F(a,0x24)-y;
   /* Native company movement may complete 3--5 units before its point.
    * Do not discard a valid build while its members can reach the landing. */
   if(dx*dx+dy*dy>36){d->workStarted[i]=0;if(now-j->lastMove>60||(!moving(d,a)&&now-j->lastMove>3)){j->id=0;d->rejected++;}continue;}
   dx=F(u,0x20)-x;dy=F(u,0x24)-y;
   if(dx*dx+dy*dy>64){d->workStarted[i]=0;if(now-j->lastMove>60){j->id=0;d->rejected++;}continue;}
   {float heights[2];U site;BridgeGeometry planned=bg_points(j->points,j->count);
    if(!bridge_valid(d,j->points,j->count,heights)||bridge_occupied(d,j->points,j->count,j->id)||!bridge_funds(d,bridge_definition_owner(d,bg_model(&planned),0,d->jobMaterials[i],P(a,0xe8)),a,0)){j->id=0;d->rejected++;continue;}
    site=bridge_object_create(d,j->points,j->count,P(a,0xe8),(heights[0]>heights[1]?heights[0]:heights[1])+.08f,1,d->jobMaterials[i]);
    if(!site){j->id=0;d->rejected++;continue;}
    if(!command_target(d,a,P(site,0x14))){invoke(d,0x24338e,d->world,1,site,0);j->id=0;d->rejected++;continue;}
    d->construction[i]=P(site,0x14);d->siteHealth[i]=P(site,0x60)?F(P(site,0x60),0x10):0;d->siteCommitted[i]=0;j->lastWork=now;d->nativeStarted++;
   }continue;
  }
#endif
  if(!passable(d,integer(x)>>1,integer(y)>>1)){j->id=0;d->rejected++;continue;}
  if(!j->issued){if(!command(d,a,"move",x,y)){j->id=0;d->rejected++;continue;}j->issued=1;j->lastMove=now;j->lastWork=now;}
  dx=F(a,0x20)-x;dy=F(a,0x24)-y;
  if(dx*dx+dy*dy>9){j->lastWork=now;if(now-j->lastMove>60||(!moving(d,a)&&now-j->lastMove>3)){j->id=0;d->rejected++;}continue;}
  dx=F(u,0x20)-x;dy=F(u,0x24)-y;if(dx*dx+dy*dy>64){j->lastWork=now;if(now-j->lastMove>60){j->id=0;d->rejected++;}continue;}
  if(now-j->lastWork<.5f)continue;painted=build(d,j->points[j->index]);if(painted<0){j->id=0;d->rejected++;continue;}
  dirty|=painted;j->index++;j->issued=0;j->lastWork=now;
 }
#ifdef PAWS_BRIDGES
 bridge_ai_tick(d,now);
#endif
 if(dirty)invoke(d,0x2424b2,world,1,0,0);
}
EXPORT U FAST roads_event(U self,U unused,U event){Roads*d=current;U ui,mgr,a,code,flags;int x,y;
 if(!d)return 0;ui=P(d->image,0x5f3fbc);mgr=P(d->image,0x5f3fc0);code=*(W*)(event+8);flags=P(event,4);
 if(!allowed(d)){d->armed=d->dragging=0;return m1(d,0xd4e76,self,event);}
 if(d->armed){
  if((code==0x1b||code==0x101)&&(flags&1)){d->armed=d->dragging=d->count=0;return 1;}
  if(code==0x100){
   a=selected(d);if(!a||P(a,0x14)!=d->armed){d->armed=d->dragging=0;return 1;}
   if(flags&1){if(cursor(d,&x,&y)){d->dragging=1;d->startX=x;d->startY=y;plan(d,x,y);}return 1;}
   if(flags&2){if(d->dragging&&cursor(d,&x,&y)){plan(d,x,y);if(d->valid){d->pending=d->armed;
#ifdef PAWS_BRIDGES
    d->pendingTool=d->tool;
#endif
   }else d->rejected++;}d->armed=d->dragging=0;return 1;}
  }
 }
 /* A normal right-click is an explicit replacement of this company's task. */
 if(!bridge_networked(d)&&code==0x101&&(flags&1)&&ui&&mgr&&P(mgr,0x60)==ui&&(a=selected(d))){Job*j=job(d,P(a,0x14));if(j){
#ifdef PAWS_BRIDGES
 bridge_abandon(d,j-d->jobs);
#else
 j->id=0;
#endif
 d->completed++;}}
 return m1(d,0xd4e76,self,event);
}
static void FAST activate(U self,U unused){Roads*d=current;U a;if(!d||d->pending||!(a=selected(d)))return;
 if(job(d,P(a,0x14))){d->cancel=P(a,0x14);return;}
 if(d->armed){d->armed=d->dragging=d->count=0;return;}
#ifdef PAWS_BRIDGES
 d->tool=self==d->bridgeButton;
#endif
 d->armed=P(a,0x14);d->dragging=d->count=0;
}
/* Mouse release owns the road tool only, never issues a native move itself. */
static void FAST mouse_release(U self,U unused){Roads*d=current;if(!d)return;if(P(self,0x24)&0x100)activate(self,0);m1(d,0x2b8b5d,self,0);}
static float FAST sort(U self,U unused){return 0;}
static void FAST ui_tick(U self,U unused){Roads*d=current;U a,state=0,text;if(!d)return;m0(d,0x2b8a35,self);a=selected(d);if(a)state=job(d,P(a,0x14))?2:d->armed?3:1;
#ifdef PAWS_BRIDGES
 if(self==d->bridgeButton){bridge_ui(d,self,state);return;}
#endif
 if(d->armed&&(!a||P(a,0x14)!=d->armed)){d->armed=d->dragging=d->count=0;}
 if(d->dragging){int x,y;if(cursor(d,&x,&y))plan(d,x,y);else d->valid=0;state=d->valid?3:4;
  if(d->valid&&++d->drawTick%30==0){U k,step=d->count/12+1,ui=P(d->image,0x5f3fbc);for(k=0;k<d->count;k+=step){union{float f;U u;}px,py;px.f=(d->points[k]&65535)*2+1;py.f=(d->points[k]>>16)*2+1;invoke(d,0x2ec00c,ui,2,px.u,py.u);}}
 }
 if(!d->uiId){U lang=d->language<6?d->language:0;release(d,P(self,0x3c));P(self,0x3c)=str(d,(const W*)road_labels[lang][1]);release(d,P(self,0x40));P(self,0x40)=str(d,(const W*)road_tips[lang]);d->uiId=1;}
 if(d->uiStatus!=state+1){d->uiStatus=state+1;text=str(d,(const W*)road_labels[d->language<6?d->language:0][state]);((M1)P(P(d->label,0),0xc8))(d->label,0,(U)&text);release(d,text);}
}
EXPORT void roads_create(Roads*d,U game){U name,label,w,i;current=d;clear(d);d->world=0;d->uiStatus=0;d->uiId=0;
#ifdef PAWS_BRIDGES
 d->gameInterface=game;d->bridgeWorld=d->bridgeCount=0;
#endif
 /* Own vtable keeps every native operation except activation/update/sort. */
 for(i=0;i<54;i++)d->vt[i]=P(d->image,0x504be0+i*4);
 d->vt[1+0x6c/4]=(U)activate;d->vt[1+0xcc/4]=(U)mouse_release;d->vt[1+0xc/4]=(U)ui_tick;d->vt[1+0xa8/4]=(U)sort;
 name=str(d,(const W*)L"Client");label=((C2)(d->image+0x81d30))((U)&name,0);release(d,name);d->label=label;
 name=str(d,(const W*)L"PawRoadButton");w=((C5)(d->image+0x2b88c0))((U)&name,1,0,0,label);release(d,name);
 if(!w)return;P(w,0)=(U)(d->vt+1);d->button=w;((M2)(d->image+0x2b7486))(game,0,w,0);
#ifdef PAWS_BRIDGES
 /* Bridge is supplied by the native engineer BuilderComponent menu. */
 d->bridgeButton=d->bridgeLabel=0;
#endif
}
