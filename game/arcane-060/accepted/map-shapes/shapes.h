/* Integer-only layout, independent of process pointers, clocks and simulation RNG. */
typedef unsigned int U;
static U mix(U x) { x^=x>>16; x*=0x7feb352dU; x^=x>>15; x*=0x846ca68bU; return x^(x>>16); }
static U shape_choice(U selected,U seed){return selected==3?mix(seed^0xd1b54a35U)%3:selected<=2?selected:0;}
static int ab(int x) { return x<0?-x:x; }
static int max(int a,int b) { return a>b?a:b; }
#include "rivers.h"
static int noise1(int t,U seed) {
    int k=t/128,r=t%128,a=(int)(mix(seed+(U)k)%1025)-512,b=(int)(mix(seed+(U)k+1)%1025)-512;
    /* Cubic interpolation with bounded 32-bit arithmetic. */
    r=r*r*(384-2*r)/16384;
    return (a*(128-r)+b*r)/128;
}
static int water_at(int x,int y,int w,int h,U seed,int kind) {
    int u=(x*2048+w)/(2*w),v=(y*2048+h)/(2*h),dx,dy,r,coast;
    /* Coordinates are [0,1024), with rotational variants chosen from the seed. */
    if(seed&1){int z=u;u=v;v=z;}
    if(seed&2)u=1023-u;
    if(seed&4)v=1023-v;
    if(kind<3) {
        dx=(u-512)*2;dy=(v-512)*2;
        coast=noise1(u,seed^0xf871ab31U)+noise1(v,seed^0x259c9719U);
        if(kind==1){r=dx*dx+dy*dy*110/100;return r>790000+coast*180;}
        r=dx*dx*80/100+dy*dy*125/100;
        return r<370000+coast*100;
    }
    return 0;
}
static int make_shape_mask(unsigned char *m,int w,int h,U seed,int kind) {
    int x,y;if(w<64||h<64||w>1024||h>1024||kind<1||kind>3)return 0;
    for(y=0;y<h;y++)for(x=0;x<w;x++)m[y*w+x]=(unsigned char)water_at(x,y,w,h,seed,kind);
    /* Eliminate single-cell diagonal pockets at the tributary confluence. */
    for(y=1;y+1<h;y++)for(x=1;x+1<w;x++)
        if(!m[y*w+x]&&m[y*w+x-1]&&m[y*w+x+1]&&m[(y-1)*w+x]&&m[(y+1)*w+x])m[y*w+x]=1;
    return 1;
}
static int make_mask(unsigned char*m,int w,int h,U seed,int kind){
 if(!make_shape_mask(m,w,h,seed,kind))return 0;
 if(kind==3)river_paths(m,0,w,h,seed,-1);
 return 1;
}
