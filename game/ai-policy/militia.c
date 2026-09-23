/* Final Arcane Wars center upgrades retain native prerequisites, payment and
 * execution. Equal income must not hide their substantially larger garrison. */
static int militia_upgrade(U image,U goal){
 U def,s,i;const char*suffix="_militia";U n=8;
 if(!goal||P(goal,0)!=image+0x4da738||(def=P(goal,0x40))==0||!P(def,0x430)||!settlement_site(def))return 0;
 s=P(def,8);if(!s)return 0;
 for(i=0;i<96&&*(W*)(s+2*i);i++);
 if(i==96||i<n)return 0;
 {U j;for(j=0;j<n;j++)if(*(W*)(s+2*(i-n+j))!=(W)suffix[j])return 0;}
 return 1;
}
static float militia_priority(U image,Data*d,U goal,U pl,float before){
 if(!militia_upgrade(image,goal)||!pl||!finite(before)||before<=0)return before;
 if(before<100000){
  F(goal,0x38)=100000;
  emit(image,d,49,goal,pl,P(goal,0x40),1,before,100000,0,0,0,0);
  return 100000;
 }
 return before;
}
