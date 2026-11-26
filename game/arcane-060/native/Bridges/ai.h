/* Strategic and explored-river bridge planning. Never edits native strategic goal lists.
 * All path probes are read-only; only the common native construction job pays.
 * Six global AI jobs leave two shared slots available for the human player. */
#define BAI_UNKNOWN 1.0e29f
#define BAI_UNREACHABLE 1.0e28f
typedef struct {U source,target,kind;float sx,sy,x,y;} BridgeAIGoal;
static float bai_dist(float x,float y,float a,float b){x-=a;y-=b;return bg_sqrt(x*x+y*y);}
static U bai_player(Roads*d,U k){U sai=P(d->image,0x5f3fc8),list,n,i;
 if(!sai||!k||k==local(d))return 0;list=P(sai,0x6c);n=P(sai,0x70);if(!list||n>96)return 0;
 for(i=0;i<n;i++){U p=P(list,i*4);if(p&&P(p,8)==k&&P(p,0xc))return p;}return 0;
}
static int bai_allied(U a,U b){return a&&b&&(a==b||(P(a,0x1f8)&&P(a,0x1f8)==P(b,0x1f8)));}
static U bai_kingdom(Roads*d,U id){U list=P(d->world,0x150),n=P(d->world,0x154),i;if(!list||n>96)return 0;
 for(i=0;i<n;i++){U k=P(list,i*4);if(k&&P(k,0x14)==id)return k;}return 0;}
static U bai_state_kind(Roads*d,U a){U ai=P(a,0x70),list=ai?P(ai,0x14):0,s=list?P(list,0):0;return s?P(s,0)-d->image:0;}
static int bai_idle(Roads*d,U a){U s=bai_state_kind(d,a);return (s==0x4f4d98||s==0x4f4f28)&&!fighting(d,a);}
static int bai_capable(Roads*d,U a,U wood){U u=worker(d,a),def=u?P(u,4):0,node,i=0;
 if(!def)return 0;for(node=P(def,0x504);node&&i++<128;node=P(node,4)){
  U target=P(node,0);if(target&&bridge_prefix((W*)P(target,8),"paws_bridge_")&&bridge_wood(target)==wood)return 1;
 }return 0;
}
static U bai_worker(Roads*d,U pl){U node,steps=0,best=0;
 for(node=P(pl,0x2c);node&&steps++<4096;node=P(node,4)){U sa=P(node,0),a=sa?actor(d,P(sa,8)):0,g=sa?P(sa,0x10):0,body;
  if(!a||P(sa,0xc)!=pl||P(a,0xe8)!=P(pl,8)||!P(a,0x7c)||job(d,P(a,0x14))||!bai_idle(d,a)||!worker(d,a))continue;
  if(g&&(P(g,4)!=P(pl,0xc)||P(g,0)!=d->image+0x4da510))continue;
  body=P(a,0x60);if(body&&(!finite(F(body,0x10))||F(body,0x10)<F(body,0x14)*.8f))continue;
  if(!bai_capable(d,a,1)&&!bai_capable(d,a,0))continue;
  if(!best||P(a,0x14)<P(best,0x14))best=a;
 }return node?0:best;
}
static int bai_known(Roads*d,U k,float x,float y){U c=tile(d,integer(x)>>1,integer(y)>>1);return c&&(m1(d,0x24a845,c,k)&255);}
static int bai_safe(Roads*d,U k,float x,float y,float radius){U reg=P(d->image,0x5ef72c),i;if(!reg)return 0;
 for(i=1;i<65536;i++){U a=P(reg,0x20004+i*4),owner,c;
  if(!a||P(a,0)!=d->image+0x4e5c58||(P(a,8)&3)||!(owner=P(a,0xe8))||bai_allied(owner,k))continue;
  if(bg_abs(F(a,0x20)-x)>radius||bg_abs(F(a,0x24)-y)>radius)continue;
  c=tile(d,integer(F(a,0x20))>>1,integer(F(a,0x24))>>1);if(!c||!(m1(d,0x24a86a,c,k)&255))continue;
  if((((M1)P(P(a,0),0x144))(a,0,k)==3)&&(P(a,0x7c)||P(a,0x6c)||P(a,0x94)))return 0;
 }return 1;
}
/* Actual modified cost and native resource ordering, including modded slots. */
static int bai_budget(Roads*d,U k,U a,U wood,U model){U def=bridge_definition_owner(d,model,0,wood,k),n,table,defs,i,vector[3],u,gold=32;float values[32],extra=0;
 if(!def||!a||!bai_capable(d,a,wood)||!(u=worker(d,a)))return 0;
 n=P(k,0x1d0);table=P(d->image,0x5efa8c);if(!table||!n||n>32||P(table,0x28)!=n||P(def,0x328)!=n||P(def,0x334)!=n||!P(def,0x330)||!P(k,0x1cc)||!P(k,0x1a8)||!P(k,0x1c0))return 0;
 defs=P(table,0x24);if(!defs)return 0;vector[0]=(U)values;vector[1]=vector[2]=n;
 for(i=0;i<n;i++)values[i]=0;invoke(d,0x29eaa,def,2,(U)vector,m0(d,0x2277b6,u));
 for(i=0;i<n;i++){U rd=P(defs,i*4);if(rd&&eq((W*)P(rd,8),"gold"))gold=i;}
 if(gold>=n)return 0;
 for(i=0;i<n;i++){U rd=P(defs,i*4);float reserve=i==gold?150:0,need=F(P(def,0x330),i*4);
  if(!rd||!finite(values[i])||values[i]<0||!finite(need)||need<0)return 0;
  if(P(rd,0x18)==0&&(!finite(F(P(k,0x1cc),i*4))||F(P(k,0x1cc),i*4)<values[i]+reserve))return 0;
  /* Native definitions own racial/material upkeep. A wooden model may use
   * stone and a stronger Haroun crossing uses wood. Do not infer this from art.
   * Native gold upkeep already includes existing resource deficits (239377);
   * charge only the additional conversion induced by this actual definition. */
  if(need>0){float net=F(P(k,0x1a8),i*4)-F(P(k,0x1c0),i*4);
   if(!finite(net))return 0;if(i==gold){extra+=need;continue;}
   if(net<need){U price=P(rd,0x1c);float rate;if(!price||P(rd,0x20)!=n)return 0;rate=F(price,gold*4);if(!finite(rate)||rate<=0)return 0;
    extra+=(net<0?need:need-net)*rate;
   }
  }
 }
 if(!finite(extra)||(extra>0&&F(P(k,0x1a8),gold*4)-F(P(k,0x1c0),gold*4)-extra<20))return 0;
 return bridge_funds(d,def,a,0);
}
/* Shared owner-aware queue. An intention does not create or reserve an actor. */
static int bridge_job_queue(Roads*d,U a,U*points,U n,U wood){U i,j,side;Job*q;
 if(!a||!worker(d,a)||n<5||n>32||wood>1||!bridge_valid(d,points,n,0))return -1;
 if(job(d,P(a,0x14)))return -1;for(i=0;i<JOBS;i++)if(!d->jobs[i].id)break;if(i==JOBS)return -1;
 side=bridge_approach(d,a,points,n);if(!side)return -1;q=&d->jobs[i];q->id=P(a,0x14);q->kingdom=P(P(a,0xe8),0x14);q->index=q->issued=0;q->count=n;q->lastMove=q->lastWork=F(d->world,0xe8);
 for(j=0;j<n;j++)q->points[j]=points[side==2?n-1-j:j];
 d->jobTools[i]=1;d->jobMaterials[i]=wood;d->workStarted[i]=0;d->construction[i]=0;d->siteCommitted[i]=0;return (int)i;
}
static int bridge_ai_job_owned(Roads*d,U slot,U a){U i,id=P(a,0x14),k=P(P(a,0xe8),0x14);if(!bai_player(d,P(a,0xe8)))return 0;
 for(i=0;i<BAI_PLAYERS;i++){BridgeAIPlayer*p=&d->ai.players[i];if(p->worker==id&&p->kingdom==k&&p->slot==slot+1)return 1;}return 0;}
static void bridge_ai_clear(Roads*d){U i;for(i=0;i<sizeof(BridgeAI)/4;i++)P(&d->ai,i*4)=0;}
/* Walk-cost probes share the existing bounded route scratch, never its results.
 * A hypothetical deck only opens water, never a cliff, building or wetland. */
static int bai_open(Roads*d,U cell,U width,U k,U*pts,U count,U intents){U c=P(P(d->world,0x30),0x28)+cell*48,j;float x=(cell%width)*2+1,y=(cell/width)*2+1;
 if(!(P(c,0x20)&0x100))return 1;if((P(c,0x20)&0x70)!=0x20||bridge_wetland(c))return 0;
 if(count){BridgeGeometry g=bg_points(pts,count);if(bg_nav(&g,x,y))return 1;}
 if(intents)for(j=0;j<JOBS;j++){Job*q=&d->jobs[j];U a=q->id?actor(d,q->id):0;if(a&&d->jobTools[j]&&bai_allied(k,P(a,0xe8))){BridgeGeometry g=bg_points(q->points,q->count);if(bg_nav(&g,x,y))return 1;}}
 return 0;
}
static int bai_ground(Roads*d,float x,float y,U*out){U map=P(d->world,0x30),w=P(map,0x1c);int cx=integer(x)>>1,cy=integer(y)>>1,r,xx,yy;float best=1e20f;U result=0;
 if(!finite(x)||!finite(y)||x<0||y<0)return 0;
 for(r=0;r<=6;r++){for(yy=cy-r;yy<=cy+r;yy++)for(xx=cx-r;xx<=cx+r;xx++){U c=tile(d,xx,yy);float dx=xx*2+1-x,dy=yy*2+1-y,score=dx*dx+dy*dy;if(c&&!(P(c,0x20)&0x100)&&score<best){best=score;result=yy*w+xx+1;}}if(result)break;}
 if(!result)return 0;*out=result-1;return 1;
}
static int bai_connected(Roads*d,U start,U goal,U k,U*pts,U n,U intents){U width=P(P(d->world,0x30),0x1c),tiles=P(P(d->world,0x30),0x28),a=bridge_walk_island(tiles+start*48,0),b=bridge_walk_island(tiles+goal*48,0),seen[20],count=1,i,j,round;
 (void)width;seen[0]=a;if(a==b)return 1;
 for(round=0;round<JOBS+2;round++){U before=count;
  for(i=0;i<JOBS+1;i++){U *p=pts,cn=n,l,r;if(i<JOBS){Job*q=&d->jobs[i];U actorq=q->id?actor(d,q->id):0;if(!intents||!actorq||!d->jobTools[i]||!bai_allied(k,P(actorq,0xe8)))continue;p=q->points;cn=q->count;}
   if(!cn)continue;l=tile(d,p[0]&65535,p[0]>>16);r=tile(d,p[cn-1]&65535,p[cn-1]>>16);if(!l||!r)continue;l=bridge_walk_island(l,0);r=bridge_walk_island(r,0);
   for(j=0;j<count;j++)if(seen[j]==l||seen[j]==r)break;if(j==count)continue;
   for(j=0;j<count&&seen[j]!=l;j++);if(j==count&&count<20)seen[count++]=l;
   for(j=0;j<count&&seen[j]!=r;j++);if(j==count&&count<20)seen[count++]=r;
   if(l==b||r==b)return 1;
  }if(count==before)break;
 }return 0;
}
static float bai_distance(Roads*d,float sx,float sy,float tx,float ty,U k,U*pts,U count,U intents){U map=P(d->world,0x30),width=P(map,0x1c),height=P(map,0x20),cells=width*height,start,goal,stamp,i,hc=0,expanded=0,here=0;BridgeRouteNode*n;U*heap;
 d->ai.lowerBound=0;
 if(!cells||width>1024||height>1024||d->routeBusy||!bai_ground(d,sx,sy,&start)||!bai_ground(d,tx,ty,&goal))return BAI_UNKNOWN;
 if(!bai_connected(d,start,goal,k,pts,count,intents))return BAI_UNREACHABLE;
 if(d->routeCells!=cells){if(d->routeMemory)((void(*)(U,U))(d->image+0x3e1285))(d->routeMemory,d->routeCells*20);d->routeMemory=((U(*)(U))(d->image+0x2ef03c))(cells*20);d->routeCells=d->routeMemory?cells:0;d->routeStamp=0;if(!d->routeMemory)return BAI_UNKNOWN;for(i=0;i<cells;i++)P(d->routeMemory,i*16)=0;}
 n=(BridgeRouteNode*)d->routeMemory;heap=(U*)(n+cells);stamp=++d->routeStamp;if(!stamp){for(i=0;i<cells;i++)n[i].stamp=0;stamp=++d->routeStamp;}
 n[start].stamp=stamp;n[start].cost=0;n[start].heap=0;n[start].parent=start;heap[hc++]=start;
 while(hc&&expanded<4096){int x,y,xx,yy;here=br_pop(n,heap,&hc,goal,width);expanded++;if(here==goal)return n[here].cost*.2f;x=here%width;y=here/width;
  for(yy=y-1;yy<=y+1;yy++)for(xx=x-1;xx<=x+1;xx++){U next,cost;if(xx<2||yy<2||xx+2>=(int)width||yy+2>=(int)height||(xx==x&&yy==y))continue;next=yy*width+xx;if(!bai_open(d,next,width,k,pts,count,intents))continue;
   if(xx!=x&&yy!=y&&(!bai_open(d,y*width+xx,width,k,pts,count,intents)||!bai_open(d,yy*width+x,width,k,pts,count,intents)))continue;
   cost=n[here].cost+(xx!=x&&yy!=y?14:10);if(n[next].stamp==stamp){if(cost>=n[next].cost||n[next].heap==0xffffffff)continue;n[next].cost=cost;n[next].parent=here;br_up(n,heap,n[next].heap,goal,width);}else{n[next].stamp=stamp;n[next].cost=cost;n[next].parent=here;n[next].heap=hc;heap[hc++]=next;br_up(n,heap,hc-1,goal,width);}
  }
 }d->ai.unknownPaths++;if(hc)d->ai.lowerBound=br_score(n,heap[0],goal,width)*.2f;return hc?BAI_UNKNOWN:BAI_UNREACHABLE;
}
/* On exhaustion only the admissible frontier lower bound can prove a saving.
 * A prospective route and a builder approach still require complete paths. */
static float bai_baseline(Roads*d,float sx,float sy,float tx,float ty,U k){float v=bai_distance(d,sx,sy,tx,ty,k,0,0,1);return v>=BAI_UNKNOWN&&d->ai.lowerBound>0?d->ai.lowerBound:v;}
static int bai_useful(float before,float after){return finite(before)&&finite(after)&&before<BAI_UNKNOWN&&after<BAI_UNREACHABLE&&(before>=BAI_UNREACHABLE||(after+50<=before&&after<=before*.75f));}
EXPORT U bridge_ai_useful_check(float before,float after){return bai_useful(before,after);}
EXPORT float bridge_ai_distance_check(Roads*d,float sx,float sy,float tx,float ty,U k,U*pts,U n,U intents){return bai_distance(d,sx,sy,tx,ty,k,pts,n,intents);}
static int bai_purpose_live(Roads*d,U pl,U source,U targetID,U kind,float tx,float ty){U a=actor(d,source),target=actor(d,targetID),mind,cmd,node,steps=0;
 if(!pl||!a||P(a,0xe8)!=P(pl,8))return 0;
 if(kind==6)return worker(d,a)&&bai_known(d,P(pl,8),tx,ty);
 if(kind==4)return target&&P(target,0xe8)==P(pl,8)&&P(target,0x98);
 if(kind==5){U engine=P(pl,0xc),table=P(engine,8),typ,status;if(!target||!table)return 0;
  for(typ=0;typ<23;typ++){U lists=P(table,typ*4);if(!lists)continue;for(status=0;status<3;status++)for(node=P(lists,status*8),steps=0;node&&steps++<4096;node=P(node,4)){U g=P(node,0),vt=g?P(g,0)-d->image:0;if(g&&P(g,4)==engine&&(vt==0x4da480||vt==0x4d84d4)&&P(g,8)<=2&&F(g,0x38)>0&&P(g,0x4c)==targetID)return 1;}}return 0;}
 if(kind==3){U engine=P(pl,0xc),table=P(engine,8),typ,status;if(!table)return 0;
  for(typ=0;typ<23;typ++){U lists=P(table,typ*4);if(!lists)continue;for(status=0;status<3;status++)for(node=P(lists,status*8),steps=0;node&&steps++<4096;node=P(node,4)){U g=P(node,0);if(g&&P(g,4)==engine&&P(g,0)==d->image+0x4da6b0&&P(g,8)<=2&&F(g,0x38)>0&&bai_dist(F(g,0x48),F(g,0x4c),tx,ty)<8)return 1;}}return 0;}
 mind=P(a,0x70);cmd=mind?P(mind,0x20):0;if(!cmd||!P(cmd,8))return 0;
 if(kind==1)return P(P(cmd,8),0xc)==5&&(P(cmd,0xc)&4)&&bai_dist(F(cmd,0x18),F(cmd,0x1c),tx,ty)<16;
 return kind==2&&target&&(P(P(cmd,8),0xc)==0||P(P(cmd,8),0xc)==1)&&P(cmd,0x10)==targetID;
}
static int bai_failed(BridgeAIPlayer*p,float x,float y,float now){U i;for(i=0;i<BAI_FAILED;i++)if(p->failed[i].until>now&&bai_dist(x,y,p->failed[i].x,p->failed[i].y)<48)return 1;return 0;}
static void bai_failure_at(BridgeAIPlayer*p,float x,float y,float now){BridgeAIFailure*f=&p->failed[p->failedCursor++%BAI_FAILED];f->x=x;f->y=y;f->until=now+180;p->cooldown=now+30;}
static void bai_failure(BridgeAIPlayer*p,float now){bai_failure_at(p,p->x,p->y,now);}
static void bai_finish(Roads*d,BridgeAIPlayer*p,float now,U success){U a=actor(d,p->worker),site=actor(d,p->site);if(success){U at=p->builtCursor++%4;p->built[at]=p->site;p->builtX[at]=p->x;p->builtY[at]=p->y;p->cooldown=now+180;d->ai.finished++;}else{bai_failure(p,now);d->ai.aborted++;}
 if(p->slot&&p->slot<=JOBS&&d->jobs[p->slot-1].id==p->worker){
  if(bridge_networked(d)){if(a&&!success)bridge_net_normal(d,a,6,0,0,0);}
  else{bridge_abandon(d,p->slot-1);if(a&&!fighting(d,a)&&!success)command(d,a,"stop",0,0);}
 }
 (void)site;p->worker=p->site=p->slot=0;p->next=now+15;
}
static int bai_goal_add(Roads*d,U k,BridgeAIGoal*goals,U*n,U source,U target,U kind,float sx,float sy,float x,float y){U i;if(*n==24||!finite(x)||!finite(y)||bai_dist(sx,sy,x,y)<64||bai_dist(sx,sy,x,y)>4096||!bai_known(d,k,x,y))return 0;
 for(i=0;i<*n;i++)if(bai_dist(x,y,goals[i].x,goals[i].y)<24)return 0;
 goals[*n].source=source;goals[*n].target=target;goals[*n].kind=kind;goals[*n].sx=sx;goals[*n].sy=sy;goals[*n].x=x;goals[(*n)++].y=y;return 1;
}
static int bai_goal(Roads*d,U pl,U builder,BridgeAIPlayer*p,BridgeAIGoal*out){BridgeAIGoal goals[24];U n=0,node,steps=0,k=P(pl,8),engine=P(pl,0xc),i,cities=P(k,0x2dc),nc=P(k,0x2e0),table=engine?P(engine,8):0,typ,status;
 /* Restore a stranded builder's link to an owned city before new expansion. */
 if(cities&&nc<=256)for(i=0;i<nc&&n<24;i++){U a=P(cities,i*4);if(a&&actor(d,P(a,0x14))==a&&P(a,0xe8)==k&&P(a,0x98)&&!(P(a,8)&3))bai_goal_add(d,k,goals,&n,P(builder,0x14),P(a,0x14),4,F(builder,0x20),F(builder,0x24),F(a,0x20),F(a,0x24));}
 /* Existing army travel/attack orders express a real strategic destination. */
 for(node=P(pl,0x2c);node&&steps++<4096&&n<12;node=P(node,4)){U sa=P(node,0),a=sa?actor(d,P(sa,8)):0,mind=a?P(a,0x70):0,cmd=mind?P(mind,0x20):0,def=cmd?P(cmd,8):0,kind=def?P(def,0xc):99,target=cmd?actor(d,P(cmd,0x10)):0;
  if(!a||P(a,0xe8)!=k||!P(a,0x7c)||worker(d,a)||!cmd)continue;
  if(kind==5&&(P(cmd,0xc)&4))bai_goal_add(d,k,goals,&n,P(a,0x14),0,1,F(a,0x20),F(a,0x24),F(cmd,0x18),F(cmd,0x1c));
  else if((kind==0||kind==1)&&target)bai_goal_add(d,k,goals,&n,P(a,0x14),P(target,0x14),2,F(a,0x20),F(a,0x24),F(target,0x20),F(target,0x24));
 }
 if(node&&steps>=4096)return 0;
 /* Native desired city construction includes reachable settlement expansion. */
 if(table)for(typ=0;typ<23&&n<20;typ++){U lists=P(table,typ*4);if(!lists)continue;for(status=0;status<3&&n<20;status++)for(node=P(lists,status*8),steps=0;node&&steps++<4096&&n<20;node=P(node,4)){U g=P(node,0);if(!g||P(g,4)!=engine||P(g,8)>2||!finite(F(g,0x38))||F(g,0x38)<=0)continue;
   if(P(g,0)==d->image+0x4da6b0)bai_goal_add(d,k,goals,&n,P(builder,0x14),0,3,F(builder,0x20),F(builder,0x24),F(g,0x48),F(g,0x4c));
   else if(P(g,0)==d->image+0x4da480||P(g,0)==d->image+0x4d84d4){U target=actor(d,P(g,0x4c));if(target)bai_goal_add(d,k,goals,&n,P(builder,0x14),P(target,0x14),5,F(builder,0x20),F(builder,0x24),F(target,0x20),F(target,0x24));}
  }}

 if(!n)return 0;*out=goals[p->goalCursor++%n];return 1;
}
static U bai_live_jobs(Roads*d){U i,n=0;for(i=0;i<BAI_PLAYERS;i++)if(d->ai.players[i].worker)n++;return n;}
/* A crossing must be at least 24 world units from either river end. Flood
 * only explored channel cells in a bounded local strip, allowing bends without
 * turning a short puddle or a dry gap into a river. The generated lake-named
 * river variations follow exactly the same rule as native river variations. */
static int bai_channel_margin(Roads*d,U k,U*pts,U n){U queue[512],head=0,tail=0,i,seed=0;unsigned char seen[1089];int cx,cy,positive=0,negative=0;BridgeGeometry g=bg_points(pts,n);
 for(i=0;i<n;i++)if(bridge_channel(d,pts[i]&65535,pts[i]>>16)){seed=pts[i];break;}if(i==n)return 0;
 cx=seed&65535;cy=seed>>16;for(i=0;i<1089;i++)seen[i]=0;queue[tail++]=16+16*33;seen[16+16*33]=1;
 while(head<tail){U at=queue[head++];int x=(int)(at%33)-16,y=(int)(at/33)-16,xx,yy;float across=x*g.ux+y*g.uy,along=x*g.uy-y*g.ux;
  if(bg_abs(across)>10)continue;if(along>=12)positive=1;if(along<=-12)negative=1;if(positive&&negative)return 1;
  for(yy=y-1;yy<=y+1;yy++)for(xx=x-1;xx<=x+1;xx++){U next;if((xx!=x&&yy!=y)||xx<-16||yy<-16||xx>16||yy>16)continue;next=(yy+16)*33+xx+16;if(seen[next])continue;seen[next]=1;
   if(!bai_known(d,k,(cx+xx)*2+1,(cy+yy)*2+1)||!bridge_channel(d,cx+xx,cy+yy))continue;
   /* Four-connected steps prevent two diagonally touching ponds joining. */
   if(tail==512)return 0;queue[tail++]=next;
  }
 }return 0;
}
/* Spacing is a policy for bots, not an artificial restriction on players.
 * Unknown enemy bridges are not queried by this policy. Allied pending jobs
 * count before a site exists, so simultaneous intentions cannot bunch up. */
static int bai_spaced(Roads*d,U k,U*pts,U n,U workerID){U i;BridgeGeometry g=bg_points(pts,n);
 for(i=0;i<d->bridgeCount;i++){U a=actor(d,d->spans[i].id);if(!a||(P(a,8)&3)||!bai_known(d,k,F(a,0x20),F(a,0x24)))continue;
  if(!bai_allied(k,P(a,0xe8))){U c=tile(d,integer(F(a,0x20))>>1,integer(F(a,0x24))>>1);if(!c||!(m1(d,0x24a86a,c,k)&255))continue;}
  if(bai_dist(g.x,g.y,F(a,0x20),F(a,0x24))<96)return 0;
 }
 for(i=0;i<JOBS;i++){Job*q=&d->jobs[i];U a=q->id?actor(d,q->id):0;if(a&&q->id!=workerID&&d->jobTools[i]&&bai_allied(k,P(a,0xe8))){BridgeGeometry other=bg_points(q->points,q->count);if(bai_dist(g.x,g.y,other.x,other.y)<96)return 0;}}
 return 1;
}
/* Closest cells first, deterministic at every relocation and player index.
 * 41 squared samples, 8 world units apart, cover a 320-unit local square. */
static void bai_river_sample(U index,int*x,int*y){U ring=0,side,offset;while(index>=(2*ring+1)*(2*ring+1))ring++;if(!ring){*x=*y=0;return;}side=2*ring;offset=index-(2*ring-1)*(2*ring-1);
 if(offset<side){*x=ring;*y=-(int)ring+1+(int)offset;}else if(offset<side*2){*x=(int)ring-1-(int)(offset-side);*y=ring;}else if(offset<side*3){*x=-(int)ring;*y=(int)ring-1-(int)(offset-side*2);}else{*x=-(int)ring+1+(int)(offset-side*3);*y=-(int)ring;}
}
EXPORT U bridge_ai_river_check(Roads*d,U k,U*pts,U n,U workerID){return n>=5&&n<=32&&bridge_valid(d,pts,n,0)&&bai_channel_margin(d,k,pts,n)&&bai_spaced(d,k,pts,n,workerID);}
EXPORT U bridge_ai_sample_check(U index){int x,y;if(index>=1681)return 0xffffffff;bai_river_sample(index,&x,&y);return (U)(x+32)|((U)(y+32)<<16);}
static int bai_candidate(Roads*d,BridgeAIPlayer*p,U k,U builder,U*pts,U n,float now){U i,side,material=2;float after,approach,x,y,score;BridgeGeometry g;
 if(!n||!bridge_valid(d,pts,n,0)){d->ai.refusals[1]++;return 0;}if(bridge_occupied(d,pts,n,P(builder,0x14))){d->ai.refusals[2]++;return 0;}g=bg_points(pts,n);d->ai.candidateX=g.x;d->ai.candidateY=g.y;if(bai_failed(p,g.x,g.y,now))return 0;
 if(!bai_channel_margin(d,k,pts,n)||!bai_spaced(d,k,pts,n,P(builder,0x14))){d->ai.refusals[7]++;return 0;}
 for(i=0;i<n;i++)if(!bai_known(d,k,(pts[i]&65535)*2+1,(pts[i]>>16)*2+1)){d->ai.refusals[3]++;return 0;}
 side=bridge_approach(d,builder,pts,n);if(!side){d->ai.refusals[4]++;return 0;}i=side==2?n-1:0;x=(pts[i]&65535)*2+1;y=(pts[i]>>16)*2+1;
 approach=bai_distance(d,F(builder,0x20),F(builder,0x24),x,y,k,0,0,0);d->ai.approach=approach;if(approach>=BAI_UNREACHABLE||approach>240){d->ai.refusals[5]++;return 0;}
 after=d->ai.kind==6?0:bai_distance(d,d->ai.sx,d->ai.sy,d->ai.tx,d->ai.ty,k,pts,n,1);d->ai.after=after;if(d->ai.kind!=6&&!bai_useful(d->ai.baseline,after)){d->ai.refusals[6]++;if(after<BAI_UNREACHABLE)d->ai.duplicates++;return 0;}
 if(!bai_safe(d,k,g.x-g.ux*g.half,g.y-g.uy*g.half,48)||!bai_safe(d,k,g.x+g.ux*g.half,g.y+g.uy*g.half,48)||!bai_safe(d,k,F(builder,0x20),F(builder,0x24),32)){d->ai.dangerRejected++;return 0;}
 /* Cheap timber first. Durable stone is useful for a major permanent link. */
 if(d->ai.kind!=6&&(d->ai.baseline>=BAI_UNREACHABLE||d->ai.baseline-after>150)&&bai_budget(d,k,builder,0,bg_model(&g)))material=0;
 else if(bai_budget(d,k,builder,1,bg_model(&g)))material=1;else if(bai_budget(d,k,builder,0,bg_model(&g)))material=0;
 if(material>1){d->ai.budgetRejected++;return 0;}
 score=after+approach*(d->ai.kind==6?1:.25f)+g.half*.5f+(material?0:10);
 if(!d->ai.bestN||score<d->ai.best){d->ai.best=score;d->ai.bestN=n;d->ai.bestMaterial=material;for(i=0;i<n;i++)d->ai.bestPoints[i]=pts[i];return 1;}return 0;
}
static int bai_adopt(Roads*d,U pl,BridgeAIPlayer*p,U builder,float now){U i,k=P(pl,8),mind=builder?P(builder,0x70):0,cmd=mind?P(mind,0x20):0,repair=cmd&&P(cmd,8)&&P(P(cmd,8),0xc)==3&&(P(cmd,0xc)&1)?P(cmd,0x10):0;for(i=0;i<d->bridgeCount;i++){U a=actor(d,d->spans[i].id),n,axis,pts[32],j;BridgeGeometry g;int slot;
  if(!a||P(a,0xe8)!=k||(P(a,8)&3)||!(P(a,0x100)&0x200000)||!bridge_kind(P(a,4),&n,&axis))continue;
  if(repair&&P(a,0x14)!=repair)continue;
  if(!builder)return 1;
  if(bridge_networked(d)){Job*q=job(d,P(builder,0x14));if(q&&d->construction[q-d->jobs]==P(a,0x14)){p->worker=P(builder,0x14);p->slot=(U)(q-d->jobs)+1;p->site=P(a,0x14);p->x=F(a,0x20);p->y=F(a,0x24);p->started=p->progress=now;p->health=P(a,0x60)?F(P(a,0x60),0x10):0;d->ai.resumed++;}return 1;}
  g=bg_actor(a,n,axis);n=bg_line(bg_round((g.x-g.ux*g.half-1)*.5f),bg_round((g.y-g.uy*g.half-1)*.5f),bg_round((g.x+g.ux*g.half-1)*.5f),bg_round((g.y+g.uy*g.half-1)*.5f),pts);
  if(!n||!bridge_approach(d,builder,pts,n)||!bai_capable(d,builder,bridge_wood(P(a,4)))||!bai_safe(d,k,g.x,g.y,48))return 1;
  for(j=0;j<JOBS;j++)if(!d->jobs[j].id)break;if(j==JOBS)return 1;slot=(int)j;
  d->jobs[j].id=P(builder,0x14);d->jobs[j].kingdom=P(k,0x14);d->jobs[j].count=n;d->jobs[j].index=d->jobs[j].issued=0;d->jobs[j].lastWork=d->jobs[j].lastMove=now;
  for(j=0;j<n;j++)d->jobs[slot].points[j]=pts[j];d->jobTools[slot]=1;d->jobMaterials[slot]=bridge_wood(P(a,4));d->construction[slot]=P(a,0x14);d->siteCommitted[slot]=bridge_paid(a);d->siteHealth[slot]=P(a,0x60)?F(P(a,0x60),0x10):0;
  p->worker=P(builder,0x14);p->slot=slot+1;p->site=P(a,0x14);p->x=g.x;p->y=g.y;p->started=p->progress=now;p->health=d->siteHealth[slot];
  if(repair!=P(a,0x14)&&!command_target(d,builder,P(a,0x14))){bai_finish(d,p,now,0);return 1;}d->ai.resumed++;return 1;
 }return 0;}
/* Restore an actually saved bridge repair before the new-plan delay. This
 * reserves its existing builder without replacing the native repair command. */
static void bai_restore_worker(Roads*d,U pl,BridgeAIPlayer*p,float now){U node,steps=0;
 if(p->worker||bai_live_jobs(d)>=6)return;
 for(node=P(pl,0x2c);node&&steps++<4096;node=P(node,4)){U sa=P(node,0),a=sa?actor(d,P(sa,8)):0,mind=a?P(a,0x70):0,cmd=mind?P(mind,0x20):0,site,n,axis;
  if(!a||P(a,0xe8)!=P(pl,8)||!worker(d,a)||(job(d,P(a,0x14))&&!bridge_networked(d))||fighting(d,a)||!cmd||!P(cmd,8)||P(P(cmd,8),0xc)!=3||!(P(cmd,0xc)&1))continue;
  site=actor(d,P(cmd,0x10));if(!site||P(site,0xe8)!=P(pl,8)||!(P(site,0x100)&0x200000)||!bridge_kind(P(site,4),&n,&axis)||!bridge_paid(site))continue;
  p->kingdom=P(P(pl,8),0x14);bai_adopt(d,pl,p,a,now);return;
 }
}
static void bai_watch(Roads*d,float now){U i,j;for(i=0;i<BAI_PLAYERS;i++){BridgeAIPlayer*p=&d->ai.players[i];U k=bai_kingdom(d,p->kingdom),a=actor(d,p->worker),site;
  for(j=0;j<4;j++)if(p->built[j]&&!actor(d,p->built[j])){bai_failure_at(p,p->builtX[j],p->builtY[j],now);p->built[j]=0;}
  if(!p->worker)continue;if(!k||!bai_player(d,k)||!a||P(a,0xe8)!=k||!worker(d,a)||fighting(d,a)){d->ai.abortReason=1;bai_finish(d,p,now,0);continue;}
  if(p->slot&&p->slot<=JOBS&&d->construction[p->slot-1])p->site=d->construction[p->slot-1];site=actor(d,p->site);
  if(site&&!(P(site,8)&3)&&!(P(site,0x100)&0x200000)){bai_finish(d,p,now,1);continue;}
  if(bridge_networked(d)&&!p->slot){Job*q=job(d,p->worker);if(q)p->slot=(U)(q-d->jobs)+1;else if(now-p->started<10)continue;}
  if(!p->slot||p->slot>JOBS||d->jobs[p->slot-1].id!=p->worker){d->ai.abortReason=2;bai_finish(d,p,now,0);continue;}
  if(site&&P(site,0x60)&&F(P(site,0x60),0x10)>p->health+.01f){p->health=F(P(site,0x60),0x10);p->progress=now;}
  if((!site&&now-p->started>240)||now-p->progress>90){d->ai.abortReason=3;bai_finish(d,p,now,0);continue;}
  if(now>=p->nextSafety){p->nextSafety=now+2;
   if(!site){BridgeGeometry g=bg_points(d->jobs[p->slot-1].points,d->jobs[p->slot-1].count);
    if(!bai_purpose_live(d,bai_player(d,k),p->source,p->target,p->kind,p->goalX,p->goalY)||!bai_budget(d,k,a,p->material,bg_model(&g))||!bridge_valid(d,d->jobs[p->slot-1].points,d->jobs[p->slot-1].count,0)){d->ai.abortReason=6;bai_finish(d,p,now,0);continue;}
   }
   if(!bai_safe(d,k,F(a,0x20),F(a,0x24),32)){d->ai.abortReason=4;bai_finish(d,p,now,0);continue;}
  }
 }}
/* A free builder is reserved against new native travel/construction orders.
 * Human commands bypass this queue. Combat/retreat/other work releases the
 * reservation; mixed group orders also pass intact, never lose other members. */
EXPORT U bridge_ai_sai_block(U pl,U envelope){Roads*d=current;U list,node,count=0,id=0,steps=0,i,cmd,def;BridgeAIPlayer*p=0;
 if(!d||!allowed(d)||!pl||!envelope||P(envelope,0)!=d->image+0x4dc574||!P(pl,8)||bai_player(d,P(pl,8))!=pl)return 0;
 list=P(envelope,4);for(node=list?P(list,8):0;node&&steps++<128;node=P(node,4)){U a=actor(d,P(node,0));if(a){count++;id=P(a,0x14);for(i=0;i<BAI_PLAYERS;i++)if(d->ai.players[i].worker==id&&d->ai.players[i].kingdom==P(P(pl,8),0x14))p=&d->ai.players[i];}}
 if(node||!p)return 0;cmd=P(envelope,0x10);def=cmd?P(cmd,8):0;
 if(count==1&&id==p->worker&&((p->slot&&p->slot<=JOBS&&d->jobs[p->slot-1].id==id)||(bridge_networked(d)&&!p->slot))&&def&&(eq((W*)P(def,8),"move")||eq((W*)P(def,8),"guard")||eq((W*)P(def,8),"stop")||eq((W*)P(def,8),"construct")||eq((W*)P(def,8),"repair"))){d->ai.guardedCommands++;return 1;}
 d->ai.lastSAICommand=def;d->ai.abortReason=5;bai_finish(d,p,F(d->world,0xe8),0);return 0;
}
static void bridge_ai_tick(Roads*d,float now){BridgeAI*b=&d->ai;U sai=P(d->image,0x5f3fc8),list,n,pl,k,i;BridgeAIPlayer*p;
 if(!bridge_authority(d)||!sai||!(list=P(sai,0x6c))||!(n=P(sai,0x70))||n>96)return;
 if(b->world!=d->world){bridge_ai_clear(d);b->world=d->world;b->nextStep=now+20;for(i=0;i<BAI_PLAYERS;i++)b->players[i].next=now+20+i*.15f;
  for(i=0;i<n;i++){pl=P(list,i*4);k=pl?P(pl,8):0;if(k&&bai_player(d,k)==pl)bai_restore_worker(d,pl,&b->players[i],now);}
 }
 if(now<b->nextStep)return;b->nextStep=now+.1f;bai_watch(d,now);
 if(b->planning){U pts[32],cn=0,builder=actor(d,b->company);float fraction;
  p=&b->players[b->planning-1];k=bai_kingdom(d,p->kingdom);pl=bai_player(d,k);
  if(!builder||!pl||P(builder,0xe8)!=k||!bai_idle(d,builder)||p->worker||now-b->started>20||!bai_purpose_live(d,pl,b->source,b->target,b->kind,b->tx,b->ty)){b->planning=0;return;}
  /* Probe the crossing and neighbouring banks along the river. A direct
   * source-to-goal chord can hit city walls or an unusable landing; shifting
   * beside it still has to prove the complete route improvement. */
  if(b->kind==6){U probes=0;for(i=0;i<12&&b->sample<b->samples&&probes<1;i++){int dx,dy,x,y;bai_river_sample(b->sample++,&dx,&dy);x=(integer(b->sx)>>1)+dx*4;y=(integer(b->sy)>>1)+dy*4;
    if(!bai_known(d,k,x*2+1,y*2+1)||!bridge_wet(d,x,y))continue;cn=bridge_auto(d,x,y,pts);probes++;b->candidates++;b->goalType++;if(cn)bai_candidate(d,p,k,builder,pts,cn,now);if(b->bestN)break;
   }}else if(!b->probe)for(i=0;i<12&&b->sample<b->samples;i++){int x,y;float length;
   fraction=(float)(++b->sample)/(float)(b->samples+1);x=integer((b->sx+(b->tx-b->sx)*fraction)*.5f);y=integer((b->sy+(b->ty-b->sy)*fraction)*.5f);
   if(bridge_wet(d,x,y)||bridge_wet(d,x-2,y)||bridge_wet(d,x+2,y)||bridge_wet(d,x,y-2)||bridge_wet(d,x,y+2)){
    length=bai_dist(b->sx,b->sy,b->tx,b->ty);b->probe=1;b->probeX=x;b->probeY=y;b->probeDX=(b->ty-b->sy)/length;b->probeDY=(b->sx-b->tx)/length;break;}}
  if(b->kind!=6&&b->probe){U at=b->probe-1;float offset=at?((at+1)/2)*4:0;int x,y;if(at&1)offset=-offset;
   x=bg_round(b->probeX+b->probeDX*offset);y=bg_round(b->probeY+b->probeDY*offset);
   cn=bridge_auto(d,x,y,pts);b->candidates++;b->goalType++;if(cn)bai_candidate(d,p,k,builder,pts,cn,now);else b->refusals[0]++;
   if(++b->probe>7)b->probe=0;
  }
  if((b->probe||b->sample<b->samples)&&(b->kind==6?!b->bestN:b->goalType<21))return;
  if(b->bestN&&bai_live_jobs(d)<6){BridgeGeometry bestGeometry=bg_points(b->bestPoints,b->bestN);float check=b->kind==6?0:bai_baseline(d,b->sx,b->sy,b->tx,b->ty,k),after=b->kind==6?0:bai_distance(d,b->sx,b->sy,b->tx,b->ty,k,b->bestPoints,b->bestN,1);U free=0;
   for(i=0;i<JOBS;i++)if(!d->jobs[i].id)free++;
   if(free>2&&bai_budget(d,k,builder,b->bestMaterial,bg_model(&bestGeometry))&&(b->kind==6||bai_useful(check,after))&&bridge_valid(d,b->bestPoints,b->bestN,0)&&bai_channel_margin(d,k,b->bestPoints,b->bestN)&&bai_spaced(d,k,b->bestPoints,b->bestN,P(builder,0x14))&&!bridge_occupied(d,b->bestPoints,b->bestN,P(builder,0x14))){int slot=bridge_networked(d)?(bridge_net_send(d,builder,b->bestPoints,b->bestN,b->bestMaterial)?-2:-1):bridge_job_queue(d,builder,b->bestPoints,b->bestN,b->bestMaterial);if(slot>=0||slot==-2){BridgeGeometry g=bg_points(b->bestPoints,b->bestN);p->worker=b->company;p->slot=slot>=0?(U)slot+1:0;p->site=0;p->source=b->source;p->target=b->target;p->kind=b->kind;p->goalX=b->tx;p->goalY=b->ty;p->material=b->bestMaterial;p->x=g.x;p->y=g.y;p->started=p->progress=now;p->health=0;b->accepted++;}}
  }p->next=now+15;b->planning=0;return;
 }
 if(bai_live_jobs(d)>=6)return;
 for(i=0;i<n;i++){U index=b->cursor++%n;BridgeAIGoal goal;U builder;
  pl=P(list,index*4);k=pl?P(pl,8):0;if(!k||bai_player(d,k)!=pl)continue;p=&b->players[index];
  if(p->kingdom&&p->kingdom!=P(k,0x14)){U j;for(j=0;j<sizeof(*p)/4;j++)P(p,j*4)=0;}p->kingdom=P(k,0x14);
  if(p->worker||now<p->next||now<p->cooldown)continue;p->next=now+15;builder=bai_worker(d,pl);if(!builder)continue;
  if(bai_adopt(d,pl,p,builder,now))return;
  if(!bai_budget(d,k,builder,0,5)&&!bai_budget(d,k,builder,1,5)){b->budgetRejected++;return;}
  /* Alternate strategic detours with nearby explored river crossings.
   * With no current army/city goal, an idle engineer can still improve access. */
  if((p->planCursor++&1)||!bai_goal(d,pl,builder,p,&goal)){goal.source=P(builder,0x14);goal.target=0;goal.kind=6;goal.sx=goal.x=F(builder,0x20);goal.sy=goal.y=F(builder,0x24);}
  b->sx=goal.sx;b->sy=goal.sy;b->tx=goal.x;b->ty=goal.y;b->source=goal.source;b->target=goal.target;b->kind=goal.kind;
  b->baseline=b->kind==6?0:bai_baseline(d,b->sx,b->sy,b->tx,b->ty,k);if(b->baseline>=BAI_UNKNOWN)return;
  b->planning=index+1;b->company=P(builder,0x14);b->started=now;b->sample=0;b->goalType=0;b->probe=0;b->samples=integer(bai_dist(b->sx,b->sy,b->tx,b->ty)/6);if(b->samples>512)b->samples=512;if(b->samples<12)b->samples=12;if(b->kind==6)b->samples=1681;b->bestN=0;b->scans++;return;
 }
}
EXPORT const U bridge_ai_layout[]={offsetof(Roads,ai),sizeof(BridgeAI),offsetof(BridgeAI,players),sizeof(BridgeAIPlayer),offsetof(BridgeAI,scans)};
EXPORT const U bridge_ai_diagnostics[]={offsetof(BridgeAI,refusals),offsetof(BridgeAI,candidateX),offsetof(BridgeAI,lastSAICommand)};
EXPORT const U bridge_ai_job_layout[]={offsetof(Roads,jobs),sizeof(Job),offsetof(Roads,jobTools),offsetof(Roads,construction),offsetof(Roads,siteCommitted),JOBS};
EXPORT void bridge_ai_check_tick(Roads*d,float now){bridge_ai_tick(d,now);}

