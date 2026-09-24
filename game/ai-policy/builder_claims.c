/* Team-wide civilian reservations. Rebuilt on the simulation thread from
 * registered field companies and current factory jobs, never speculative
 * recruitment goals. No pointers to factory jobs are dereferenced later.
 * Four-second cache; native hire/remove/reset invalidates it immediately.
 * A bounded/incomplete census fails open rather than stopping expansion. */
static int builder_allied(U a,U b){return a&&b&&(a==b||(P(a,0x1f8)&&P(a,0x1f8)==P(b,0x1f8)));}
static int builder_team(U image,U pl){
 U sai=P(image,0x5f3fc8),i,n,list,k=P(pl,8);
 if(!sai||!k||!P(k,0x1f8))return 0;n=P(sai,0x70);list=P(sai,0x6c);
 if(!list||n>96)return 0;
 for(i=0;i<n;i++){U q=P(list,i*4);if(q&&q!=pl&&builder_enabled(image,q)&&builder_allied(k,P(q,8)))return 1;}return 0;
}
static BuilderClaim* builder_claim_add(FastData*f,U k,U actor,U job,U target,float x,float y){
 BuilderClaim*c;if(f->claimCount==2048)return 0;c=&f->claims[f->claimCount++];
 c->kingdom=k;c->actor=actor;c->job=job;c->target=target;c->site=0;c->assigned=0;c->x=x;c->y=y;return c;
}
static int builder_claim_taken(FastData*f,BuilderClaim*c,U site){
 U i;for(i=0;i<f->claimCount;i++){BuilderClaim*q=&f->claims[i];
  if(q!=c&&q->site==site&&builder_allied(q->kingdom,c->kingdom))return 1;}return 0;
}
static int builder_claim_usable(U image,FastData*f,BuilderClaim*c,U pl,U site){
 U a=actor_id(image,site);if(!a||builder_claim_taken(f,c,site))return 0;
 if(economy_sovereign(c->target)&&economy_has_kingdom(image,pl))return 0;
 if(economy_free_site(image,pl,c->target,a))return 1;
 return guarded_structure(image,a)&&!*(unsigned char*)(P(a,4)+0x290)
   &&P(P(a,4),0x4e0)==P(c->target,0x4e0)&&builder_camp_committed(image,pl,site);
}
static void builder_claim_refresh(U image,Data*d){
 FastData*f=(FastData*)d;U world=P(image,0x5f3fb8),reg=P(image,0x5ef72c),i,j,oldCount,pl,target;
 float time;if(f->claimBusy||!world||!reg)return;time=F(world,0xe8);if(!finite(time))return;
 if(f->claimValid&&f->claimWorld==world&&time>=f->claimTime&&time-f->claimTime<4)return;
 f->claimBusy=1;oldCount=f->claimWorld==world&&time>=f->claimTime?f->claimCount:0;
 for(i=0;i<oldCount;i++)for(j=0;j<sizeof(BuilderClaim)/4;j++)P(&f->oldClaims[i],j*4)=P(&f->claims[i],j*4);
 f->claimWorld=world;f->claimTime=time;f->claimValid=0;f->claimCount=0;f->claimSiteCount=0;
 for(i=0;i<65536;i++){
  U a=P(reg,0x20004+4*i),k,factory,list,n;BuilderClaim*c;
  if(!live_actor(image,a)||(P(a,8)&1))continue;
  if(ids_equal(P(a,4),"marker_settlement")||(guarded_structure(image,a)&&settlement_site(P(a,4))&&!*(unsigned char*)(P(a,4)+0x290))){
   if(f->claimSiteCount==512)goto incomplete;f->claimSites[f->claimSiteCount++]=P(a,0x14);
  }
  k=P(a,0xe8);pl=ai_for_kingdom(image,k);if(!builder_enabled(image,pl)||!builder_team(image,pl))continue;
  target=builder_target(image,a);
  if(target){
   U sa=construction_sa(pl,a),g=sa?P(sa,0x10):0;
   c=builder_claim_add(f,k,P(a,0x14),0,target,F(a,0x20),F(a,0x24));if(!c)goto incomplete;
   if(g&&P(g,4)==P(pl,0xc)&&P(g,0)==image+0x4da6b0&&(P(g,8)==1||P(g,8)==2)){
    /* Including an already occupied construction site prevents an active
     * builder being counted as available for another prospective site. */
    c->assigned=1;c->x=F(g,0x48);c->y=F(g,0x4c);
   }else{
    BuilderWork*w=builder_work(image,d,a,time);
    if(w&&w->camp&&w->goal==g&&builder_camp_committed(image,pl,w->camp)){
     U camp=actor_id(image,w->camp);c->assigned=1;c->x=F(camp,0x20);c->y=F(camp,0x24);
    }
   }
  }
  factory=P(a,0xa0);if(!factory||P(factory,4)!=a)continue;
  list=P(factory,0x14);n=P(factory,0x18);if(n>256||(!list&&n))goto incomplete;
  for(j=0;j<n;j++){
   U job=P(list,j*4),def=job?P(job,8):0;
   if(!job||P(job,4)!=0||!def||!(P(def,0x174)&128))continue;
   target=economy_center(def,P(job,0xc),0);if(!target)continue;
   if(!builder_claim_add(f,k,P(a,0x14),job,target,F(a,0x20),F(a,0x24)))goto incomplete;
  }
 }
 /* Accepted construction/staging beats provisional reservations. Company
  * registry order is stable and independent of the order in which bots tick. */
 for(i=0;i<f->claimCount;i++){
  BuilderClaim*c=&f->claims[i];if(!c->assigned)continue;pl=ai_for_kingdom(image,c->kingdom);
  for(j=0;j<f->claimSiteCount;j++){U site=f->claimSites[j],a=actor_id(image,site);
   if(a&&dist2(c->x,c->y,F(a,0x20),F(a,0x24))<1&&builder_claim_usable(image,f,c,pl,site)){c->site=site;break;}
  }
 }
 /* Keep each surviving promise so newly hired allies cannot make workers
  * oscillate between sites. Removed jobs/dead companies have no new record. */
 for(i=0;i<f->claimCount;i++){
  BuilderClaim*c=&f->claims[i];if(c->assigned)continue;pl=ai_for_kingdom(image,c->kingdom);
  for(j=0;j<oldCount;j++){BuilderClaim*q=&f->oldClaims[j];
   if(q->kingdom==c->kingdom&&q->actor==c->actor&&q->job==c->job&&q->target==c->target
    &&q->site&&builder_claim_usable(image,f,c,pl,q->site)){c->site=q->site;break;}
  }
 }
 for(i=0;i<f->claimCount;i++){
  BuilderClaim*c=&f->claims[i];float near=1e30f;
  if(c->site||c->assigned)continue;pl=ai_for_kingdom(image,c->kingdom);
  for(j=0;j<f->claimSiteCount;j++){
   U site=f->claimSites[j],a=actor_id(image,site);float dist;
   if(!a)continue;dist=dist2(c->x,c->y,F(a,0x20),F(a,0x24));
   if(!finite(dist)||dist>=near||!builder_claim_usable(image,f,c,pl,site))continue;
   /* Unknown locations never become reservations. Guarded sites additionally
    * require an actual committed friendly clearing force above. */
   if(!guarded_structure(image,a)){
    float score=((ConstructionF5)(image+0x1ee5b3))(pl,0,c->target,P(a,0x20),P(a,0x24),0,0);
    if(!finite(score)||score<=0)continue;
   }
   c->site=site;near=dist;
  }
 }
 f->claimValid=1;f->claimBusy=0;return;
 incomplete:f->claimCount=0;f->claimBusy=0;
}
static int builder_claim_blocked(U image,Data*d,U pl,float x,float y,U actor){
 FastData*f=(FastData*)d;U i,k;
 if(f->claimBusy||!builder_enabled(image,pl)||!builder_team(image,pl))return 0;
 builder_claim_refresh(image,d);if(!f->claimValid)return 0;k=P(pl,8);
 for(i=0;i<f->claimCount;i++){
  BuilderClaim*c=&f->claims[i];U a;if(!c->site||!builder_allied(c->kingdom,k))continue;
  a=actor_id(image,c->site);if(!a)continue;
  if(dist2(x,y,F(a,0x20),F(a,0x24))<1){
   if(c->kingdom!=k||(actor&&(c->job||actor!=c->actor)))return 1;
  }else if(actor&&c->kingdom==k&&!c->job&&c->actor==actor)return 1;
 }
 return 0;
}
