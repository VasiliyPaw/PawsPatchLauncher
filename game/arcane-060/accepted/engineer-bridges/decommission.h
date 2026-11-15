/* Saved native structure_razing state owns abandonment. No sidecar state or
 * wall clock is used; decay/healing follow the simulation's time delta. */
static void bridge_clear_doodads(Roads*d,U a);
static int bridge_actor(Roads*d,U a){U n,axis;return d&&a&&allowed(d)&&bridge_kind(P(a,4),&n,&axis);}
static int bridge_razing(U a){return (P(a,0x100)&0x40000000)!=0;}
EXPORT U FAST bridge_construction_commands(U self,U unused){Roads*d=current;U a=P(self,4),result=m0(d,0x20583d,self);
 if(bridge_actor(d,a)&&(P(a,0x100)&0x200000)&&!bridge_paid(a))P(a,0xf0)&=~(1u<<19);
 if(bridge_actor(d,a)&&!(P(a,8)&3)&&!(P(a,0x100)&0x200000)){
  U mask=(1u<<22)|(1u<<19);P(a,0xf0)=(P(a,0xf0)&~mask)|(bridge_razing(a)?(1u<<19):(1u<<22));
 }
 return result;
}
EXPORT U bridge_upkeep_active(U a){Roads*d=current;
 if(bridge_actor(d,a)&&bridge_razing(a))return 0;
 return ((U(*)(U))(d->image+0x20dbcb))(a);
}
/* Raze/cancel retain the stock confirmation and state transitions. Refresh
 * the native economy immediately rather than waiting for an economy tick. */
EXPORT U FAST bridge_raze_start(U self,U unused){Roads*d=current;U a=P(self,4),result=m0(d,0x205e72,self);
 if(bridge_actor(d,a))m0(d,0x22a99c,a);return result;
}
EXPORT U FAST bridge_raze_cancel(U self,U unused){Roads*d=current;U a=P(self,4),result=m0(d,0x205ec2,self);
 if(bridge_actor(d,a))m0(d,0x22a99c,a);return result;
}
/* The native property system supplies Haroun's 15 and Rapid Growth's +10.
 * Suppress its unconditional periodic pulse for bridges; apply the resulting
 * construction rate below only to an actually paid site, using game time.
 * Finished bridges retain their separately requested fractional repair. */
EXPORT U FAST bridge_periodic_heal(U body,U unused,U packet){Roads*d=current;U a=P(body,4);
 if(d&&bridge_actor(d,a)&&bridge_style_def(P(a,4))==6)return 0;
 return m1(d,0x202e47,body,packet);
}
EXPORT U FAST bridge_construct_heal(U body,U unused,U packet){Roads*d=current;U a=P(body,4),source=packet?P(packet,0):0,args[2];
 if(d&&bridge_actor(d,a)&&(P(a,0x100)&0x200000)&&!bridge_paid(a)){
  U element=source?P(source,0x80):0,company=element?P(element,0x10):0,pts[32],n,axis;BridgeGeometry g;
  if(!company||P(company,0xe8)!=P(a,0xe8)||!alive_worker(d,source)||!bridge_kind(P(a,4),&n,&axis))return 0;
  g=bg_actor(a,n,axis);n=bg_line(bg_round((g.x-g.ux*g.half-1)*.5f),bg_round((g.y-g.uy*g.half-1)*.5f),bg_round((g.x+g.ux*g.half-1)*.5f),bg_round((g.y+g.uy*g.half-1)*.5f),pts);
  if(!n||bridge_occupied(d,pts,n,P(a,0x14))||!bridge_funds(d,P(a,4),company,a))return 0;
  bridge_clear_doodads(d,a);
 }
 if(d&&allowed(d)&&a&&source&&(P(a,0x100)&0x200000)&&eq((W*)P(P(a,4),8),"haroun_keep")&&eq((W*)P(P(source,4),8),"caretaker")){
  args[0]=source;F(args,4)=F(packet,4)*5;return m1(d,0x202e47,body,(U)args);
 }
 return m1(d,0x202e47,body,packet);
}
static float bridge_growth_rate(U a){U props=P(a,0x78),n=props?P(props,0xc4):0,list=props?P(props,0xc0):0,i;float rate=0;
 if(list&&n<=32)for(i=0;i<n;i++){U modifier=P(list,i*4);float v=modifier?F(modifier,0xc):0;if(finite(v)&&v>0&&v<1000)rate+=v;}
 return rate;
}
static void bridge_health_tick(Roads*d,float dt){U i;
 if(!finite(dt)||dt<=0)return;
 for(i=0;i<d->bridgeCount;i++){U a=actor(d,d->spans[i].id),body,args[4];float hp,maxhp,next;
  if(!a||(P(a,8)&3)||!(body=P(a,0x60)))continue;
  hp=F(body,0x10);maxhp=F(body,0x14);if(!finite(hp)||!finite(maxhp)||hp<=0||maxhp<=0)continue;
  if(P(a,0x100)&0x200000){U construction=P(a,0x9c),paid=construction?P(construction,0x10):0;if(bridge_style_def(P(a,4))!=6||!bridge_paid(a)||!paid||!P(construction,0x14)||F(paid,0)<=0)continue;next=hp+bridge_growth_rate(a)*dt;}
  else if(bridge_razing(a))next=hp-maxhp*(bridge_wood(P(a,4))?.01f:.005f)*dt;
  else if(bridge_style_def(P(a,4))==6)next=hp+maxhp*.001f*dt;
  else continue;
  if(next>maxhp)next=maxhp;if(next<0)next=0;
  F(args,0)=next;args[1]=0;args[2]=1;args[3]=0;((NativeCall)d->call)(d->image+0x202f8c,body,4,args);
  if(next<=0)m1(d,0x245157,d->world,a);
 }
}
/* Same native decoration clearing used by ordinary structures, with the
 * bridge's oriented footprint. It never removes actors, cities or resources. */
static void bridge_clear_doodads(Roads*d,U a){U shape[6];
 shape[0]=P(a,4)+0x68;shape[1]=P(a,0x2c);shape[2]=P(a,0x30);shape[3]=P(a,0x20);shape[4]=P(a,0x24);shape[5]=0;
 m1(d,0x2428db,d->world,(U)shape);
}
EXPORT U bridge_health_check(Roads*d,float dt){bridge_health_tick(d,dt);return 1;}
static void bridge_health_fixture_tick(Roads*d){U a=actor(d,d->ownerPoints[0]),body,args[4];float hp=F(d->ownerPoints,4);if(!bridge_actor(d,a)||!(body=P(a,0x60)))return;if(hp>F(body,0x14))hp=F(body,0x14);F(args,0)=hp;args[1]=0;args[2]=1;args[3]=0;((NativeCall)d->call)(d->image+0x202f8c,body,4,args);if(hp<=0)m1(d,0x245157,d->world,a);}
/* Marked QA only: a real native construction actor, optionally charged by
 * the same transaction as a worker-started site. No workers supply extra HP. */
static void bridge_site_fixture_tick(Roads*d){U company=actor(d,d->ownerPoints[0]),wood=F(d->ownerPoints,4)!=0,paid=F(d->ownerPoints,8)!=0,pts[16],i,site,map=P(d->world,0x30);float level[2];int y=paid?40:60;
 if(!company||!map||P(map,0x1c)!=96||P(map,0x20)!=96)return;
 for(i=0;i<16;i++)pts[i]=(50+i)|((U)y<<16);
 if(!bridge_valid(d,pts,16,level)||bridge_occupied(d,pts,16,P(company,0x14)))return;
 site=bridge_object_create(d,pts,16,P(company,0xe8),(level[0]>level[1]?level[0]:level[1])+.08f,1,wood);
 if(site&&paid&&!bridge_funds(d,P(site,4),company,site))invoke(d,0x24338e,d->world,1,site,0);
}
static void bridge_rapid_fixture_tick(Roads*d){U a=actor(d,d->ownerPoints[0]),db=P(d->image,0x5f3fb4),key,def,props,i,n,list,has=0;
 if(!bridge_actor(d,a)||bridge_style_def(P(a,4))!=6||!db||!(props=P(a,0x78)))return;
 key=str(d,(W*)L"rapid_growth");def=m1(d,0x2edb9,P(db,0x464),key);release(d,key);if(!def)return;
 n=P(props,0x14);list=P(props,0x10);if(n>256)return;for(i=0;i<n;i++){U record=P(list,i*4);if(record&&P(record,0xc)==def){has=1;break;}}
 if(F(d->ownerPoints,4)!=0){if(!has){U args[3];args[0]=def;args[1]=args[2]=0;((NativeCall)d->call)(d->image+0x229f7b,a,3,args);}}
 else if(has)invoke(d,0x21c115,props,2,def,0);
}
