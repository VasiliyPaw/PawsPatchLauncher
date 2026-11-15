#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "shapes.h"
int main(void){int sizes[]={64,128,192,256,384,512,1024},s,j,k,n,c,r,wet,i,checks=0,seen[17],minx=1024,maxx=0,edge=0,inland=0;
 unsigned char*m=malloc(1024*1024+16),*copy=malloc(1024*1024),*sea=malloc(1024*1024);if(!m||!copy||!sea)return 1;
 for(s=0;s<7;s++){
  n=sizes[s]*sizes[s];memset(seen,0,sizeof(seen));
  for(j=0;j<128;j++)for(k=0;k<4;k++){
   int selected=k==0?0:k==1?1:k==2?river_limit(sizes[s],sizes[s]):-1;U seed=mix((U)j);
   memset(m,0x6d,n+16);c=river_paths(m,0,sizes[s],sizes[s],seed,selected);memcpy(copy,m,n);
   r=river_paths(m,0,sizes[s],sizes[s],seed,selected);
   if(c!=r||memcmp(copy,m,n))return 2;checks++;
   if(c<0||c>river_limit(sizes[s],sizes[s]))return 3;checks++;
   if(selected<0)seen[c]=1;
   for(i=0,wet=0;i<n;i++){if(m[i]>1)return 4;wet+=m[i];}
   if((!c&&wet)||(c&&!wet)||wet>n/3)return 5;checks++;
   for(i=n;i<n+16;i++)if(m[i]!=0x6d)return 6;checks++;
   if(s==3&&k==1){long sum=0;int touches=0;for(i=0;i<n;i++)if(m[i]){sum+=i%sizes[s];if(i/sizes[s]==1||i/sizes[s]==sizes[s]-2||i%sizes[s]==1||i%sizes[s]==sizes[s]-2)touches=1;}
    i=(int)(sum/wet);if(i<minx)minx=i;if(i>maxx)maxx=i;if(touches)edge++;else inland++;
   }
  }
  for(i=0;i<=river_limit(sizes[s],sizes[s]);i++)if(!seen[i])return 7;checks++;
 }
 if(maxx-minx<70||edge<10||inland<10)return 8;
 /* Entire rivers must also occur in the outer quarters, not merely touch
  * an edge while every route's centre remains in the middle half. */
 if(minx>=32||maxx<=224)return 18;checks+=2;
 for(s=0;s<7;s++)for(j=0;j<64;j++)for(k=1;k<=2;k++){
  int size=sizes[s];U seed=mix((U)j);n=size*size;make_shape_mask(sea,size,size,seed,k);
  c=river_paths(m,sea,size,size,seed,1);if(c!=1)return 9;checks++;
  for(i=0,wet=0;i<n;i++){if(m[i]&&sea[i])return 10;wet+=m[i];}
  if(wet<8)return 11;checks++;
  c=river_paths(m,sea,size,size,seed,river_limit(size,size));if(c!=river_limit(size,size))return 12;checks++;
 }
 /* A single river cannot resume on the opposite side of a lake/sea.
  * Use a full-height water strip, with enough width to distinguish the
  * mouth from a course incorrectly continued beyond the far shore. */
 for(j=0;j<256;j++){
  int left=0,right=0;memset(sea,0,128*128);
  for(i=0;i<128*128;i++)if(i%128>=54&&i%128<=74)sea[i]=1;
  if(river_paths(m,sea,128,128,mix(j),1)!=1)return 19;checks++;
  for(i=0;i<128*128;i++)if(m[i]){if(sea[i])return 20;if(i%128<54)left++;else if(i%128>74)right++;}
  if((!left&&!right)||(left&&right))return 21;checks++;
 }
 memset(sea,1,64*64);if(river_paths(m,sea,64,64,123,1)!=0)return 13;checks++;
 /* A tributary detected four cells from the parent must physically reach it. */
 memset(m,0,64*64);memset(sea,0,64*64);for(i=5;i<59;i++)m[i*64+32]=1;
 river_join(m,sea,64,64,28,30,3,2);
 for(i=28;i<=32;i++)if(!m[30*64+i])return 14;checks+=5;
 /* A low connected dry channel becomes water; positive banks and an
  * existing lake remain barriers. Repeating the fill cannot widen it. */
 {float base[4096];U queue[4096];RiverRelief relief;for(i=0;i<4096;i++)base[i]=2;
  memset(m,0,4096);memset(sea,0,4096);m[30*64+30]=1;
  for(i=31;i<=40;i++)base[30*64+i]=-.5f;base[31*64+32]=base[32*64+32]=-.5f;sea[30*64+35]=1;
  relief.base=base;relief.delta=0;relief.width=relief.height=64;relief.shift=1;relief.pad=0;
  if(river_fill_depressions(m,sea,64,64,&relief,queue)!=6)return 15;checks++;
  if(!m[32*64+32]||m[30*64+35]||m[30*64+36]||m[29*64+32])return 16;checks+=4;
  if(river_fill_depressions(m,sea,64,64,&relief,queue))return 17;checks++;
 }
 printf("RIVERS_PASS %d checks: seeded paths, zero/max/random, every random count, bounds, inland endings and offset routes; centroids=%d..%d edge=%d inland=%d\n",checks,minx,maxx,edge,inland);
 free(m);free(copy);free(sea);return 0;
}
