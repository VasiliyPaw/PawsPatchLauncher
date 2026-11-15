#include "shapes.h"
#include "profiles.h"
typedef unsigned short W;
#define R(p,o) (*(U *)((U)(p)+(o)))
#define B(p,o) (*(unsigned char *)((U)(p)+(o)))
typedef U (*NativeCall)(U,U,U,U*);
typedef struct { U image,call,world,creator,shape,seed,width,height,result,land,water,hash,runs,phase,bodies,heights,rivers,riverCells,priorTerrain,riverRepairs,riverGaps,afterNoise,riverPlan,riverPlanSize,placementOverrides,bedRepairs,waterMeshes,waterExtra,waterUpdates,waterBlended; } State;
__attribute__((dllexport)) U finish_river_bed(State*s);
int __attribute__((stdcall)) _dllstart(void *m,U reason,void *unused){return 1;}
static U invoke(State *s,U rva,U self,U n,U a,U b,U c,U d) {
 U args[4];args[0]=a;args[1]=b;args[2]=c;args[3]=d;
 return ((NativeCall)s->call)(s->image+rva,self,n,args);
}
static int eq(W *w,char *a){int i;if(!w)return 0;for(i=0;i<80&&a[i];i++)if(w[i]!=(unsigned char)a[i])return 0;return !a[i]&&!w[i];}
static int prefix(W*w,char*a){U i;if(!w)return 0;for(i=0;a[i];i++)if(w[i]!=(W)a[i])return 0;return 1;}
static int river_bad_shore(W*w){U i,j;const char*bad[4]={"swamp","marsh","quicksand","rough"};if(!w)return 0;for(i=0;i<100&&w[i];i++)for(j=0;j<4;j++){U k=0;while(bad[j][k]&&w[i+k]==(W)bad[j][k])k++;if(!bad[j][k])return 1;}return 0;}
static U terrain(State*s,U generator){if(s->afterNoise)return 1;return ((NativeCall)s->call)(s->priorTerrain?s->priorTerrain:s->image+0x256f19,generator,0,0);}
static U find(State *s,char *id){U mgr=R(s->image,0x5f0030),i,p;if(!mgr||R(mgr,0x28)>4096)return 0;for(i=0;i<R(mgr,0x28);i++){p=R(R(mgr,0x24),4*i);if(p&&eq((W*)R(p,8),id))return p;}return 0;}
#include "water_blend.h"
__attribute__((dllexport)) int layout(unsigned char *m,int w,int h,U seed,int kind){return make_mask(m,w,h,seed,kind);}
__attribute__((dllexport)) int river_maximum(int w,int h){return river_limit(w,h);}
__attribute__((dllexport)) int river_layout(unsigned char*m,const unsigned char*sea,int w,int h,U seed,int count){if(w<64||h<64||w>1024||h>1024)return -1;return river_paths(m,sea,w,h,seed,count);}
static int river_setting(U world,int kind){U i,n,items,def;if(!world)return kind==3?-1:0;
 items=R(world,0x18);n=R(world,0x1c);if(items&&n<256)for(i=0;i<n;i++){
  U rule=items+i*12;def=R(rule,0);
  if(def&&(eq((W*)R(def,8),"PawsRivers")||eq((W*)R(def,8),"pawsrivers"))&&R(def,0x20)==3)return R(rule,8)<17?(int)R(rule,8):-1;
 }return kind==3?-1:0;
}
static U map_shape(U world,U seed){U i,n,items,def;if(!world)return 0;items=R(world,0x18);n=R(world,0x1c);if(items&&n<256)for(i=0;i<n;i++){U r=items+i*12;def=R(r,0);if(def&&(eq((W*)R(def,8),"PawsMapShape")||eq((W*)R(def,8),"pawsmapshape")))return shape_choice(R(r,8),seed);}return 0;}
/* The installed build chains the existing terrain stage (including mixed
   biomes), then applies independent shape/river rules to every native profile.
   Native decoration, actor placement and serialization continue normally. */
__attribute__((dllexport)) U generate(State *s,U generator) {
 U creator=R(generator,0),rmc=creator?R(creator,0x50):0,kind=0,world,map,grid,w,h,n,x,y,i,water,waters[4],riverWaters[4],ctx[8],point[2],body,hm,basehm,hw,hh,shift,pad;
 unsigned char *mask=0,*rivers=0;U *dist=0;U ret;int xx,yy,d,nearest,requested;union{float f;U u;}z;
 int shape=0,climate=0;
 W *id=rmc?(W*)R(rmc,8):0;
#ifdef PAWS_INSTALLED_RIVERS
 /* Preserve installed biome generation first. Elevation noise can repaint
    mountains over water, so overlay rivers after that native stage, before
    any kingdoms or other actors are placed. */
 if(!s->afterNoise)return terrain(s,generator);
#endif
 if(s->riverPlan){((void(*)(void*))(s->image+0x2ef05f))((void*)s->riverPlan);s->riverPlan=s->riverPlanSize=0;}
 profile_decode(id,&shape,&climate);kind=(U)shape;
#ifdef PAWS_INSTALLED_RIVERS
 kind=map_shape(R(s->image,0x5f3fb8),R(creator,0x4c));
#endif
 world=R(s->image,0x5f3fb8);requested=river_setting(world,(int)kind);
 s->riverRepairs=s->riverGaps=s->placementOverrides=0;
 if(!kind&&!requested){s->creator=creator;s->world=world;s->shape=0;s->seed=creator?R(creator,0x4c):0;s->rivers=s->riverCells=0;s->result=s->phase=0;if(world&&R(world,0x30)){s->width=R(R(world,0x30),0x1c);s->height=R(R(world,0x30),0x20);}return terrain(s,generator);}
 s->creator=creator;s->shape=kind;s->seed=R(creator,0x4c);s->result=1;s->runs++;s->phase=1;s->bodies=0;s->heights=0;s->riverCells=0;
 /* Multiplayer remains opt-in until the three-peer candidate passes QA. */
 if(!R(s->image,0x5f3fe4)
#ifndef PAWS_BRIDGE_MULTIPLAYER
 ||B(R(s->image,0x5f3fe4),0x100)
#endif
 ){s->result=2;return 0;}
 s->world=world;if(!world)return 0;
 map=R(world,0x30);if(!map)return 0;
 w=R(map,0x1c);h=R(map,0x20);s->width=w;s->height=h;
 if(w<64||h<64||w>1024||h>1024)return 0;
 water=find(s,climate==1?(kind==3?"arctic_river01":"arctic_lake01"):
  climate==2?"desert_lake01":kind==3?"temperate_river01":"temperate_lake01");if(!water){s->result=3;return 0;}
 waters[0]=find(s,"temperate_lake01");waters[1]=find(s,"arctic_lake01");waters[2]=find(s,"desert_lake01");waters[3]=find(s,"cursed_lake01");
 /* Native biome surfaces also carry the registered ground textures and
  * transition rules. Independent water definitions rendered an opaque blue
  * strip over Arctic ice and a hard seam at a native lake. Explicit river
  * coverage/depth below still guarantees a continuous blocked channel. */
 for(i=0;i<4;i++){if(!waters[i])waters[i]=water;riverWaters[i]=waters[i];}
 n=w*h;mask=(unsigned char*)((U(*)(U))(s->image+0x2ef03c))(n*6);
 if(!mask){s->result=4;return 0;}
 rivers=mask+n;dist=(U*)(mask+n*2);
 ret=terrain(s,generator);if(!(ret&255))goto done;
 grid=R(map,0x28);
 if(kind)make_shape_mask(mask,w,h,s->seed,kind);
 /* A shaped coastline supplements the native lakes; it does not replace
  * them. Both are outlets, so a river stops at its first water body. */
 for(i=0;i<n;i++)if(!kind||(R(grid+i*0x30,0x20)&0x170)==0x120)
  mask[i]=(R(grid+i*0x30,0x20)&0x170)==0x120;
 {RiverRelief relief;U bh=R(world,0x34),dh=R(world,0x38);relief.base=(float*)R(bh,0x40);relief.delta=(float*)R(dh,0x40);relief.width=R(bh,0xc);relief.height=R(bh,0x10);relief.shift=R(bh,0x14);relief.pad=R(bh,0x1c);
  s->rivers=river_paths_relief(rivers,mask,w,h,s->seed,requested,&relief);
  if(s->rivers)river_fill_depressions(rivers,mask,w,h,&relief,dist);}
 /* Keep native bog/quicksand cutout surfaces away from open river water.
  * Record a small bank strip now, before transition painting changes IDs. */
 for(i=0;i<n;i++)dist[i]=0;
 for(y=1;y+1<h;y++)for(x=1;x+1<w;x++){U v=R(grid+(y*w+x)*0x30,0),b=(U)climate;W*name=v?(W*)R(v,8):0;int rx,ry,near=0;
  i=y*w+x;if(rivers[i]||!river_bad_shore(name))continue;
  for(ry=(int)y-4;ry<=(int)y+4&&!near;ry++)for(rx=(int)x-4;rx<=(int)x+4;rx++){int dx=rx-(int)x,dy=ry-(int)y;if(rx>=0&&ry>=0&&rx<(int)w&&ry<(int)h&&dx*dx+dy*dy<=16&&rivers[ry*w+rx]){near=1;break;}}
  if(!near)continue;if(prefix(name,"arctic_"))b=1;else if(prefix(name,"desert_"))b=2;else if(prefix(name,"cursed_"))b=3;else if(prefix(name,"temperate_"))b=0;dist[i]=b+1;
 }
 if(s->rivers){s->riverPlan=((U(*)(U))(s->image+0x2ef03c))(n);if(!s->riverPlan){s->result=4;ret=0;goto done;}s->riverPlanSize=n;for(i=0;i<n;i++)((unsigned char*)s->riverPlan)[i]=rivers[i];}
 for(i=0;i<n;i++){s->riverCells+=rivers[i];mask[i]|=rivers[i];}
 s->hash=2166136261U;s->water=0;
 for(i=0;i<n;i++){s->hash=(s->hash^mask[i])*16777619U;s->water+=mask[i];}
 s->land=n-s->water;
 s->phase=2;
 for(i=0;i<8;i++)ctx[i]=0;
 invoke(s,0x2517a3,(U)ctx,0,0,0,0,0);
 for(y=0;y<h;y++)for(x=0;x<w;x++)if(kind?mask[y*w+x]:rivers[y*w+x]){
  U v=R(grid+(y*w+x)*0x30,0),b=(U)climate;W*name=v?(W*)R(v,8):0;
  if((prefix(name,"arctic_")||prefix(name,"paws_river_arctic")))b=1;else if((prefix(name,"desert_")||prefix(name,"paws_river_desert")))b=2;else if((prefix(name,"cursed_")||prefix(name,"paws_river_cursed")))b=3;else if(prefix(name,"temperate_"))b=0;
  point[0]=x;point[1]=y;invoke(s,0x2517f9,(U)ctx,2,(U)point,rivers[y*w+x]?riverWaters[b]:waters[b],0,0);
 }
 invoke(s,0x25185b,(U)ctx,1,0,0,0,0);
 invoke(s,0x20d4b,(U)(ctx+3),0,0,0,0,0);invoke(s,0x20d4b,(U)(ctx+5),0,0,0,0,0);
 /* Native cross-biome transition resolution can replace part of an explicit
    water stroke with dry shore. Keep its outer banks, but restore every
    requested river cell with the native cell setter before depth/path caches
    and water bodies are built. No dry fords are introduced into a river. */
 grid=R(map,0x28);
 {U banks[4];banks[0]=find(s,"temperate_grass01");banks[1]=find(s,"arctic_snow01");banks[2]=find(s,"desert_sand01");banks[3]=find(s,"cursed_grass01");
  for(i=0;i<n;i++)if(dist[i]&&banks[dist[i]-1]){U changes[4]={0,0,0,0};invoke(s,0x24a522,grid+i*0x30,3,banks[dist[i]-1],0,(U)changes,0);}
 }
 for(i=0;i<n;i++)if(rivers[i]&&((R(grid+i*0x30,0x20)&0x70)!=0x20||!(R(grid+i*0x30,0x20)&0x100))){
  U cell=grid+i*0x30,v=R(cell,0),b=(U)climate;W*name=v?(W*)R(v,8):0;U changes[4];
  if((prefix(name,"arctic_")||prefix(name,"paws_river_arctic")))b=1;else if((prefix(name,"desert_")||prefix(name,"paws_river_desert")))b=2;else if((prefix(name,"cursed_")||prefix(name,"paws_river_cursed")))b=3;else if(prefix(name,"temperate_"))b=0;
  changes[0]=changes[1]=changes[2]=changes[3]=0;
  invoke(s,0x24a522,cell,3,riverWaters[b],0,(U)changes,0);s->riverRepairs++;
 }
 for(i=0;i<n;i++)if(rivers[i]&&((R(grid+i*0x30,0x20)&0x70)!=0x20||!(R(grid+i*0x30,0x20)&0x100)))s->riverGaps++;
 if(s->riverGaps){s->result=7;ret=0;goto done;}
 s->phase=3;grid=R(map,0x28);
 /* Native transitions may widen banks. Use actual wet cells for bed depth.
    Classic maps retain their original terrain deformation outside new rivers. */
 for(i=0;i<n;i++){mask[i]=(R(grid+i*0x30,0x20)&0x70)==0x20;dist[i]=mask[i]?10000:0;}
 for(y=0;y<h;y++)for(x=0;x<w;x++){i=y*w+x;if(x&&dist[i]>dist[i-1]+1)dist[i]=dist[i-1]+1;if(y&&dist[i]>dist[i-w]+1)dist[i]=dist[i-w]+1;}
 for(y=h;y-->0;)for(x=w;x-->0;){i=y*w+x;if(x+1<w&&dist[i]>dist[i+1]+1)dist[i]=dist[i+1]+1;if(y+1<h&&dist[i]>dist[i+w]+1)dist[i]=dist[i+w]+1;}
 hm=R(world,0x38);basehm=R(world,0x34);hw=R(hm,0xc);hh=R(hm,0x10);shift=R(hm,0x14);pad=R(hm,0x1c);
 if(hw>2049||hh>2049||shift>4||R(basehm,0xc)!=hw||R(basehm,0x10)!=hh||R(basehm,0x14)!=shift||R(basehm,0x1c)!=pad){s->result=5;ret=0;goto done;}
 for(y=0;y<hh;y++)for(x=0;x<hw;x++){
  xx=((int)(x<<shift)-(int)pad)/2;yy=((int)(y<<shift)-(int)pad)/2;
  if(xx<0)xx=0;if(yy<0)yy=0;if(xx>=(int)w)xx=w-1;if(yy>=(int)h)yy=h-1;
  nearest=(int)dist[yy*w+xx];d=nearest>6?6:nearest;
  if(!d)continue; /* Preserve installed native hills/mountains on dry land. */
  if(!kind){int rx,ry,touched=0;for(ry=yy-1;ry<=yy+1&&!touched;ry++)for(rx=xx-1;rx<=xx+1;rx++)if(rx>=0&&ry>=0&&rx<(int)w&&ry<(int)h&&rivers[ry*w+rx]){touched=1;break;}if(!touched||!d)continue;}
  z.f=-.25f-(float)d*.25f;if(z.f< -1.5f)z.f=-1.5f;
  /* +38 is the deformation layer, added to the base heights at +34.
     Native temperate land starts at +2, so subtract that base for wet
     vertices; otherwise narrow rivers never reach the water plane at zero. */
  if(d)z.f-=((float*)R(basehm,0x40))[y*hw+x];
  invoke(s,0x2f95f8,hm,4,x,y,z.u,0);s->heights++;
 }
 s->phase=4;
 for(y=1;y+1<h;y++)for(x=1;x+1<w;x++){
  i=y*w+x;if(!mask[i]||B(grid+i*0x30,0x2c))continue;
  body=invoke(s,0x24f6b0,map,0,0,0,0,0)&255;if(!body){s->result=6;ret=0;goto done;}
  invoke(s,0x25fe70,R(world,0x248),3,x,y,R(R(map,0x50),body*4),0);s->bodies++;
 }
 s->phase=5;finish_river_bed(s);s->result=0;ret=1;
 done:((void(*)(void*))(s->image+0x2ef05f))(mask);return ret&255;
}
__attribute__((dllexport)) U generate_after_noise(State*s,U generator){U result;s->afterNoise=1;result=generate(s,generator);s->afterNoise=0;return result;}
/* The stock placement gate only accepts the largest connected land island.
   Rivers split that island, so kingdoms and neutral cities otherwise all
   collect on one side. Relax ONLY this RMG gate; native footprint, water,
   slope, spacing and actor checks still run, and real navigation is intact. */
__attribute__((dllexport)) U placement_island(State*s,U cell,U original){U analysis,primary;
 if(!s||!cell||s->world!=R(s->image,0x5f3fb8)||s->phase!=5||(!s->shape&&!s->rivers))return original;
 if(!R(cell,0x10)||(R(cell,0x20)&0x100)||(R(cell,0x20)&0x70)==0x20)return original;
 analysis=R(s->image,0x5f3fcc);primary=analysis?R(analysis,0x2c):0;if(!primary)return original;
 if(original!=R(primary,0)){s->placementOverrides++;return R(primary,0);}return original;
}

/* Every vertex of a river quad must be below the water plane. The native
 * beautification stage can otherwise leave individual high corners protruding. */
__attribute__((dllexport)) U finish_river_bed(State*s){U map,grid,hm,base,w,h,hw,hh,shift,pad,x,y;int xx,yy,dx,dy;union{float f;U u;}z;
 if(!s||s->phase!=5||!s->rivers||!s->riverPlan||s->world!=R(s->image,0x5f3fb8))return 0;
 map=R(s->world,0x30);w=R(map,0x1c);h=R(map,0x20);if(w*h!=s->riverPlanSize)return 0;grid=R(map,0x28);
 hm=R(s->world,0x38);base=R(s->world,0x34);hw=R(hm,0xc);hh=R(hm,0x10);shift=R(hm,0x14);pad=R(hm,0x1c);s->bedRepairs=0;
 if(hw>2049||hh>2049||shift>4||R(base,0xc)!=hw||R(base,0x10)!=hh)return 0;
 for(y=0;y<hh;y++)for(x=0;x<hw;x++){int river=0,wet=0,total=0,vx=(int)(x<<shift)-(int)pad,vy=(int)(y<<shift)-(int)pad,step=1<<shift;float target,current,near=10000,dry=10000;
  xx=(vx-step)/2;yy=(vy-step)/2;
  for(dy=yy;dy<=(vy+step-1)/2;dy++)for(dx=xx;dx<=(vx+step-1)/2;dx++){U i;if(dx<0||dy<0||dx>=(int)w||dy>=(int)h)continue;i=dy*w+dx;river|=((unsigned char*)s->riverPlan)[i];wet+=((R(grid+i*0x30,0x20)&0x70)==0x20);total++;}
  /* A short dry-bank blend replaces the vertical two-unit shelf. Only the
   * requested river and its immediate banks are touched, not distant hills. */
  for(dy=vy/2-3;dy<=vy/2+3;dy++)for(dx=vx/2-3;dx<=vx/2+3;dx++){
   U i;float a,b,d;if(dx<0||dy<0||dx>=(int)w||dy>=(int)h)continue;i=dy*w+dx;
   a=(float)(dx*2+1-vx);b=(float)(dy*2+1-vy);d=a*a+b*b;
   if(((unsigned char*)s->riverPlan)[i]&&d<near)near=d;
   if((R(grid+i*0x30,0x20)&0x70)!=0x20&&d<dry)dry=d;
  }
  if(!river&&near>36)continue;
  current=((float*)R(base,0x40))[y*hw+x]+((float*)R(hm,0x40))[y*hw+x];
  if(river){target=wet==total?-.45f-.03f*dry:-.12f;if(target< -1.5f)target=-1.5f;}
  else{float blend=(near-2)/34;if(wet||current<0||current>8)continue;if(blend<0)blend=0;if(blend>1)blend=1;blend=blend*blend*(3-2*blend);target=.15f+1.85f*blend;if(current<=target)continue;}
  if(current>target+.0001f||(river&&current<target-.0001f)){z.f=target-((float*)R(base,0x40))[y*hw+x];invoke(s,0x2f95f8,hm,4,x,y,z.u,0);s->bedRepairs++;}
 }return s->bedRepairs;
}
