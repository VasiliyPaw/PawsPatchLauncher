/* Split the final native requested camp total, after restored settings and
 * hidden-slider randomization. No RNG, allocation, commands or save writes. */
typedef unsigned int U;
typedef unsigned short W;
#define P(a,o) (*(U*)((U)(a)+(o)))
#define F(a,o) (*(float*)((U)(a)+(o)))
int __attribute__((stdcall)) _dllstart(void*a,U b,void*c){return 1;}
typedef float (__attribute__((fastcall)) *Scale)(U,U,float);
static int finite(float n){return (*(U*)&n&0x7f800000)!=0x7f800000;}
static int trunc_count(float f){int i;__asm__ volatile(".byte 0xf3,0x0f,0x2c,0x00":"=a"(i):"a"(&f));return i;}
static int equal(U str,const char*s){
 U i;if(!str)return 0;
 for(i=0;i<64;i++){W c=*(W*)(str+2*i);if(c!=(unsigned char)s[i])return 0;if(!c)return 1;}return 0;
}
static U find_value(U creator,const char*id){
 U a=P(creator,0x64),n=P(creator,0x68),i;
 if(!a||n>1024)return 0;
 for(i=0;i<n;i++)if(equal(P(a,i*8),id))return a+i*8;
 return 0;
}
static U find_group(U profile,const char*id){
 U a=P(profile,0x74),n=P(profile,0x78),i;
 if(!a||n>256)return 0;
 for(i=0;i<n;i++){U g=P(a,i*4);if(g&&equal(P(g,8),id))return g;}
 return 0;
}
__attribute__((dllexport)) U split_count(U image,U balancer,U original){
 U group=P(balancer,8),ctx=P(balancer,4),creator,profile,s,f,sv,fv,total,foundations,is_foundation;
 float scale,sd,fd;volatile float scaled_s,scaled_f;
 if(!group||!ctx)return original;
 is_foundation=equal(P(group,8),"random_foundationcamps");
 if(!is_foundation&&!equal(P(group,8),"random_settlementcamps"))return original;
 creator=P(ctx,0);if(!creator||P(creator,0)!=image+0x4fdf7c)return original;
 profile=P(creator,0x50);if(!profile)return original;
 s=find_group(profile,"random_settlementcamps");f=find_group(profile,"random_foundationcamps");
 if(!s||!f||(group!=s&&group!=f)||!*(unsigned char*)(s+0x58)||!*(unsigned char*)(f+0x58))return original;
 if(!finite(F(s,0x20))||F(s,0x20)<0||F(s,0x20)>4||F(s,0x20)!=F(f,0x20))return original;
 sv=find_value(creator,"random_settlementcamps");fv=find_value(creator,"random_foundationcamps");
 if(!sv||!fv)return original;sd=F(sv,4);fd=F(fv,4);
 if(!finite(sd)||!finite(fd)||sd<0||fd<0||sd>256||fd>256)return original;
 scale=((Scale)(image+0x255e1c))(ctx,0,F(s,0x20));
 if(!finite(scale)||scale<=0||scale>1024)return original;
 scaled_s=sd*scale;scaled_f=fd*scale;
 if(!finite(scaled_s)||!finite(scaled_f)||scaled_s>4096||scaled_f>4096)return original;
 /* Reproduce the two native truncations, then round the foundation share
  * to its nearest integer. The complementary settlement count keeps the
  * total exact and makes the result independent of group placement order. */
 total=trunc_count(scaled_s)+trunc_count(scaled_f);foundations=(total+2)/5;
 return is_foundation?foundations:total-foundations;
}
#include "final.c"
