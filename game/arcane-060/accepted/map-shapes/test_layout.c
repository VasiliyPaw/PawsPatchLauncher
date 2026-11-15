#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "shapes.h"
/* Four-way connectivity, including a two-cell bank margin for whole companies. */
static int connected(unsigned char *m,int w,int h,int margin) {
 int n=w*h,x,y,dx,dy,i,start=-1,land=0,head=0,tail=0;
 unsigned char *ok=calloc(n,1);int *q=malloc(n*sizeof(int));
 for(y=0;y<h;y++)for(x=0;x<w;x++)if(!m[y*w+x]){
  int good=1;
  for(dy=-margin;dy<=margin&&good;dy++)for(dx=-margin;dx<=margin;dx++)
   if(x+dx>=0&&x+dx<w&&y+dy>=0&&y+dy<h&&m[(y+dy)*w+x+dx]){good=0;break;}
  if(good){ok[y*w+x]=1;start=y*w+x;land++;}
 }
 if(start>=0){q[tail++]=start;ok[start]=0;}
 while(head<tail){i=q[head++];x=i%w;y=i/w;
  if(x&&ok[i-1]){ok[i-1]=0;q[tail++]=i-1;}
  if(x+1<w&&ok[i+1]){ok[i+1]=0;q[tail++]=i+1;}
  if(y&&ok[i-w]){ok[i-w]=0;q[tail++]=i-w;}
  if(y+1<h&&ok[i+w]){ok[i+w]=0;q[tail++]=i+w;}
 }
 /* Eroding a diagonal shore can leave a few isolated shore pixels: require
    all original land, and >99.99% of land with full company bank clearance. */
 i=(margin?(long long)tail*10000>=(long long)land*9999:land==tail)&&land>n/4;
 if(!i)printf("margin=%d reached=%d land=%d\n",margin,tail,land);
 free(ok);free(q);return i;
}
int main(void) {
 int sizes[]={192,256,352,384,512},s,k,j,n,i,wet,checks=0;
 {int seen[3]={0,0,0},seed;for(seed=0;seed<128;seed++){U actual=shape_choice(3,(U)seed);if(actual>2||shape_choice(3,(U)seed)!=actual)return 20;seen[actual]++;checks++;}if(!seen[0]||!seen[1]||!seen[2])return 21;for(seed=0;seed<3;seed++)if(shape_choice(seed,123)!=(U)seed)return 22;}
 unsigned char *m=malloc(512*512),*copy=malloc(512*512);
 for(s=0;s<5;s++)for(k=1;k<=2;k++)for(j=0;j<128;j++){
  U seed=mix((U)j);n=sizes[s]*sizes[s];
  if(!make_mask(m,sizes[s],sizes[s],seed,k))return 1;
  memcpy(copy,m,n);make_mask(m,sizes[s],sizes[s],seed,k);
  if(memcmp(m,copy,n))return 2;
  for(wet=0,i=0;i<n;i++)wet+=m[i];
  if(wet<n/40||wet>n*3/4){printf("Bad ratio %d %d %u %d\n",sizes[s],k,seed,wet);return 3;}
  if(!connected(m,sizes[s],sizes[s],0)||!connected(m,sizes[s],sizes[s],2)){
   printf("Disconnected %d %d %u\n",sizes[s],k,seed);return 4;
  }
  checks+=4;
 }
 printf("%d PASS: deterministic layouts, water ratio, all land connected, >99.99%% at 2-cell clearance\n",checks);
 free(m);free(copy);return 0;
}
