/* These filters change AI goal scores/admission, never orders, ownership or
 * combat. Only known, living guards are considered. Native prerequisites,
 * economy, diplomacy and final assignment checks still run. */
static U actor_id(U image,U id){
 U reg=P(image,0x5ef72c),a=reg&&id?P(reg,0x20004+4*(id&65535)):0;
 return live_actor(image,a)&&P(a,0x14)==id&&!(P(a,8)&1)?a:0;
}
static int ids_equal(U def,const char* text){
 U s=def?P(def,8):0,i;if(!s)return 0;
 for(i=0;i<64;i++){W c=*(W*)(s+2*i);if(c!=(unsigned char)text[i])return 0;if(!c)return 1;}return 0;
}
static int settlement_site(U definition){
 return definition&&ids_equal(P(definition,0x4e0),"marker_settlement");
}
static int offense(U image,U goal){
 U vt=goal?P(goal,0)-image:0;return vt==0x4da480||vt==0x4d84d4;
}
static float expansion_rank(U image,Expansion*s,U a){
 U cell,j,cities=P(s->kingdom,0x2dc),n=P(s->kingdom,0x2e0);float cv,near=1.0e20f;
 if(!cities||n>256||!guarded_structure(image,a)||!settlement_site(P(a,4)))return 0;
 if(((RouteM1)P(P(a,0),0x144))(a,0,s->kingdom)!=3)return 0;
 cell=route_cell(image,F(a,0x20),F(a,0x24));
 if(!cell||!(((RouteM1)(image+0x24a845))(cell,0,s->kingdom)&255))return 0;
 cv=((RouteF0)(image+0x2274c1))(a,0);
 if(!finite(cv)||cv<0||s->strength<1.5f*cv)return 0;
 for(j=0;j<n;j++){
  U city=P(cities,4*j);
  if(live_actor(image,city)&&!(P(city,8)&1)&&P(city,0xe8)==s->kingdom&&P(city,0x94)&&P(city,0x98))
   near=minimum(near,dist2(F(city,0x20),F(city,0x24),F(a,0x20),F(a,0x24)));
 }
 if(!finite(near)||near>256*256)return 0;
 return (1+near/4096)*(1+cv/maximum(s->strength,1));
}
static Expansion* expansion_state(U image,Data*d,U pl){
 U sai=P(image,0x5f3fc8),world=P(image,0x5f3fb8),list,n,i,k,reg,cities,ncities;
 Expansion*s;float time,best=0;U node,steps;
 if(!pl||!sai||!world||P(image,0x5f9218)!=2)return 0;
 list=P(sai,0x6c);n=P(sai,0x70);if(!list||n>96)return 0;
 for(i=0;i<n;i++)if(P(list,4*i)==pl)break;
 if(i==n)return 0;k=P(pl,8);if(!k)return 0;
 time=F(world,0xe8);if(!finite(time))return 0;s=&d->expansion[i];
 if(s->world==world&&s->kingdom==k&&time>=s->time&&time-s->time<1)return s;
 s->world=world;s->kingdom=k;s->time=time;s->camp=0;s->cities=0;s->strength=0;
 cities=P(k,0x2dc);ncities=P(k,0x2e0);if(!cities||ncities>256)return s;
 for(i=0;i<ncities;i++){
  U a=P(cities,4*i);
  if(live_actor(image,a)&&!(P(a,8)&1)&&P(a,0xe8)==k&&P(a,0x94)&&P(a,0x98)&&!invalid_center(image,P(a,0x98)))s->cities++;
 }
 /* Native AI-owned actor list, not every friendly army on the map. */
 for(node=P(pl,0x2c),steps=0;node&&steps++<4096;node=P(node,4)){
  U sa=P(node,0),a=sa?actor_id(image,P(sa,8)):0,org;float cv;
  if(!a||P(a,0xe8)!=k||(org=P(a,0x7c))==0||route_builder(image,a))continue;
  cv=((RouteF0)(image+0x2274c1))(a,0);if(finite(cv)&&cv>0)s->strength+=cv;
 }
 /* Clearing a settlement site remains useful after the opening, including
  * when an AW sovereign builder needs room for its kingdom. */
 if(!s->cities||!finite(s->strength)||s->strength<=0)return s;
 reg=P(image,0x5ef72c);if(!reg)return s;
 for(i=0;i<65536;i++){
  U a=P(reg,0x20004+4*i);float score;if(!a)continue;score=expansion_rank(image,s,a);
  if(score<=0)continue;
  if(!s->camp||score<best){best=score;s->camp=P(a,0x14);}
 }
 return s;
}
static float expansion_priority(U image,Data*d,U goal,U pl,float before){
 U target=0,reason=0,vt=P(goal,0)-image;float after=before;Expansion*s;
 if(!finite(before)||before<=0||(!offense(image,goal)&&vt!=0x4da6b0))return before;
 s=expansion_state(image,d,pl);if(!s||!s->cities)return before;
 if(vt==0x4da6b0){
  if(s->cities==1&&settlement_site(P(goal,0x44))){after=before*3;reason=1;}
 }else{
  target=structure_center(image,actor_id(image,P(goal,0x4c)));
  if(!guarded_structure(image,target)||((RouteM1)P(P(target,0),0x144))(target,0,s->kingdom)!=3)return before;
  /* Do not reduce attacks on ordinary enemy towns, or activate a native
   * zero-priority goal. A candidate camp must remain alive and hostile. */
  if(P(target,0x98))return before;
  if(s->camp&&actor_id(image,s->camp)){
   if(expansion_rank(image,s,target)>0){after=before*4;reason=2;}
   else if(!settlement_site(P(target,4))){after=before*0.15f;reason=3;}
  }
 }
 if(after!=before&&finite(after)){
  F(goal,0x38)=after;d->counts[19]++;
  emit(image,d,31,goal,pl,target?P(target,4):P(goal,0x44),reason,before,after,target?F(target,0x20):F(goal,0x48),target?F(target,0x24):F(goal,0x4c),target,0);
  return after;
 }
 return before;
}
/* 1F77B6: an attack-region candidate has passed the native object-list,
 * diplomacy, destruction and CanAttack/CanCapture checks. Rank it BEFORE
 * 1F77CD compares candidates. A goal-level multiplier alone is too late:
 * 1D7154 has already stored the winning actor ID by then. */
static void expansion_candidate(U image,Data*d,U pl,U target,float*score){
 Expansion*s;float before=*score,after;
 if(!finite(before)||before<=0||!pl||!target)return;
 s=expansion_state(image,d,pl);
 if(!s||!s->cities||expansion_rank(image,s,target)<=0)return;
 after=before*4;if(!finite(after))return;
 *score=after;
 emit(image,d,40,target,pl,P(target,4),1,before,after,F(target,0x20),F(target,0x24),target,0);
}
