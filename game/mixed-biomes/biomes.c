/* Local experimental Kohan II 1.3.72 generator. Engine addresses are RVAs.
   Region partition uses only the saved creator seed; never the runtime RNG. */
typedef unsigned int U;
typedef unsigned short W;
#define R(p,o) (*(U*)((U)(p)+(o)))
typedef U (*Call)(U,U,U,U*);
#include "regions.h"
typedef struct {U image,call,trampoline,world,seed,width,height,active,result,runs,painted,rejected,accepted,missing;U regions[4];Layout geom;
 unsigned char cells[1048576],seen[1048576];U queue[1048576];} State;
#include "spawn-index.h"
int __attribute__((stdcall)) _dllstart(void*m,U r,void*u){return 1;}
static int eq(W*w,char*a){int i;if(!w)return 0;for(i=0;a[i]&&i<160;i++)if(w[i]!=(unsigned char)a[i])return 0;return !a[i]&&!w[i];}
static int starts(W*w,char*a){int i;if(!w)return 0;for(i=0;a[i];i++)if(w[i]!=(unsigned char)a[i])return 0;return 1;}
static U invoke(State*s,U rva,U self,U n,U a,U b,U c,U d){U args[4];args[0]=a;args[1]=b;args[2]=c;args[3]=d;return ((Call)s->call)(s->image+rva,self,n,args);}
static U find(State*s,char*id){U mgr=R(s->image,0x5f0030),i,p;if(!mgr||R(mgr,0x28)>8192)return 0;for(i=0;i<R(mgr,0x28);i++){p=R(R(mgr,0x24),4*i);if(p&&eq((W*)R(p,8),id))return p;}return 0;}
static U kind(W*id){
 if(starts(id,"temperate_forest"))return 1;
 if(starts(id,"temperate_denseforest"))return 1;
 if(starts(id,"temperate_mountainpeak"))return 3;
 if(starts(id,"temperate_mountain"))return 2;
 if(starts(id,"temperate_lake")||starts(id,"temperate_river"))return 4;
 if(starts(id,"temperate_marsh")||starts(id,"temperate_mist"))return 5;
 if(starts(id,"temperate_rough")||starts(id,"temperate_rocky"))return 6;
 if(starts(id,"temperate_road"))return 7;
 if(starts(id,"temperate_shore"))return 8;
 return 0;
}
static char* variations[4][9]={
 {"temperate_grass01","temperate_forestconiferous01","temperate_mountain01","temperate_mountainpeak01","temperate_lake01","temperate_marsh01","temperate_rough01","temperate_road01","temperate_shore01"},
 {"arctic_snow01","arctic_forest01","arctic_mountain01","arctic_mountainpeak01","arctic_lake01","arctic_snowswamp01","arctic_tundra01","arctic_road01","arctic_snow01"},
 {"desert_sand01","desert_forest01","desert_mountain01","desert_mountain01","desert_lake01","desert_quicksand01","desert_scrub01","desert_road01","desert_shore01"},
 {"cursed_grass01","cursed_darkforest01","cursed_mountain01","cursed_mountainpeak01","cursed_lake01","cursed_marsh01","cursed_rough01","cursed_road01","cursed_shore01"}};
/* Cache the authoritative terrain/spawn partition once. Absorb detached
   components below one percent into a neighbour, keeping broad regions.
   Scratch storage is part of the private RW allocation, not the game heap. */
__attribute__((dllexport)) void prepare_regions(State*s,U w,U h,U seed){
 U x,y,i,j,k,n=w*h,pass,head,tail,b,next,start,border[4],replacement,changed;
 s->width=w;s->height=h;s->seed=seed;layout(&s->geom,seed);
 for(y=0;y<h;y++)for(x=0;x<w;x++)s->cells[y*w+x]=(unsigned char)classify(&s->geom,x,y,w,h);
 for(pass=0;pass<4;pass++){
  for(i=0;i<n;i++)s->seen[i]=0;
  changed=0;
  for(start=0;start<n;start++){
   if(s->seen[start])continue;
   b=s->cells[start];head=0;tail=1;s->queue[0]=start;s->seen[start]=1;
   for(i=0;i<4;i++)border[i]=0;
   while(head<tail){
    k=s->queue[head++];x=k%w;y=k/w;
    for(j=0;j<4;j++){
     next=j==0?(x?k-1:n):j==1?(x+1<w?k+1:n):j==2?(y?k-w:n):(y+1<h?k+w:n);
     if(next>=n)continue;
     if(s->cells[next]!=b){border[s->cells[next]]++;continue;}
     if(!s->seen[next]){s->seen[next]=1;s->queue[tail++]=next;}
    }
   }
   if(tail<n/100){
    replacement=0;for(i=1;i<4;i++)if(border[i]>border[replacement])replacement=i;
    if(border[replacement]){for(i=0;i<tail;i++)s->cells[s->queue[i]]=(unsigned char)replacement;changed++;}
   }
  }
  if(!changed)break;
 }
 for(b=0;b<4;b++)s->regions[b]=0;
 for(i=0;i<n;i++)s->regions[s->cells[i]]++;
}
/* Only the creator's private copy is changed, after terrain paint and before
   object placement. The lobby's saved common slider values are untouched.
   Actor settings are native (TGCString,float) pairs at creator+64/+68. */
__attribute__((dllexport)) void shared_groups(State*s,U creator){
 U items=R(creator,0x64),n=R(creator,0x68),i,k,b;float value[3];W*id;
 char*ids[3][4]={
  {"random_monsterlairtemperatecamps","random_monsterlairarcticcamps","random_monsterlairdesertcamps","random_monsterlaircursedcamps"},
  {"random_monsterlargelairtemperatecamps","random_monsterlargelairarcticcamps","random_monsterlargelairdesertcamps","random_monsterlargelaircursedcamps"},
  {"random_techlairtemperatecamps","random_techlairarcticcamps","random_techlairdesertcamps","random_techlaircursedcamps"}};
 if(n>256||!items||!s->width||!s->height)return;
 for(k=0;k<3;k++){
  value[k]=-1;
  for(i=0;i<n;i++)if(eq((W*)R(items,i*8),ids[k][0])){value[k]=*(float*)(items+i*8+4);break;}
 }
 for(i=0;i<n;i++){
  id=(W*)R(items,i*8);
  for(k=0;k<3;k++)if(value[k]>=0)for(b=0;b<4;b++)if(eq(id,ids[k][b]))
   *(float*)(items+i*8+4)=value[k]*(float)s->regions[b]/(float)(s->width*s->height);
 }
}
__attribute__((dllexport)) U generate(State*s,U gen){
 U creator=R(gen,0),rmc=creator?R(creator,0x50):0,world,map,w,h,grid,x,y,k,b,v,ctx[8],point[2],table[4][9];U ret;
 s->active=0;
 if(!rmc||!eq((W*)R(rmc,8),"paws_mixed_biomes"))return invoke(s,0x256f19,gen,0,0,0,0,0);
 s->result=1;s->missing=0;s->painted=0;s->rejected=0;s->accepted=0;s->runs++;
 world=R(s->image,0x5f3fb8);if(!world)return 0;map=R(world,0x30);if(!map)return 0;
 w=R(map,0x1c);h=R(map,0x20);if(w<32||h<32||w>1024||h>1024){s->result=2;return 0;}
 for(b=0;b<4;b++)for(k=0;k<9;k++){table[b][k]=find(s,variations[b][k]);if(!table[b][k])s->missing++;}
 if(s->missing){s->result=3;return 0;}
 ret=invoke(s,0x256f19,gen,0,0,0,0,0);if(!(ret&255)){s->result=4;return ret;}
 s->world=world;s->seed=R(creator,0x4c);s->width=w;s->height=h;
 prepare_regions(s,w,h,s->seed);
 grid=R(map,0x28);
 for(k=0;k<8;k++)ctx[k]=0;
 invoke(s,0x2517a3,(U)ctx,0,0,0,0,0);
 for(y=0;y<h;y++)for(x=0;x<w;x++){
  b=s->cells[y*w+x];if(!b)continue;
  v=R(grid+(y*w+x)*0x30,0);if(!v)continue;k=kind((W*)R(v,8));
  point[0]=x;point[1]=y;invoke(s,0x2517f9,(U)ctx,2,(U)point,table[b][k],0,0);s->painted++;
 }
 invoke(s,0x25185b,(U)ctx,1,0,0,0,0);
 invoke(s,0x20d4b,(U)(ctx+3),0,0,0,0,0);invoke(s,0x20d4b,(U)(ctx+5),0,0,0,0,0);
 shared_groups(s,creator);
 s->active=1;s->result=0;return 1;
}
/* Called after a successful native placement check, using its final (possibly
   snapped or relocated) point. Retains native collisions and restrictions. */
__attribute__((dllexport)) U allowed(State*s,U object,float*point){
 U map,w,h,b,i,mask=15;W*id;
 if(!s->active||s->world!=R(s->image,0x5f3fb8)||!object||!point)return 1;
 map=R(s->world,0x30);w=R(map,0x1c);h=R(map,0x20);
 if(point[0]<0||point[1]<0||point[0]>=(float)(w*2)||point[1]>=(float)(h*2))return 1;
 b=s->cells[(int)(point[1]/2)*w+(int)(point[0]/2)];
 id=(W*)R(object,8);
 for(i=0;i<SPAWN_COUNT;i++)if(eq(id,spawn_ids[i])){mask=spawn_masks[i];break;}
 if(mask&(1<<b)){s->accepted++;return 1;}s->rejected++;return 0;
}
static int digit(W c){return c>='0'&&c<='9';}
/* Native list sort callback: pointers to item pointers; +c is its displayed
   string. Keep Custom before numbers, then compare numeric runs as numbers. */
__attribute__((dllexport)) int natural_compare(U*a,U*b){
 W*x=(W*)R(*a,12),*y=(W*)R(*b,12);U p=0,q=0,n,m,steps=0;
 if(!x||!y)return x?1:y?-1:0;
 if(digit(x[0])!=digit(y[0]))return digit(x[0])?1:-1;
 while(steps++<160&&(x[p]||y[q])){
  if(digit(x[p])&&digit(y[q])){
   n=0;m=0;
   while(digit(x[p])&&p<160){n=n<1000000?n*10+x[p]-'0':10000000;p++;}
   while(digit(y[q])&&q<160){m=m<1000000?m*10+y[q]-'0':10000000;q++;}
   if(n!=m)return n<m?-1:1;
  }else{if(x[p]!=y[q])return x[p]<y[q]?-1:1;p++;q++;}
 }
 return 0;
}
__attribute__((dllexport)) void sort_main(State*s,U scope){
 U list=R(scope,0x14),n,previous;
 if(!list)return;n=R(list,0x70);if(n<2||n>256)return;
 previous=R(list,0xc8);R(list,0xc8)=(U)natural_compare;
 invoke(s,0x2a1a12,list,0,0,0,0,0);R(list,0xc8)=previous;
}
