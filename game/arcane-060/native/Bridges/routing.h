/* Local single-player bridge routing. Orders and saved native paths remain
 * owned by the game. The running static AI analysis is never rebuilt or freed. */
typedef struct {U stamp,parent,cost,heap;} BridgeRouteNode;
typedef struct {float x,y;} BridgeRoutePoint;
#ifdef PAWS_BRIDGE_ROUTE_TRACE
EXPORT U bridge_route_trace[1+256*10];
#endif
static U br_h(U cell,U goal,U width){int x=(int)(cell%width)-(int)(goal%width),y=(int)(cell/width)-(int)(goal/width);if(x<0)x=-x;if(y<0)y=-y;return 10*(x+y)-6*(x<y?x:y);}
static U br_score(BridgeRouteNode*n,U cell,U goal,U width){return n[cell].cost+br_h(cell,goal,width);}
static int br_less(BridgeRouteNode*n,U a,U b,U goal,U width){U x=br_score(n,a,goal,width),y=br_score(n,b,goal,width);return x<y||(x==y&&n[a].cost>n[b].cost);}
static void br_up(BridgeRouteNode*n,U*heap,U at,U goal,U width){U item=heap[at],p;while(at){p=(at-1)/2;if(!br_less(n,item,heap[p],goal,width))break;heap[at]=heap[p];n[heap[at]].heap=at;at=p;}heap[at]=item;n[item].heap=at;}
static U br_pop(BridgeRouteNode*n,U*heap,U*count,U goal,U width){U result=heap[0],item=heap[--*count],at=0,c;if(*count){while((c=at*2+1)<*count){if(c+1<*count&&br_less(n,heap[c+1],heap[c],goal,width))c++;if(!br_less(n,heap[c],item,goal,width))break;heap[at]=heap[c];n[heap[at]].heap=at;at=c;}heap[at]=item;n[item].heap=at;}n[result].heap=0xffffffff;return result;}
static int br_open(U tiles,U cell){return !(P(tiles+cell*0x30,0x20)&0x100);}
/* Supercover line-of-sight on the same live walking grid as native fine
 * planning. Corner checks prevent a smoothed segment cutting through a bank. */
static int br_visible(U tiles,U from,U to,U width){int x=from%width,y=from/width,tx=to%width,ty=to/width,dx=tx-x,dy=ty-y,sx=dx<0?-1:1,sy=dy<0?-1:1,err,e;
 if(dx<0)dx=-dx;if(dy<0)dy=-dy;err=dx-dy;
 for(;;){int nx=x,ny=y;if(!br_open(tiles,y*width+x))return 0;if(x==tx&&y==ty)return 1;e=err*2;if(e>-dy){err-=dy;nx+=sx;}if(e<dx){err+=dx;ny+=sy;}
  if(nx!=x&&ny!=y&&(!br_open(tiles,y*width+nx)||!br_open(tiles,ny*width+x)))return 0;x=nx;y=ny;
 }
}
EXPORT U bridge_route_clear_check(U tiles,U from,U to,U width){return br_visible(tiles,from,to,width);}
static int br_bridge(Roads*d,U cell,U width){U i;float x=(cell%width)*2+1,y=(cell/width)*2+1;for(i=0;i<d->bridgeCount;i++){BridgeSpan*s=&d->spans[i];U a=actor(d,s->id),j,key=(cell%width)|((cell/width)<<16);BridgeGeometry g=bg_span(s);if(a&&s->opened&&!(P(a,8)&3)&&!(P(a,0x100)&0x200000)&&bg_nav(&g,x,y)){
  /* The dry ends of a long model are ordinary approach terrain. Routing
   * through its entire footprint forces an artificial detour to the tip. */
  if(!s->originalCount){U map=P(d->world,0x30),c=P(map,0x28)+cell*0x30,def=P(c,0);
   /* Older private saves can lack the original-water metadata. Their
    * converted wet tiles still identify the actual traversable channel. */
   if(!def||eq((W*)P(def,8),"paws_engineer_bridge01"))return i+1;continue;
  }
  for(j=0;j<s->originalCount&&j<256;j++)if(s->originalPoints[j]==key)return i+1;
 }}return 0;}
/* Return a complete route or nothing; never emit a partial queue on exhaustion.
 * An octile A* uses the live walkable grid, including completed bridge cells.
 * Search and number of queued points are explicitly bounded. */
EXPORT U bridge_route_plan(Roads*d,float sx,float sy,float dx,float dy,BridgeRoutePoint*out){
 U map=P(d->world,0x30),width=P(map,0x1c),height=P(map,0x20),tiles=P(map,0x28),cells=width*height,start,goal,i,heapCount=0,expanded=0,stamp,here,next,cost,steps=0,ports=0,active=0;int x,y,xx,yy,b;BridgeRouteNode*n;U*heap;
 if(!width||!height||width>1024||height>1024||!tiles||!finite(sx)||!finite(sy)||!finite(dx)||!finite(dy)||sx<0||sy<0||dx<0||dy<0||sx>=width*2||dx>=width*2||sy>=height*2||dy>=height*2)return 0;
 start=(integer(sy)>>1)*width+(integer(sx)>>1);goal=(integer(dy)>>1)*width+(integer(dx)>>1);
 if(start==goal||!br_open(tiles,start)||!br_open(tiles,goal))return 0;
 if(d->routeCells!=cells){
  if(d->routeMemory)((void(*)(U,U))(d->image+0x3e1285))(d->routeMemory,d->routeCells*20);
  d->routeMemory=((U(*)(U))(d->image+0x2ef03c))(cells*20);d->routeCells=d->routeMemory?cells:0;d->routeStamp=0;
  if(!d->routeMemory)return 0;for(i=0;i<cells;i++)P(d->routeMemory,i*16)=0;
 }
 n=(BridgeRouteNode*)d->routeMemory;heap=(U*)(n+cells);stamp=++d->routeStamp;
 if(!stamp){for(i=0;i<cells;i++)n[i].stamp=0;stamp=++d->routeStamp;}
 n[start].stamp=stamp;n[start].cost=0;n[start].parent=start;n[start].heap=0;heap[heapCount++]=start;
 while(heapCount&&expanded<16384){here=br_pop(n,heap,&heapCount,goal,width);expanded++;if(here==goal)break;x=here%width;y=here/width;
  for(yy=y-1;yy<=y+1;yy++)for(xx=x-1;xx<=x+1;xx++){
   if(xx<0||yy<0||xx>=(int)width||yy>=(int)height||(xx==x&&yy==y))continue;
   next=yy*width+xx;if(!br_open(tiles,next))continue;
   if(xx!=x&&yy!=y&&(!br_open(tiles,y*width+xx)||!br_open(tiles,yy*width+x)))continue;
   cost=n[here].cost+(xx!=x&&yy!=y?14:10);
   if(n[next].stamp==stamp){if(cost>=n[next].cost||n[next].heap==0xffffffff)continue;n[next].cost=cost;n[next].parent=here;br_up(n,heap,n[next].heap,goal,width);}
   else{n[next].stamp=stamp;n[next].cost=cost;n[next].parent=here;heap[heapCount]=next;n[next].heap=heapCount;br_up(n,heap,heapCount++,goal,width);}
  }
 }
 d->routeExpanded=expanded;if(here!=goal)return 0;
 /* String-pull the actual walking route. Keep only turns whose removal
  * would cross blocked terrain, rather than forcing evenly spaced centreline
  * points along a model. The native fine planner and collision steering own
  * every step between these ordinary coarse waypoints. */
 here=goal;active=goal;out[ports].x=dx;out[ports++].y=dy;b=br_bridge(d,here,width)!=0;
 for(;;){U parent;if(br_bridge(d,here,width))b=1;if(here==start)break;parent=n[here].parent;
  if(!br_visible(tiles,active,parent,width)){
   if(ports>=63||here==active)return 0;out[ports].x=(here%width)*2+1;out[ports++].y=(here/width)*2+1;active=here;
  }
  here=parent;if(++steps>cells)return 0;
 }
 if(!b)return 0;
 for(i=0;i<ports/2;i++){BridgeRoutePoint p=out[i];out[i]=out[ports-1-i];out[ports-1-i]=p;}return ports;
}
static int br_ground_target(Roads*d,U mind,U target,float*out){U a=target?actor(d,target):0,cmd=P(mind,0x20),company=P(mind,4),n,axis;BridgeGeometry g;float along,side;
 if(!a||!company||(P(a,0x100)&0x200000)||!bridge_kind(P(a,4),&n,&axis))return 0;
 /* Attack/repair/construction retain their explicit object interaction. */
 if(cmd&&(!P(cmd,8)||P(P(cmd,8),0xc)!=5))return 0;
 if((P(mind,0x160)==d->image+0x4f4efc&&P(mind,0x16c)==2)||(P(mind,0x17c)==d->image+0x4f4f28&&P(mind,0x188)==2))return 0;
 g=bg_actor(a,n,axis);along=(F(company,0x20)-g.x)*g.ux+(F(company,0x24)-g.y)*g.uy;side=along>0?-1:1;
 out[0]=g.x+g.ux*(g.half+2.5f)*side;out[1]=g.y+g.uy*(g.half+2.5f)*side;return 1;
}
/* Resuming an interrupted native repair/construction order must approach a
 * usable bank. The bridge centre may still be impassable water. Only the
 * movement sub-state changes; the native command keeps its bridge target. */
static int br_work_target(Roads*d,U mind,U target,float*out){U a=target?actor(d,target):0,cmd=mind?P(mind,0x20):0,company=mind?P(mind,4):0,n,axis,pts[32],bank;BridgeGeometry g;float side;
 if(!a||!company||!P(company,0x7c)||P(company,0xe8)!=P(a,0xe8)||!cmd||!P(cmd,8)||P(cmd,0x10)!=target||(P(P(cmd,8),0xc)!=3&&P(P(cmd,8),0xc)!=4)||!bridge_kind(P(a,4),&n,&axis))return 0;
 g=bg_actor(a,n,axis);n=bg_line(bg_round((g.x-g.ux*g.half-1)*.5f),bg_round((g.y-g.uy*g.half-1)*.5f),bg_round((g.x+g.ux*g.half-1)*.5f),bg_round((g.y+g.uy*g.half-1)*.5f),pts);
 if(!n||!(bank=bridge_approach(d,company,pts,n)))return 0;
 side=bank==1?-1:1;out[0]=g.x+g.ux*(g.half+2.5f)*side;out[1]=g.y+g.uy*(g.half+2.5f)*side;
 if(!passable(d,integer(out[0])>>1,integer(out[1])>>1)){out[0]=g.x+g.ux*g.half*side;out[1]=g.y+g.uy*g.half*side;}
 return 1;
}
/* Native roaming AI can choose a bridge as an object destination, then wait
 * outside its building radius forever. A travel order crosses to the far
 * landing instead; explicit attack, repair and construction are unaffected. */
EXPORT U FAST bridge_move_to_actor(U self,U unused,U mode,U target,U formation,U fx,U fy){Roads*d=current;U args[6];float xy[2];
 if(d&&allowed(d)&&(br_work_target(d,P(self,4),target?P(target,0x14):0,xy)||br_ground_target(d,P(self,4),target?P(target,0x14):0,xy))){
  args[0]=mode;F(args,4)=xy[0];F(args,8)=xy[1];args[3]=formation;args[4]=fx;args[5]=fy;
  return ((NativeCall)d->call)(d->image+0x26f1cf,self,6,args);
 }
 args[0]=mode;args[1]=target;args[2]=formation;args[3]=fx;args[4]=fy;return ((NativeCall)d->call)(d->image+0x26f0d1,self,5,args);
}
/* Native region waypoints guide its bounded fine search. An empty coarse
 * path lets that search pick a convenient but longer crossing. Feed the live
 * shortest route's bridge landings into the ordinary native path instead.
 * These are path segments, never extra commands in the player's order queue. */
static void br_native_ports(Roads*d,U path,BridgeRoutePoint*ports,U count,float dx,float dy,U mover){U i,node[8];float x=dx,y=dy;
 /* Native coarse nodes describe obstacle/region transitions, not the final
  * order destination. That destination already belongs to the fine planner.
  * Queuing it again as a type-2 gate makes every member converge on one
  * point and keeps a company in its crossing column on the open far bank. */
 (void)mover;
 if(count&&bg_abs(ports[count-1].x-dx)<.001f&&bg_abs(ports[count-1].y-dy)<.001f)count--;
 for(i=count;i>0;i--){float px=ports[i-1].x,py=ports[i-1].y,vx=x-px,vy=y-py,length;
  length=bg_sqrt(vx*vx+vy*vy);
  F(node,0)=px;F(node,4)=py;F(node,8)=length?vx/length:0;F(node,12)=length?vy/length:0;node[4]=2;node[5]=0;F(node,24)=px;F(node,28)=py;
  m1(d,0x27b99b,path,(U)node);x=px;y=py;
 }
}
EXPORT U FAST bridge_region_route(U solver,U unused,U path,float sx,float sy,float dx,float dy,U query){Roads*d=current;U args[6],a=query?P(query,0x1c):0;BridgeRoutePoint ports[64];
#ifdef PAWS_BRIDGE_ROUTE_TRACE
 if(d&&a){U e=P(a,0x80),*row=bridge_route_trace+1+(bridge_route_trace[0]++%256)*10;row[0]=P(a,0x14);row[1]=e&&P(e,0x10)?P(P(e,0x10),0x14):0;F(row,8)=sx;F(row,12)=sy;F(row,16)=dx;F(row,20)=dy;F(row,24)=F(a,0x20);F(row,28)=F(a,0x24);row[8]=P(a,8);F(row,36)=F(d->world,0xe8);}
#endif
 if(d&&allowed(d)&&d->bridgeCount&&d->world==P(d->image,0x5f3fb8)&&!P(path,4)&&a&&actor(d,P(a,0x14))==a&&!(P(a,8)&0x201000)){
  U from=finite(sx)&&finite(sy)?tile(d,integer(sx)>>1,integer(sy)>>1):0,to=finite(dx)&&finite(dy)?tile(d,integer(dx)>>1,integer(dy)>>1):0;
  d->routeCalls++;
  U count=bridge_route_plan(d,sx,sy,dx,dy,ports);
  if(count){br_native_ports(d,path,ports,count,dx,dy,a);P(path,0x18)=0xffffffff;d->routeQueued++;return 1;}
  /* Preserve the connectivity fallback if a bounded grid probe is exhausted. */
  if(from&&to&&bridge_native_island(from)!=bridge_native_island(to)&&bridge_walk_island(from,0)==bridge_walk_island(to,0)){d->routeQueued++;return 1;}
  d->routeFallback++;
 }
 args[0]=path;F(args,4)=sx;F(args,8)=sy;F(args,12)=dx;F(args,16)=dy;args[5]=query;
 return ((NativeCall)d->call)(d->image+0x263752,solver,6,args);
}
/* Upgrade still-running point moves from older saves once, without discarding
 * queued user orders or interfering with battles, construction or retreat. */
static void bridge_route_restore(Roads*d){U end,reg=P(d->image,0x5ef72c),a,mind;
 if(!reg||!d->routeRestoreCursor||!d->bridgeCount)return;
 end=d->routeRestoreCursor+256;if(end>65536)end=65536;
 for(;d->routeRestoreCursor<end;d->routeRestoreCursor++){
  a=P(reg,0x20004+d->routeRestoreCursor*4);
  if(!a||P(a,0)!=d->image+0x4e5c58||!P(a,0x7c))continue;
  mind=P(a,0x70);
  if(mind&&P(mind,0x68)==d->image+0x4f4df0&&P(mind,0x74)==2){float xy[2];U args[2];BridgeRoutePoint ports[64];
   if(br_ground_target(d,mind,P(mind,0x78),xy)){P(mind,0x78)=0;F(args,0)=xy[0];F(args,4)=xy[1];((NativeCall)d->call)(d->image+0x26f786,mind+0x68,2,args);}
   if(!P(mind,0x78)&&bridge_route_plan(d,F(a,0x20),F(a,0x24),F(mind,0x84),F(mind,0x88),ports))m0(d,0x26f772,mind+0x68);
  }
 }
 if(end==65536)d->routeRestoreCursor=0;
}
/* Context picking alone treats a finished owned bridge as land. Left-click
 * selection, repair during construction and enemy attack targeting stay native. */
EXPORT U bridge_context_pick(Roads*d,U self){U view=m0(d,0x2d8c10,self),a,n,axis;
 if(d&&allowed(d)&&view&&(a=P(view,0x14))&&actor(d,P(a,0x14))==a&&!(P(a,0x100)&0x200000)&&bridge_kind(P(a,4),&n,&axis)){
  U ui=P(d->image,0x5f3fbc),camera=P(d->image,0x5fafe0);float z=F(a,0x28)+(bridge_wood(P(a,4))?.1f:0),x,y,t,dz,along,across;BridgeGeometry g=bg_actor(a,n,axis);
  camera=camera?P(camera,0):0;
  /* The ordinary world cursor intersects the submerged river bed, not the
   * picked model. Intersect the same camera ray with the deck plane. */
  if(!ui||!camera||!finite(z))return view;dz=F(ui,0x18c)-F(camera,0x98);if(bg_abs(dz)<.001f)return view;
  t=(z-F(camera,0x98))/dz;if(!finite(t)||t<0||t>1.2f)return view;
  x=F(camera,0x90)+(F(ui,0x184)-F(camera,0x90))*t;y=F(camera,0x94)+(F(ui,0x188)-F(camera,0x94))*t;
  if(!finite(x)||!finite(y))return view;
  along=(x-g.x)*g.ux+(y-g.y)*g.uy;across=(x-g.x)*g.uy-(y-g.y)*g.ux;
  if(along>g.half)along=g.half;if(along<-g.half)along=-g.half;
  if(across>2.8f)across=2.8f;if(across<-2.8f)across=-2.8f;
  F(ui,0x184)=g.x+g.ux*along+g.uy*across;F(ui,0x188)=g.y+g.uy*along-g.ux*across;F(ui,0x18c)=z;return 0;
 }
 return view;
}
/* This static native floor function has no ECX receiver. Its call site is
 * scoped to destination markers; ECX is merely a volatile scratch register. */
EXPORT U bridge_marker_floor(Roads*d,U ui,float*xy,U flags,U original){return bridge_floor(d,d->world,xy,flags,original);}
/* Persistent queued-command flags are created by FXC, independently of the
 * short-lived click marker. Raise only waypoint models, never terrain FX. */
EXPORT U FAST bridge_waypoint_position(U self,U unused,U event,U owner,float*xyz){Roads*d=current;U args[3],result,def=P(self,0x3c);const W*name=def?(W*)P(def,8):0;
 args[0]=event;args[1]=owner;args[2]=(U)xyz;result=((NativeCall)d->call)(d->image+0x2c6a85,self,3,args);
 if(result&&name&&bridge_prefix(name,"waypoint_")&&xyz)P(xyz,8)=bridge_floor(d,d->world,xyz,0x222,P(xyz,8));
 return result;
}
