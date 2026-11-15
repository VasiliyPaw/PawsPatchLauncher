/* Render-only feathering of adjacent native water materials. Nothing writes
 * terrain, water bodies, heights or navigation. Native shore polygons and
 * animated textures are retained. A foreign tile belongs to one source
 * chunk, avoiding doubled transparent surfaces at chunk boundaries. */
typedef float (__attribute__((fastcall)) *WaterFloor)(U,U,U,U);
static int water_points[4096*2];
static unsigned char water_seen[68*68];
static U water_build_busy;
static int water_integer(float f){int i;__asm__ volatile(".byte 0xf3,0x0f,0x2c,0x00":"=a"(i):"a"(&f));return i;}
static int water_slot(U def){
 const char*names[6]={"temperate_lake","arctic_lake","desert_lake","cursed_lake","temperate_river","arctic_river"};int i;
 if(!def)return -1;for(i=0;i<6;i++)if(eq((W*)R(def,8),(char*)names[i]))return i;return -1;
}
static U water_cell(U map,int x,int y){
 U c,v;if(x<0||y<0||x>=(int)R(map,0x1c)||y>=(int)R(map,0x20))return 0;
 c=R(map,0x28)+(y*R(map,0x1c)+x)*0x30;
 if((R(c,0x20)&0x170)!=0x120||!(v=R(c,0)))return 0;
 v=R(v,0x1c);return water_slot(v)>=0?v:0;
}
static int water_scope(State*s){U w=R(s->image,0x5f3fb8),session=R(s->image,0x5f3fe4);return w&&session&&!B(session,0x100)&&R(session,0xf0)==2&&R(w,0xd8)!=6;}
__attribute__((dllexport)) U water_build_blended(State*s,U self,U cells){
 int *points=water_points,minx,miny,maxx,maxy,x,y,dx,dy,xx,yy,cx,cy,ownerx,ownery;unsigned char *seen=water_seen;
 U world,map,view,chunk,ratio,ox,oy,n,i,count=0,foreign,vector[3],def;int slot;
 s->waterMeshes++;
 if(water_build_busy||!water_scope(s)||!self||!cells||!(n=R(cells,4))||n>1024||(slot=water_slot(def=R(self,8)))<0)goto original;
 world=R(s->image,0x5f3fb8);map=R(world,0x30);view=R(s->image,0x5f3fa8);chunk=R(self,0);
 if(!map||!view||!chunk||!R(view,0xb4)||!R(cells,0))goto original;
 ratio=R(view,0xa8)/R(view,0xb4);if(!ratio||ratio>64)goto original;
 ox=R(chunk,0xac)*ratio;oy=R(chunk,0xb0)*ratio;
 minx=(int)ox-1;miny=(int)oy-1;maxx=(int)(ox+ratio);maxy=(int)(oy+ratio);
 for(i=0;i<68*68;i++)seen[i]=0;
 for(i=0;i<n;i++){
  x=((int*)R(cells,0))[i*2]+ox;y=((int*)R(cells,0))[i*2+1]+oy;
  if(x<minx||x>maxx||y<miny||y>maxy)goto original;
  seen[(y-miny)*68+x-minx]=1;points[count*2]=x-ox;points[count*2+1]=y-oy;count++;
 }
 for(i=0;i<n;i++){
  cx=((int*)R(cells,0))[i*2]+ox;cy=((int*)R(cells,0))[i*2+1]+oy;
  for(dy=-1;dy<=1;dy++)for(dx=-1;dx<=1;dx++){
   x=cx+dx;y=cy+dy;if(x<minx||x>maxx||y<miny||y>maxy||seen[(y-miny)*68+x-minx])continue;
   foreign=water_cell(map,x,y);if(!foreign||foreign==def)continue;
   ownerx=ownery=-1;
   for(yy=y-1;yy<=y+1&&ownery<0;yy++)for(xx=x-1;xx<=x+1;xx++)if(water_cell(map,xx,yy)==def){ownerx=xx;ownery=yy;break;}
   if(ownerx<0||ownerx/(int)ratio!=(int)(ox/ratio)||ownery/(int)ratio!=(int)(oy/ratio))continue;
   if(count>=4096)goto original;
   seen[(y-miny)*68+x-minx]=1;points[count*2]=x-ox;points[count*2+1]=y-oy;count++;
  }
 }
 vector[0]=(U)points;vector[1]=vector[2]=count;
 s->waterExtra+=count-n;water_build_busy=1;i=invoke(s,0x1b29dc,self,1,(U)vector,0,0,0);water_build_busy=0;return i;
original:return invoke(s,0x1b29dc,self,1,cells,0,0,0);
}
static float water_alpha(State*s,U profile,float depth){
 float*t;U n,i;if(!profile||!(n=R(profile,0xc))||n>256||!R(profile,8)){
  U parameters=R(s->image,0x5f94d0),value=parameters?R(parameters,0x14):0;float scale=value?*(float*)value:1;
  return scale>.00001f?depth/scale:0;
 }
 t=(float*)R(profile,8);if(depth<=t[0])return t[4];
 for(i=1;i<n;i++)if(depth<t[i*5]){float q=(depth-t[(i-1)*5])/(t[i*5]-t[(i-1)*5]);return t[(i-1)*5+4]+q*(t[i*5+4]-t[(i-1)*5+4]);}
 return t[(n-1)*5+4];
}
__attribute__((dllexport)) void water_blend_vertices(State*s,U self){
 U world,map,view,biome,data,count,i,j,def,profile[6],defs[6]={0,0,0,0,0,0};float*vertices,*colors;
 int own,x,y,xx,yy,k;float gx,gy,tx,ty,weight[6],sum,other,contribution,depth,alpha;
 s->waterUpdates++;
 if(!water_scope(s)||!self||(own=water_slot(R(self,8)))<0||!R(self,4))return;
 world=R(s->image,0x5f3fb8);map=R(world,0x30);view=R(s->image,0x5f3fa8);if(!map||!view)return;biome=R(view,0x70);
 data=R(R(self,4),0xcc);if(!data)return;count=*(W*)(data+0xc);vertices=(float*)R(data,0x20);colors=(float*)R(data,0x28);if(!vertices||!colors)return;
 for(j=0;j<6;j++)profile[j]=0;
 for(i=0;i<count;i++){
  gx=vertices[i*3]*.5f-.5f;gy=vertices[i*3+1]*.5f-.5f;
  x=water_integer(gx);if(gx<x)x--;y=water_integer(gy);if(gy<y)y--;tx=gx-x;ty=gy-y;
  for(j=0;j<6;j++)weight[j]=0;
  for(yy=0;yy<2;yy++)for(xx=0;xx<2;xx++)if((def=water_cell(map,x+xx,y+yy))&&(k=water_slot(def))>=0){weight[k]+=(xx?tx:1-tx)*(yy?ty:1-ty);defs[k]=def;}
  sum=0;for(j=0;j<6;j++)sum+=weight[j];if(sum<.00001f)continue;
  if(weight[own]>=sum-.00001f)continue;
  if(weight[own]<.00001f){colors[i*4+3]=0;continue;}
  depth=vertices[i*3+2]-((WaterFloor)(s->image+0x2424d0))(world,0,(U)(vertices+i*3),0x122);
  other=0;contribution=0;
  for(j=0;j<6;j++)if(weight[j]>0&&defs[j]){
   if(!profile[j])profile[j]=invoke(s,0x70e6f,biome,1,defs[j],0,0,0);
   alpha=(int)j==own?colors[i*4+3]:water_alpha(s,profile[j],depth);if(alpha<0)alpha=0;if(alpha>1)alpha=1;
   if((int)j==own)contribution=weight[j]/sum*alpha;
   else if((int)j>own)other+=weight[j]/sum*alpha;
  }
  alpha=1-other;colors[i*4+3]=alpha>.00001f?contribution/alpha:0;s->waterBlended++;
 }
}
