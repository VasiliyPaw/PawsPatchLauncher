#include <stdio.h>
#include <math.h>
#include "water_mix_math.h"
static unsigned rng=12345;
static float next(void){rng=rng*1664525u+1013904223u;return (float)(rng&65535)/65535;}
int main(void){unsigned t,k,j,n;for(t=0;t<10000;t++){
 float w[10],a[10],rgb[10][3],sum=0,target[4]={0},out[4]={0};n=2+t%9;
 for(k=0;k<n;k++){w[k]=next();a[k]=(t%17==0)?1:next();sum+=w[k];for(j=0;j<3;j++)rgb[k][j]=next();}
 for(k=0;k<n;k++){w[k]/=sum;target[3]+=w[k]*a[k];for(j=0;j<3;j++)target[j]+=w[k]*a[k]*rgb[k][j];}
 for(k=0;k<n;k++){float alpha=water_layer_alpha(w,a,n,k);if(!(alpha>=0&&alpha<=1.0001))return 1;for(j=0;j<3;j++)out[j]=out[j]*(1-alpha)+rgb[k][j]*alpha;out[3]=out[3]*(1-alpha)+alpha;}
 for(j=0;j<4;j++)if(fabs(out[j]-target[j])>.00002)return 2;
 }puts("10000 compiled opacity and premultiplied RGB conservation cases PASS");return 0;}
