/* Explicit disposable SP fixtures; excluded from the deliverable DLL. */
static void siege_fixture(const char*cmd){U id,ids[6],target,kind,i,a,key=0,ctx[24],def;float x,y;char name[80];wchar_t wide[80];
 if(sscanf(cmd,"ungroup %u",&id)==1&&(a=actor(id))!=0){U g=m0(0x2277c3,a);if(g)m1(0x231b43,g,a);}
 if(sscanf(cmd,"pointorder %u %u %f %f",&id,&kind,&x,&y)==4&&(a=actor(id))!=0&&kind<39){
  U held=((U(__cdecl*)(U))(image+0x2ef03c))(0x40);if(!held)return;m1(0x22f4e9,held,kind);P(held,4)++;P(held,12)|=4;F(held,24)=x;F(held,28)=y;
  if(P(a,0)==image+0x4e7d60)m1(0x231980,a,(U)&held);else m1(0x22f651,held,a);m0(0x42fca,(U)&held);
 }
 if(sscanf(cmd,"rest %u",&id)==1&&(a=actor(id))!=0&&P(a,0x7c)){U org=P(a,0x7c);F(org,0x5c)=F(org,0x60);}
 if(sscanf(cmd,"org %79s %u %f %f",name,&id,&x,&y)==4&&kingdom(id)){
  mbstowcs(wide,name,79);wide[79]=0;m1(0x205de,(U)&key,(U)wide);
  def=m1(0x2edb9,P(P(image,0x5f3fb4),0xc),key);
  if(def){memset(ctx,0,sizeof(ctx));m0(0x91a87,(U)ctx);ctx[1]=def;F(ctx,8)=x;F(ctx,12)=y;F(ctx,20)=1;ctx[10]=kingdom(id);
   a=m1(0x242fcd,world,(U)ctx);host->log("siege-qa","org %s actor %u members %u",name,a?P(a,0x14):0,a&&P(a,0x7c)?P(P(a,0x7c),0x2c):0);}
  else host->log("siege-qa","missing org definition %s",name);
  if(key)m0(0x21375,key-16);
 }
 if(sscanf(cmd,"group %u %u %u %u %u %u",ids,ids+1,ids+2,ids+3,ids+4,ids+5)==6){
  U nodes[6][3],list[2],g;for(i=0;i<6;i++)if(!actor(ids[i]))return;
  g=m1(0x2429b5,world,v0(actor(ids[0]),0x108));if(!g)return;
  for(i=0;i<6;i++){nodes[i][0]=actor(ids[i]);nodes[i][1]=i<5?(U)nodes[i+1]:0;nodes[i][2]=i?(U)nodes[i-1]:0;}
  list[0]=(U)nodes;list[1]=(U)nodes[5];m1(0x231a82,g,(U)list);
  host->log("siege-qa","group %u count %u",P(g,0x14),P(g,0x194));
 }
 if(sscanf(cmd,"order %u %u %u",&id,&kind,&target)==3&&(a=actor(id))!=0&&kind<39){
  U held=((U(__cdecl*)(U))(image+0x2ef03c))(0x40),r;
  if(!held)return;m1(0x22f4e9,held,kind);P(held,4)++;if(target)m1(0x22f571,held,actor(target));
  if(P(a,0)==image+0x4e7d60)r=m1(0x231980,a,(U)&held);
  else r=m1(0x22f651,held,a);
  m0(0x42fca,(U)&held);host->log("siege-qa","order %u kind %u target %u result %u",id,kind,target,r&255);
 }
}
