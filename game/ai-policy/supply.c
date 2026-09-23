/* Arcane Wars' four supply-company recipes share one per-kingdom cap.
 * Count live companies, including incomplete/new recruits, at execution too.
 * Never disband existing supply, block replacement soldiers, or affect humans. */
static int supply_definition(U def){
 return ids_equal(def,"human_company_supply")||ids_equal(def,"drauga_company_supply")
  ||ids_equal(def,"gauri_company_supply")||ids_equal(def,"haroun_company_supply");
}
static int supply_capped(U image,Data*d,U pl,U def){
 U reg,i,count=0,k,world=P(image,0x5f3fb8);
 if(!(d->mask&8)||!pl||!*(unsigned char*)(pl+4)||!world||P(image,0x5f9218)!=2||!supply_definition(def))return 0;
 k=P(pl,8);reg=P(image,0x5ef72c);if(!k||!reg)return 0;
 /* The command creates a registered actor before the strategic actor list
  * is refreshed. Scanning that list alone misses other cities' same-tick hires. */
 for(i=0;i<65536;i++){
  U a=P(reg,0x20004+4*i);
  if(live_actor(image,a)&&!(P(a,8)&1)&&P(a,0xe8)==k&&supply_definition(P(a,4))&&++count>=2)return 1;
 }
 return 0;
}
