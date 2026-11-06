/* Seeded, normalized geometry. No engine RNG, imports, or mutable globals.
   Sites cover the whole map; one starts inside it, rather than in a corner.
   Two smooth shears bend borders without scattering independent tiny patches. */
typedef struct {U seed,n;int x[7],y[7];U biome[7];} Layout;
static U hash(U v){v^=v>>16;v*=0x7feb352d;v^=v>>15;v*=0x846ca68b;return v^(v>>16);}
static int noise(int p,U seed,int scale){
 int cell=p/scale,t=p%scale,a,b;
 if(t<0){t+=scale;cell--;}
 a=(int)(hash(seed+(U)cell*0x9e3779b9)%201)-100;
 b=(int)(hash(seed+(U)(cell+1)*0x9e3779b9)%201)-100;
 t=t*1024/scale;t=t*t/1024*(3072-2*t)/1024;
 return a+(b-a)*t/1024;
}
static U classify(Layout*l,int x,int y,U w,U h){
 U k,best=0;int dx,dy,d,minimum=0x7fffffff;
 x=(x*1024+512)/(int)w;y=(y*1024+512)/(int)h;
 x+=noise(y,l->seed+81,320)*140/100+noise(y,l->seed+92,115)*35/100;
 y+=noise(x,l->seed+17,360)*140/100+noise(x,l->seed+36,130)*35/100;
 for(k=0;k<l->n;k++){
  dx=x-l->x[k];dy=y-l->y[k];d=dx*dx+dy*dy;
  if(d<minimum){minimum=d;best=k;}
 }
 return l->biome[best];
}
static void layout(Layout*l,U seed){
 U attempt,k,j,c,v,perm[4],counts[4],head,tail,start,next,good;
 unsigned char grid[1024];unsigned short queue[1024];
 int x,y,dx,dy,d,near,best,bx,by;
 for(attempt=0;attempt<16;attempt++){
  l->seed=hash(seed+attempt*0x9e3779b9);l->n=attempt==15?4:5+hash(l->seed+9)%3;
  for(k=0;k<4;k++)perm[k]=k;
  for(k=3;k;k--){j=hash(l->seed+k)%(k+1);v=perm[k];perm[k]=perm[j];perm[j]=v;}
  v=hash(l->seed+101);l->x[0]=300+v%425;l->y[0]=300+(v>>12)%425;
  for(k=1;k<l->n;k++){
   best=-1;bx=by=0;
   for(c=0;c<24;c++){
    v=hash(l->seed+k*281+c*619);x=32+v%897;y=32+(v>>12)%897;near=0x7fffffff;
    for(j=0;j<k;j++){dx=x-l->x[j];dy=y-l->y[j];d=dx*dx+dy*dy;if(d<near)near=d;}
    if(near>best){best=near;bx=x;by=y;}
   }
   l->x[k]=bx;l->y[k]=by;
  }
  for(k=0;k<l->n;k++)l->biome[k]=perm[k<4?k:(hash(l->seed+k*997)%4)];
  for(k=0;k<4;k++)counts[k]=0;
  for(y=0;y<32;y++)for(x=0;x<32;x++)counts[classify(l,x,y,32,32)]++;
  if(counts[0]<96||counts[1]<96||counts[2]<96||counts[3]<96)continue;
  /* Reject layouts with small detached areas on a coarse topology grid.
     Four-connected flood fill, no heap or engine calls. */
  for(y=0;y<32;y++)for(x=0;x<32;x++)grid[y*32+x]=(unsigned char)classify(l,x,y,32,32);
  good=1;
  for(start=0;start<1024&&good;start++){
   if(grid[start]==255)continue;
   v=grid[start];head=0;tail=1;queue[0]=(unsigned short)start;grid[start]=255;
   while(head<tail){
    k=queue[head++];x=k%32;y=k/32;
    for(j=0;j<4;j++){
     next=j==0?(x?k-1:1024):j==1?(x<31?k+1:1024):j==2?(y?k-32:1024):(y<31?k+32:1024);
     if(next<1024&&grid[next]==v){grid[next]=255;queue[tail++]=(unsigned short)next;}
    }
   }
   if(tail<16)good=0;
  }
  if(good)break;
 }
}
__attribute__((dllexport)) U region(int x,int y,U w,U h,U seed){Layout l;layout(&l,seed);return classify(&l,x,y,w,h);}
__attribute__((dllexport)) void init_layout(Layout*l,U seed){layout(l,seed);}
__attribute__((dllexport)) U at_layout(Layout*l,int x,int y,U w,U h){return classify(l,x,y,w,h);}
