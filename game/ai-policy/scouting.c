/* Complete a pending Explore goal's native recruitment phase (1E4779).
 * The original 1E4C9D has finished all list iteration. Its caller still owns
 * the sorted vector and will recalculate this goal, activate it or reject it.
 * Never write goal state, manufacture a goal, or issue a movement command. */
/* A remembered settlement camp may not yet have a native attack goal. Give
 * its region a scouting preference only after the engine has accepted that
 * region as reachable, unexplored and useful. Keep the native RNG draw and
 * zero/negative scores intact; do not invent visibility or attack goals. */
static void scouting_reveal(U image,Data*d,U ego,U*args,float*result){
 U pl,goal,engine,camp,node,steps=0,region;Expansion*exp;float score=*result;
 if(!finite(score)||score<=0||!args[4])return;
 pl=ai_for_kingdom(image,args[1]);goal=args[4]-0xc;
 if(!pl||P(pl,0x1c)!=ego||P(goal,0)!=image+0x4d79e8||P(goal,4)!=P(pl,0xc))return;
 exp=expansion_state(image,d,pl);camp=exp?actor_id(image,exp->camp):0;
 if(!camp||expansion_rank(image,exp,camp)<=0)return;
 engine=P(pl,0xc);
 for(node=P(engine,0xc);node&&steps++<4096;node=P(node,4)){
  U g=P(node,0);
  if(g&&P(g,4)==engine&&(P(g,8)==1||P(g,8)==2)&&offense(image,g)
    &&P(g,0x4c)==P(camp,0x14)&&finite(F(g,0x38))&&F(g,0x38)>0)return;
 }
 if(node)return;
 region=((EconomyM0)(image+0x2273c2))(camp,0);
 if(region&&region==args[2]&&finite(score*4)){
  *result=score*4;emit(image,d,47,goal,pl,P(camp,4),1,score,*result,F(camp,0x20),F(camp,0x24),camp,0);
 }
}
static U scouting_candidate(U image,Data*d,U pl,U goal,U sa,float time,U*object,float*gain,ClearingSafety*safety,U*checked){
 U a=actor_id(image,P(sa,8)),source=P(sa,0x10),city,j;
 if(!a||P(a,0xe8)!=P(pl,8)||P(sa,0xc)!=pl||!source||P(source,4)!=P(pl,0xc)
  ||P(source,0)!=image+0x4da510||P(source,8)!=2)return 1;
 city=defense_object(image,source,P(pl,8),a);if(!city)return 1;*object=city;
 if(!defense_eligible(image,d,a,defense_key(source,city),time))return 2;
 if(defense_reserved(image,d,a))return 3;
 if(defense_has_construct(image,pl,sa))return 4;
 if(!route_builder(image,a)&&defense_has_clear(image,d,pl,sa))return 5;
 for(j=0;j<*checked;j++)if(safety[j].object==city)break;
 if(j==*checked){
  if(j==128)return 6;
  safety[j].object=city;safety[j].danger=defense_danger(image,d,source,city,P(pl,8),time,1);(*checked)++;
 }
 if(safety[j].danger)return 6;
 if(((RouteM1)P(P(goal,0),0x6c))(goal,0,sa)&255)return 7;
 /* Same native gain/admission call as 1E4DBA. Unlike defense_admitted,
  * this particular caller is recruiting for a goal still in state 1. */
 *gain=((DefenseF2)P(P(goal,0),0x28))(goal,0,sa,1);
 return finite(*gain)&&*gain>0?0:7;
}
static void scouting_evaluate(U image,Data*d,U goal,U*args){
 U world=P(image,0x5f3fb8),pl,engine,vector=args[1],budget=args[0],list,n,node,steps=0,checked=0;
 U selected=0,source=0,actor=0,object=0;float time,best=0;DefensePlayer*p;ClearingSafety safety[128];
 if(!world||P(image,0x5f9218)!=2||!goal||P(goal,0)!=image+0x4d79e8||P(goal,8)!=1||!budget||!vector)return;
 pl=player(goal);if(!pl)return;engine=P(pl,0xc);
 if(!engine||P(goal,4)!=engine||vector!=engine+0x14)return;
 list=P(vector,0);n=P(vector,4);
 if(!list||!n||n>4096||args[2]>=n||P(list,4*args[2])!=goal)return;
 if(!finite(F(goal,0x38))||F(goal,0x38)<=0||P(goal,0xc)||P(goal,0x14))return;
 time=F(world,0xe8);p=defense_player(image,d,pl,time);
 if(!p||time-p->dispatch<10||defense_scout_count(image,pl)>=5)return;
 for(node=P(pl,0x2c);node&&steps++<4096;node=P(node,4)){
  U sa=P(node,0),a,g,city=0,reason;float gain=0;
  if(!sa||P(sa,0xc)!=pl)continue;
  a=actor_id(image,P(sa,8));g=P(sa,0x10);
  if(!a||!P(a,0x7c)||!g||P(g,0)!=image+0x4da510)continue;
  reason=scouting_candidate(image,d,pl,goal,sa,time,&city,&gain,safety,&checked);
  if(reason){emit(image,d,37,goal,pl,P(a,4),reason,0,0,F(a,0x20),F(a,0x24),a,0);continue;}
  /* Native suitability first, full actor ID breaks ties independently of ASLR. */
  if(!selected||gain>best||(gain==best&&P(a,0x14)<P(actor,0x14))){selected=sa;source=g;actor=a;object=city;best=gain;}
 }
 if(node||!selected)return;
 /* No simulation callback can interleave here, but revalidate associations
  * before the first mutation; refuse any target already filled natively. */
 if(P(goal,8)!=1||P(goal,0xc)||P(goal,0x14)||P(selected,0x10)!=source)return;
 {
  U check=0,held=selected;float gain=0;DefenseUnit*t;
  if(scouting_candidate(image,d,pl,goal,selected,time,&check,&gain,safety,&checked)||check!=object)return;
  P(held,4)++;
  ((DefenseM5)P(P(source,0),0x68))(source,0,selected,budget,1,1,0);
  /* Pending-goal AddActor uses NULL budget and no recalculation, exactly as
   * 1E4DF0. The enclosing activation recalculates once with its real budget. */
  if(!P(selected,0x10))((DefenseM4)P(P(goal,0),0x64))(goal,0,selected,0,0,0);
  if(P(selected,0x10)==goal){
   t=defense_record(image,d,actor,defense_key(source,object),time);t->cooldown=time+45;t->destination=0x4d79e8;t->since=-1;p->dispatch=time;
   /* Staged assignment, not an assertion that native activation succeeded. */
   emit(image,d,38,goal,pl,P(actor,4),1,best,45,F(actor,0x20),F(actor,0x24),actor,0);
  }else{
   if(!P(selected,0x10))((DefenseM4)P(P(source,0),0x64))(source,0,selected,budget,1,1);
   emit(image,d,38,goal,pl,P(actor,4),P(selected,0x10)==source?2:3,best,0,F(actor,0x20),F(actor,0x24),actor,0);
  }
  ((ClearingM0)(image+0x42fca))((U)&held,0);
 }
}
