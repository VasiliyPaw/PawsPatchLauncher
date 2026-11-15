/* Bridge intentions use the stock ActorCommand order, native serialization,
 * player ownership validation, tick ordering and CRC failure handler. Only the
 * host plans strategic AI; every peer executes the same received bridge job. */
#ifdef PAWS_BRIDGE_MULTIPLAYER
#define BRIDGE_NET_TAG 0x400U
#define BRIDGE_NET_MAGIC 0x42524700U
static U bridge_net_issuer(Roads*d,U kingdom){U s=P(d->image,0x5f3fe4),node=s?P(s,0xc8):0,i=0;
 for(;node&&i++<96;node=P(node,4)){U p=P(node,0);if(p&&P(p,0x28)==kingdom)return p;}return 0;}
static int bridge_net_submit(Roads*d,U a,U held){U order[3],args[2],issuer=bridge_net_issuer(d,P(a,0xe8)),ok;
 if(!issuer)return 0;args[0]=(U)&held;args[1]=a;
 ((NativeCall)d->call)(d->image+0xcd843,(U)order,2,args);
 ok=m0(d,0xd3d5f,(U)order)&255;
 if(ok)m1(d,0xd4bf1,(U)order,issuer);
 m0(d,0xd3d3c,(U)order);return ok;
}
static int bridge_net_normal(Roads*d,U a,U kind,float x,float y,U target){U c,held,ok;
 if(!bridge_networked(d)||!a||!P(a,0xe8)||(P(a,0xe8)!=local(d)&&!bridge_authority(d)))return 0;
 c=((U(*)(U))(d->image+0x2ef03c))(0x40);if(!c)return 0;held=m1(d,0x22f4e9,c,kind);if(!held)return 0;P(held,4)++;
 if(kind==5){P(held,0xc)|=4;F(held,0x18)=x;F(held,0x1c)=y;}
 if(target){P(held,0xc)|=1;P(held,0x10)=target;}
 ok=bridge_net_submit(d,a,held);m0(d,0x42fca,(U)&held);return ok;
}
static int bridge_net_send(Roads*d,U a,U*pts,U n,U wood){U c,held,ok,canonical[32],count;
 if(!bridge_networked(d)||!allowed(d)||!a||!worker(d,a)||!P(a,0xe8)||n<5||n>32||wood>1||(P(a,0xe8)!=local(d)&&!bridge_authority(d)))return 0;
 count=bg_line(pts[0]&65535,pts[0]>>16,pts[n-1]&65535,pts[n-1]>>16,canonical);
 if(count!=n)return 0;
 c=((U(*)(U))(d->image+0x2ef03c))(0x40);if(!c)return 0;held=m1(d,0x22f4e9,c,5);if(!held)return 0;P(held,4)++;
 /* The live network serializer carries eleven flag bits (unlike saves).
  * Both coordinate pairs and the integer signature need their presence bits.
  * Field +30 is a single network BIT, even though saves store a full byte.
  * Pack length/material into the signature's low byte instead. */
 P(held,0xc)|=BRIDGE_NET_TAG|4|8|0x10;P(held,0x28)=BRIDGE_NET_MAGIC|n|(wood<<7);
 F(held,0x18)=(pts[0]&65535)*2+1;F(held,0x1c)=(pts[0]>>16)*2+1;
 F(held,0x20)=(pts[n-1]&65535)*2+1;F(held,0x24)=(pts[n-1]>>16)*2+1;
 ok=bridge_net_submit(d,a,held);m0(d,0x42fca,(U)&held);if(ok)d->netSent++;return ok;
}
static int bridge_net_job_owned(Roads*d,U i,U a){return bridge_networked(d)&&i<JOBS&&d->netJobs[i]==P(a,0x14);}
/* Called after native player/actor validation, on the common order stream. */
EXPORT U FAST bridge_net_process(U cmd,U unused,U a){Roads*d=current;U def=cmd?P(cmd,8):0;Job*q;
 if(!d)return 0;
 if(bridge_networked(d)&&allowed(d)&&a&&actor(d,P(a,0x14))==a){
  q=job(d,P(a,0x14));
  if(def&&P(def,0xc)==5&&(P(cmd,0xc)&BRIDGE_NET_TAG)&&(P(cmd,0x28)&0xffffff00U)==BRIDGE_NET_MAGIC){
   U pts[32],n=P(cmd,0x28)&0x7f,wood=(P(cmd,0x28)>>7)&1,count,i;int xy[4];
   d->netReceived++;
   for(i=0;i<4;i++){float f=F(cmd,0x18+i*4);xy[i]=integer(f);if(!finite(f)||f!=(float)xy[i]||xy[i]<5||xy[i]>2047||!(xy[i]&1)){d->netRejected++;return 0;}xy[i]=(xy[i]-1)/2;}
   count=bg_line(xy[0],xy[1],xy[2],xy[3],pts);
   if(n<5||n>32||count!=n||!P(a,0xe8)||!bai_capable(d,a,wood)||!bridge_valid(d,pts,n,0)){d->netRejected++;return 0;}
   if(q){bridge_abandon(d,(U)(q-d->jobs));d->netJobs[q-d->jobs]=0;}
   {int slot=bridge_job_queue(d,a,pts,n,wood);if(slot>=0){d->netJobs[slot]=P(a,0x14);return 1;}}
   d->netRejected++;return 0;
  }
  if(q&&!B(cmd,0x3c)){bridge_abandon(d,(U)(q-d->jobs));d->netJobs[q-d->jobs]=0;d->netCancelled++;}
 }
 return m1(d,0x22f651,cmd,a);
}
static void bridge_net_restore(Roads*d){U reg=P(d->image,0x5ef72c),i;
 if(!bridge_networked(d)||!reg||d->netWorld==d->world)return;d->netWorld=d->world;
 for(i=1;i<65536;i++){U a=P(reg,0x20004+i*4),mind,cmd,site,n,axis,pts[32],j;BridgeGeometry g;
  if(!a||actor(d,P(a,0x14))!=a||!worker(d,a)||job(d,P(a,0x14)))continue;
  mind=P(a,0x70);cmd=mind?P(mind,0x20):0;if(!cmd||!P(cmd,8)||P(P(cmd,8),0xc)!=3||!(P(cmd,0xc)&1))continue;
  site=actor(d,P(cmd,0x10));if(!site||P(site,0xe8)!=P(a,0xe8)||!(P(site,0x100)&0x200000)||!bridge_kind(P(site,4),&n,&axis)||!bridge_paid(site))continue;
  g=bg_actor(site,n,axis);n=bg_line(bg_round((g.x-g.ux*g.half-1)*.5f),bg_round((g.y-g.uy*g.half-1)*.5f),bg_round((g.x+g.ux*g.half-1)*.5f),bg_round((g.y+g.uy*g.half-1)*.5f),pts);
  if(!n)continue;for(j=0;j<JOBS;j++)if(!d->jobs[j].id)break;if(j==JOBS)break;
  {Job*q=&d->jobs[j];U k;q->id=P(a,0x14);q->kingdom=P(P(a,0xe8),0x14);q->count=n;q->index=q->issued=0;q->lastMove=q->lastWork=F(d->world,0xe8);for(k=0;k<n;k++)q->points[k]=pts[k];}
  d->jobTools[j]=1;d->jobMaterials[j]=bridge_wood(P(site,4));d->construction[j]=P(site,0x14);d->siteCommitted[j]=1;d->siteHealth[j]=P(site,0x60)?F(P(site,0x60),0x10):0;d->netJobs[j]=P(a,0x14);d->netRestored++;
 }
}
EXPORT const U bridge_net_layout[]={offsetof(Roads,netWorld),offsetof(Roads,netSent),6};
/* Private test input enters the same native sender as the placement brush.
 * It neither creates actors nor pays costs nor executes simulation commands. */
EXPORT U bridge_net_input(Roads*d,U id,U wood,float x,float y){U a=actor(d,id),pts[32],n;
 if(!a||P(a,0xe8)!=local(d)||!finite(x)||!finite(y)||wood>1)return 0;
 n=bridge_auto(d,integer(x)>>1,integer(y)>>1,pts);return n?bridge_net_send(d,a,pts,n,wood):0;
}
EXPORT U bridge_net_order_input(Roads*d,U id,U kind,float x,float y,U target){U a=actor(d,id);
 if(!a||P(a,0xe8)!=local(d)||(kind!=5&&kind!=6&&kind!=0&&kind!=3))return 0;
 return bridge_net_normal(d,a,kind,x,y,target);
}
#else
static int bridge_net_normal(Roads*d,U a,U kind,float x,float y,U target){(void)d;(void)a;(void)kind;(void)&x;(void)&y;(void)target;return 0;}
static int bridge_net_send(Roads*d,U a,U*pts,U n,U wood){(void)d;(void)a;(void)pts;(void)n;(void)wood;return 0;}
static int bridge_net_job_owned(Roads*d,U i,U a){(void)d;(void)i;(void)a;return 0;}
static void bridge_net_restore(Roads*d){(void)d;}
#endif
