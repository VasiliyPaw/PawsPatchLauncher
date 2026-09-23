/* Peaceful defense -> native clearing/exploration/construction assignments.
 * The frame hook only observes. Transfers occur inside SelectGoals, with its
 * live resource budget and an existing native-admitted goal. No direct orders,
 * actor coordinates, health, morale, ownership or save records are written. */
typedef U (FAST *DefenseM2)(U,U,U,U);
typedef float (FAST *DefenseF2)(U,U,U,U);
typedef void (FAST *DefenseM4)(U,U,U,U,U,U);
typedef void (FAST *DefenseM5)(U,U,U,U,U,U,U);
#define DEFENSE_QUIET_SECONDS 10
static U defense_state(U a){
 U cai=P(a,0x70),s=cai?P(cai,0x14):0;return s?P(s,0):0;
}
static int defense_idle(U image,U a){
 U s=defense_state(a),vt=s?P(s,0)-image:0;
 /* Sleep and Guard only. Moving, killing, engaging, retreating, exhausted,
  * repairing and constructing companies keep their native task. */
 return vt==0x4f4d98||vt==0x4f4f28;
}
static int company_readiness(U image,U a,U percent,U moralePercent,U fullRoster){
 U org,layout,map,defs,units,heroes,n,types,i,present=0;
 float hp=0,maxhp=0;
 if(!live_actor(image,a)||(P(a,8)&1))return 0;
 org=P(a,0x7c);if(!org||P(org,4)!=a||P(org,0)!=image+0x4e1ae0)return 0;
 /* A zero threshold means morale is not part of this policy's readiness. */
 if(moralePercent&&(!finite(F(org,0x5c)*100)||!finite(F(org,0x60)*moralePercent)||F(org,0x60)<=0||F(org,0x5c)*100<F(org,0x60)*moralePercent))return 0;
 layout=P(org,0x18);map=layout?P(layout,0x28):0;defs=P(org,0x1c);units=P(org,0x28);
 n=P(org,0x2c);types=P(org,0x20);heroes=P(org,0x34);
 if(!map||!defs||!units||!n||n>64||!types||types>32||P(layout,0x2c)!=n)return 0;
 if(heroes&&P(org,0x38)!=n)return 0;
 /* The layout maps physical slots to chosen unit types. Empty optional flank
  * slots are valid; a dead member of a selected type is not a full company. */
 for(i=0;i<n;i++){
  U type=P(map,4*i),unit=P(units,4*i),body,element;
  if(type>=types)return 0;
  if(!P(defs,4*type)&&!unit&&(!heroes||!P(heroes,4*i)))continue;
  if(!fullRoster&&(!unit||(live_actor(image,unit)&&(P(unit,8)&1))))continue;
  if(!live_actor(image,unit)||(P(unit,8)&1)||P(unit,0xe8)!=P(a,0xe8))return 0;
  element=P(unit,0x80);body=P(unit,0x60);
  if(!element||P(element,4)!=unit||P(element,0x10)!=a||!body||P(body,4)!=unit)return 0;
  if(!finite(F(body,0x10))||!finite(F(body,0x14))||F(body,0x14)<=0||F(body,0x10)<0)return 0;
  if(F(body,0x10)==0){if(fullRoster)return 0;continue;}
  hp+=minimum(F(body,0x10),F(body,0x14));maxhp+=F(body,0x14);
  present++;
 }
 /* Aggregate HP of living members, with no per-member wound threshold.
  * Full-roster checks remain available to the unrelated recovery policies. */
 return present>0&&finite(hp*100)&&finite(maxhp*percent)&&hp*100>=maxhp*percent;
}
static int company_health(U image,U a,U percent){return company_readiness(image,a,percent,100,1);}
static int defense_full(U image,U a){return company_health(image,a,100);}
static int defense_ready(U image,U a){return defense_idle(image,a)&&defense_full(image,a);}
static U defense_object(U image,U goal,U k,U company){
 U a=actor_id(image,P(goal,0x4c)),structure,body;
 /* Native DefendRegion legitimately has target ID 0 (1D8654/1D8530).
  * Observe that company's surroundings and the native region's guard point.
  * A stale nonzero target remains invalid, rather than becoming a region. */
 if(!P(goal,0x4c)){
  U region=P(goal,0x48);
  return region&&finite(F(region,0x54))&&finite(F(region,0x58))
   &&live_actor(image,company)&&P(company,0xe8)==k&&P(company,0x7c)?company:0;
 }
 if(!a||P(a,0xe8)!=k||!(structure=P(a,0x94))||P(structure,4)!=a)return 0;
 if(P(a,0x98))return invalid_center(image,P(a,0x98))?0:a;
 body=P(a,0x60);
 return body&&P(body,4)==a&&finite(F(body,0x10))&&F(body,0x10)>0?a:0;
}
static U defense_key(U goal,U object){
 /* Runtime identity only: never persisted, sorted, or used as random input.
  * Moving to another region resets the continuously quiet observation. */
 return P(goal,0x4c)?P(object,0x14):P(goal,0x48);
}
static float defense_radius(U image,U city){
 U center=structure_center(image,city),def=P(center,4);float r=def?maximum(F(def,0x364),F(def,0x368)):0;
 if(!finite(r)||r<0||r>512)return 0;
 return maximum(48,r+24);
}
static float defense_damage_at(U image,Data*d,U k,float time,float x,float y,float r){
 U i,world=P(image,0x5f3fb8);float last=-100;
 for(i=0;i<4096;i++){
  DefenseDamage*t=&d->damage[i];
  if(t->world==world&&t->kingdom==k&&time>=t->time&&time-t->time<DEFENSE_QUIET_SECONDS&&dist2(x,y,t->x,t->y)<=r*r)last=maximum(last,t->time);
 }
 return last;
}
static int defense_danger_at(U image,Data*d,U k,float time,int recent,float x,float y,float r){
 U i,reg=P(image,0x5ef72c);
 if(!reg||!r||!finite(x)||!finite(y))return 1;
 if(recent&&defense_damage_at(image,d,k,time,x,y,r)>-100)return 1;
 for(i=0;i<65536;i++){
  U a=P(reg,0x20004+4*i),owner,cell,s,vt;float distance;
  if(!a||!live_actor(image,a)||(P(a,8)&1))continue;
  distance=dist2(x,y,F(a,0x20),F(a,0x24));if(!finite(distance)||distance>r*r)continue;
  owner=P(a,0xe8);if(!owner)continue;
  s=defense_state(a);vt=s?P(s,0)-image:0;
  /* A friendly company already fighting beside the city is enough reason
   * to keep defenders, including a threat just outside current visibility. */
  if(owner==k){if(vt==0x4f4e20||vt==0x4f4fb4)return 1;continue;}
  if(((RouteM1)P(P(a,0),0x144))(a,0,k)!=3)continue;
  cell=route_cell(image,F(a,0x20),F(a,0x24));
  /* Current shared visibility (upper fog bits), not explored-map knowledge. */
  if(!cell||!(((RouteM1)(image+0x24a86a))(cell,0,k)&255))continue;
  /* A stationary nearby lair/tower is not a permanent defensive emergency.
   * Its deployed units or actual attacks still block release. */
  if(P(a,0x94)){if(vt==0x4f4e20||vt==0x4f4fb4)return 1;continue;}
  if(P(a,0x7c)||P(a,0x6c)){
   float cv=((RouteF0)(image+0x2274c1))(a,0);if(finite(cv)&&cv>0)return 1;
  }
 }
 return 0;
}
static float defense_last_damage(U image,Data*d,U goal,U object,U k,float time){
 float last=defense_damage_at(image,d,k,time,F(object,0x20),F(object,0x24),defense_radius(image,object));
 if(goal&&!P(goal,0x4c)){
  U region=P(goal,0x48);
  last=maximum(last,defense_damage_at(image,d,k,time,F(region,0x54),F(region,0x58),48));
 }
 return last;
}
static int defense_danger(U image,Data*d,U goal,U object,U k,float time,int recent){
 if(defense_danger_at(image,d,k,time,recent,F(object,0x20),F(object,0x24),defense_radius(image,object)))return 1;
 if(goal&&!P(goal,0x4c)){
  U region=P(goal,0x48);
  if(!region)return 1;
  return defense_danger_at(image,d,k,time,recent,F(region,0x54),F(region,0x58),48);
 }
 return 0;
}
/* Expansion donors protecting a city use its actual siege flag, not a fight
 * somewhere in the city's supply radius. Mines and region guards retain the
 * existing threat test. The individual company is checked separately. */
static int defense_expansion_danger(U image,Data*d,U goal,U object,U k,float time){
 U component=P(object,0x98),center;
 if(component){
  if(invalid_center(image,component))return 1;
  center=P(component,0x14);
  return ((P(object,0x100)|P(center,0x100))&0x00100000)!=0;
 }
 return defense_danger(image,d,goal,object,k,time,1);
}
static int company_recent_damage(U image,Data*d,U a,float time){
 U org=P(a,0x7c),i,n=org?P(org,0x2c):0,list=org?P(org,0x28):0,world=P(image,0x5f3fb8);
 if(!org||!list||!n||n>64)return 1;
 for(i=0;i<=n;i++){
  U u=i<n?P(list,4*i):a,id;DefenseDamage*t;
  if(!live_actor(image,u))continue;id=P(u,0x14);t=&d->damage[id&4095];
  if(t->world==world&&t->kingdom==P(a,0xe8)&&t->id==id&&time>=t->time&&time-t->time<DEFENSE_QUIET_SECONDS)return 1;
 }
 return 0;
}
static DefenseUnit* defense_record(U image,Data*d,U a,U city,float time){
 U id=P(a,0x14),world=P(image,0x5f3fb8),k=P(a,0xe8);DefenseUnit*t=&d->defenders[id&4095];
 if(t->world!=world||t->kingdom!=k||t->id!=id||time<t->last){
  t->world=world;t->kingdom=k;t->id=id;t->city=0;t->since=-1;t->cooldown=0;t->destination=0;
 }
 if(t->city!=city){t->city=city;t->since=-1;}
 if(time-t->last>15)t->since=-1;
 t->last=time;return t;
}
static DefensePlayer* defense_player(U image,Data*d,U pl,float time){
 U sai=P(image,0x5f3fc8),world=P(image,0x5f3fb8),list,n,i;DefensePlayer*p;
 if(!sai||!pl||!world||!finite(time))return 0;
 list=P(sai,0x6c);n=P(sai,0x70);if(!list||n>96)return 0;
 for(i=0;i<n;i++)if(P(list,4*i)==pl)break;if(i==n)return 0;
 p=&d->defensePlayers[i];
 if(p->world!=world||p->kingdom!=P(pl,8)||time<p->last){p->world=world;p->kingdom=P(pl,8);p->last=-100;p->dispatch=-100;}
 return p;
}
static void defense_tick_player(U image,Data*d,U pl,float time){
 DefensePlayer*p=defense_player(image,d,pl,time);U engine,node,steps=0,cityIds[128],dangerFlags[128],count=0;float hits[128];
 if(!p||time-p->last<10)return;p->last=time;
 engine=P(pl,0xc);node=engine?P(pl,0x2c):0;
 /* Engine+c is the pending-goal list, not active defense goals. Traverse the
  * native owned SA actors and their actual assignments instead. */
 for(;node&&steps++<4096;node=P(node,4)){
  U sa=P(node,0),g=sa?P(sa,0x10):0,city,a,j;DefenseUnit*t;
  if(!g||P(g,0)!=image+0x4da510||P(g,4)!=engine||P(g,8)!=2)continue;
  a=actor_id(image,P(sa,8));if(!a||P(a,0xe8)!=P(pl,8))continue;
  city=defense_object(image,g,P(pl,8),a);if(!city)continue;
  for(j=0;j<count;j++)if(cityIds[j]==P(city,0x14))break;
  if(j==count){
   if(count==128)continue;
   cityIds[j]=P(city,0x14);dangerFlags[j]=defense_danger(image,d,g,city,P(pl,8),time,0);
   hits[j]=defense_last_damage(image,d,g,city,P(pl,8),time);count++;
  }
  t=defense_record(image,d,a,defense_key(g,city),time);
  if(dangerFlags[j]||!defense_ready(image,a))t->since=-1;
  else if(t->since<0)t->since=time;
  else if(hits[j]>t->since)t->since=hits[j];
 }
}
static void defense_tick(U image,Data*d){
 U world=P(image,0x5f3fb8),sai=P(image,0x5f3fc8),list,n,i;float time;
 if(!world||!sai||P(image,0x5f9218)!=2)return;time=F(world,0xe8);
 list=P(sai,0x6c);n=P(sai,0x70);if(!finite(time)||!list||n>96)return;
 for(i=0;i<n;i++){U pl=P(list,4*i);if(pl)defense_tick_player(image,d,pl,time);}
}
static int defense_eligible(U image,Data*d,U a,U key,float time){
 DefenseUnit*t=&d->defenders[P(a,0x14)&4095];
 return t->world==P(image,0x5f3fb8)&&t->kingdom==P(a,0xe8)&&t->id==P(a,0x14)&&t->city==key
  &&t->since>=0&&time>=t->last&&time-t->last<=15&&time-t->since>=DEFENSE_QUIET_SECONDS&&defense_ready(image,a);
}
static int defense_admitted(U image,U goal,U sa){
 float gain;
 if(!goal||P(goal,8)!=2||!finite(F(goal,0x38))||F(goal,0x38)<=0)return 0;
 if(((RouteM1)P(P(goal,0),0x6c))(goal,0,sa)&255)return 0;
 gain=((DefenseF2)P(P(goal,0),0x28))(goal,0,sa,1);
 return finite(gain)&&gain>0;
}
static int defense_reserved(U image,Data*d,U a){
 U def=P(a,4),table=P(image,0x5efa8c),n,list,i,count;float cost[16];
 /* Native company recipe. Reserve kingdom-point companies (sovereign builders
  * and elite siege) from scouting, without hard-coding race names. */
 if(!d->query||!table||!def)return 1;
 n=P(table,0x28);list=P(table,0x24);if(!list||!n||n>16)return 1;
 count=((Query)d->query)(image,def,(P(def,0x174)&128)?P(def,0x2f0):0,cost);
 if(count!=n)return 1;
 for(i=0;i<n;i++)if(ids_equal(P(list,4*i),"kingdom_points_consumed")&&(!finite(cost[i])||cost[i]>0))return 1;
 return 0;
}
static U defense_scout_count(U image,U pl){
 U node=P(pl,0x2c),i=0,count=0;
 for(;node&&i++<4096;node=P(node,4)){
  U sa=P(node,0),g=sa?P(sa,0x10):0;
  /* Include an assignment staged during native activation (state 1). */
  if(g&&P(g,0)==image+0x4d79e8&&(P(g,8)==1||P(g,8)==2)&&actor_id(image,P(sa,8)))count++;
 }
 return count;
}
static int defense_has_construct(U image,U pl,U sa){
 U engine=P(pl,0xc),list=engine?P(engine,0x14):0,n=engine?P(engine,0x18):0,i;
 if(!list||n>4096)return 0;
 /* This vector is owned by the current SelectGoals invocation. */
 for(i=0;i<n;i++){
  U g=P(list,4*i);
  if(g&&P(g,4)==engine&&P(g,0)==image+0x4da6b0&&defense_admitted(image,g,sa))return 1;
 }
 return 0;
}
static int defense_clear_goal(U image,Data*d,U pl,U goal){
 Expansion*s;U target;
 if(!offense(image,goal)||P(goal,4)!=P(pl,0xc))return 0;
 s=expansion_state(image,d,pl);if(!s||!s->camp)return 0;
 target=structure_center(image,actor_id(image,P(goal,0x4c)));
 return target&&P(target,0x14)==s->camp&&guarded_structure(image,target)&&settlement_site(P(target,4));
}
static int defense_has_clear(U image,Data*d,U pl,U sa){
 return clearing_reserved(image,d,pl,sa);
}
static void defense_transfer(U image,Data*d,U source,U*args){
 U target=args[0],sa=args[1],budget=args[2],pl,city,a,kind;float time;DefensePlayer*p;DefenseUnit*t;
 if(!source||P(source,0)!=image+0x4da510||P(source,8)!=2||!target||!sa||!budget||P(sa,0x10)!=source)return;
 /* Offensive transfers are performed as a complete feasible group by
  * clearing_evaluate, not one company at a time through this fallback. */
 kind=P(target,0)-image;if(kind!=0x4d79e8&&kind!=0x4da6b0)return;
 pl=player(source);if(!pl||player(target)!=pl||P(sa,0xc)!=pl)return;
 a=actor_id(image,P(sa,8));if(!a||P(a,0xe8)!=P(pl,8))return;
 city=defense_object(image,source,P(pl,8),a);if(!city)return;
 time=F(P(image,0x5f3fb8),0xe8);p=defense_player(image,d,pl,time);
 if(!p||time-p->dispatch<10||!defense_eligible(image,d,a,defense_key(source,city),time))return;
 if(kind==0x4d79e8){
  if(defense_scout_count(image,pl)>=5||defense_reserved(image,d,a)||defense_has_construct(image,pl,sa)||(!route_builder(image,a)&&defense_has_clear(image,d,pl,sa)))return;
 }
 if(!defense_admitted(image,target,sa))return;
 if(defense_danger(image,d,source,city,P(pl,8),time,1))return;
 /* Same pair of virtual methods, budget, recalculation flags and lifetime
  * as native successful transfer at 1E50DE / 1E50ED. Caller owns a SA ref. */
 ((DefenseM5)P(P(source,0),0x68))(source,0,sa,budget,1,1,0);
 ((DefenseM4)P(P(target,0),0x64))(target,0,sa,budget,1,1);
 if(P(sa,0x10)!=target)return;
 t=defense_record(image,d,a,defense_key(source,city),time);t->cooldown=time+45;t->destination=kind;t->since=-1;p->dispatch=time;
 emit(image,d,32,source,pl,P(a,4),kind,DEFENSE_QUIET_SECONDS,45,F(a,0x20),F(a,0x24),a,0);
}
static void defense_evaluate(U image,Data*d,U mode,U obj,U*args,float*result){
 U world=P(image,0x5f3fb8);float time;
 if(!world||P(image,0x5f9218)!=2)return;time=F(world,0xe8);if(!finite(time))return;
 if(mode==17){defense_tick(image,d);return;}
 if(mode==20){defense_transfer(image,d,obj,args);return;}
 if(mode==21){
  U a=args[0],ev=args[1];DefenseDamage*t;
  if(!ev||!finite(F(ev,0xc))||F(ev,0xc)<=0||!live_actor(image,a)||!ai_for_kingdom(image,P(a,0xe8)))return;
  t=&d->damage[P(a,0x14)&4095];t->world=world;t->id=P(a,0x14);t->kingdom=P(a,0xe8);t->time=time;t->x=F(a,0x20);t->y=F(a,0x24);return;
 }
 if(mode==18){
  U goal=args[0],a=obj,city,clearing;DefenseUnit*t;
  if((*(U*)result&255)||!goal||P(goal,0)!=image+0x4da510||!live_actor(image,a))return;
  t=&d->defenders[P(a,0x14)&4095];
  if(t->world!=world||t->kingdom!=P(a,0xe8)||t->id!=P(a,0x14)||time<t->last||time>=t->cooldown)return;
  clearing=t->destination==0x4da480||t->destination==0x4d84d4;
  if(clearing){
   /* The same siege rule must govern the existing return cooldown, or the
    * next strategic pass immediately steals a newly dispatched clearer. */
   if(!company_readiness(image,a,70,60,0)||(P(a,0x100)&0x6000)||company_recent_damage(image,d,a,time))return;
  }else if(!defense_full(image,a))return;
  city=defense_object(image,goal,P(a,0xe8),a);
  if(!city||(clearing?defense_expansion_danger(image,d,goal,city,P(a,0xe8),time):defense_danger(image,d,goal,city,P(a,0xe8),time,1)))return;
  *(U*)result|=1; /* The native invalid-actor branch rejects this one calm goal. */
 }
}
