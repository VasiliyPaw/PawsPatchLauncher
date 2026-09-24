/* Settlement workers are a fleet of civilian companies. Count real vacant
 * sites, field companies and factory jobs; keep native hiring/goal/command
 * ownership. All caches are world/player scoped and contain generation IDs. */
static int builder_enabled(U image,U pl){
 return pl&&*(unsigned char*)(pl+4)&&P(pl,8)&&P(image,0x5f3fb8)&&P(image,0x5f9218)==2;
}
static int builder_reusable(U pl,U target){
 U k=pl?P(pl,8):0,nation=k?P(k,0x240):0;
 return target&&!economy_sovereign(target)&&nation&&(ids_equal(nation,"haroun")||ids_equal(nation,"Haroun"));
}
static U builder_target(U image,U a){
 U org=P(a,0x7c),target;
 if(!org||P(a,0x144)==2||P(a,0x144)==3||(P(a,0x100)&4)||!route_builder(image,a))return 0;
 target=economy_center(P(a,4),org+0x10,0);return target;
}
static void builder_invalidate(Data*d,U pl,int reset){
 FastData*f=(FastData*)d;U i;
 f->claimValid=0;
 if(reset){f->claimWorld=0;f->claimCount=0;}
 for(i=0;i<192;i++)if(reset||!pl||f->builderSites[i].kingdom==P(pl,8)){
  f->builderSites[i].counted=0;
  if(reset)f->builderSites[i].world=0;
 }
 if(reset)for(i=0;i<4096;i++)f->builderWork[i].id=0;
}
static BuilderWork* builder_work(U image,Data*d,U a,float time){
 FastData*f=(FastData*)d;U id=P(a,0x14),i,start=id*2654435761u,world=P(image,0x5f3fb8),k=P(a,0xe8);
 BuilderWork*r=0;
 for(i=0;i<4096;i++){
  BuilderWork*t=&f->builderWork[(start+i)&4095];
  if(t->world==world&&t->kingdom==k&&t->id==id){r=t;break;}
  if(!t->id||t->world!=world||!actor_id(image,t->id)){r=t;break;}
 }
 if(!r)return 0;
 if(r->world!=world||r->kingdom!=k||r->id!=id||time<r->last){
  r->world=world;r->kingdom=k;r->id=id;r->camp=0;r->goal=0;r->surplusSince=-1;r->sent=-100;
 }
 r->last=time;return r;
}
static U builder_camp(U image,U pl,U g){
 U a,node,steps=0;
 if(!g||!offense(image,g)||P(g,4)!=P(pl,0xc)||P(g,8)!=2)return 0;
 a=structure_center(image,actor_id(image,P(g,0x4c)));
 if(!a||!guarded_structure(image,a)||!settlement_site(P(a,4)))return 0;
 /* Capturable centers remain cities after conquest: required_object_ids alone
  * does not mean that this attack will leave an empty settlement marker.
  * Native BodyComponent.captureable is definition + 0x290. */
 if(*(unsigned char*)(P(a,4)+0x290))return 0;
 if(((RouteM1)P(P(a,0),0x144))(a,0,P(pl,8))!=3)return 0;
 for(node=P(g,0xc);node&&steps++<4096;node=P(node,4)){
  U sa=P(node,0),company=sa?actor_id(image,P(sa,8)):0;
  if(company&&P(sa,0xc)==pl&&P(sa,0x10)==g&&P(company,0xe8)==P(pl,8)
    &&P(company,0x7c)&&!route_builder(image,company)&&clearing_available(image,company))return a;
 }
 return 0;
}
static int builder_camp_committed(U image,U pl,U id){
 U node,steps=0;
 for(node=P(pl,0x2c);node&&steps++<4096;node=P(node,4)){
  U sa=P(node,0),camp=sa?builder_camp(image,pl,P(sa,0x10)):0;
  if(camp&&P(camp,0x14)==id)return 1;
 }
 return 0;
}
static BuilderSites* builder_sites(U image,Data*d,U pl,U target){
 FastData*f=(FastData*)d;Economy*e=economy_record(image,d,pl,target);BuilderSites*r;U index,reg,i,node,steps=0;float time;
 if(!e||!target||!settlement_site(target))return 0;
 index=(U)(e-d->economy);if(index>=192)return 0;r=&f->builderSites[index];time=F(e->world,0xe8);
 if(r->world==e->world&&r->kingdom==P(pl,8)&&r->target==target&&time>=r->time&&time-r->time<4)return r;
 r->world=e->world;r->kingdom=P(pl,8);r->target=target;r->time=time;r->count=0;r->valid=0;r->counted=0;r->unscored=0;
 reg=P(image,0x5ef72c);if(!reg)return r;
 if(economy_sovereign(target)&&economy_has_kingdom(image,pl)){r->valid=1;return r;}
 for(i=0;i<65536;i++){
  U a=P(reg,0x20004+4*i);float score;
  if(!a||!economy_free_site(image,pl,target,a))continue;
  score=((ConstructionF5)(image+0x1ee5b3))(pl,0,target,P(a,0x20),P(a,0x24),0,0);
  if(!finite(score)||score<=0){r->unscored++;continue;}
  if(r->count==512)return r;r->sites[r->count++]=P(a,0x14);
 }
 /* One arriving worker can wait for each already committed clearing army.
  * A merely discovered camp does not create a recruitment demand. */
 for(node=P(pl,0x2c);node&&steps++<4096;node=P(node,4)){
  U sa=P(node,0),camp=sa?builder_camp(image,pl,P(sa,0x10)):0,j;
  if(!camp||P(P(camp,4),0x4e0)!=P(target,0x4e0))continue;
  for(j=0;j<r->count;j++)if(r->sites[j]==P(camp,0x14))break;
  if(j<r->count)continue;if(r->count==512)return r;r->sites[r->count++]=P(camp,0x14);
 }
 if(!node)r->valid=1;return r;
}
static void builder_census(U image,U pl,BuilderSites*r){
 U reg=P(image,0x5ef72c),i;
 if(r->counted)return;
 r->owned[0]=r->owned[1]=r->queued[0]=r->queued[1]=0;
 if(!reg)return;
 for(i=0;i<65536;i++){
  U a=P(reg,0x20004+4*i),t,factory,j,n,list;
  if(!live_actor(image,a)||(P(a,8)&1)||P(a,0xe8)!=P(pl,8))continue;
  t=builder_target(image,a);if(t)r->owned[economy_sovereign(t)?1:0]++;
  factory=P(a,0xa0);if(!factory||P(factory,4)!=a)continue;
  list=P(factory,0x14);n=P(factory,0x18);if(n>256||(!list&&n)){r->valid=0;return;}
  for(j=0;j<n;j++){
   U job=P(list,4*j),def=job?P(job,8):0;
   if(!job||P(job,4)!=0||!def||!(P(def,0x174)&128))continue;
   t=economy_center(def,P(job,0xc),0);
   if(t)r->queued[economy_sovereign(t)?1:0]++;
  }
 }
 r->counted=1;
}
static int builder_desired(U image,Data*d,U pl,U target){
 BuilderSites*r=builder_sites(image,d,pl,target);U count,i;
 if(!r||!r->valid)return -1;count=0;
 /* Revalidate cached IDs so capture/destruction takes effect immediately. */
 for(i=0;i<r->count;i++){
  U a=actor_id(image,r->sites[i]);
  if(a&&(economy_free_site(image,pl,target,a)||(guarded_structure(image,a)&&settlement_site(P(a,4))&&builder_camp_committed(image,pl,r->sites[i]))))count++;
 }
 if(economy_sovereign(target))return count?1:0;
 builder_census(image,pl,r);if(!r->valid||!r->counted)return -1;
 /* An existing/ordered first-kingdom builder consumes one settlement too. */
 if(!economy_has_kingdom(image,pl)&&(r->owned[1]||r->queued[1])&&count)count--;
 /* Haroun settlement workers survive construction and service sites serially.
  * Keep that one reusable company between discoveries, not a hire/disband loop. */
 if(builder_reusable(pl,target))return (count||r->owned[0]||r->queued[0])?1:0;
 return (int)count;
}
static int builder_missing(U image,Data*d,U pl,U target){
 int desired=builder_desired(image,d,pl,target);BuilderSites*r;U kind=economy_sovereign(target)?1:0;
 if(desired<0)return 0;
 r=builder_sites(image,d,pl,target);if(!r)return 0;
 builder_census(image,pl,r);if(!r->valid||!r->counted)return 0;
 return desired>(int)(r->owned[kind]+r->queued[kind])?desired-(int)(r->owned[kind]+r->queued[kind]):0;
}
static int builder_recruit_capped(U image,Data*d,U pl,U def,U layout){
 U target;if(!(d->mask&8)||!builder_enabled(image,pl)||!def||!(P(def,0x174)&128))return 0;
 target=economy_center(def,layout,0);if(!target)return 0;
 if(builder_desired(image,d,pl,target)<0)return 0;
 return builder_missing(image,d,pl,target)<=0;
}
static int builder_site_claimed(U image,U pl,U goal,U sa){
 U node,steps=0;
 if(sa&&P(sa,0x10)==goal)return 0;
 for(node=P(pl,0x2c);node&&steps++<4096;node=P(node,4)){
  U other=P(node,0),g=other?P(other,0x10):0,a;
  if(other==sa||!g||P(other,0xc)!=pl||P(g,4)!=P(pl,0xc)
   ||P(g,0)!=image+0x4da6b0||(P(g,8)!=1&&P(g,8)!=2))continue;
  a=actor_id(image,P(other,8));if(!a||P(a,0xe8)!=P(pl,8)||!route_builder(image,a))continue;
  if(dist2(F(goal,0x48),F(goal,0x4c),F(g,0x48),F(g,0x4c))<1)return 1;
 }
 return node!=0;
}
static void builder_hero_score(U image,Data*d,U pl,U*args,float*result){
 U sa=args[1],a;
 if(!builder_enabled(image,pl)||!sa||P(sa,0xc)!=pl)return;
 a=actor_id(image,P(sa,8));if(a&&P(a,0xe8)==P(pl,8)&&route_builder(image,a))*result=0;
}
/* Prepare iterates available unit definitions, including recalled heroes.
 * Filter before scoring/putting a candidate into the private recruit layout;
 * the ordinary captain is still selected and priced by the native planner.
 * Definition component bit 17 is CharacterComponent (heroes), not an IDS or
 * faction heuristic. The caller passes its Recruit goal from EBP-0x34. */
static void builder_recruit_hero(U image,Data*d,U def,U goal,float*result){
 U pl;
 if(!(*(U*)result&255)||!def||!(P(def,0x174)&0x20000)||!goal||P(goal,0)!=image+0x4d9274)return;
 pl=player(goal);
 if(!builder_enabled(image,pl)||!economy_center(P(goal,0x44),0,0))return;
 *(U*)result&=0xffffff00;
 emit(image,d,61,goal,pl,def,1,0,0,0,0,0,0);
}
static void builder_admission(U image,Data*d,U a,U goal,float*result){
 U pl,sa,g;float time;BuilderWork*r;
 if((*(U*)result&255)||!goal||!live_actor(image,a)||!route_builder(image,a))return;
 pl=player(goal);if(!builder_enabled(image,pl)||P(a,0xe8)!=P(pl,8))return;
 /* Never plan an offensive expedition for a civilian builder, even wounded
  * or currently without a construction site. Tactical self-defense is native. */
 if(offense(image,goal)){*(U*)result|=1;return;}
 if(P(goal,0)==image+0x4da6b0){sa=construction_sa(pl,a);if(builder_site_claimed(image,pl,goal,sa)) *(U*)result|=1;return;}
 sa=construction_sa(pl,a);g=sa?P(sa,0x10):0;time=F(P(image,0x5f3fb8),0xe8);
 r=builder_work(image,d,a,time);
 /* Regional defense is also a military assignment. Only this worker's safe
  * staging reservation may use it; local self-defense/retreat are CAI states.
  * builderBusy admits the native staging probe, whose route is checked below. */
 if(P(goal,0)==image+0x4da510&&!((FastData*)d)->builderBusy){
  if(!(r&&r->camp&&g==goal&&r->goal==goal&&builder_camp_committed(image,pl,r->camp)
    &&construction_ready(image,a,0)&&!defense_danger(image,d,0,a,P(pl,8),time,1))) *(U*)result|=1;
  return;
 }
 if(r&&r->camp&&g&&g==r->goal&&g!=goal&&(P(goal,0)==image+0x4da510||P(goal,0)==image+0x4d79e8)
  &&builder_camp_committed(image,pl,r->camp)&&construction_ready(image,a,0)
  &&!defense_danger(image,d,0,a,P(pl,8),time,1))*(U*)result|=1;
}
/* Conservative staging: the native rally point and the whole straight
 * approach must remain outside all known camp guard/pursuit radii. Native
 * weighted routing still handles terrain and other visible hostiles. */
static int builder_approach(U image,U pl,U a,U goal){
 U reg=P(image,0x5ef72c),region=P(goal,0x48),i;float ax=F(a,0x20),ay=F(a,0x24),bx=F(region,0x54),by=F(region,0x58);
 float dx=bx-ax,dy=by-ay,len=dx*dx+dy*dy;
 if(!reg||!finite(len))return 0;
 for(i=0;i<65536;i++){
  U camp=P(reg,0x20004+4*i),cell,def;float t,x,y,radius;
  if(!camp||!guarded_structure(image,camp)||((RouteM1)P(P(camp,0),0x144))(camp,0,P(pl,8))!=3)continue;
  cell=route_cell(image,F(camp,0x20),F(camp,0x24));if(!cell||!(((RouteM1)(image+0x24a845))(cell,0,P(pl,8))&255))continue;
  def=P(camp,4);radius=maximum(F(def,0x364),F(def,0x368))+48;
  if(!finite(radius)||radius<=0||radius>560)return 0;
  t=len>0?((F(camp,0x20)-ax)*dx+(F(camp,0x24)-ay)*dy)/len:0;t=maximum(0,minimum(1,t));
  x=ax+t*dx;y=ay+t*dy;if(dist2(x,y,F(camp,0x20),F(camp,0x24))<=radius*radius)return 0;
 }
 return 1;
}
static void builder_wait(U image,Data*d,U goal,U*args){
 FastData*f=(FastData*)d;U pl,engine,node,steps=0,budget=args[0],best=0,camp=0,source=0,actor=0,pending;
 float time,distance=1e20f;
 if(f->builderBusy||!goal||P(goal,0)!=image+0x4da510||P(goal,0x4c)||!P(goal,0x48)||!budget)return;
 pl=player(goal);if(!builder_enabled(image,pl))return;engine=P(pl,0xc);
 if(args[1]!=engine+0x14||args[2]>=P(engine,0x18)||P(P(engine,0x14),4*args[2])!=goal)return;
 time=F(P(image,0x5f3fb8),0xe8);if(!finite(time))return;
 for(node=P(pl,0x2c);node&&steps++<4096;node=P(node,4)){
  U sa=P(node,0),candidate=sa?builder_camp(image,pl,P(sa,0x10)):0;float near;
  if(!candidate)continue;
  near=dist2(F(P(goal,0x48),0x54),F(P(goal,0x48),0x58),F(candidate,0x20),F(candidate,0x24));
  if(near<distance&&clearing_rally_point(image,d,pl,goal,candidate,time)){camp=candidate;distance=near;}
 }
 if(!camp||node)return;
 /* A camp has at most one staged worker; generation IDs prevent reuse. */
 for(node=P(pl,0x2c),steps=0;node&&steps++<4096;node=P(node,4)){
  U sa=P(node,0),a=sa?actor_id(image,P(sa,8)):0;BuilderWork*r;
  if(!a||!builder_target(image,a))continue;r=builder_work(image,d,a,time);
  if(r&&r->camp==P(camp,0x14)&&r->goal==P(sa,0x10))return;
 }
 distance=1e20f;f->builderBusy=1;
 for(node=P(pl,0x2c),steps=0;node&&steps++<4096;node=P(node,4)){
  U sa=P(node,0),a=sa?actor_id(image,P(sa,8)):0,g=sa?P(sa,0x10):0,target;float near;
  if(!a||P(a,0xe8)!=P(pl,8)||!(target=builder_target(image,a))||!construction_ready(image,a,0))continue;
  if(economy_sovereign(target)&&economy_has_kingdom(image,pl))continue;
  if(g&&(P(g,4)!=engine||P(g,8)!=2||P(g,0)==image+0x4da6b0||P(g,0)==image+0x4da5a0))continue;
  /* Vacant usable sites always take precedence over waiting for a camp. */
  if(economy_site(image,d,pl,target)||defense_danger(image,d,0,a,P(pl,8),time,1))continue;
  if(!(((DefenseM2)P(P(sa,0),0x20))(sa,0,goal,0)&255)||!builder_approach(image,pl,a,goal))continue;
  near=dist2(F(a,0x20),F(a,0x24),F(camp,0x20),F(camp,0x24));
  if(near<distance){best=sa;actor=a;source=g;distance=near;}
 }
 if(best&&!node){
  BuilderWork*r=builder_work(image,d,actor,time);pending=P(goal,8)==1;P(best,4)++;
  if(source)((DefenseM5)P(P(source,0),0x68))(source,0,best,budget,1,1,0);
  if(!P(best,0x10))((DefenseM4)P(P(goal,0),0x64))(goal,0,best,pending?0:budget,pending?0:1,pending?0:1);
  if(P(best,0x10)==goal){if(r){r->camp=P(camp,0x14);r->goal=goal;r->surplusSince=-1;}emit(image,d,56,goal,pl,P(actor,4),1,0,0,F(camp,0x20),F(camp,0x24),actor,0);}
  else if(source&&!P(best,0x10))((DefenseM4)P(P(source,0),0x64))(source,0,best,budget,1,1);
  ((ClearingM0)(image+0x42fca))((U)&best,0);
 }
 f->builderBusy=0;
}
typedef U (*BuilderAlloc)(U);
typedef U (FAST *BuilderM3)(U,U,U,U,U);
static int builder_disband(U image,U pl,U a){
 U command,held,envelope[8],i;
 if(!(((RouteM1)P(P(a,0),0x34))(a,0,10)&255))return 0;
 command=((BuilderAlloc)(image+0x2ef03c))(0x40);if(!command)return 0;
 held=((RouteM1)(image+0x22f4e9))(command,0,10);if(!held)return 0;P(held,4)++;
 for(i=0;i<8;i++)envelope[i]=0;
 ((BuilderM3)(image+0x1f384d))((U)envelope,0,(U)&held,P(a,0x14),P(pl,0x198));
 ((RouteM1)(image+0x1f2c03))(pl,0,(U)envelope);
 ((ClearingM0)(image+0x1f397b))((U)envelope,0);
 ((ClearingM0)(image+0x42fca))((U)&held,0);return 1;
}
static void builder_tick(U image,Data*d,U pl){
 U node,steps=0,i;float time;FastData*f=(FastData*)d;
 if(f->builderBusy||!builder_enabled(image,pl))return;time=F(P(image,0x5f3fb8),0xe8);if(!finite(time))return;
 for(i=0;i<4096;i++){
  BuilderWork*r=&f->builderWork[i];
  if(r->world==P(image,0x5f3fb8)&&r->kingdom==P(pl,8)&&r->id&&time>=r->sent&&time-r->sent<30&&actor_id(image,r->id))return;
 }
 for(node=P(pl,0x2c);node&&steps++<4096;node=P(node,4)){
  U sa=P(node,0),a=sa?actor_id(image,P(sa,8)):0,target,g;BuilderWork*r;BuilderSites*sites;int desired;U owned;
  if(!a||P(sa,0xc)!=pl||P(a,0xe8)!=P(pl,8)||!(target=builder_target(image,a)))continue;
  r=builder_work(image,d,a,time);if(!r)continue;g=P(sa,0x10);
  if(r->camp&&(!builder_camp_committed(image,pl,r->camp)||g!=r->goal)){r->camp=0;r->goal=0;}
  desired=builder_desired(image,d,pl,target);sites=builder_sites(image,d,pl,target);
  if(!sites){r->surplusSince=-1;continue;}builder_census(image,pl,sites);owned=sites->owned[economy_sovereign(target)?1:0];
  if(desired<0||sites->unscored||owned<=(U)desired||r->camp||(g&&P(g,0)==image+0x4da6b0)
   ||!construction_ready(image,a,0)||!defense_idle(image,a)||defense_danger(image,d,0,a,P(pl,8),time,1)){
   r->surplusSince=-1;continue;
  }
  if(r->surplusSince<0){r->surplusSince=time;continue;}
  if(time-r->surplusSince<30)continue;
  /* One native command per pulse, and a grace interval after sending, so a
   * queued multiplayer command cannot trigger repeated disband attempts. */
  f->builderBusy=1;
  if(builder_disband(image,pl,a)){r->surplusSince=time;r->sent=time;emit(image,d,57,g,pl,P(a,4),1,(float)owned,(float)desired,0,0,a,0);}
  f->builderBusy=0;return;
 }
}
