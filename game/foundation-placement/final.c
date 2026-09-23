/* Classify successfully placed random camp placeholders before the engine
 * replaces them with camps. The stock weighted choice still runs exactly once.
 * Coordinates, actors, definitions and saves are never edited here. */
typedef U (__attribute__((fastcall)) *FindDefinition)(U,U,U);
typedef struct { U id,actor,definition,foundation,used; float x,y,nearest; } Site;
typedef struct { U world,ready,count,foundations,remaining,selected,revision; Site sites[4096]; } FinalPlan;
static float sqdist(float x,float y,float a,float b){float dx=x-a,dy=y-b;return dx*dx+dy*dy;}
static U camp_kind(U def){
 if(!def)return 0;
 if(equal(P(def,8),"random_settlement_camps"))return 1;
 if(equal(P(def,8),"random_foundation_camps"))return 2;
 return 0;
}
__attribute__((dllexport)) void plan_map(U image,FinalPlan*d,U success){
 U reg,world,i,n=0,k,j,best,sd,fd,db;float cx=0,cy=0,score;
 d->ready=0;d->count=0;d->remaining=0;d->foundations=0;d->selected=0;d->revision=2;
 world=P(image,0x5f3fb8);d->world=world;
 if(!success||!world||(reg=P(image,0x5ef72c))==0||(db=P(image,0x5f3fb4))==0)return;
 sd=((FindDefinition)(image+0x2edb9))(P(db,0xc),0,(U)L"random_settlement_camps");
 fd=((FindDefinition)(image+0x2edb9))(P(db,0xc),0,(U)L"random_foundation_camps");
 if(camp_kind(sd)!=1||camp_kind(fd)!=2)return;
 if(!P(sd,0x18)||!P(fd,0x18)||P(P(sd,0x18),0xc)!=0x23||P(P(fd,0x18),0xc)!=0x23)return;
 for(i=0;i<65536;i++){
  U a=P(reg,0x20004+4*i),def;if(!a||(P(a,8)&1))continue;def=P(a,4);
  if(def!=sd&&def!=fd)continue;
  if((P(a,0x14)&65535)!=i||!finite(F(a,0x20))||!finite(F(a,0x24))||n==4096)return;
  if(F(a,0x20)<0||F(a,0x24)<0||F(a,0x20)>65536||F(a,0x24)>65536)return;
  d->sites[n].id=P(a,0x14);d->sites[n].actor=a;d->sites[n].definition=def;
  d->sites[n].x=F(a,0x20);d->sites[n].y=F(a,0x24);
  d->sites[n].foundation=0;d->sites[n].used=0;d->sites[n].nearest=1e30f;
  cx+=F(a,0x20);cy+=F(a,0x24);n++;
 }
 if(!n)return;cx/=n;cy/=n;k=(n+2)/5;
 /* Deterministic farthest-point sampling spreads the foundation subset over
  * the successful shared pool. Ties retain ascending actor ID order. */
 for(j=0;j<k;j++){
  best=0xffffffffu;score=-1;
  for(i=0;i<n;i++)if(!d->sites[i].foundation){
   float v=j?d->sites[i].nearest:1.0f/(1.0f+sqdist(d->sites[i].x,d->sites[i].y,cx,cy));
   if(v>score){score=v;best=i;}
  }
  if(best==0xffffffffu)return;d->sites[best].foundation=1;
  for(i=0;i<n;i++){
   float v=sqdist(d->sites[i].x,d->sites[i].y,d->sites[best].x,d->sites[best].y);
   if(v<d->sites[i].nearest)d->sites[i].nearest=v;
  }
 }
 /* Store the selected prototype, not a mutation of any engine definition. */
 for(i=0;i<n;i++)d->sites[i].foundation=d->sites[i].foundation?fd:sd;
 d->count=n;d->foundations=k;d->remaining=n;d->ready=1;
}
__attribute__((dllexport)) U select_table(U image,FinalPlan*d,U actor,U original){
 U i;if(!d->ready||!actor||d->world!=P(image,0x5f3fb8)||d->count>4096)return original;
 for(i=0;i<d->count;i++){
  Site*s=&d->sites[i];
  if(s->actor!=actor||s->id!=P(actor,0x14)||s->definition!=P(actor,4))continue;
  if(original!=s->definition+0x5c0||s->used)return original;
  s->used=1;d->remaining--;d->selected++;
  if(!d->remaining)d->ready=0;
  return s->foundation+0x5c0;
 }
 return original;
}
__attribute__((dllexport)) U final_data_size(void){return sizeof(FinalPlan);}
