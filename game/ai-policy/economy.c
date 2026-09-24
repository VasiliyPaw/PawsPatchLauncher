/* Expansion capacity and first-kingdom budget policy. All world decisions run
 * on the native SAI thread. Recruitment, payment and replacement execution
 * remain native; no units/resources are created or removed by this callback. */
typedef void (FAST *EconomyM2)(U,U,U,U);
typedef U (FAST *EconomyM0)(U,U);
static int economy_affordable(U image,U pl,U goal);
static int economy_sovereign(U def){
 U s=def?P(def,8):0,i,j;const char*word="_center_sovereign";
 if(!s)return 0;
 for(i=0;i<64&&*(W*)(s+2*i);i++){
  for(j=0;word[j]&&i+j<96&&*(W*)(s+2*(i+j))==(W)word[j];j++);
  if(!word[j])return 1;
 }
 return 0;
}
static U economy_center(U def,U layout,U depth){
 U node,i=0,t,types,n;
 if(!def||depth>3)return 0;
 for(node=P(def,0x504);node&&i++<64;node=P(node,4)){
  t=P(node,0);if(t&&P(t,0x430)&&settlement_site(t))return t;
 }
 if(!layout){if(!(P(def,0x174)&128))return 0;layout=P(def,0x2f0);}
 if(!layout||(t=P(layout,8))==0||(types=P(layout,0xc))==0)return 0;
 n=P(t,0x20);if(n>64)return 0;
 for(i=0;i<n;i++){t=economy_center(P(types,4*i),0,depth+1);if(t)return t;}
 return 0;
}
static U economy_owned_builder(U image,U pl,U target){
 U node,steps=0;
 for(node=P(pl,0x2c);node&&steps++<4096;node=P(node,4)){
  U sa=P(node,0),a=sa?actor_id(image,P(sa,8)):0,org,list,n,i;
  if(!a||P(a,0xe8)!=P(pl,8)||P(sa,0xc)!=pl)continue;
  if(route_center_capable(image,a)&&economy_center(P(a,4),0,0)==target)return a;
  org=P(a,0x7c);list=org?P(org,0x28):0;n=org?P(org,0x2c):0;if(!list||n>64)continue;
  for(i=0;i<n;i++){
   U member=P(list,4*i);
   if(live_actor(image,member)&&!(P(member,8)&1)&&P(member,0xe8)==P(pl,8)
    &&route_center_capable(image,member)&&economy_center(P(member,4),0,0)==target)return a;
  }
 }
 return 0;
}
static int economy_has_kingdom(U image,U pl){
 U k=P(pl,8),list=P(k,0x2dc),n=P(k,0x2e0),i;if(!list||n>256)return 1;
 for(i=0;i<n;i++){
  U a=P(list,4*i),container,center;
  if(!live_actor(image,a)||(P(a,8)&1)||P(a,0xe8)!=k)continue;
  container=P(a,0x98);center=container?P(container,0x14):0;
  if(live_actor(image,center)&&economy_sovereign(P(center,4)))return 1;
 }
 return 0;
}
static Economy* economy_record(U image,Data*d,U pl,U target){
 U manager=P(image,0x5f3fc8),list,n,i,world=P(image,0x5f3fb8);Economy*r;float time;
 if(!pl||!manager||!world||P(image,0x5f9218)!=2||!P(pl,8))return 0;
 list=P(manager,0x6c);n=P(manager,0x70);if(!list||n>96)return 0;
 for(i=0;i<n;i++)if(P(list,4*i)==pl)break;if(i==n)return 0;
 r=&d->economy[i*2+(economy_sovereign(target)?1:0)];time=F(world,0xe8);
 if(!finite(time))return 0;
 if(r->world!=world||r->kingdom!=P(pl,8)||r->target!=target||time<r->time){
  U j;for(j=0;j<sizeof(Economy);j+=4)P(r,j)=0;
  r->world=world;r->kingdom=P(pl,8);r->target=target;r->time=-100;r->observed=-100;
 }
 return r;
}
static int economy_free_site(U image,U pl,U target,U a){
 U cell,node,steps=0;
 if(!live_actor(image,a)||(P(a,8)&1)||P(a,4)!=P(target,0x4e0)||P(a,0x94)||P(a,0x88))return 0;
 cell=route_cell(image,F(a,0x20),F(a,0x24));
 if(!cell||!(((RouteM1)(image+0x24a845))(cell,0,P(pl,8))&255))return 0;
 /* Ghost markers are not proof of vacancy. Require the real marker to still
  * occupy this cell and reject a live occupying camp/settlement. */
 for(node=P(cell,8);node&&steps++<1024;node=P(node,4)){
  U other=P(node,0);
  if(other!=a&&live_actor(image,other)&&!(P(other,8)&1)&&(P(other,0x94)||P(other,0x88))
   &&same_spot(F(a,0x20),F(a,0x24),other,0x20))return 0;
 }
 if(node)return 0;
 for(node=P(cell,8),steps=0;node&&steps++<1024;node=P(node,4))if(P(node,0)==a)break;
 return node!=0;
}
static U economy_site(U image,Data*d,U pl,U target){
 Economy*r=economy_record(image,d,pl,target);U reg,i,k,cities,n,best=0;float time,nearBest=1e20f;
 if(!r)return 0;time=F(r->world,0xe8);
 if(time-r->time<1){U a=actor_id(image,r->site);return a&&economy_free_site(image,pl,target,a)?a:0;}
 r->time=time;r->site=0;
 if(!settlement_site(target)||(economy_sovereign(target)&&economy_has_kingdom(image,pl)))return 0;
 k=P(pl,8);cities=P(k,0x2dc);n=P(k,0x2e0);reg=P(image,0x5ef72c);if(!reg||!cities||!n||n>256)return 0;
 for(i=0;i<65536;i++){
  U a=P(reg,0x20004+4*i),j;float near=1e20f,score;
  if(!a||!economy_free_site(image,pl,target,a))continue;
  for(j=0;j<n;j++){
   U city=P(cities,4*j);
   if(live_actor(image,city)&&!(P(city,8)&1)&&P(city,0xe8)==k&&P(city,0x94)&&P(city,0x98))
    near=minimum(near,dist2(F(a,0x20),F(a,0x24),F(city,0x20),F(city,0x24)));
  }
  if(!finite(near)||near>256*256||near>=nearBest)continue;
  score=((ConstructionF5)(image+0x1ee5b3))(pl,0,target,P(a,0x20),P(a,0x24),0,0);
  if(!finite(score)||score<=0||defense_danger_at(image,d,k,time,1,F(a,0x20),F(a,0x24),40))continue;
  best=a;nearBest=near;
 }
 r->site=best?P(best,0x14):0;return best;
}
static U economy_need(U image,Data*d,U pl,U def,U layout){
 U target=economy_center(def,layout,0);Economy*r;
 if(!target||builder_missing(image,d,pl,target)<=0)return 0;
 r=economy_record(image,d,pl,target);if(!r)return 0;
 /* Retain immutable definitions only. A goal-owned custom layout can be
  * destroyed before the next strategic pass. Final admission uses its live
  * layout; the one-slot reservation uses the definition's stable default. */
 r->recruit=def;r->layout=P(def,0x2f0);r->observed=F(r->world,0xe8);return target;
}
static U economy_unit_resource(U image){
 U table=P(image,0x5efa8c),defs,n,i;if(!table)return 0;
 defs=P(table,0x24);n=P(table,0x28);if(!defs||n>16)return 0;
 for(i=0;i<n;i++){U rd=P(defs,4*i);if(rd&&P(rd,0x18)==2&&ids_equal(rd,"unit_limit_consumed"))return i+1;}
 return 0;
}
static int economy_slot(U image,Data*d,U pl,U def,U layout,U production,U upkeep){
 U manager=P(image,0x5f3fc8),list,n,i,j,index=economy_unit_resource(image),rd,pair,capacity,k=P(pl,8);float need[16],builder[16],time;
 if(!index||!manager||!production||!upkeep||!d->query||!P(image,0x5f3fb8)||P(image,0x5f9218)!=2)return 0;index--;
 if(economy_center(def,layout,0))return 0;
 list=P(manager,0x6c);n=P(manager,0x70);if(!list||n>96)return 0;
 for(i=0;i<n;i++)if(P(list,4*i)==pl)break;if(i==n)return 0;
 rd=P(P(P(image,0x5efa8c),0x24),index*4);pair=P(rd,0x30);if(!pair)return 0;capacity=P(pair,0xc);if(capacity>=16)return 0;
 n=((Query)d->query)(image,def,layout,need);if(index>=n||capacity>=n||!finite(need[index])||need[index]<=0)return 0;
 time=F(P(image,0x5f3fb8),0xe8);
 for(j=0;j<2;j++){
  Economy*r=&d->economy[i*2+j];
  if(r->world!=P(image,0x5f3fb8)||r->kingdom!=k||!r->recruit||time<r->observed||time-r->observed>40)continue;
  if(builder_missing(image,d,pl,r->target)<=0)continue;
  if(((Query)d->query)(image,r->recruit,r->layout,builder)!=n||!finite(builder[index])||builder[index]<=0)continue;
  /* Reserving an army slot is pointless if another hard capacity (e.g. the
   * sovereign's kingdom points) still makes this builder impossible. */
  {U q,ready=1,defs=P(P(image,0x5efa8c),0x24);
   for(q=0;q<n;q++){
    U other=P(defs,4*q),p,c;
    if(!other||!finite(builder[q])){ready=0;break;}
    if(q==index||P(other,0x18)!=2)continue;
    p=P(other,0x30);if(!p||(c=P(p,0xc))>=n||!finite(F(production,4*c))||!finite(F(upkeep,4*q))
      ||F(upkeep,4*q)+builder[q]>F(production,4*c)){ready=0;break;}
   }
   if(!ready)continue;
  }
  if(finite(F(production,4*capacity))&&finite(F(upkeep,4*index))&&F(upkeep,4*index)+need[index]+builder[index]>F(production,4*capacity)){
   emit(image,d,44,def,pl,r->recruit,1,builder[index],F(production,4*capacity)-F(upkeep,4*index),0,0,0,0);return 1;
  }
 }
 return 0;
}
static int economy_swap_safe(U image,Data*d,U pl,U sa,U goal,int assigned){
 U a=sa?actor_id(image,P(sa,8)):0,g=sa?P(sa,0x10):0,org,list,n,i,s,vt;float time;
 if(!a||P(sa,0xc)!=pl||P(a,0xe8)!=P(pl,8)||!P(a,0x7c)||route_builder(image,a)||(P(a,0x100)&0x6000))return 0;
 if(assigned){if(g!=goal)return 0;}
 else if(!g||P(g,4)!=P(pl,0xc)||(P(g,0)!=image+0x4da510&&P(g,0)!=image+0x4d79e8)||P(g,8)!=2)return 0;
 if(!defense_idle(image,a)){
  /* Scouts may still be travelling. Once reserved, their strategic goal is
   * Recruit, while the same native Move/Explore state can remain active. */
  s=defense_state(a);vt=s?P(s,0)-image:0;
  if((vt!=0x4f4df0&&vt!=0x4f5038)||(!assigned&&P(g,0)!=image+0x4d79e8))return 0;
 }
 org=P(a,0x7c);list=P(org,0x28);n=P(org,0x2c);if(!list||!n||n>64)return 0;
 /* Hero membership does not veto the normal native Disband command. */
 for(i=0;i<n;i++){
  U u=P(list,4*i);
  if(live_actor(image,u)&&route_fighting(image,u))return 0;
 }
 time=F(P(image,0x5f3fb8),0xe8);
 if(!finite(time)||defense_danger(image,d,0,a,P(pl,8),time,1))return 0;
 if(!assigned&&clearing_reserved(image,d,pl,sa))return 0;
 return 1;
}
static int economy_swap_fits(U image,Data*d,U pl,U goal,U old){
 float need[16],freed[16];U k=P(pl,8),table=P(image,0x5efa8c),n,i,defs,unit=economy_unit_resource(image),shortage=0;
 U pr=P(k,0x1a8),up=P(k,0x1c0);
 if(!unit||!table||!pr||!up||!d->query)return 0;
 n=P(table,0x28);defs=P(table,0x24);if(!n||n>16||!defs)return 0;
 if(((Query)d->query)(image,P(goal,0x44),P(goal,0x48),need)!=n)return 0;
 if(old&&((Query)d->query)(image,P(old,4),P(old,0x7c)+0x10,freed)!=n)return 0;
 for(i=0;i<n;i++){
  U rd=P(defs,4*i),pair,index;float used,cap;
  if(!rd||!finite(need[i])||(old&&!finite(freed[i])))return 0;
  if(P(rd,0x18)!=2)continue;
  pair=P(rd,0x30);if(!pair||(index=P(pair,0xc))>=n)return 0;
  used=F(up,4*i);cap=F(pr,4*index);if(!finite(used)||!finite(cap))return 0;
  if(used+need[i]>cap){if(i+1!=unit)return 0;shortage=1;}
  if(old&&used-freed[i]+need[i]>cap)return 0;
 }
 return shortage;
}
static int economy_factory_ready(U image,U pl,U goal){
 U sa=P(goal,0x4c),city=sa?actor_id(image,P(sa,8)):0,factory,ego=P(pl,0x1c);
 if(!city||P(sa,0xc)!=pl||P(city,0xe8)!=P(pl,8)||!P(city,0x94)||invalid_center(image,P(city,0x98)))return 0;
 factory=((EconomyM0)(image+0x1df308))(sa,0);if(!factory)return 0;
 /* Recruit::Execute checks this per-city quota AFTER its Disband command.
  * Check the existing hash bucket without insertion before releasing a unit,
  * so a throttled city cannot disband first and skip recruitment afterwards. */
 if(ego&&P(ego,0x398)&&(((EconomyM0)(image+0x21c6ec))(factory,0)&255)){
  U map=P(pl,0xc)+0x28,table=P(map,0),n=P(map,4),entry,steps=0;
  if(!table||!n||n>4096)return 0;
  for(entry=P(table,4*(city%n));entry&&steps++<4096;entry=P(entry,8)){
   if(P(entry,0)==city){if(P(entry,4)>=P(ego,0x398))return 0;break;}
  }
  if(steps>=4096)return 0;
 }
 return 1;
}
static int economy_swap_ready(U image,Data*d,U pl,U goal){
 return economy_factory_ready(image,pl,goal)&&economy_need(image,d,pl,P(goal,0x44),P(goal,0x48))
   &&economy_affordable(image,pl,goal)&&economy_swap_fits(image,d,pl,goal,0);
}
/* Replacement is attached to the native Recruit goal exactly as at 1DF1B2.
 * Its stock execution validates CanDisband, sends the simulation command and
 * enqueues the replacement. No general army liquidation rule is introduced. */
static void economy_replace(U image,Data*d,U goal,float*result){
 U pl,def,best=0,actor=0,node,steps=0,military=0;float weakest=0;
 if(!goal||P(goal,0)!=image+0x4d9274)return;
 def=P(goal,0x44);pl=player(goal);if(!pl)return;
 if(!economy_center(def,P(goal,0x48),0)){
  U k=P(pl,8);if(k&&economy_slot(image,d,pl,def,P(goal,0x48),P(k,0x1a8),P(k,0x1c0))) *(U*)result=0x100;
  return;
 }
 *(U*)result=0x100; /* handled, no replacement unless every check succeeds */
 pl=player(goal);if(!pl||!P(image,0x5f3fb8)||P(image,0x5f9218)!=2||!economy_swap_ready(image,d,pl,goal))return;
 if(P(goal,0x50)){if(economy_swap_safe(image,d,pl,P(goal,0x50),goal,1))*(U*)result=0x101;return;}
 for(node=P(pl,0x2c);node&&steps++<4096;node=P(node,4)){
  U sa=P(node,0),a=sa?actor_id(image,P(sa,8)):0,g=sa?P(sa,0x10):0;float cv;
  if(!a||P(sa,0xc)!=pl||P(a,0xe8)!=P(pl,8)||!P(a,0x7c)||route_builder(image,a))continue;
  military++;
  /* One native replacement reservation at a time per kingdom. */
  if(g&&g!=goal&&P(g,0)==image+0x4d9274&&P(g,0x50))return;
  if(!economy_swap_safe(image,d,pl,sa,goal,0)||!economy_swap_fits(image,d,pl,goal,a))continue;
  if(!(((RouteM1)P(P(a,0),0x34))(a,0,10)&255))continue;
  cv=((ClearingF1)(image+0x227526))(a,0,1);
  if(!finite(cv)||cv<0)continue;
  if(!best||cv<weakest||(cv==weakest&&P(a,0x14)<P(actor,0x14))){best=sa;actor=a;weakest=cv;}
 }
 if(node||!best||military<2)return;
 {U source=P(best,0x10),held=best;
  P(best,4)++;
  if(source)((DefenseM5)P(P(source,0),0x68))(source,0,best,0,0,1,0);
  if(!P(best,0x10)){
   ((RouteM1)(image+0x6a62a))(goal+0x50,0,best);
   ((DefenseM4)P(P(goal,0),0x64))(goal,0,best,0,0,1);
  }
  if(P(best,0x10)==goal&&P(goal,0x50)==best){
   *(U*)result=0x101;emit(image,d,46,goal,pl,def,1,weakest,0,0,0,actor,0);
  }else{
   if(P(goal,0x50)==best)((RouteM1)(image+0x6a62a))(goal+0x50,0,0);
   if(!P(best,0x10)&&source)((DefenseM4)P(P(source,0),0x64))(source,0,best,0,0,0);
  }
  ((ClearingM0)(image+0x42fca))((U)&held,0);
 }
}
/* Native goal cost is recalculated by Construct/Build/Upgrade/Recruit::Update
 * before affordability (1E3CDA); it includes actual kingdom/unit discounts. */
static int economy_affordable(U image,U pl,U goal){
 U values=P(goal,0x1c),n=P(goal,0x20),stock=P(P(pl,8),0x1cc),table=P(image,0x5efa8c),i,defs;
 if(!values||!stock||!n||n>16||!table||n!=P(table,0x28)||n>P(P(pl,8),0x1d0))return 0;
 defs=P(table,0x24);if(!defs)return 0;
 for(i=0;i<n;i++){
  U rd=P(defs,4*i);float cost=F(values,4*i);
  if(!rd||!finite(cost))return 0;
  if(P(rd,0x18)==0&&(!finite(F(stock,4*i))||cost>F(stock,4*i)))return 0;
 }
 return 1;
}
static int economy_spend(U image,Data*d,U goal,U budget){
 U pl=player(goal),vt=P(goal,0)-image,node,steps=0,k,world=P(image,0x5f3fb8);float reserve=0,spend;
 if(!pl||!world||P(image,0x5f9218)!=2||d->economyBusy||!budget||!P(budget,0)||!P(goal,0x1c)||!P(goal,0x20)||P(goal,8)==2)return 0;
 /* Only optional new costs. Repair/recovery/defense retain native budgets. */
 if(vt!=0x4da628&&vt!=0x4da738&&vt!=0x4d9274&&vt!=0x4da6b0)return 0;
 if(militia_upgrade(image,goal))return 0;
 if(vt==0x4da6b0&&economy_sovereign(P(goal,0x44)))return 0;
 if(vt==0x4d9274&&economy_center(P(goal,0x44),P(goal,0x48),0))return 0;
 k=P(pl,8);if(!k||economy_has_kingdom(image,pl))return 0;
 spend=F(P(goal,0x1c),0);if(!finite(spend)||spend<=0)return 0;
 d->economyBusy=1;
 for(node=P(pl,0x2c);node&&steps++<4096;node=P(node,4)){
  U sa=P(node,0),a=sa?actor_id(image,P(sa,8)):0,target,stats,n;float values[16];U vector[3];
  if(!a||P(sa,0xc)!=pl||P(a,0xe8)!=k||!construction_ready(image,a,0))continue;
  target=economy_center(P(a,4),0,0);
  if(!target||!economy_sovereign(target)||!economy_site(image,d,pl,target)||defense_danger(image,d,0,a,k,F(world,0xe8),1))continue;
  n=P(target,0x328);if(!n||n>16)continue;
  vector[0]=(U)values;vector[1]=n;vector[2]=n;
  stats=((EconomyM0)(image+0x2277b6))(a,0);
  ((EconomyM2)(image+0x29eaa))(target,0,(U)vector,stats);
  if(finite(values[0])&&values[0]>reserve)reserve=values[0];
 }
 d->economyBusy=0;
 if(!node&&reserve>0&&finite(F(P(budget,0),0))&&F(P(budget,0),0)-spend<reserve){
  emit(image,d,45,goal,pl,vt==0x4da628||vt==0x4da738?P(goal,0x40):P(goal,0x44),1,spend,reserve,0,0,0,0);return 1;
 }
 return 0;
}
