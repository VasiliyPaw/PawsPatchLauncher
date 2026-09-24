/* Native TeamCommand GIVE_ACTOR, just as SAIGoalGiveActor::GenerateOrders.
 * The simulation/network command validates ownership and performs transfer.
 * We never write ownership, city lists, resources or saved game fields. */
typedef U (FAST *GiftM3)(U,U,U,U,U);
static U gift_city_count(U image,U k){
 U list=P(k,0x2dc),n=P(k,0x2e0),i,count=0;
 if(n>256||(!list&&n))return 0xffffffffu;
 for(i=0;i<n;i++){
  U a=P(list,4*i);
  if(live_actor(image,a)&&!(P(a,8)&1)&&P(a,0xe8)==k&&P(a,0x94)&&!invalid_center(image,P(a,0x98)))count++;
 }
 return count;
}
static void city_share(U image,Data*d,U pl,U slot){
 U world=P(image,0x5f3fb8),k=P(pl,8),list,n,i,own,recipient=0,fewest=0xffffffffu,best=0,bestSize=0xffffffffu;
 U command[8],defs=P(image,0x5f3fb4);float now=F(world,0xe8);CityGift*c=&((FastData*)d)->cityGifts[slot];
 if(c->world!=world||c->kingdom!=k||now<c->last){c->world=world;c->kingdom=k;c->last=-60;c->city=0;}
 if(now-c->last<60)return;
 /* An accepted command may still be in flight. Never enqueue it repeatedly. */
 if(c->city){U pending=actor_id(image,c->city);if(pending&&P(pending,0xe8)==k&&now-c->last<120)return;c->city=0;}
 c->last=now;
 if(P(k,0x1a4)==2||!P(k,0x1f8))return;
 own=gift_city_count(image,k);if(own==0xffffffffu||own<5)return;
 list=P(world,0x150);n=P(world,0x154);if(!list||n>96)return;
 for(i=0;i<n;i++){
  U other=P(list,4*i),count;
  if(!other||other==k||P(other,0x1a4)==2||P(other,0x1f8)!=P(k,0x1f8))continue;
  count=gift_city_count(image,other);
  if(count<fewest&&count<own&&own-count>4){fewest=count;recipient=other;}
 }
 if(!recipient||!defs||!(defs=P(defs,0x270))||!P(defs,0x24)||!P(P(defs,0x24),16))return;
 list=P(k,0x2dc);n=P(k,0x2e0);
 for(i=0;i<n;i++){
  U a=P(list,4*i),container,center,size;
  if(!live_actor(image,a)||(P(a,8)&1)||P(a,0xe8)!=k||!P(a,0x94))continue;
  container=P(a,0x98);if(invalid_center(image,container))continue;center=P(container,0x14);
  if(economy_sovereign(P(center,4))||((P(a,0x100)|P(center,0x100))&0x00100000))continue;
  /* Container's last building index: fewer buildings means less developed.
   * Native tribute validation also rejects non-transferable settlements. */
  size=P(container,0x1c);if(size>256)continue;
  ((GiftM3)(image+0x287201))((U)command,0,4,k,recipient);
  ((RouteM1)(image+0x287257))((U)command,0,P(a,0x14));
  if(!(((ClearingM0)(image+0x287287))((U)command,0)&255))continue;
  if(!best||size<bestSize||(size==bestSize&&P(a,0x14)<P(best,0x14))){best=a;bestSize=size;}
 }
 if(!best)return;
 ((GiftM3)(image+0x287201))((U)command,0,4,k,recipient);
 ((RouteM1)(image+0x287257))((U)command,0,P(best,0x14));
 if(!(((ClearingM0)(image+0x287287))((U)command,0)&255))return;
 c->city=P(best,0x14);c->recipient=P(recipient,0x14);
 ((RouteM1)(image+0xb8e65))((U)command,0,P(pl,0x198));
 emit(image,d,59,best,pl,P(best,4),c->recipient,(float)own,(float)fewest,0,0,best,0);
}
