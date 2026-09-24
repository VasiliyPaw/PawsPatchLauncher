/* Prefer an available settlement construction plan to optional assignments.
 * Use native capability/site/score queries and native goal membership methods.
 * Never pin a company in combat/retreat or synthesize a construction order. */
typedef float (FAST *ConstructionF5)(U,U,U,U,U,U,U);
static int construction_one_worker(U a){
 U k=P(a,0xe8),def=k?P(k,0x240):0;
 return def&&(ids_equal(def,"Undead")||ids_equal(def,"undead")||ids_equal(def,"Haroun")||ids_equal(def,"haroun"));
}
static int construction_live_worker(U image,U a){
 U org=P(a,0x7c),list,n,i;
 if(!org||P(org,4)!=a)return 0;
 list=P(org,0x28);n=P(org,0x2c);if(!list||!n||n>64)return 0;
 for(i=0;i<n;i++){
  U u=P(list,4*i),body,element;
  if(!live_actor(image,u)||(P(u,8)&1)||P(u,0xe8)!=P(a,0xe8)||!route_center_capable(image,u))continue;
  body=P(u,0x60);element=P(u,0x80);
  if(body&&P(body,4)==u&&element&&P(element,4)==u&&P(element,0x10)==a
    &&finite(F(body,0x10))&&F(body,0x10)>0)return 1;
 }
 return 0;
}
static int construction_ready(U image,U a,int assigned){
 U s=defense_state(a),vt=s?P(s,0)-image:0,org=P(a,0x7c),n,i,list;
 /* Native Construct also covers travel to the still-free settlement marker.
  * Protect that phase of an assigned build; it is not protected by the native
  * optional-goal exchange. Do not reclaim Construct/Repair from another task. */
 if(vt!=0x4f4d98&&vt!=0x4f4f28&&vt!=0x4f4df0&&vt!=0x4f5038
   &&!(assigned&&vt==0x4f4ed0))return 0;
 /* Do not reclaim a child Move that belongs to native recovery/retreat. */
 if((P(a,0x100)&0x4000)||((P(a,0x100)&0x2000)&&!construction_one_worker(a)))return 0;
 if(!route_builder(image,a))return 0;
 if(construction_one_worker(a)){if(!construction_live_worker(image,a))return 0;}
 else if(!company_readiness(image,a,70,0,0))return 0;
 n=P(org,0x2c);list=P(org,0x28);
 if(!list||!n||n>64)return 0;
 for(i=0;i<n;i++){U u=P(list,4*i);if(u&&route_fighting(image,u))return 0;}
 return 1;
}
static int construction_available(U image,U pl,U g,U sa){
 U def,cell,node,steps=0;float score;
 if(!g||P(g,0)!=image+0x4da6b0||P(g,4)!=P(pl,0xc)||(P(g,8)!=1&&P(g,8)!=2))return 0;
 def=P(g,0x44);
 if(!def||!P(def,0x430)||!settlement_site(def)||!finite(F(g,0x38))||F(g,0x38)<=0)return 0;
 if(builder_site_claimed(image,pl,g,sa))return 0;
 if(!(((RouteM1)(image+0x1d13d4))(g,0,sa)&255))return 0;
 cell=route_cell(image,F(g,0x48),F(g,0x4c));if(!cell)return 0;
 /* Only a real free settlement marker. Occupied/removed/changed sites do not
  * reserve a builder forever. Current construction already has native locking. */
 for(node=P(cell,8);node&&steps++<1024;node=P(node,4)){
  U a=P(node,0);
  if(live_actor(image,a)&&!(P(a,8)&1)&&P(a,4)==P(def,0x4e0)
    &&same_spot(F(g,0x48),F(g,0x4c),a,0x20))break;
 }
 if(!node||steps>=1024)return 0;
 score=((ConstructionF5)(image+0x1ee5b3))(pl,0,def,P(g,0x48),P(g,0x4c),0,0);
 return finite(score)&&score>0;
}
static U construction_sa(U pl,U actor){
 U node,steps=0,id=P(actor,0x14);
 for(node=P(pl,0x2c);node&&steps++<4096;node=P(node,4)){
  U sa=P(node,0);if(sa&&P(sa,8)==id&&P(sa,0xc)==pl)return sa;
 }
 return 0;
}
static void construction_admission(U image,Data*d,U a,U goal,float*result){
 U pl,sa,source,vt,world=P(image,0x5f3fb8);
 if(d->constructionBusy||(*(U*)result&255)||!goal||!live_actor(image,a)||!world||P(image,0x5f9218)!=2)return;
 vt=P(goal,0)-image;
 /* A second Construct goal is optional too: native optimization can otherwise
  * exchange the same builder between several valid settlement sites in one
  * planning pass. Keep the accepted site through pending native activation.
  * Haroun/Undead with a living worker also keep construction instead of health/
  * morale-only Recover reassignment. Optional repair cannot steal this plan.
  * Danger, insufficient HP, combat and retreat still release protection.
  * Other races keep their normal recovery behavior. */
 if(!offense(image,goal)&&vt!=0x4d79e8&&vt!=0x4da510&&vt!=0x4da6b0&&vt!=0x4da3f8
   &&!(vt==0x4da5a0&&construction_one_worker(a)))return;
 pl=player(goal);if(!pl||P(a,0xe8)!=P(pl,8))return;
 sa=construction_sa(pl,a);source=sa?P(sa,0x10):0;
 if(!source||source==goal||P(source,0)!=image+0x4da6b0
   ||(P(source,8)!=1&&P(source,8)!=2)||!construction_ready(image,a,1))return;
 d->constructionBusy=1;
 if(construction_available(image,pl,source,sa)
   &&!defense_danger(image,d,0,a,P(pl,8),F(world,0xe8),1)){
  *(U*)result|=1;
  emit(image,d,41,goal,pl,P(a,4),1,0,1,F(source,0x48),F(source,0x4c),a,0);
 }
 d->constructionBusy=0;
}
static void construction_recruit(U image,Data*d,U goal,U*args){
 U pl,engine,world=P(image,0x5f3fb8),node,steps=0,best=0,source=0,a=0,budget=args[0],pending;
 float time,bestDistance=0;
 if(d->constructionBusy||!world||P(image,0x5f9218)!=2||!goal||!budget)return;
 if(P(goal,0)!=image+0x4da6b0||(P(goal,8)!=1&&P(goal,8)!=2)||P(goal,0xc))return;
 pl=player(goal);if(!pl)return;engine=P(pl,0xc);
 if(args[1]!=engine+0x14||!P(engine,0x14)||P(engine,0x18)>4096||args[2]>=P(engine,0x18)||P(P(engine,0x14),4*args[2])!=goal)return;
 time=F(world,0xe8);if(!finite(time))return;
 d->constructionBusy=1;
 for(node=P(pl,0x2c);node&&steps++<4096;node=P(node,4)){
  U sa=P(node,0),actor=sa?actor_id(image,P(sa,8)):0,g=sa?P(sa,0x10):0,vt;float distance;
  if(!actor||P(actor,0xe8)!=P(pl,8)||P(sa,0xc)!=pl||g==goal)continue;
  if(g){
   if(P(g,4)!=engine||P(g,8)!=2)continue;
   vt=P(g,0)-image;if(!offense(image,g)&&vt!=0x4da510&&vt!=0x4d79e8
     &&!(vt==0x4da5a0&&construction_one_worker(actor)))continue;
  }
  if(!construction_ready(image,actor,0)||!construction_available(image,pl,goal,sa))continue;
  /* Native Recover locks its actor until full healing. A surviving Haroun or
   * Undead worker can leave recovery; capability, site and danger still pass. */
  if(!(g&&P(g,0)==image+0x4da5a0&&construction_one_worker(actor))
    &&!(((DefenseM2)P(P(sa,0),0x20))(sa,0,goal,0)&255))continue;
  if(defense_danger(image,d,0,actor,P(pl,8),time,1))continue;
  distance=dist2(F(actor,0x20),F(actor,0x24),F(goal,0x48),F(goal,0x4c));if(!finite(distance))continue;
  if(!best||distance<bestDistance||(distance==bestDistance&&P(actor,0x14)<P(a,0x14))){best=sa;source=g;a=actor;bestDistance=distance;}
 }
 if(best&&!node){
  pending=P(goal,8)==1;P(best,4)++;
  if(source)((DefenseM5)P(P(source,0),0x68))(source,0,best,budget,1,1,0);
  if(!P(best,0x10))((DefenseM4)P(P(goal,0),0x64))(goal,0,best,pending?0:budget,pending?0:1,pending?0:1);
  if(P(best,0x10)==goal){expansion_changed(d,pl,goal);emit(image,d,42,goal,pl,P(a,4),pending?2:1,0,1,F(goal,0x48),F(goal,0x4c),a,0);}
  else if(source&&!P(best,0x10))((DefenseM4)P(P(source,0),0x64))(source,0,best,budget,1,1);
  ((ClearingM0)(image+0x42fca))((U)&best,0);
 }
 d->constructionBusy=0;
}
