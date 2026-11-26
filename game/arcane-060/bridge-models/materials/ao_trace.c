/* Deterministic double-precision nearest-hit accelerator for the existing AO24
 * algorithm. Reads/writes task-owned binary files only. No game/GUI APIs. */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <stdint.h>

typedef struct { double a[3],e1[3],e2[3],lo[3],hi[3],center[3]; } Tri;
typedef struct { double lo[3],hi[3]; int left,right,start,count; } Node;
static Tri *tris;static Node *nodes;static int *indices,node_count,sort_axis;
static double min2(double a,double b){return a<b?a:b;}
static double max2(double a,double b){return a>b?a:b;}
static int cmp(const void *aa,const void *bb){
 int a=*(const int*)aa,b=*(const int*)bb;
 double d=tris[a].center[sort_axis]-tris[b].center[sort_axis];
 return d<0?-1:d>0?1:(a>b)-(a<b);
}
static int build(int start,int count){
 int id=node_count++,i,k,axis=0;Node*n=&nodes[id];
 n->start=start;n->count=count;n->left=n->right=-1;
 for(k=0;k<3;k++){n->lo[k]=HUGE_VAL;n->hi[k]=-HUGE_VAL;}
 for(i=start;i<start+count;i++)for(k=0;k<3;k++){
  Tri*t=&tris[indices[i]];if(t->lo[k]<n->lo[k])n->lo[k]=t->lo[k];if(t->hi[k]>n->hi[k])n->hi[k]=t->hi[k];
 }
 if(count<=8)return id;
 for(k=1;k<3;k++)if(n->hi[k]-n->lo[k]>n->hi[axis]-n->lo[axis])axis=k;
 sort_axis=axis;qsort(indices+start,count,sizeof(int),cmp);
 n->left=build(start,count/2);n->right=build(start+count/2,count-count/2);n->count=0;
 return id;
}
static void cross(const double*a,const double*b,double*c){
 c[0]=a[1]*b[2]-a[2]*b[1];c[1]=a[2]*b[0]-a[0]*b[2];c[2]=a[0]*b[1]-a[1]*b[0];
}
static double dot(const double*a,const double*b){return (a[0]*b[0]+a[1]*b[1])+a[2]*b[2];}
static int box(const Node*n,const double*o,const double*d,double limit){
 double low=.035,high=limit;int k;
 for(k=0;k<3;k++){
  if(fabs(d[k])<1e-18){if(o[k]<n->lo[k]-1e-8||o[k]>n->hi[k]+1e-8)return 0;}
  else{
   double a=(n->lo[k]-1e-8-o[k])/d[k],b=(n->hi[k]+1e-8-o[k])/d[k],tmp;
   if(a>b){tmp=a;a=b;b=tmp;}if(a>low)low=a;if(b<high)high=b;if(high<low)return 0;
  }
 }
 return 1;
}
static double nearest(const double*pos,const double*origin,const double*dir,double radius){
 int stack[128],top=0;double best=radius;int found=0;
 stack[top++]=0;
 while(top){
  Node*n=&nodes[stack[--top]];int i;
  if(!box(n,origin,dir,best))continue;
  if(!n->count){if(top>125)exit(20);stack[top++]=n->left;stack[top++]=n->right;continue;}
  for(i=n->start;i<n->start+n->count;i++){
   Tri*t=&tris[indices[i]];double dist[3],h[3],s[3],q[3],det,inv,u,v,hit;int k;
   for(k=0;k<3;k++){double a=t->lo[k]-pos[k],b=pos[k]-t->hi[k];dist[k]=a>b?a:b;if(dist[k]<0)dist[k]=0;}
   /* Exact prefilter of the original NumPy implementation, around pos. */
   if(dot(dist,dist)>=radius*radius)continue;
   cross(dir,t->e2,h);det=dot(t->e1,h);if(fabs(det)<=1e-8)continue;inv=1./det;
   for(k=0;k<3;k++)s[k]=origin[k]-t->a[k];
   u=inv*dot(s,h);if(u<0)continue;cross(s,t->e1,q);v=inv*dot(dir,q);
   if(v<0||u+v>1)continue;hit=inv*dot(t->e2,q);
   if(hit>.035&&hit<best){best=hit;found=1;}
  }
 }
 return found?best:HUGE_VAL;
}
static void read_exact(void*ptr,size_t size,size_t count,FILE*f){if(fread(ptr,size,count,f)!=count)exit(3);}
int main(int argc,char**argv){
 FILE*in,*out;char magic[4];uint32_t nt,nq,samples;double radius;uint32_t i,j,k;
 if(argc!=3)return 1;in=fopen(argv[1],"rb");if(!in)return 2;
 read_exact(magic,1,4,in);if(memcmp(magic,"AO24",4))return 4;
 read_exact(&nt,4,1,in);read_exact(&nq,4,1,in);read_exact(&samples,4,1,in);read_exact(&radius,8,1,in);
 if(!nt||nt>200000||nq>300000||samples!=24||radius!=2.4)return 5;
 tris=(Tri*)calloc(nt,sizeof(Tri));nodes=(Node*)calloc(nt*2,sizeof(Node));indices=(int*)malloc(nt*sizeof(int));if(!tris||!nodes||!indices)return 6;
 for(i=0;i<nt;i++){
  double v[9];Tri*t=&tris[i];read_exact(v,8,9,in);indices[i]=i;
  for(k=0;k<3;k++){t->a[k]=v[k];t->e1[k]=v[3+k]-v[k];t->e2[k]=v[6+k]-v[k];t->lo[k]=min2(v[k],min2(v[3+k],v[6+k]));t->hi[k]=max2(v[k],max2(v[3+k],v[6+k]));t->center[k]=(t->lo[k]+t->hi[k])*.5;}
 }
 build(0,nt);out=fopen(argv[2],"wb");if(!out)return 7;
 for(i=0;i<nq;i++){
  double pos[3],normal[3],origin[3],dirs[72],hits[24];
  read_exact(pos,8,3,in);read_exact(normal,8,3,in);read_exact(dirs,8,72,in);
  for(k=0;k<3;k++)origin[k]=pos[k]+normal[k]*.045;
  for(j=0;j<24;j++)hits[j]=nearest(pos,origin,dirs+j*3,radius);
  if(fwrite(hits,8,24,out)!=24)return 8;
 }
 if(fgetc(in)!=EOF)return 9;fclose(in);if(fclose(out))return 10;
 free(tris);free(nodes);free(indices);return 0;
}
