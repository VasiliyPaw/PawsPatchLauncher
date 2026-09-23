/* Runs after the player's native tactical update, on the AI thread. Reuses
 * the native goal lists, SelectGoals resource budget and activation protocol.
 * No planning is invoked from the render/frame observer or another thread. */
#define EXPANSION_PULSE_SECONDS 4
static int expansion_regions(U image,FastData*f,U pl){
 U regions=P(image,0x5f3fcc),table,n,registry=P(image,0x5ef72c),i;
 if(!regions||!registry)return 0;table=P(regions,0x14);n=P(regions,0x18);
 if(!table||!n||n>65536)return 0;
 for(i=0;i<2048;i++)f->expansionRegions[i]=0;
 for(i=0;i<65536;i++){
  U a=P(registry,0x20004+4*i),def,cell,region,id;
  if(!live_actor(image,a)||(P(a,8)&1))continue;def=P(a,4);
  if(!ids_equal(def,"marker_settlement")&&!(settlement_site(def)&&guarded_structure(image,a)))continue;
  cell=route_cell(image,F(a,0x20),F(a,0x24));
  if(!cell||!(((RouteM1)(image+0x24a845))(cell,0,P(pl,8))&255))continue;
  region=((ClearingRoute0)(image+0x2273c2))(a,0);if(!region)continue;id=P(region,0);
  if(id<n&&P(table,4*id)==region)f->expansionRegions[id>>5]|=1u<<(id&31);
 }
 return 1;
}
static int expansion_fast_goal(U image,U pl,U g){
 U target,def;
 if(!g||P(g,4)!=P(pl,0xc)||P(g,8)>2)return 0;
 if(P(g,0)==image+0x4da6b0){
  def=P(g,0x44);return def&&P(def,0x430)&&settlement_site(def);
 }
 if(!offense(image,g))return 0;
 target=structure_center(image,actor_id(image,P(g,0x4c)));
 return target&&guarded_structure(image,target)&&settlement_site(P(target,4))
  &&((RouteM1)P(P(target,0),0x144))(target,0,P(pl,8))==3;
}
static void expansion_fast_dispatch(U image,Data*d,U mode,U goal,U*args,float*result){
 FastData*f=(FastData*)d;U pl=f->fastPlayer,i;
 if(!(d->mask&8)||!pl||player(goal)!=pl)return;
 /* 35: skip unrelated activation. 36: active-goal transfers only; no native
  * optional exchange. 37: pending recruiting is supplied by mode23's complete
  * group/builder callbacks, then the original caller finalizes activation. */
 if(mode==35){if(P(goal,8)!=1||!expansion_fast_goal(image,pl,goal))*(U*)result=1;return;}
 if(mode==38){
  /* Execute only assignments actually changed in this pass, once, through
   * the native affordability/command path. Never reissue ongoing orders. */
  for(i=0;i<f->commandCount;i++)if(f->commandGoals[i]==goal&&P(goal,8)==2&&expansion_fast_goal(image,pl,goal))return;
  *(U*)result=1;return;
 }
 *(U*)result=1;
 if(mode==36&&expansion_fast_goal(image,pl,goal)){
  construction_recruit(image,d,goal,args);clearing_evaluate(image,d,goal,args);
 }
}
static void expansion_pulse(U image,Data*d,U pl){
 U world=P(image,0x5f3fb8),sai=P(image,0x5f3fc8),players,n,i,engine,table,type,state,node,steps,count=0;
 float time;ExpansionPulse*cache;FastData*f=(FastData*)d;U*goals=f->pulseGoals;
 if(f->fastPlayer||!pl||!world||!sai||P(image,0x5f9218)!=2)return;
 if(!(*(unsigned char*)(pl+4))||!(*(unsigned char*)(sai+0x2c))||!P(pl,8)||(P(P(pl,8),8)&32))return;
 time=F(world,0xe8);players=P(sai,0x6c);n=P(sai,0x70);
 if(!finite(time)||!players||n>96)return;
 for(i=0;i<n;i++)if(P(players,4*i)==pl)break;if(i==n)return;
 cache=&f->pulses[i];
 if(cache->world!=world||cache->kingdom!=P(pl,8)||time<cache->last){cache->world=world;cache->kingdom=P(pl,8);cache->last=-100;}
 if(time-cache->last<EXPANSION_PULSE_SECONDS)return;
 engine=P(pl,0xc);table=engine?P(engine,8):0;
 /* SelectGoals temporarily drains these lists into engine+14. Never nest
  * inside that scope or keep pointers from a previous strategic update. */
 if(!engine||P(engine,4)!=pl||!table||P(engine,0x18))return;
 cache->last=time;
 builder_tick(image,d,pl);
 if(!expansion_regions(image,f,pl))return;
 for(type=0;type<23;type++){
  U lists=P(table,4*type);if(!lists)return;
  for(state=0;state<3;state++){
   for(node=P(lists,8*state),steps=0;node&&steps++<4096;node=P(node,4)){
    U g=P(node,0),vt=g?P(g,0)-image:0;
    if(!g||P(g,4)!=engine||P(g,8)!=state)return;
    if(vt!=0x4da6b0&&vt!=0x4da480&&vt!=0x4d84d4)continue;
    /* Re-evaluate dormant regional goals too: their native target/recipe can
     * first become available after exploration or the destruction of a camp. */
    if(state==2&&!expansion_fast_goal(image,pl,g))continue;
    if(state!=2&&vt==0x4d84d4){
     /* A direct structure goal is not a regional goal: do not interpret its
      * tail as a region pointer. Its known target is sufficient. */
     if(!expansion_fast_goal(image,pl,g))continue;
    }else if(state!=2){
     U region=vt==0x4da6b0?P(g,0x40):P(g,0x48),id;
     if(!region)continue;id=P(region,0);
     if(id>=65536||!(f->expansionRegions[id>>5]&(1u<<(id&31))))continue;
    }
    if(count==4096)return;goals[count++]=g;
   }
   if(node)return;
  }
 }
 f->fastPlayer=pl;f->commandCount=0;
 for(i=0;i<count;i++){
  U g=goals[i];
  if(((ClearingRoute0)P(P(g,0),0x14))(g,0)&255)continue;
  /* Keep targets of already occupied construction/attacks stable. The full
   * strategic update remains responsible for their reevaluation. */
  if(P(g,0xc))continue;
  ((RouteM1)P(P(g,0),0x60))(g,0,P(pl,8)+0x1cc);
  if(P(g,8)==0&&finite(F(g,0x38))&&F(g,0x38)>0&&expansion_fast_goal(image,pl,g))
   ((DefenseM2)(image+0x1e481e))(g,0,1,1);
 }
 /* Native selection supplies fresh affordability/resource accounting, owns
  * vector mutations and pending activation. Fast-dispatch hooks restrict the
  * work to expansion; other goals keep their original strategic cadence. */
 if(count)((ClearingM0)(image+0x1e838a))(engine,0);
 if(f->commandCount){
  /* This flag is the native execution pass's insufficient-budget cascade,
   * not a durable goal state. Give the extra pass its own scope. */
  unsigned char saved=*(unsigned char*)(engine+0x20);
  *(unsigned char*)(engine+0x20)=0;
  ((ClearingM0)(image+0x1e8925))(engine,0);
  *(unsigned char*)(engine+0x20)=saved;
 }
 f->commandCount=0;
 f->fastPlayer=0;
 emit(image,d,52,engine,pl,0,1,(float)count,EXPANSION_PULSE_SECONDS,0,0,0,0);
}
