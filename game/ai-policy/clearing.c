/* One complete settlement-clearing plan feeds both reservations and transfers.
 * Planning never mutates assignments. Transfers run only after native list
 * iteration, within SelectGoals' borrowed vector/resource budget. Pending goals
 * are filled only inside their own native activation caller. */
typedef float (FAST *ClearingF1)(U,U,U);
typedef float (FAST *ClearingF4)(U,U,U,U,U,U);
typedef void (FAST *ClearingM0)(U,U);
typedef struct { U sa,source,actor,object; float cv,distance; } ClearingMember;
typedef struct { U value,next,previous; } ClearingNode;
typedef struct { U head,tail,count; } ClearingList;
typedef struct { U object,danger; } ClearingSafety;
#define CLEARING_MAX 32
typedef struct { U player,goal,camp,count,state; float time,need,power; ClearingMember members[CLEARING_MAX]; } ClearingPlan;
static int clearing_rally_point(U image,Data*d,U pl,U goal,U camp,float time);

static ClearingRally* clearing_rally_record(U image,Data*d,U pl){
 U sai=P(image,0x5f3fc8),list=sai?P(sai,0x6c):0,n=sai?P(sai,0x70):0,i;
 if(!list||n>96)return 0;
 for(i=0;i<n;i++)if(P(list,4*i)==pl)return &d->rallies[i];
 return 0;
}
static int clearing_rallied(U image,Data*d,U pl,U source,U camp,float time){
 ClearingRally*r=clearing_rally_record(image,d,pl);U region=source?P(source,0x48):0;
 if(!source||P(source,0)!=image+0x4da510||P(source,4)!=P(pl,0xc)||P(source,8)!=2||P(source,0x4c)||!region)return 0;
 if(r&&r->world==P(image,0x5f3fb8)&&r->kingdom==P(pl,8)&&r->camp==camp&&r->goal==source
  &&time>=r->time&&P(source,0)==image+0x4da510&&P(source,4)==P(pl,0xc)&&P(source,8)==2
  &&!P(source,0x4c)&&region&&F(region,0x54)==r->x&&F(region,0x58)==r->y)return 1;
 /* A loaded native region-defense assignment has no sidecar history. Infer
  * suitability again from the live camp and safe native guard point. */
 {U a=actor_id(image,camp);return a&&clearing_rally_point(image,d,pl,source,a,time);}
}

typedef U (FAST *ClearingRoute0)(U,U);
typedef U (FAST *ClearingRoute3)(U,U,U,U,U);
typedef U (FAST *ClearingRoute4)(U,U,U,U,U,U);
static int clearing_direct_route(U image,Data*d,U goal,U sa){
 U pl=player(goal),world=P(image,0x5f3fb8),regions=P(image,0x5f3fcc),table,n,from,to,router;
 U path[2]={0,0},node,steps=0,blocked=0,result=3,a,camp;Expansion*exp;
 /* Only this exact native AttackRegion precheck scans neighboring regions.
  * Other refusal methods and ordinary offensive targets retain their veto. */
 if(P(goal,0)!=image+0x4da480||P(P(goal,0),0x6c)!=image+0x1d6817
  ||!pl||P(sa,0xc)!=pl||!world||!regions||!P(sa,0)||!P(P(sa,0),8))return 0;
 exp=expansion_state(image,d,pl);camp=actor_id(image,P(goal,0x4c));
 if(!exp||!camp||expansion_rank(image,exp,camp)<=0)return 0;
 a=actor_id(image,P(sa,8));if(!a)return 0;
 table=P(regions,0x14);n=P(regions,0x18);router=P(world,0x23c);to=P(goal,0x48);
 if(!table||!n||n>65536||!router||!to)return 0;
 from=((ClearingRoute0)P(P(sa,0),8))(sa,0);
 if(!from||P(from,0)>=n||P(to,0)>=n||P(table,4*P(from,0))!=from||P(table,4*P(to,0))!=to)return 0;
 /* Same synchronous regional planner and flags as 1D6817. Its owned list
  * uses value/+0, previous/+4, next/+8; destroy with the native allocator.
  * Re-run for each candidate and again at commit, without changing the
  * native goal cache or the ego's two-region alert radius. */
 if(((ClearingRoute4)(image+0x2648eb))(router,0,(U)path,P(from,0),P(to,0),1)==1
  &&path[0]&&path[1]&&P(path[1],0)==P(to,0)&&!P(path[1],8)){
  result=1;
  for(node=path[0];node&&node!=path[1]&&steps++<n;node=P(node,8)){
   U id=P(node,0),region=id<n?P(table,4*id):0;
   if(!region||P(region,0)!=id){result=3;break;}
   /* The native precheck excludes the destination too. Keep its hostility,
    * known-building and positive-CV test for every traversed region. */
   if(((ClearingRoute3)(image+0x1f582a))(region,0,P(pl,8),0,1)&255){blocked=region;result=2;break;}
  }
  if(result==1&&node!=path[1])result=3;
 }
 ((ClearingM0)(image+0x763dc))((U)path,0);
 emit(image,d,51,goal,pl,P(a,4),result,0,0,blocked?F(blocked,0x54):F(a,0x20),blocked?F(blocked,0x58):F(a,0x24),a,0);
 return result==1;
}
static int clearing_admits(U image,Data*d,U goal,U sa){
 if(!goal||(P(goal,8)!=1&&P(goal,8)!=2)||!finite(F(goal,0x38))||F(goal,0x38)<=0)return 0;
 if(!(((RouteM1)P(P(goal,0),0x6c))(goal,0,sa)&255))return 1;
 return clearing_direct_route(image,d,goal,sa);
}
static int clearing_guard(U image,U camp,U actor){
 U den=guarded_structure(image,camp),group,steps=0,id=P(actor,0x14),element=P(actor,0x80),parent=0;
 if(!den)return 0;
 if(element&&P(element,4)==actor&&live_actor(image,P(element,0x10)))parent=P(P(element,0x10),0x14);
 /* Native DenizenComponent removal/update (20A36C/20A3CB) traverses group
  * nodes at +40, then full generation-checked actor IDs in group +C.
  * Same owner or mere proximity never proves membership of this camp. */
 for(group=P(den,0x40);group&&steps++<256;group=P(group,4)){
  U item=P(group,0),node,n=0;if(!item)return 0;
  for(node=P(item,0xc);node&&n++<512;node=P(node,4)){
   U ref=P(node,0);if((ref==id||(parent&&ref==parent))&&actor_id(image,ref))return 1;
  }
 }
 return 0;
}
static int clearing_scout_danger(U image,Data*d,U camp,U a,U k,float time){
 U reg=P(image,0x5ef72c),i;float x=F(a,0x20),y=F(a,0x24),r=defense_radius(image,a);
 if(!reg||!r||!finite(x)||!finite(y))return 1;
 if(defense_damage_at(image,d,k,time,x,y,r)>-100)return 1;
 for(i=0;i<65536;i++){
  U enemy=P(reg,0x20004+4*i),cell;float distance,cv;
  if(!enemy||!live_actor(image,enemy)||(P(enemy,8)&1)||P(enemy,0xe8)==k)continue;
  distance=dist2(x,y,F(enemy,0x20),F(enemy,0x24));if(!finite(distance)||distance>r*r)continue;
  if(!P(enemy,0xe8)||((RouteM1)P(P(enemy,0),0x144))(enemy,0,k)!=3)continue;
  cell=route_cell(image,F(enemy,0x20),F(enemy,0x24));if(!cell||!(((RouteM1)(image+0x24a86a))(cell,0,k)&255))continue;
  if(enemy==camp||clearing_guard(image,camp,enemy))continue;
  if(P(enemy,0x94)){if(route_fighting(image,enemy))return 1;continue;}
  if(P(enemy,0x7c)||P(enemy,0x6c)){
   cv=((RouteF0)(image+0x2274c1))(enemy,0);if(finite(cv)&&cv>0)return 1;
  }
 }
 return 0;
}
static int clearing_available(U image,U a){
 U state=defense_state(a),vt=state?P(state,0)-image:0;
 /* Recovery can run as a child Move, as in the recorded return to supply.
  * Native actor-state bits 2000/4000 remain set during that movement.
  * Keep its assignment intact; only omit its unavailable combat strength. */
 if(P(a,0x100)&0x6000)return 0;
 return vt==0x4f4d98||vt==0x4f4f28||vt==0x4f4df0||vt==0x4f5038
  ||vt==0x4f4f5c||vt==0x4f4f88||route_fighting(image,a);
}
static int clearing_scout_ready(U image,U a){
 U state=defense_state(a),vt=state?P(state,0)-image:0,org=P(a,0x7c),i,n,list;
 /* Exact native Sleep, Guard, Move and Explore classes. Retreat, exhaustion,
  * combat and construction are deliberately absent. Check members as well. */
 if(vt!=0x4f4d98&&vt!=0x4f4f28&&vt!=0x4f4df0&&vt!=0x4f5038)return 0;
 if(!clearing_available(image,a)||!company_readiness(image,a,70,60,0))return 0;
 n=P(org,0x2c);list=P(org,0x28);
 for(i=0;i<n;i++){U member=P(list,4*i);if(member&&route_fighting(image,member))return 0;}
 return 1;
}
static U clearing_candidate(U image,Data*d,U pl,U goal,U sa,float time,U*obj,ClearingSafety*safety,U*checked){
 U a=actor_id(image,P(sa,8)),source=P(sa,0x10),object,i,vt,rallied;
 if(!a||P(a,0xe8)!=P(pl,8)||P(sa,0xc)!=pl||!source||P(source,4)!=P(pl,0xc)||P(source,8)!=2)return 1;
 vt=P(source,0)-image;if(vt!=0x4da510&&vt!=0x4d79e8)return 1;
 rallied=clearing_rallied(image,d,pl,source,P(goal,0x4c),time);
 if(route_builder(image,a))return 6;
 if(company_recent_damage(image,d,a,time))return 3;
 if(vt==0x4da510&&!rallied){
  object=defense_object(image,source,P(pl,8),a);if(!object)return 1;
  /* Clearing has its own 70% HP / 60% morale gate. The stricter peaceful
   * scouting-release timer must not silently restore a 100% requirement.
   * Current threats and the last ten seconds of damage are checked below. */
  if(!defense_idle(image,a)||!clearing_scout_ready(image,a))return 2;
 }else{
  object=a;if(!clearing_scout_ready(image,a))return 2;
 }
 *obj=object;
 for(i=0;i<*checked;i++)if(safety[i].object==object)break;
 if(i==*checked){
  if(i==128)return 3;
  /* For a scout the radius is centered on that company, so a nearby fight
   * or damage blocks reassignment even when its top state is still Move. */
  safety[i].object=object;
  safety[i].danger=vt==0x4da510&&!rallied?defense_expansion_danger(image,d,source,object,P(pl,8),time)
   :clearing_scout_danger(image,d,actor_id(image,P(goal,0x4c)),object,P(pl,8),time);
  (*checked)++;
 }
 if(safety[i].danger)return 3;
 if(!clearing_admits(image,d,goal,sa))return 4;
 return 0;
}
static float clearing_power(U image,U ego,U target,ClearingNode*nodes,U n,float cv){
 ClearingList list;float factor;U i;
 for(i=0;i<n;i++){nodes[i].next=i+1<n?(U)&nodes[i+1]:0;nodes[i].previous=i?(U)&nodes[i-1]:0;}
 list.head=n?(U)nodes:0;list.tail=n?(U)&nodes[n-1]:0;list.count=n;
 factor=((ClearingF4)(image+0x5cb59))(ego,0,(U)&list,0,0,target);
 return finite(factor)&&factor>0?cv*factor:0;
}
/* The native planner otherwise keeps filling a highly ranked camp after our
 * group planner already reports enough. Veto only NEW members of that same
 * goal, never its existing attackers, retreat, or a different kind of target. */
static void clearing_staffed_admission(U image,Data*d,U a,U goal,float*result){
 U pl,sa,node,steps=0,count=0,camp,ego;float cv=0,need,power;ClearingNode members[CLEARING_MAX];
 if((*(U*)result&255)||!goal||!offense(image,goal)||!live_actor(image,a)||(P(goal,8)!=1&&P(goal,8)!=2))return;
 pl=player(goal);if(!pl||P(a,0xe8)!=P(pl,8))return;
 camp=structure_center(image,actor_id(image,P(goal,0x4c)));
 if(!camp||!guarded_structure(image,camp)||!settlement_site(P(camp,4))||((RouteM1)P(P(camp,0),0x144))(camp,0,P(pl,8))!=3)return;
 ego=P(pl,0x1c);if(!ego)return;
 need=((RouteF0)(image+0x2274c1))(camp,0);
 if(!finite(need)||need<0||!finite(F(goal,0x40))||F(goal,0x40)<0)return;
 need=maximum(1,maximum(need,F(goal,0x40))*1.5f);
 for(node=P(goal,0xc);node&&steps++<4096;node=P(node,4)){
  U actor;float v;sa=P(node,0);
  if(!sa||P(sa,0x10)!=goal||P(sa,0xc)!=pl)continue;
  actor=actor_id(image,P(sa,8));if(actor==a)return;
  if(!actor||P(actor,0xe8)!=P(pl,8)||!P(actor,0x7c)||!clearing_available(image,actor))continue;
  if(count==CLEARING_MAX)return;
  v=((ClearingF1)(image+0x5ca80))(ego,0,sa);if(!finite(v)||v<0)return;
  members[count++].value=sa;cv+=v;
 }
 if(node||!count)return;
 power=clearing_power(image,ego,camp,members,count,cv);
 if(finite(power)&&power>=need){
  *(U*)result|=1;
  emit(image,d,53,goal,pl,P(a,4),1,power,need,F(a,0x20),F(a,0x24),a,0);
 }
}
/* 0 invalid/no candidate; 3 no goal; 4 insufficient; 5 already staffed;
 * 6 complete plan. A tiny/zero individual marginal gain is not a veto:
 * feasibility is computed for the entire force with the native siege factor. */
static U clearing_goal_plan(U image,Data*d,U pl,ClearingPlan*q,U report,U goal,U camp){
 U world=P(image,0x5f3fb8),engine,ego,n,list,i,j,node,steps=0,have=0,existing=0,checked=0;
 float cv=0;Expansion*exp;ClearingNode planned[CLEARING_MAX*2];ClearingSafety safety[128];
 ClearingMember*members=q->members;
 for(i=0;i<sizeof(ClearingPlan);i+=4)P(q,i)=0;
 if(!world||P(image,0x5f9218)!=2||!pl)return 0;
 q->player=pl;q->time=F(world,0xe8);if(!finite(q->time))return 0;
 engine=P(pl,0xc);ego=P(pl,0x1c);if(!engine||!ego)return 0;
 list=P(engine,0x14);n=P(engine,0x18);if(!list||!n||n>4096)return 0;
 exp=expansion_state(image,d,pl);if(!exp||!exp->camp)return 0;
 q->camp=camp;q->goal=goal;q->state=P(goal,8);if(!q->camp)return 0;
 q->need=((RouteF0)(image+0x2274c1))(q->camp,0);
 if(!finite(q->need)||q->need<0||!finite(F(q->goal,0x40))||F(q->goal,0x40)<0)return 0;
 q->need=maximum(1,maximum(q->need,F(q->goal,0x40))*1.5f);
 for(node=P(q->goal,0xc);node&&steps++<4096;node=P(node,4)){
  U sa=P(node,0),a=sa?actor_id(image,P(sa,8)):0;float v;
  if(!a||P(sa,0x10)!=q->goal||P(sa,0xc)!=pl||P(a,0xe8)!=P(pl,8))continue;
  if(!P(a,0x7c)||!clearing_available(image,a)){
   if(report)emit(image,d,48,q->goal,pl,P(a,4),1,0,q->need,F(a,0x20),F(a,0x24),a,0);
   continue;
  }
  if(existing==CLEARING_MAX)return 0;
  v=((ClearingF1)(image+0x5ca80))(ego,0,sa);if(!finite(v)||v<0)return 0;
  planned[existing++].value=sa;cv+=v;
 }
 if(node)return 0;
 q->power=clearing_power(image,ego,q->camp,planned,existing,cv);
 if(!finite(q->power))return 0;
 if(q->power>=q->need)return 5;
 for(node=P(pl,0x2c),steps=0;node&&steps++<4096;node=P(node,4)){
  U sa=P(node,0),a,source,vt,object=0,reason;float v=0,distance;
  if(!sa||P(sa,0xc)!=pl)continue;a=actor_id(image,P(sa,8));if(!a||!P(a,0x7c))continue;
  source=P(sa,0x10);if(!source||source==q->goal)continue;vt=P(source,0)-image;
  if(vt!=0x4da510&&vt!=0x4d79e8)continue;
  reason=clearing_candidate(image,d,pl,q->goal,sa,q->time,&object,safety,&checked);
  distance=dist2(F(a,0x20),F(a,0x24),F(q->camp,0x20),F(q->camp,0x24));
  if(!reason&&(!finite(distance)||distance>256*256))reason=7;
  if(!reason){v=((ClearingF1)(image+0x5ca80))(ego,0,sa);if(!finite(v)||v<=0)reason=8;}
  if(reason){if(report)emit(image,d,34,q->goal,pl,P(a,4),reason,0,q->need,F(a,0x20),F(a,0x24),a,0);continue;}
  for(j=0;j<have;j++)if(distance<members[j].distance||(distance==members[j].distance&&P(a,0x14)<P(members[j].actor,0x14)))break;
  if(j==CLEARING_MAX)continue;
  if(have<CLEARING_MAX)have++;
  for(i=have-1;i>j;i--){U t;for(t=0;t<sizeof(ClearingMember);t+=4)P(&members[i],t)=P(&members[i-1],t);}
  members[j].sa=sa;members[j].source=source;members[j].actor=a;members[j].object=object;members[j].cv=v;members[j].distance=distance;
 }
 if(node)return 0;
 for(i=0;i<have;i++){
  planned[existing+i].value=members[i].sa;cv+=members[i].cv;q->count=i+1;
  q->power=clearing_power(image,ego,q->camp,planned,existing+q->count,cv);
  if(!finite(q->power))return 0;if(q->power>=q->need)break;
 }
 return q->count&&q->power>=q->need?6:4;
}
/* Rank native goals, skipping missing, rejected and already staffed targets.
 * A missing goal for the best registry camp cannot block the next site. */
static U clearing_plan(U image,Data*d,U pl,ClearingPlan*q,U report){
 U engine,list,n,i,j,have=0,first=0,result=0;Expansion*exp;
 struct {U goal,camp;float rank;} candidates[128];ClearingPlan attempt;
 for(i=0;i<sizeof(ClearingPlan);i+=4)P(q,i)=0;
 if(!pl||(engine=P(pl,0xc))==0)return 0;
 list=P(engine,0x14);n=P(engine,0x18);if(!list||!n||n>4096)return 0;
 exp=expansion_state(image,d,pl);if(!exp||!exp->camp)return 0;
 q->player=pl;q->time=exp->time;q->camp=actor_id(image,exp->camp);
 for(i=0;i<n;i++){
  U g=P(list,4*i),camp,state=g?P(g,8):0;float rank;
  if(!g||P(g,4)!=engine||(state!=1&&state!=2)||!offense(image,g)||!finite(F(g,0x38))||F(g,0x38)<=0)continue;
  camp=actor_id(image,P(g,0x4c));if(!camp||(rank=expansion_rank(image,exp,camp))<=0)continue;
  for(j=0;j<have;j++)if(candidates[j].camp==camp)break;
  if(j<have){if(state>P(candidates[j].goal,8))candidates[j].goal=g;continue;}
  for(j=0;j<have;j++)if(rank<candidates[j].rank)break;
  if(j==128)continue;
  if(have<128)have++;
  {U k,t;for(k=have-1;k>j;k--)for(t=0;t<sizeof(candidates[0]);t+=4)P(&candidates[k],t)=P(&candidates[k-1],t);}
  candidates[j].goal=g;candidates[j].camp=camp;candidates[j].rank=rank;
 }
 if(!have)return q->camp?3:0;
 for(i=0;i<have;i++){
  result=clearing_goal_plan(image,d,pl,&attempt,report,candidates[i].goal,candidates[i].camp);
  if(result==6){U t;for(t=0;t<sizeof(ClearingPlan);t+=4)P(q,t)=P(&attempt,t);return result;}
  /* Best insufficient group is retained for native nearby rallying. */
  if((result==4&&first!=4)||(result==5&&!first)){U t;for(t=0;t<sizeof(ClearingPlan);t+=4)P(q,t)=P(&attempt,t);first=result;}
 }
 return first;
}
static int clearing_reserved(U image,Data*d,U pl,U sa){
 ClearingPlan q;U i,result=clearing_plan(image,d,pl,&q,0);
 if(result==4&&q.camp&&clearing_rallied(image,d,pl,P(sa,0x10),P(q.camp,0x14),q.time))return 1;
 if(result!=6)return 0;
 for(i=0;i<q.count;i++)if(q.members[i].sa==sa){
  emit(image,d,39,q.goal,pl,P(q.camp,4),q.state,q.power,q.need,F(q.camp,0x20),F(q.camp,0x24),q.members[i].actor,0);
  return 1;
 }
 return 0;
}
static U clearing_commit(U image,Data*d,ClearingPlan*q,U budget){
 U i,checked=0,done=0,failed=0;ClearingSafety safety[128];
 if(P(q->goal,8)!=q->state||!actor_id(image,P(q->camp,0x14)))return 7;
 for(i=0;i<q->count;i++){
  U check=0;ClearingMember*m=&q->members[i];
  if(P(m->sa,0x10)!=m->source||clearing_candidate(image,d,q->player,q->goal,m->sa,q->time,&check,safety,&checked)||check!=m->object)return 7;
 }
 for(i=0;i<q->count;i++)P(q->members[i].sa,4)++;
 for(i=0;i<q->count;i++){
  ClearingMember*m=&q->members[i];
  ((DefenseM5)P(P(m->source,0),0x68))(m->source,0,m->sa,budget,1,1,0);
  if(!P(m->sa,0x10))((DefenseM4)P(P(q->goal,0),0x64))(q->goal,0,m->sa,q->state==1?0:budget,q->state==1?0:1,q->state==1?0:1);
  if(P(m->sa,0x10)!=q->goal){failed=1;break;}done++;
 }
 if(failed){
  /* Undo this group, not pre-existing attackers. Never leave a knowingly
   * incomplete new force when a native add unexpectedly refuses a member. */
  for(i=0;i<q->count;i++){
   ClearingMember*m=&q->members[i];
   if(P(m->sa,0x10)==q->goal)((DefenseM5)P(P(q->goal,0),0x68))(q->goal,0,m->sa,q->state==1?0:budget,q->state==1?0:1,q->state==1?0:1,0);
   if(!P(m->sa,0x10))((DefenseM4)P(P(m->source,0),0x64))(m->source,0,m->sa,budget,1,1);
  }
 }else{
  expansion_changed(d,q->player,q->goal);
  for(i=0;i<q->count;i++){
   ClearingMember*m=&q->members[i];DefenseUnit*t=defense_record(image,d,m->actor,P(m->source,0)==image+0x4da510?defense_key(m->source,m->object):P(m->object,0x14),q->time);
   t->cooldown=q->time+45;t->destination=P(q->goal,0)-image;t->since=-1;
   emit(image,d,35,q->goal,q->player,P(m->actor,4),q->state==1?2:1,q->power,q->need,F(m->actor,0x20),F(m->actor,0x24),m->actor,0);
  }
  {DefensePlayer*p=defense_player(image,d,q->player,q->time);if(p)p->dispatch=q->time;}
 }
 for(i=0;i<q->count;i++){U held=q->members[i].sa;((ClearingM0)(image+0x42fca))((U)&held,0);}
 return failed?8:q->state==1?2:1;
}
static void clearing_run(U image,Data*d,U obj,U*args,U pending){
 U world=P(image,0x5f3fb8),pl,engine,vector=args[1],budget=args[0],sai,players,n,i,result;float time;
 ClearingPlayer*cache;ClearingPlan q;
 if(!world||P(image,0x5f9218)!=2||!obj||!vector||!budget)return;
 pl=player(obj);if(!pl)return;engine=P(pl,0xc);
 if(!engine||P(obj,4)!=engine||vector!=engine+0x14||!P(vector,0)||P(vector,4)>4096||args[2]>=P(vector,4)||P(P(vector,0),4*args[2])!=obj)return;
 time=F(world,0xe8);if(!finite(time))return;
 sai=P(image,0x5f3fc8);if(!sai)return;players=P(sai,0x6c);n=P(sai,0x70);if(!players||n>96)return;
 for(i=0;i<n;i++)if(P(players,4*i)==pl)break;if(i==n)return;
 cache=&d->clearing[i];
 if(cache->world!=world||cache->kingdom!=P(pl,8)||time<cache->last){cache->world=world;cache->kingdom=P(pl,8);cache->last=-100;cache->camp=0;}
 /* Own pending activation must not miss its one valid commit window merely
  * because an active-goal callback ran earlier in this same planning pass. */
 if(!pending&&time-cache->last<4)return;
 result=clearing_plan(image,d,pl,&q,1);
 if(pending&&(!q.goal||q.goal!=obj||q.state!=1))return;
 if(!pending&&q.state==1){result=9;} /* reserve until its own activation */
 cache->last=time;cache->camp=q.camp?P(q.camp,0x14):0;
 if(result==6)result=clearing_commit(image,d,&q,budget);
 if(result&&q.camp)emit(image,d,33,q.goal,pl,P(q.camp,4),result,q.power,q.need,F(q.camp,0x20),F(q.camp,0x24),q.camp,0);
}
static void clearing_evaluate(U image,Data*d,U obj,U*args){clearing_run(image,d,obj,args,0);}
static void clearing_recruit(U image,Data*d,U obj,U*args){
 if(!obj||P(obj,8)!=1)return;
 if(offense(image,obj))clearing_run(image,d,obj,args,1);
 else if(P(obj,0)==image+0x4d79e8)clearing_run(image,d,obj,args,0);
}

/* Waiting for reinforcements uses a native region-defense goal already in the
 * current selection vector. It must be away from cities and outside every
 * explored guarded structure's reach. No custom goal/state/order is created;
 * if there is no admissible safe point, native exploration remains available. */
static int clearing_rally_point(U image,Data*d,U pl,U goal,U camp,float time){
 U region,cell,k=P(pl,8),reg=P(image,0x5ef72c),i,list,n;float x,y,distance;
 if(!goal||P(goal,0)!=image+0x4da510||P(goal,4)!=P(pl,0xc)||(P(goal,8)!=1&&P(goal,8)!=2)
  ||P(goal,0x4c)||!finite(F(goal,0x38))||F(goal,0x38)<=0||!(region=P(goal,0x48)))return 0;
 x=F(region,0x54);y=F(region,0x58);cell=route_cell(image,x,y);
 if(!cell||!(((RouteM1)(image+0x24a845))(cell,0,k)&255))return 0;
 distance=dist2(x,y,F(camp,0x20),F(camp,0x24));if(!finite(distance)||distance>160*160)return 0;
 if(defense_danger_at(image,d,k,time,1,x,y,48))return 0;
 list=P(k,0x2dc);n=P(k,0x2e0);if(n>256||(!list&&n))return 0;
 for(i=0;i<n;i++){
  U city=P(list,4*i);float radius;
  if(!live_actor(image,city)||(P(city,8)&1)||P(city,0xe8)!=k||!P(city,0x98))continue;
  radius=defense_radius(image,city);if(!radius||dist2(x,y,F(city,0x20),F(city,0x24))<=radius*radius)return 0;
 }
 if(!reg)return 0;
 for(i=0;i<65536;i++){
  U actor=P(reg,0x20004+4*i),def;float radius;
  if(!actor||!guarded_structure(image,actor)||((RouteM1)P(P(actor,0),0x144))(actor,0,k)!=3)continue;
  cell=route_cell(image,F(actor,0x20),F(actor,0x24));if(!cell||!(((RouteM1)(image+0x24a845))(cell,0,k)&255))continue;
  def=P(actor,4);radius=maximum(F(def,0x364),F(def,0x368))+48;
  if(!finite(radius)||radius<=0||radius>560||dist2(x,y,F(actor,0x20),F(actor,0x24))<=radius*radius)return 0;
 }
 return 1;
}
static void clearing_rally_recruit(U image,Data*d,U obj,U*args){
 U pl,engine,world=P(image,0x5f3fb8),list,n,i,j,budget=args[0],best=0,pending,checked=0,done=0;
 float bestDistance=0;ClearingPlan q;ClearingRally*r;ClearingSafety safety[128];
 if(!world||P(image,0x5f9218)!=2||!obj||P(obj,0)!=image+0x4da510||P(obj,0x4c)||!budget)return;
 pl=player(obj);if(!pl)return;engine=P(pl,0xc);list=P(engine,0x14);n=P(engine,0x18);
 if(args[1]!=engine+0x14||!list||n>4096||args[2]>=n||P(list,4*args[2])!=obj)return;
 if(clearing_plan(image,d,pl,&q,0)!=4||!q.count||!q.camp)return;
 r=clearing_rally_record(image,d,pl);if(!r)return;
 if(r->world==world&&r->kingdom==P(pl,8)&&q.time>=r->time&&q.time-r->time<10)return;
 for(i=0;i<n;i++){
  U goal=P(list,4*i),region;float distance;
  if(!clearing_rally_point(image,d,pl,goal,q.camp,q.time))continue;
  region=P(goal,0x48);distance=dist2(F(region,0x54),F(region,0x58),F(q.camp,0x20),F(q.camp,0x24));
  for(j=0;j<q.count;j++){
   U sa=q.members[j].sa;float gain;
   if(P(sa,0x10)==goal)continue;
   if(!clearing_admits(image,d,goal,sa))break;
   gain=((DefenseF2)P(P(goal,0),0x28))(goal,0,sa,1);
   if(!finite(gain)||gain<=0)break;
  }
  if(j==q.count&&(!best||distance<bestDistance)){best=goal;bestDistance=distance;}
 }
 /* Pending members can be added only in that goal's native activation call. */
 if(best!=obj)return;
 pending=P(obj,8)==1;
 for(i=0;i<q.count;i++){
  ClearingMember*m=&q.members[i];U check=0;
  if(P(m->sa,0x10)!=m->source||clearing_candidate(image,d,pl,q.goal,m->sa,q.time,&check,safety,&checked))return;
 }
 for(i=0;i<q.count;i++)P(q.members[i].sa,4)++;
 for(i=0;i<q.count;i++){
  ClearingMember*m=&q.members[i];if(m->source==obj)continue;
  ((DefenseM5)P(P(m->source,0),0x68))(m->source,0,m->sa,budget,1,1,0);
  if(!P(m->sa,0x10))((DefenseM4)P(P(obj,0),0x64))(obj,0,m->sa,pending?0:budget,pending?0:1,pending?0:1);
  if(P(m->sa,0x10)!=obj)break;done++;
 }
 if(i!=q.count){
  for(j=0;j<q.count;j++){
   ClearingMember*m=&q.members[j];if(m->source==obj)continue;
   if(P(m->sa,0x10)==obj)((DefenseM5)P(P(obj,0),0x68))(obj,0,m->sa,pending?0:budget,pending?0:1,pending?0:1,0);
   if(!P(m->sa,0x10))((DefenseM4)P(P(m->source,0),0x64))(m->source,0,m->sa,budget,1,1);
  }
 }else if(done){
  U region=P(obj,0x48);r->world=world;r->kingdom=P(pl,8);r->camp=P(q.camp,0x14);r->goal=obj;r->time=q.time;r->x=F(region,0x54);r->y=F(region,0x58);
  for(j=0;j<q.count;j++)if(q.members[j].source!=obj)emit(image,d,43,obj,pl,P(q.members[j].actor,4),pending?2:1,q.power,q.need,r->x,r->y,q.members[j].actor,0);
 }
 for(j=0;j<q.count;j++){U held=q.members[j].sa;((ClearingM0)(image+0x42fca))((U)&held,0);}
}
