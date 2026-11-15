/* Local bridge mechanics. Included after Roads and the common native helpers. */
#include "bridge_text.h"
#define BRIDGE_MAX 32
#include "geometry.h"
static U bridge_water(Roads*d,int l,int r,int t,int b);
static int bridge_hm(Roads*d);
static float bridge_height(Roads*d,int x,int y);
EXPORT U bridge_material(Roads*d,U kingdom);
static U bridge_metadata_make(Roads*d,U*pts,U n,U pending);
static U bridge_metadata_geometry(Roads*d,BridgeGeometry*g,U pending);
static void bridge_cache_clear(Roads*d);
static void bridge_cache_capture(Roads*d,BridgeSpan*s,U text);
static U bridge_original_at(Roads*d,int x,int y);
#include "objects.h"
#include "growth_effect.h"
static int bridge_abs(int v){return v<0?-v:v;}
static int bridge_wetland(U cell){const W*w=P(cell,0)?(W*)P(P(cell,0),8):0;U i,j;const char*names[3];names[0]="swamp";names[1]="marsh";names[2]="quicksand";
 if(!w)return 0;for(i=0;i<80&&w[i];i++)for(j=0;j<3;j++){U k=0;while(names[j][k]&&w[i+k]&&(W)names[j][k]==w[i+k])k++;if(!names[j][k])return 1;}return 0;}
static int bridge_bank(Roads*d,int x,int y){int xx,yy;U c;
 if(!passable(d,x,y))return 0;for(yy=y-2;yy<=y+2;yy++)for(xx=x-2;xx<=x+2;xx++){c=tile(d,xx,yy);if(!c||(P(c,0x20)&0x70)==0x20||bridge_wetland(c))return 0;}return 1;}
static U bridge_variant(Roads*d,const char*name){U mgr=P(d->image,0x5f0030),i,n,p;if(!mgr||!(n=P(mgr,0x28))||n>4096)return 0;
 for(i=0;i<n;i++){p=P(P(mgr,0x24),i*4);if(p&&eq((W*)P(p,8),name))return p;}return 0;}
static int bridge_hm(Roads*d){U h=P(d->world,0x38),b=P(d->world,0x34);return h&&b&&P(h,0xc)>0&&P(h,0x10)>0&&P(h,0xc)<=2049&&P(h,0x10)<=2049&&P(h,0x14)<=4&&P(h,0x1c)<=64&&P(h,0x40)&&P(b,0x40)&&P(h,0xc)==P(b,0xc)&&P(h,0x10)==P(b,0x10)&&P(h,0x14)==P(b,0x14)&&P(h,0x1c)==P(b,0x1c);}
static float bridge_height(Roads*d,int x,int y){U h=P(d->world,0x38),b=P(d->world,0x34),at;int xx=(x*2+1+(int)P(h,0x1c))>>P(h,0x14),yy=(y*2+1+(int)P(h,0x1c))>>P(h,0x14);
 if(xx<0||yy<0||xx>=(int)P(h,0xc)||yy>=(int)P(h,0x10))return -10000;
 at=(yy*P(h,0xc)+xx)*4;return F(P(h,0x40),at)+F(P(b,0x40),at);}
/* One narrow continuous water band, sound landings, no mountains or islands. */
static int bridge_valid(Roads*d,U*points,U n,float*level){U i,c,phase=0,wet=0;int x,y,xx,yy,x0,y0,x1,y1;float z0,z1;
 if(n<5||n>BRIDGE_MAX||!bridge_hm(d))return 0;
 {BridgeGeometry g=bg_points(points,n);U canonical[32],cn,j;if(bg_model(&g)>32)return 0;cn=bg_line(points[0]&65535,points[0]>>16,points[n-1]&65535,points[n-1]>>16,canonical);if(cn!=n)return 0;for(j=0;j<n&&canonical[j]==points[j];j++);
  /* Choosing the reachable bank reverses the original rasterized line.
   * Bresenham tie cells depend on traversal direction. Accept either exact
   * rasterization, including the reversed preview, while rejecting bends. */
  if(j<n){cn=bg_line(points[n-1]&65535,points[n-1]>>16,points[0]&65535,points[0]>>16,canonical);if(cn!=n)return 0;for(j=0;j<n;j++)if(canonical[n-1-j]!=points[j])return 0;}
 }
 x0=points[0]&65535;y0=points[0]>>16;x1=points[n-1]&65535;y1=points[n-1]>>16;
 if(!bridge_bank(d,x0,y0)||!bridge_bank(d,x1,y1))return 0;
 z0=bridge_height(d,x0,y0);z1=bridge_height(d,x1,y1);
 if(!finite(z0)||!finite(z1)||z0<.4f||z1<.4f||z0>8||z1>8||z0-z1>2||z1-z0>2)return 0;
 for(i=0;i<n;i++){
  x=points[i]&65535;y=points[i]>>16;
  if(i&&(bridge_abs(x-(int)(points[i-1]&65535))>1||bridge_abs(y-(int)(points[i-1]>>16))>1||points[i]==points[i-1]))return 0;
  c=tile(d,x,y);if(!c||bridge_wetland(c))return 0;
  if(P(c,0)&&eq((W*)P(P(c,0),8),"paws_engineer_bridge01"))return 0;
  if((P(c,0x20)&0x70)==0x20){if(phase==2)return 0;phase=1;wet++;}
  else{if(P(c,0x20)&0x100)return 0;if(phase==1)phase=2;}
  for(yy=y-1;yy<=y+1;yy++)for(xx=x-1;xx<=x+1;xx++){
   float z;c=tile(d,xx,yy);if(!c)return 0;
   if((P(c,0x20)&0x100)&&(P(c,0x20)&0x70)!=0x20)return 0;
   z=bridge_height(d,xx,yy);if(!finite(z)||z<-8||z>8)return 0;
  }
 }
 if(!wet||wet>16||phase!=2)return 0;
 if(level){level[0]=z0;level[1]=z1;}return 1;
}
static void bridge_plan(Roads*d,int x,int y){d->count=bg_line(d->startX,d->startY,x,y,d->points);d->valid=d->count&&bridge_valid(d,d->points,d->count,0);}
/* Mobile animals/companies cannot permanently reserve a river. Native
 * structures and already-started bridges do. Pending intents reserve nothing. */
static int bridge_occupied(Roads*d,U*pts,U n,U owner){U reg=P(d->image,0x5ef72c),i,a,j,count,axis;BridgeGeometry plan=bg_points(pts,n);
 if(!reg)return 1;
 for(i=1;i<65536;i++){
  a=P(reg,0x20004+i*4);if(!a||P(a,0)!=d->image+0x4e5c58||(P(a,8)&3)||P(a,0x14)==owner)continue;
  for(j=0;j<JOBS;j++)if(d->jobs[j].id&&d->construction[j]==P(a,0x14)&&(d->jobs[j].id==owner||!d->siteCommitted[j]))break;
  if(j<JOBS)continue;
  if(bridge_kind(P(a,4),&count,&axis)){BridgeGeometry other=bg_actor(a,count,axis);if(bg_overlap(&plan,&other,3))return 1;continue;}
  if(P(a,0x6c)||P(a,0x7c)||P(a,0x80))continue;
  if(bg_inside(&plan,F(a,0x20),F(a,0x24),3,1))return 1;
 }return 0;
}

static void bridge_set_height(Roads*d,int x,int y,float value){U v[4],h=P(d->world,0x38);union{float f;U u;}z;z.f=value;v[0]=x;v[1]=y;v[2]=z.u;v[3]=0;

 ((NativeCall)d->call)(d->image+0x2f95f8,h,4,v);}

static U bridge_water(Roads*d,int l,int r,int t,int b){U map=P(d->world,0x30),body,repaired=0;int x,y;

 if(!map||!P(map,0x50)||!P(d->world,0x248))return 0;

 for(y=t;y<=b;y++)for(x=l;x<=r;x++){

  U c=tile(d,x,y);if(!c||!P(c,0)||((P(c,0x20)&0x70)!=0x20&&!eq((W*)P(P(c,0),8),"paws_engineer_bridge01"))||B(c,0x2c))continue;

  body=invoke(d,0x24f6b0,map,0,0,0)&255;

  if(body){U args[3];args[0]=x;args[1]=y;args[2]=P(P(map,0x50),body*4);((NativeCall)d->call)(d->image+0x25fe70,P(d->world,0x248),3,args);repaired++;}

 }

 return repaired;

}

static int bridge_covered_elsewhere(Roads*d,U skip,int x,int y);
static void bridge_trim(Roads*d,BridgeGeometry*g,int l,int r,int t,int b){int x,y;U changes[4],args[3];
 for(y=t;y<=b;y++)for(x=l;x<=r;x++){U c=tile(d,x,y),v;if(!c||!P(c,0)||!eq((W*)P(P(c,0),8),"paws_engineer_bridge01")||bg_nav(g,x*2+1,y*2+1))continue;
  /* Nearby angled spans can share this bounding box without overlapping.
   * Trimming transition spill must never erase another completed crossing. */
  if(bridge_covered_elsewhere(d,0xffffffff,x,y))continue;
  v=bridge_original_at(d,x,y);if(!v)continue;changes[0]=changes[1]=changes[2]=changes[3]=0;args[0]=v;args[1]=0;args[2]=(U)changes;((NativeCall)d->call)(d->image+0x24a522,c,3,args);
 }
}
static int bridge_paint(Roads*d,U*pts,U n,U variant){U ctx[8],xy[2],i;int x,y,l,r,t,b;BridgeGeometry g=bg_points(pts,n);
 bg_bounds(&g,5,4,&l,&r,&t,&b);
 for(i=0;i<8;i++)ctx[i]=0;invoke(d,0x2517a3,(U)ctx,0,0,0);
 for(y=t;y<=b;y++)for(x=l;x<=r;x++){
  U c=tile(d,x,y);if(!c||!bg_nav(&g,x*2+1,y*2+1)||(P(c,0x20)&0x70)!=0x20||P(c,0)==variant)continue;
  xy[0]=x;xy[1]=y;invoke(d,0x2517f9,(U)ctx,2,(U)xy,variant);d->painted++;
 }
 invoke(d,0x25185b,(U)ctx,1,0,0);invoke(d,0x20d4b,(U)(ctx+3),0,0,0);invoke(d,0x20d4b,(U)(ctx+5),0,0,0);
 /* Native bank transitions may retain a higher-priority water variation in
  * individual deck cells. Set the rasterized corridor once. */
 for(y=t;y<=b;y++)for(x=l;x<=r;x++){U c=tile(d,x,y),changes[4],args[3];if(!c||!bg_nav(&g,x*2+1,y*2+1)||(P(c,0x20)&0x70)!=0x20||P(c,0)==variant)continue;
  changes[0]=changes[1]=changes[2]=changes[3]=0;args[0]=variant;args[1]=0;args[2]=(U)changes;((NativeCall)d->call)(d->image+0x24a522,c,3,args);d->painted++;
 }
 bridge_trim(d,&g,l,r,t,b);bridge_water(d,l,r,t,b);return 1;
}
#include "lifecycle.h"

/* Native construction and its assigned engineer orders survive saves. Derive

 * the navigation corridor when native construction finishes, including loads

 * with no transient job left in the tool's memory. */

static U bridge_sync(Roads*d){U i,dirty=0;

 for(i=0;i<d->bridgeCount;i++){BridgeSpan*s=&d->spans[i];U a=actor(d,s->id),n,axis,j,pts[32],wet=0,v;

  if(!a||((P(a,8)&3)||(P(a,0x100)&0x200000))||!bridge_kind(P(a,4),&n,&axis)||(s->opened&2))continue;

  s->opened=1;

  {BridgeGeometry g=bg_actor(a,n,axis);n=bg_line(bg_round((g.x-g.ux*g.half-1)*.5f),bg_round((g.y-g.uy*g.half-1)*.5f),bg_round((g.x+g.ux*g.half-1)*.5f),bg_round((g.y+g.uy*g.half-1)*.5f),pts);}
  for(j=0;j<n;j++){U c=tile(d,pts[j]&65535,pts[j]>>16);if(c&&(P(c,0x20)&0x70)==0x20&&P(c,0)&&!eq((W*)P(P(c,0),8),"paws_engineer_bridge01"))wet++;}
  {BridgeGeometry g=bg_points(pts,n);int l,r,t,b,x,y;bg_bounds(&g,5,4,&l,&r,&t,&b);for(y=t;y<=b;y++)for(x=l;x<=r;x++){U c=tile(d,x,y);if(c&&bg_nav(&g,x*2+1,y*2+1)&&(P(c,0x20)&0x70)==0x20&&P(c,0)&&!eq((W*)P(P(c,0),8),"paws_engineer_bridge01"))wet++;}}
  if(wet){if((v=bridge_variant(d,"paws_engineer_bridge01"))&&bridge_paint(d,pts,n,v)){d->bridgeBuilt++;dirty=1;s->opened|=2;}}
  else s->opened|=2;

 }return dirty;

}

static int bridge_build_material(Roads*d,U*pts,U n,U kingdom,U wood){U variant,a;float level[2],deck;
 if(!bridge_valid(d,pts,n,level)||!(variant=bridge_variant(d,"paws_engineer_bridge01")))return 0;
 deck=(level[0]>level[1]?level[0]:level[1])+.08f;
 a=bridge_object_create(d,pts,n,kingdom,deck,0,wood);if(!a){d->bridgeFailed++;return 0;}
 return bridge_paint(d,pts,n,variant);
}
static int bridge_build(Roads*d,U*pts,U n,U kingdom){return bridge_build_material(d,pts,n,kingdom,bridge_material(d,kingdom));}
static void bridge_ui(Roads*d,U self,U state){U text,lang=d->language<6?d->language:0;
 if(d->dragging&&d->tool)state=d->valid?3:4;
 if(!d->bridgeTip){release(d,P(self,0x3c));P(self,0x3c)=str(d,(const W*)bridge_labels[lang][1]);release(d,P(self,0x40));P(self,0x40)=str(d,(const W*)bridge_tips[lang]);d->bridgeTip=1;}
 if(d->bridgeStatus!=state+1){d->bridgeStatus=state+1;text=str(d,(const W*)bridge_labels[lang][state]);((M1)P(P(d->bridgeLabel,0),0xc8))(d->bridgeLabel,0,(U)&text);release(d,text);}
}
/* Explicit developer fixture command; no automatic edits on game/load. */
static void bridge_peace_fixture(Roads*d){U reg=P(d->image,0x5ef72c),kingdom=local(d),i,a;
 if(!allowed(d)||!reg||!kingdom)return;
 /* Isolate native movement from combat in a disposable copy of a user save.
  * Keep terrain, buildings, player actors and bridge data unchanged. */
 for(i=1;i<65536;i++){a=P(reg,0x20004+i*4);if(a&&P(a,0)==d->image+0x4e5c58&&!(P(a,8)&3)&&P(a,0xe8)!=kingdom&&(P(a,0x6c)||P(a,0x7c)||P(a,0x80)))invoke(d,0x24338e,d->world,1,a,0);}
}
static void bridge_fixture(Roads*d){U map=P(d->world,0x30),v,ctx[8],xy[2],i,h,b,hw,hh,shift,pad,body;int x,y,left,right,width,height;
 if(!allowed(d)||!map||!bridge_hm(d))return;width=P(map,0x1c);height=P(map,0x20);if((width!=96&&width!=192)||height!=width)return;left=width==96?55:72;right=left+5;
 if(!(v=bridge_variant(d,"temperate_river01")))return;
 for(i=0;i<8;i++)ctx[i]=0;invoke(d,0x2517a3,(U)ctx,0,0,0);
 for(y=0;y<height;y++)for(x=left;x<=right;x++){xy[0]=x;xy[1]=y;invoke(d,0x2517f9,(U)ctx,2,(U)xy,v);}
 invoke(d,0x25185b,(U)ctx,1,0,0);invoke(d,0x20d4b,(U)(ctx+3),0,0,0);invoke(d,0x20d4b,(U)(ctx+5),0,0,0);
 h=P(d->world,0x38);b=P(d->world,0x34);hw=P(h,0xc);hh=P(h,0x10);shift=P(h,0x14);pad=P(h,0x1c);
 for(y=0;y<(int)hh;y++)for(x=0;x<(int)hw;x++){int wx=(x<<shift)-(int)pad;if(wx>=left*2&&wx<=(right+1)*2)bridge_set_height(d,x,y,-1.5f-F(P(b,0x40),(y*hw+x)*4));}
 body=invoke(d,0x24f6b0,map,0,0,0)&255;
 if(body){U args[3];args[0]=left+2;args[1]=height/2;args[2]=P(P(map,0x50),body*4);((NativeCall)d->call)(d->image+0x25fe70,P(d->world,0x248),3,args);}
 invoke(d,0x2424b2,d->world,1,0,0);
}
/* Small read-only validation entry point for relocation/terrain regression tests. */
EXPORT U bridge_check(Roads*d,U*pts,U n){return bridge_valid(d,pts,n,0);}
EXPORT U bridge_trim_check(Roads*d,U*pts,U n){BridgeGeometry g=bg_points(pts,n);int l,r,t,b;bg_bounds(&g,5,4,&l,&r,&t,&b);bridge_trim(d,&g,l,r,t,b);return 1;}
EXPORT U bridge_occupied_check(Roads*d,U*pts,U n,U owner){return bridge_occupied(d,pts,n,owner);}
EXPORT U bridge_commit(Roads*d,U*pts,U n){return bridge_build(d,pts,n,local(d));}
EXPORT U bridge_commit_material(Roads*d,U*pts,U n,U wood){return wood<=1?bridge_build_material(d,pts,n,local(d),wood):0;}
EXPORT U bridge_layout_size(void){return (U)sizeof(Roads);}
EXPORT U bridge_fixture_offset(void){return (U)offsetof(Roads,fixture);}
EXPORT U bridge_field(U which){switch(which){case 0:return offsetof(Roads,bridgeWorld);case 1:return offsetof(Roads,bridgeCount);case 2:return offsetof(Roads,spans);case 4:return offsetof(Roads,bridgeBuilt);case 5:return offsetof(Roads,bridgeFailed);case 6:return offsetof(Roads,bridgeError);case 7:return offsetof(Roads,nativeStarted);case 8:return offsetof(Roads,nativeFinished);case 9:return offsetof(Roads,gameInterface);case 10:return offsetof(Roads,previewCount);case 11:return offsetof(Roads,previewPoints);case 20:return offsetof(Roads,decalSelf);default:return sizeof(Roads);}}
/* Intent-only entry points for the private native QA driver. The ordinary job
 * loop owns validation, approach, time, native actor creation and painting. */
EXPORT U bridge_request(Roads*d,U id,U*pts,U n){U i;if(!allowed(d)||d->pending||n<5||n>32)return 0;
 for(i=0;i<n;i++)d->points[i]=pts[i];d->count=n;d->valid=1;d->pendingTool=1;d->pendingMaterial=bridge_material(d,local(d));d->pending=id;return 1;}
EXPORT U bridge_move_request(Roads*d,U id,float x,float y){if(!allowed(d)||!finite(x)||!finite(y)||d->moveRequest)return 0;d->moveX=x;d->moveY=y;d->moveRequest=id;return 1;}
/* Explicit private-QA fixture; never used by the normal UI or AI. */
EXPORT U bridge_move_fixture(Roads*d,U id,float x,float y){if(!allowed(d)||!finite(x)||!finite(y)||d->fixture)return 0;d->ownerPoints[0]=id;F(d->ownerPoints,4)=x;F(d->ownerPoints,8)=y;d->fixture=3;return 1;}
EXPORT U bridge_health_fixture(Roads*d,U id,float health){if(!allowed(d)||!finite(health)||health<0||d->fixture)return 0;d->ownerPoints[0]=id;F(d->ownerPoints,4)=health;d->fixture=4;return 1;}
EXPORT U bridge_actor_fixture(Roads*d,U id,U mode,float x,float y){if(!allowed(d)||mode>6||!finite(x)||!finite(y)||d->fixture)return 0;d->ownerPoints[0]=id;F(d->ownerPoints,4)=x;F(d->ownerPoints,8)=y;d->fixture=mode+5;return 1;}
EXPORT U bridge_attack_request(Roads*d,U id,U target){if(!allowed(d)||!id||!target||d->attackRequest)return 0;d->attackRequest=id;d->attackTarget=target;return 1;}
EXPORT U bridge_owner_request(Roads*d,U id,U*pts,U n){U i;if(!allowed(d)||!id||d->ownerRequest||n<5||n>32)return 0;
 for(i=0;i<n;i++)d->ownerPoints[i]=pts[i];d->ownerCount=n;d->ownerRequest=id;return 1;}
EXPORT U bridge_art_request(Roads*d,U id,U*pts,U n,U wood){if(wood>1||!bridge_owner_request(d,id,pts,n))return 0;d->ownerCount|=(wood+1)<<8;return 1;}
