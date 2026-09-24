/* Replace one idle, expendable field company only for a substantial upgrade.
 * Selection and revalidation run on SAI; native Recruit owns Disband/payment.
 * No actors, experience, resource totals or persistent game data are edited. */
typedef U (FAST *ArmyM4)(U,U,U,U,U,U);
static int army_field(U image,U a){
 return live_actor(image,a)&&!(P(a,8)&1)&&P(a,0x7c)&&P(a,0x144)!=2&&P(a,0x144)!=3
  &&!(P(a,0x100)&4)&&!route_builder(image,a)&&!supply_definition(P(a,4));
}
static int army_fits(U image,Data*d,U pl,U def,U layout,U old){
 U k=P(pl,8),table=P(image,0x5efa8c),defs,n,i,shortage=0,pr=P(k,0x1a8),up=P(k,0x1c0);
 float need[16],freed[16];
 if(!d->query||!table||!pr||!up)return 0;
 n=P(table,0x28);defs=P(table,0x24);if(!n||n>16||!defs)return 0;
 if(((Query)d->query)(image,def,layout,need)!=n)return 0;
 if(old&&((Query)d->query)(image,P(old,4),P(old,0x7c)+0x10,freed)!=n)return 0;
 for(i=0;i<n;i++){
  U rd=P(defs,4*i),pair,index;float used,cap;
  if(!rd||!finite(need[i])||(old&&(!finite(freed[i])||freed[i]<0)))return 0;
  if(P(rd,0x18)!=2)continue;
  pair=P(rd,0x30);if(!pair||(index=P(pair,0xc))>=n)return 0;
  used=F(up,4*i);cap=F(pr,4*index);if(!finite(used)||!finite(cap))return 0;
  if(used+need[i]>cap)shortage=1;
  if(old&&used-freed[i]+need[i]>cap)return 0;
 }
 return shortage;
}
static float army_new_value(U image,U pl,U def,U layout){
 U goal[22],i,types=layout?P(layout,8):0;
 if(!types||!P(layout,0xc)||!P(types,0x20)||P(types,0x20)>32)return 0;
 for(i=0;i<22;i++)goal[i]=0;
 goal[1]=P(pl,0xc);goal[17]=def;goal[18]=layout;
 /* Same full-layout value and hero normalization as native replacement. */
 return ((ClearingF1)(image+0x1dc172))((U)goal,0,1);
}
static int army_better(U image,U pl,U goal,U a){
 float old=((ClearingF1)(image+0x227526))(a,0,1),next=army_new_value(image,pl,P(goal,0x44),P(goal,0x48));
 return finite(old)&&old>0&&finite(next)&&next>=old*1.35f;
}
static int army_pending(U image,U pl,U except){
 U node,steps=0;
 for(node=P(pl,0x2c);node&&steps++<4096;node=P(node,4)){
  U sa=P(node,0),g=sa?P(sa,0x10):0;
  if(sa&&P(sa,0xc)==pl&&g&&g!=except&&P(g,0)==image+0x4d9274&&P(g,0x50))return 1;
 }
 return node!=0;
}
static int army_safe(U image,Data*d,U pl,U sa,U goal,int assigned){
 U a=sa?actor_id(image,P(sa,8)):0;
 /* Native Disband returns heroes to the kingdom's pool. Their presence does
  * not block replacing the company; native command eligibility still applies. */
 return army_field(image,a)&&economy_swap_safe(image,d,pl,sa,goal,assigned);
}
static U army_candidate(U image,Data*d,U pl,U def,U layout,U goal){
 U node,steps=0,best=0,count=0;float value=army_new_value(image,pl,def,layout),weakest=0;
 if(!finite(value)||value<=0||army_pending(image,pl,goal))return 0;
 for(node=P(pl,0x2c);node&&steps++<4096;node=P(node,4)){
  U sa=P(node,0),a=sa?actor_id(image,P(sa,8)):0;float cv;
  if(!army_field(image,a)||P(sa,0xc)!=pl||P(a,0xe8)!=P(pl,8))continue;
  count++;
  if(!army_safe(image,d,pl,sa,goal,0)||!army_fits(image,d,pl,def,layout,a))continue;
  if(!(((RouteM1)P(P(a,0),0x34))(a,0,10)&255))continue;
  cv=((ClearingF1)(image+0x227526))(a,0,1);
  if(!finite(cv)||cv<=0||value<cv*1.35f)continue;
  if(!best||cv<weakest||(cv==weakest&&P(sa,8)<P(best,8))){best=sa;weakest=cv;}
 }
 return !node&&count>=2?best:0;
}
static int army_early(U image,Data*d,U pl,U def,U layout){
 if(!(d->mask&8)||!pl||!*(unsigned char*)(pl+4)||P(image,0x5f9218)!=2||!P(image,0x5f3fb8)
  ||!def||!(P(def,0x174)&128)||!layout||economy_center(def,layout,0)||supply_definition(def))return 0;
 return army_candidate(image,d,pl,def,layout,0)!=0;
}
static int army_ready(U image,Data*d,U pl,U goal){
 U sa=P(goal,0x4c),factory;
 if(!pl||!*(unsigned char*)(pl+4)||!P(image,0x5f3fb8)||P(image,0x5f9218)!=2
  ||!economy_factory_ready(image,pl,goal)||!economy_affordable(image,pl,goal)
  ||supply_definition(P(goal,0x44))||economy_center(P(goal,0x44),P(goal,0x48),0)
  ||army_pending(image,pl,goal))return 0;
 if(economy_slot(image,d,pl,P(goal,0x44),P(goal,0x48),P(P(pl,8),0x1a8),P(P(pl,8),0x1c0)))return 0;
 factory=((EconomyM0)(image+0x1df308))(sa,0);
 /* Native requirements, without resource payment or temporary vector writes. */
 return factory&&((ArmyM4)(image+0x21cc0e))(factory,0,P(goal,0x44),P(goal,0x48),0,0)==0
  &&army_fits(image,d,pl,P(goal,0x44),P(goal,0x48),0);
}
static int army_validate(U image,Data*d,U pl,U goal){
 U sa=P(goal,0x50),a=sa?actor_id(image,P(sa,8)):0,node,steps=0,count=0;
 for(node=P(pl,0x2c);node&&steps++<4096;node=P(node,4)){
  U other=P(node,0),actor=other?actor_id(image,P(other,8)):0;
  if(other&&P(other,0xc)==pl&&army_field(image,actor)&&P(actor,0xe8)==P(pl,8))count++;
 }
 if(node||count<2)return 0;
 return army_ready(image,d,pl,goal)&&army_safe(image,d,pl,sa,goal,1)&&army_better(image,pl,goal,a)
  &&army_fits(image,d,pl,P(goal,0x44),P(goal,0x48),a);
}
static int army_reserved(U image,Data*d,U pl,U goal){
 return goal&&P(goal,0)==image+0x4d9274&&P(goal,4)==P(pl,0xc)
  &&(P(goal,8)==1||P(goal,8)==2)&&P(goal,0x50)&&army_validate(image,d,pl,goal);
}
static void army_admission(U image,Data*d,U a,U goal,float*result){
 U pl,sa,g;
 if((*(U*)result&255)||!goal||!live_actor(image,a)||(pl=player(goal))==0||P(a,0xe8)!=P(pl,8))return;
 sa=construction_sa(pl,a);g=sa?P(sa,0x10):0;
 /* Keep only a still-safe, affordable upgrade reservation. New combat,
  * recovery, lost prerequisites or funds immediately release this veto. */
 if(g!=goal&&g&&P(g,0)==image+0x4d9274&&P(g,0x50)==sa&&army_reserved(image,d,pl,g))*(U*)result|=1;
}
static void army_replace(U image,Data*d,U goal,float*result){
 U pl,best,source,held,a;
 *(U*)result=0x100;
 if(!goal||P(goal,0)!=image+0x4d9274||(pl=player(goal))==0||!army_ready(image,d,pl,goal))return;
 if(P(goal,0x50)){if(army_validate(image,d,pl,goal))*(U*)result=0x101;return;}
 best=army_candidate(image,d,pl,P(goal,0x44),P(goal,0x48),goal);if(!best)return;
 source=P(best,0x10);held=best;a=actor_id(image,P(best,8));P(best,4)++;
 if(source)((DefenseM5)P(P(source,0),0x68))(source,0,best,0,0,1,0);
 if(!P(best,0x10)){
  ((RouteM1)(image+0x6a62a))(goal+0x50,0,best);
  ((DefenseM4)P(P(goal,0),0x64))(goal,0,best,0,0,1);
 }
 if(P(best,0x10)==goal&&P(goal,0x50)==best){
  *(U*)result=0x101;
  emit(image,d,58,goal,pl,P(goal,0x44),1,((ClearingF1)(image+0x227526))(a,0,1),army_new_value(image,pl,P(goal,0x44),P(goal,0x48)),0,0,a,0);
 }else{
  if(P(goal,0x50)==best)((RouteM1)(image+0x6a62a))(goal+0x50,0,0);
  if(source&&!P(best,0x10))((DefenseM4)P(P(source,0),0x64))(source,0,best,0,0,0);
 }
 ((ClearingM0)(image+0x42fca))((U)&held,0);
}
