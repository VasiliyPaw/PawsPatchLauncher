/* Opening expansion takes precedence over optional capturable structures.
 * Definition +290 is the native BodyComponent.captureable byte (parser 027046).
 * No order/state writes: native goal selection and actor admission enforce it. */
static U opening_city_count(U image,U pl){
 U k=pl?P(pl,8):0,list,n,i,j,count=0,seen[3];
 if(!k||ai_for_kingdom(image,k)!=pl)return 3;
 list=P(k,0x2dc);n=P(k,0x2e0);
 if(n>256||(!list&&n))return 3; /* Unknown layout does not impose a new veto. */
 for(i=0;i<n;i++){
  U city=P(list,4*i),container,center,def;
  if(!live_actor(image,city)||(P(city,8)&1)||P(city,0xe8)!=k||!P(city,0x94))continue;
  container=P(city,0x98);if(!container||invalid_center(image,container))continue;
  center=P(container,0x14);def=P(center,4);
  /* Sovereign centers count as cities; foundation enclaves do not. */
  if(!settlement_site(def))continue;
  for(j=0;j<count;j++)if(seen[j]==city)break;
  if(j<count)continue;
  seen[count++]=city;if(count==3)return count;
 }
 return count;
}
/* Verified RandomActor random_lairlargemonster* definitions in the installed
 * Arcane Wars data. Exact IDs avoid classifying small settlement camps, their
 * roaming defenders, or ordinary enemy towns by size/combat strength alone. */
static int opening_large_definition(U def){
 return ids_equal(def,"active_ice_dragon_lair")||ids_equal(def,"active_lair_dragon_lair")
  ||ids_equal(def,"lair_dark_rift")||ids_equal(def,"branch_thing_dwelling")
  ||ids_equal(def,"wyvern_nest")||ids_equal(def,"active_storm_drake_crag");
}
static U opening_large_actor(U image,U pl,U actor){
 U target=structure_center(image,actor),k=pl?P(pl,8):0;
 if(!target||!k||!opening_large_definition(P(target,4))||!guarded_structure(image,target))return 0;
 if(P(target,0xe8)==k||((RouteM1)P(P(target,0),0x144))(target,0,k)!=3)return 0;
 return opening_city_count(image,pl)<3?target:0;
}
static U opening_large_target(U image,U goal,U pl){
 if(!goal||!pl||!offense(image,goal)||P(goal,4)!=P(pl,0xc))return 0;
 return opening_large_actor(image,pl,actor_id(image,P(goal,0x4c)));
}
static int opening_large_candidate(U image,Data*d,U pl,U actor,float*score){
 U target;
 if(!finite(*score)||*score<=0)return 0;
 target=opening_large_actor(image,pl,actor);if(!target)return 0;
 emit(image,d,50,target,pl,P(target,4),1,*score,0,F(target,0x20),F(target,0x24),target,0);
 *score=0;return 1;
}
static U opening_capture_target(U image,U goal,U pl){
 U target,def,structure,body,k;
 if(!goal||!pl||!offense(image,goal)||P(goal,4)!=P(pl,0xc))return 0;
 target=structure_center(image,actor_id(image,P(goal,0x4c)));
 if(!target||(P(target,8)&1)||(def=P(target,4))==0)return 0;
 if(!*(unsigned char*)(def+0x290)||settlement_site(def))return 0;
 structure=P(target,0x94);body=P(target,0x60);
 if(!structure||P(structure,4)!=target||!body||P(body,4)!=target||!finite(F(body,0x10))||F(body,0x10)<=0)return 0;
 k=P(pl,8);if(!k||P(target,0xe8)==k)return 0;
 if(((RouteM1)P(P(target,0),0x144))(target,0,k)!=3)return 0;
 return opening_city_count(image,pl)<2?target:0;
}
static void opening_capture_admission(U image,Data*d,U actor,U goal,float*result){
 U pl,target,reason=1;
 if((*(U*)result&255)||!live_actor(image,actor)||!goal)return;
 pl=player(goal);if(!pl||P(actor,0xe8)!=P(pl,8))return;
 target=opening_large_target(image,goal,pl);
 if(target)reason=2;else target=opening_capture_target(image,goal,pl);
 if(!target)return;
 *(U*)result|=1;
 emit(image,d,36,goal,pl,P(target,4),reason,0,1,F(target,0x20),F(target,0x24),actor,0);
}
