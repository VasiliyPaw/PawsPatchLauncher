#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "shapes.h"
int main(void){int w=256,n=w*w,i,s,changed=0,same=0,before=0,after=0,gorges=0,islands=0;unsigned char*a=malloc(n),*b=malloc(n),*seen=malloc(n);int*queue=malloc(n*sizeof(int));float*flat=malloc(n*sizeof(float)),*hill=malloc(n*sizeof(float));RiverRelief q={flat,0,256,256,1,-1},r={hill,0,256,256,1,-1};
 if(!a||!b||!seen||!queue||!flat||!hill)return 1;
 for(i=0;i<n;i++){int x=i%w-128,y=i/w-128;flat[i]=2;hill[i]=x*x+y*y<34*34?30:2;}
 for(s=0;s<128;s++){int old=0,now=0,head=0,tail=0,dry=0;
  if(river_paths_relief(a,0,w,w,mix(s),1,&q)!=1||river_paths_relief(b,0,w,w,mix(s),1,&r)!=1)return 2;
  for(i=0;i<n;i++)if(hill[i]>2){old+=a[i];now+=b[i];}before+=old;after+=now;
  if(memcmp(a,b,n))changed++;else{same++;if(old)gorges++;}
  memset(seen,0,n);for(i=0;i<n;i++)if(!a[i]){dry++;if(i%w==0||i%w==w-1||i/w==0||i/w==w-1){seen[i]=1;queue[tail++]=i;}}
  while(head<tail){int c=queue[head++],x=c%w,y=c/w,k,near[4]={c-1,c+1,c-w,c+w};for(k=0;k<4;k++){int v=near[k];if((k==0&&x==0)||(k==1&&x==w-1)||(k==2&&y==0)||(k==3&&y==w-1)||seen[v]||a[v])continue;seen[v]=1;queue[tail++]=v;}}
  if(dry-tail>12)islands++;
 }
 printf("RIVER_RELIEF_PASS 128 seeds: alternative bends=%d unchanged=%d preserved gorges=%d mountain cells=%d->%d rare braided islands=%d\n",changed,same,gorges,before,after,islands);
 if(changed<8||same<32||gorges<4||after>=before*9/10||islands<3||islands>50)return 3;
 free(a);free(b);free(seen);free(queue);free(flat);free(hill);return 0;
}
