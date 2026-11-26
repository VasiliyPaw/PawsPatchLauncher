/* Native engineer construction menu and brush preview. The stock brush owns
 * model resources, red/green tint, input capture, cancellation and placement
 * sounds. Only bridge plans replace the ordinary single-building footprint. */
static U bridge_definition_owner(Roads*d,U n,U axis,U wood,U kingdom){W name[48];U db=P(d->image,0x5f3fb4),key,result;
 if(!db)return 0;bridge_name_for(name,wood,axis,n,bridge_style(kingdom));
 key=str(d,name);result=m1(d,0x2edb9,P(db,0xc),key);release(d,key);return result;
}
static U bridge_definition(Roads*d,U n,U axis,U wood){return bridge_definition_owner(d,n,axis,wood,local(d));}
/* Use the same modified cost vector, affordability and stockpile methods as
 * native Builder::BuildActor. A queued crossing spends nothing; construction
 * records its paid vector for the ordinary native cancellation/refund UI. */
static int bridge_funds(Roads*d,U def,U company,U site){float storage[32];U vector[3],n,k,u;
 if(!def||!company||!(k=P(company,0xe8)))return 0;
 if(site&&bridge_metadata_present((W*)P(site,0x18))&&bridge_paid(site))return 1;
 n=P(def,0x328);
 if(!n)return 1;if(n>32||P(k,0x1d0)!=n)return 0;
 vector[0]=(U)storage;vector[1]=vector[2]=n;u=worker(d,company);if(!u)u=company;
 invoke(d,0x29eaa,def,2,(U)vector,m0(d,0x2277b6,u));
 if(!(m1(d,0x2351d7,k,(U)vector)&255))return 0;
 if(site&&(!bridge_metadata_present((W*)P(site,0x18))||!bridge_paid(site))){m1(d,0x2359d8,k,(U)vector);if(P(site,0x9c))m1(d,0x205b0f,P(site,0x9c),(U)vector);bridge_mark_paid(d,site);}
 return 1;
}
EXPORT U bridge_funds_check(Roads*d,U def,U company,U site){return bridge_funds(d,def,company,site);}
/* A menu prototype is only the building brush's catalogue entry. The brush
 * always queues a validated length-specific actor before committing. Stock
 * SAI construction bypasses that brush and used to spawn this entry on land.
 * Scope rejection to construct/summon actor-creation calls: loading old actors,
 * ordinary actors, capability checks and the human menu remain unchanged. */
static int bridge_menu_prototype(U def){const W*w=def?(W*)P(def,8):0,*tail=bridge_tail(def);return w&&(eq(w,"paws_bridge_site")||eq(tail,"wood_site")||eq(tail,"stone_site"));}
EXPORT U FAST bridge_builder_spawn(U world,U unused,U context){Roads*d=current;
 if(d&&allowed(d)&&context&&bridge_menu_prototype(P(context,4)))return 0;
 return d?m1(d,0x242eee,world,context):0;
}
EXPORT U FAST bridge_builder_spawn_alternate(U world,U unused,U context){Roads*d=current;
 if(d&&allowed(d)&&context&&bridge_menu_prototype(P(context,4)))return 0;
 return d?m1(d,0x242fcd,world,context):0;
}
/* Native construct-request entry has FIVE stack arguments (RET20). Reject
 * catalogue-only bridge definitions before its separate foundation actor is
 * created or any unit receives a work command. Human bridge brush acceptance
 * and our paid bridge transaction queue do not invoke this native request. */
EXPORT U FAST bridge_construct_request(U self,U unused,U definition,U kingdom,U position,U direction,U options){Roads*d=current;U args[5];
 if(d&&allowed(d)&&bridge_menu_prototype(definition))return 0;
 args[0]=definition;args[1]=kingdom;args[2]=position;args[3]=direction;args[4]=options;
 return d?((NativeCall)d->call)(d->image+0x28c365,self,5,args):0;
}
/* A visible menu entry represents every length/orientation. Preserve native
 * construction target checks while resolving variants through that entry. */
EXPORT U FAST bridge_can_build(U list,U unused,U*definition){Roads*d=current;U n,axis,db,key,generic;
 if(!d)return 0;
 if(allowed(d)&&definition&&bridge_kind(*definition,&n,&axis)){
  db=P(d->image,0x5f3fb4);if(db){key=str(d,bridge_menu(bridge_style_def(*definition),bridge_wood(*definition)));generic=m1(d,0x2edb9,P(db,0xc),key);release(d,key);
   if(generic){U result=m1(d,0x2f397,list,(U)&generic);if(result||!bridge_style_def(*definition))return result;}
   key=str(d,bridge_menu(0,bridge_wood(*definition)));generic=m1(d,0x2edb9,P(db,0xc),key);release(d,key);if(generic)return m1(d,0x2f397,list,(U)&generic);
  }
 }return m1(d,0x2f397,list,(U)definition);
}
static int bridge_brush(Roads*d,U self){U def=P(self,0x18);return def&&(eq((W*)P(def,8),"paws_bridge_site")||bridge_prefix((W*)P(def,8),"paws_bridge_"));}
/* Building ZOC over water cannot reliably reach a land company. Use a bridge's
 * footprint for company approach gates; individual build/attack abilities
 * retain their own eligibility, ownership and range rules. */
EXPORT U FAST bridge_work_range(U ai,U unused,U target){Roads*d=current;U n,axis,a;float dx,dy,along,across;
 if(d&&allowed(d)&&target&&!(P(target,8)&3)&&bridge_kind(P(target,4),&n,&axis)){
  a=P(ai,4);if(a&&P(a,0xe8)&&P(a,0x7c)){
   BridgeGeometry g=bg_actor(target,n,axis);dx=F(a,0x20)-g.x;dy=F(a,0x24)-g.y;
   along=bg_abs(dx*g.ux+dy*g.uy)-g.half;across=bg_abs(dx*g.uy-dy*g.ux)-3;dx=along>0?along:0;dy=across>0?across:0;
   if(dx*dx+dy*dy<=9)return 1;
  }
 }return d?m1(d,0x275a71,ai,target):0;
}
static int bridge_wet(Roads*d,int x,int y){return bridge_channel(d,x,y); }
/* Reject stale flagged ground before the angle search. Real channels have
 * higher dry banks in at least two directions. This keeps failed AI scans
 * bounded without assuming an absolute water level or native waterbody ID. */
static int bridge_channel_shores(Roads*d,int x,int y){int direction,step,shores=0;float bed=bridge_height(d,x,y);
 if(!finite(bed))return 0;for(direction=0;direction<8;direction++){int dx=direction==0||direction==4||direction==7?1:direction==2||direction==5||direction==6?-1:0,dy=direction==1||direction==4||direction==5?1:direction==3||direction==6||direction==7?-1:0;
  for(step=1;step<=20;step++){int xx=x+dx*step,yy=y+dy*step;U c=tile(d,xx,yy);if(!c)break;if(bridge_wet(d,xx,yy))continue;
   if(!(P(c,0x20)&0x100)&&(P(c,0x20)&0x70)!=0x20&&bridge_height(d,xx,yy)>=bed+.35f)shores++;break;
  }if(shores>=2)return 1;
 }return 0;
}
/* Estimate the local river normal from wet-cell covariance, then test nearby
 * angles. Endpoints and the native model use exactly the same straight span. */
static U bridge_auto(Roads*d,int mx,int my,U*points){int dx,dy,radius,best=0x7fffffff;U count=0;
 if(!bridge_hm(d))return 0;
 for(radius=0;radius<=18;radius++)for(dy=-3;dy<=3;dy++)for(dx=-3;dx<=3;dx++){
  int x=mx+dx,y=my+dy,xx,yy,k;float sx=0,sy=0,xxs=0,yys=0,xys=0,total=0,A,D,Bv,lambda,ux,uy,length;
  /* The score lower bound permits closest-first pruning without changing
   * the selected geometry, instead of repeating 49 costly angle searches. */
  if(dx*dx+dy*dy!=radius||radius*128>=best||!bridge_wet(d,x,y)||!bridge_channel_shores(d,x,y))continue;
  for(yy=-7;yy<=7;yy++)for(xx=-7;xx<=7;xx++)if(xx*xx+yy*yy<=49&&bridge_wet(d,x+xx,y+yy)){sx+=xx;sy+=yy;xxs+=xx*xx;yys+=yy*yy;xys+=xx*yy;total++;}
  A=xxs-sx*sx/total;D=yys-sy*sy/total;Bv=xys-sx*sy/total;
  lambda=(A+D-bg_sqrt((A-D)*(A-D)+4*Bv*Bv))*.5f;
  if(bg_abs(Bv)>.001f){ux=Bv;uy=lambda-A;}else{ux=A<D?1:0;uy=A<D?0:1;}
  length=bg_sqrt(ux*ux+uy*uy);ux/=length;uy/=length;
  for(k=0;k<11;k++){
   float vx,vy,left=0,right=0,c=1,s=0,landing;int step,n,i,score;U candidate[32];BridgeGeometry g;
   if(k==1||k==2){c=.9659258f;s=k==1?.258819f:-.258819f;}
   if(k==3||k==4){c=.8660254f;s=k==3?.5f:-.5f;}
   if(k==5||k==6){c=.7071068f;s=k==5?.7071068f:-.7071068f;}
   vx=ux*c-uy*s;vy=ux*s+uy*c;
   if(k==7){vx=1;vy=0;}if(k==8){vx=0;vy=1;}if(k==9){vx=.7071068f;vy=.7071068f;}if(k==10){vx=.7071068f;vy=-.7071068f;}
   for(step=1;step<=36;step++){left=step*.5f;if(!bridge_wet(d,bg_round(x-vx*left),bg_round(y-vy*left)))break;}if(step>36)continue;
   for(step=1;step<=36;step++){right=step*.5f;if(!bridge_wet(d,bg_round(x+vx*right),bg_round(y+vy*right)))break;}if(step>36||left+right>18)continue;
   landing=2+2*bg_abs(vx*vy);
   n=bg_line(bg_round(x-vx*(left+landing)),bg_round(y-vy*(left+landing)),bg_round(x+vx*(right+landing)),bg_round(y+vy*(right+landing)),candidate);if(n<5)continue;
   g=bg_points(candidate,n);score=(dx*dx+dy*dy)*128+integer(g.half*4);
   if(score>=best||!bridge_valid(d,candidate,n,0))continue;
   for(i=0;i<n;i++)points[i]=candidate[i];count=n;best=score;
  }
 }return count;
}
EXPORT U bridge_auto_check(Roads*d,int x,int y,U*points){return bridge_auto(d,x,y,points);}
EXPORT void FAST bridge_preview_tick(U self,U unused){Roads*d=current;U a,n,def;int x,y;float level[2];
 if(!d||!bridge_brush(d,self)){if(d)m0(d,0x11d95d,self);return;}
 d->previewMaterial=bridge_wood(P(self,0x18));
 if(eq((W*)P(P(self,0x18),8),"paws_bridge_site"))d->previewMaterial=bridge_material(d,local(d));
 d->previewValid=d->previewCount=0;
 if(!allowed(d)||!(a=selected(d)))return;
 /* A newly loaded paused match has not called roads_tick yet. The UI may
  * still inspect its terrain and queue an order for the first simulation tick. */
 if(!d->world)d->world=P(d->image,0x5f3fb8);
 if(!d->world||d->world!=P(d->image,0x5f3fb8))return;
 {U ui=P(d->image,0x5f3fbc);float fx=d->previewFixture?d->previewFixtureX:F(ui,0x184),fy=d->previewFixture?d->previewFixtureY:F(ui,0x188);
  if(!finite(fx)||!finite(fy)||fx<0||fy<0)return;x=integer(fx)>>1;y=integer(fy)>>1;
 }
 n=bridge_auto(d,x,y,d->previewPoints);
 if(n&&bridge_valid(d,d->previewPoints,n,level)){
  BridgeGeometry g=bg_points(d->previewPoints,n);
  def=bridge_definition(d,bg_model(&g),0,d->previewMaterial);
  if(def){
   F(self,0x24)=(float)((d->previewPoints[0]&65535)+(d->previewPoints[n-1]&65535))+1;
   F(self,0x28)=(float)((d->previewPoints[0]>>16)+(d->previewPoints[n-1]>>16))+1;
   F(self,0x2c)=(level[0]>level[1]?level[0]:level[1])+.08f;
   if(P(self,0x18)!=def){U v[3];v[0]=def;v[1]=P(self,0x40);v[2]=0;((NativeCall)d->call)(d->image+0x11dc4b,self,3,v);}
   F(self,0x34)=g.ux;F(self,0x38)=g.uy;F(self,0x3c)=0;
   d->previewCount=n;d->previewValid=bridge_approach(d,a,d->previewPoints,n)&&!bridge_occupied(d,d->previewPoints,n,P(a,0x14))&&bridge_funds(d,def,a,0);
  }
 }else{U ui=P(d->image,0x5f3fbc);F(self,0x24)=F(ui,0x184);F(self,0x28)=F(ui,0x188);F(self,0x2c)=F(ui,0x18c);}
 m0(d,0x11db7d,self);
}
EXPORT U FAST bridge_preview_valid(U self,U unused){Roads*d=current;
 if(d&&bridge_brush(d,self))return allowed(d)&&d->previewValid;
 return d?m0(d,0xd6b4f,self):0;
}
EXPORT void FAST bridge_preview_accept(U self,U unused){Roads*d=current;U a,i;
 if(!d)return;if(!bridge_brush(d,self)){m0(d,0xd6a13,self);return;}
 if(!allowed(d)||!d->previewValid||d->pending||!(a=selected(d)))return;
 if(bridge_networked(d)){if(bridge_net_send(d,a,d->previewPoints,d->previewCount,d->previewMaterial))m0(d,0x11db78,self);return;}
 d->count=d->previewCount;for(i=0;i<d->count;i++)d->points[i]=d->previewPoints[i];
 d->valid=1;d->pendingTool=1;d->pendingMaterial=d->previewMaterial;d->pending=P(a,0x14);
 m0(d,0x11db78,self);
}
/* Private QA input calls the same live brush as a mouse hover/release. The
 * shipping test plugin never invokes this entry point. */
EXPORT U bridge_preview_fixture(Roads*d,float x,float y,U accept){U self;
#ifdef PAWS_INSTALLED_RIVERS
 if(d)d->gameInterface=game_interface(d);
#endif
 if(!d||!allowed(d)||!d->gameInterface||!finite(x)||!finite(y))return 0;
 self=P(d->gameInterface,0xf0);if(!self||!bridge_brush(d,self))return 0;
 d->previewFixture=1;d->previewFixtureX=x;d->previewFixtureY=y;
 bridge_preview_tick(self,0);
 if(accept){bridge_preview_accept(self,0);d->previewFixture=0;}
 return d->previewValid;
}
