/* Exact original water variations are saved in the native actor's instance IDS
 * and decoded into the world's transient cache. No string-pool references are
 * retained across world teardown; deletion can still close its entire route. */
static int bridge_same_w(const W*a,const W*b){U i;if(!a||!b)return 0;for(i=0;i<128;i++){if(a[i]!=b[i])return 0;if(!a[i])return 1;}return 0;}
static U bridge_variation_w(Roads*d,const W*name){U mgr=P(d->image,0x5f0030),i,n;if(!mgr||!name)return 0;
 n=P(mgr,0x28);if(n>4096)return 0;for(i=0;i<n;i++){U v=P(P(mgr,0x24),i*4);if(v&&bridge_same_w((W*)P(v,8),name))return v;}return 0;
}
/* Relative cell coordinates and dictionary indices fit in three base64
 * characters. Unlike repeated terrain names, this stays below the native
 * 1024-character instance-ID limit for the supported 256-cell bridge cache. */
static const char bridge_meta_alphabet[]="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_";
static int bridge_meta_digit(W c){U i;for(i=0;i<64;i++)if(c==(W)bridge_meta_alphabet[i])return (int)i;return -1;}
static U bridge_meta2_read(Roads*d,const W*w,int x,int y,BridgeSpan*s){U p=18,i,defs[64],n=0,base[2],which=0,result=0,records=0;W name[128];
 if(!w||!bridge_prefix(w,"paws_bridge_meta2|"))return 0;
 while(p<1024&&w[p]&&w[p]!='|')p++;if(p>=1024||w[p++]!='|')return 0;
 for(i=0;i<2;i++){U v=0,k=0;while(p<1024&&w[p]>='0'&&w[p]<='9'&&k++<4)v=v*10+w[p++]-'0';if(!k||v>=1024||w[p++]!=(i?'|':','))return 0;base[i]=v;}
 while(p<1024&&w[p]&&w[p]!='|'){if(n==64)return 0;for(i=0;i<127&&p<1024&&w[p]&&w[p]!=';';i++)name[i]=w[p++];name[i]=0;if(!i||p>=1024||w[p++]!=';')return 0;defs[n++]=bridge_variation_w(d,name);}
 if(p>=1024||w[p++]!='|'||!n)return 0;
 while(p+2<1024&&w[p]&&records++<256){int a=bridge_meta_digit(w[p++]),b=bridge_meta_digit(w[p++]),c=bridge_meta_digit(w[p++]);U xx,yy;
  if(a<0||b<0||c<0||(U)c>=n)return 0;xx=base[0]+(U)a;yy=base[1]+(U)b;which=(U)c;if(xx>=1024||yy>=1024)return 0;
  if(s&&defs[which]&&s->originalCount<256){U j=s->originalCount++;s->originalPoints[j]=xx|(yy<<16);s->originalVariants[j]=defs[which];}
  if(xx==(U)x&&yy==(U)y)result=defs[which];
 }return result;
}
static U bridge_meta_find(Roads*d,U metadata,int x,int y){W*w=(W*)metadata,name[128];U p=18,i,records=0;int xx,yy;
 if(bridge_prefix(w,"paws_bridge_meta2|"))return bridge_meta2_read(d,w,x,y,0);
 if(!w||!bridge_prefix(w,"paws_bridge_meta1|"))return 0;
 while(p<32767&&w[p]&&w[p]!='|')p++;if(p>=32767||w[p]!='|')return 0;p++;
 while(p<32767&&w[p]&&records++<256){
  xx=yy=0;if(w[p]<'0'||w[p]>'9')return 0;
  for(i=0;i<4&&w[p]>='0'&&w[p]<='9';i++)xx=xx*10+w[p++]-'0';if(w[p++]!=',')return 0;
  for(i=0;i<4&&w[p]>='0'&&w[p]<='9';i++)yy=yy*10+w[p++]-'0';if(w[p++]!=',')return 0;
  for(i=0;i<127&&p<32767&&w[p]&&w[p]!=';';i++)name[i]=w[p++];name[i]=0;
  if(w[p++]!=';'||xx>=1024||yy>=1024)return 0;
  if(xx==x&&yy==y)return bridge_variation_w(d,name);
 }return 0;
}
static U bridge_span_original(BridgeSpan*s,int x,int y){U i,key=(U)x|((U)y<<16);for(i=0;i<s->originalCount&&i<256;i++)if(s->originalPoints[i]==key)return s->originalVariants[i];return 0;}
static void bridge_cache_capture(Roads*d,BridgeSpan*s,U text){int x,y;U v;s->originalCount=0;
 if(bridge_prefix((W*)text,"paws_bridge_meta2|")){bridge_meta2_read(d,(W*)text,-1,-1,s);return;}
 if(!text||!bridge_prefix((W*)text,"paws_bridge_meta1|"))return;
 for(y=(integer(s->y0)>>1)-3;y<=(integer(s->y1)>>1)+3;y++)for(x=(integer(s->x0)>>1)-3;x<=(integer(s->x1)>>1)+3;x++)
  if((v=bridge_meta_find(d,text,x,y))&&s->originalCount<256){U i=s->originalCount++;s->originalPoints[i]=(U)x|((U)y<<16);s->originalVariants[i]=v;}
}
static U bridge_original_at(Roads*d,int x,int y){U i,c,v;int r,dx,dy;
 c=tile(d,x,y);if(c&&P(c,0)&&!eq((W*)P(P(c,0),8),"paws_engineer_bridge01")&&(P(c,0x20)&0x70)==0x20)return P(c,0);
 for(i=0;i<d->bridgeCount;i++)if((v=bridge_span_original(&d->spans[i],x,y)))return v;
 /* Upgrade old local prototype saves which predate saved water metadata. */
 for(r=1;r<=12;r++)for(dy=-r;dy<=r;dy++)for(dx=-r;dx<=r;dx++){
  if(dx!=-r&&dx!=r&&dy!=-r&&dy!=r)continue;c=tile(d,x+dx,y+dy);
  if(c&&P(c,0)&&!eq((W*)P(P(c,0),8),"paws_engineer_bridge01")&&(P(c,0x20)&0x70)==0x20)return P(c,0);
 }return 0;
}
static U bridge_meta_number(W*out,U at,U value){W digits[10];U n=0;do{digits[n++]=(W)('0'+value%10);value/=10;}while(value&&n<10);while(n)out[at++]=digits[--n];return at;}
static U bridge_metadata_geometry(Roads*d,BridgeGeometry*g,U pending){W*out=d->metadataScratch;const char*head="paws_bridge_meta2|";U at=0,i,j,v,records=0,dict[64],defs=0,points[256],indices[256];int x,y,l,r,t,b,minx=1023,miny=1023;
 bg_bounds(g,5,3,&l,&r,&t,&b);
 for(y=t;y<=b;y++)for(x=l;x<=r;x++){U cell=tile(d,x,y);
  if(!cell||!P(cell,0)||!bg_inside(g,x*2+1,y*2+1,5,3))continue;
  if((P(cell,0x20)&0x70)!=0x20&&!eq((W*)P(P(cell,0),8),"paws_engineer_bridge01"))continue;
  v=bridge_original_at(d,x,y);if(!v||records==256)return 0;
  for(j=0;j<defs&&dict[j]!=v;j++);if(j==defs){if(defs==64)return 0;dict[defs++]=v;}
  if(x<minx)minx=x;if(y<miny)miny=y;points[records]=(U)x|((U)y<<16);indices[records++]=j;
 }
 if(!records)return 0;
 for(i=0;head[i];i++)out[at++]=(W)head[i];out[at++]=pending?'U':'P';at=bridge_meta_number(out,at,d->tick);out[at++]='|';
 at=bridge_meta_number(out,at,(U)minx);out[at++]=',';at=bridge_meta_number(out,at,(U)miny);out[at++]='|';
 for(j=0;j<defs;j++){W*name=(W*)P(dict[j],8);for(i=0;i<127&&name[i];i++){if(at+records*3+3>=1024)return 0;out[at++]=name[i];}if(name[i])return 0;out[at++]=';';}out[at++]='|';
 for(i=0;i<records;i++){U xx=(points[i]&65535)-(U)minx,yy=(points[i]>>16)-(U)miny;if(xx>=64||yy>=64||at+3>=1024)return 0;out[at++]=(W)bridge_meta_alphabet[xx];out[at++]=(W)bridge_meta_alphabet[yy];out[at++]=(W)bridge_meta_alphabet[indices[i]];}
 out[at]=0;return str(d,out);
}
static U bridge_metadata_make(Roads*d,U*pts,U n,U pending){BridgeGeometry g=bg_points(pts,n);return bridge_metadata_geometry(d,&g,pending);}
EXPORT U bridge_metadata_read_check(Roads*d,U metadata,U x,U y){return bridge_meta_find(d,metadata,(int)x,(int)y);}
EXPORT U bridge_metadata_write_check(Roads*d,U*pts,U n,U pending){return bridge_metadata_make(d,pts,n,pending);}
static void bridge_cache_clear(Roads*d){U i;d->bridgeCount=0;for(i=0;i<128;i++)d->bridgeDeathTime[i]=0;}
static int bridge_covered_elsewhere(Roads*d,U skip,int x,int y){U i;float fx=x*2+1,fy=y*2+1;
 for(i=0;i<d->bridgeCount;i++){BridgeSpan*s=&d->spans[i];U a;if(i==skip||!s->opened)continue;
  {BridgeGeometry g=bg_span(s);if(!bg_nav(&g,fx,fy))continue;}a=actor(d,s->id);
  if(a&&!(P(a,8)&3)&&!(P(a,0x100)&0x200000))return 1;
 }return 0;
}
static U bridge_close(Roads*d,U index){BridgeSpan*s=&d->spans[index];U ctx[8],xy[2],i,count=0;int x,y;
 for(i=0;i<8;i++)ctx[i]=0;invoke(d,0x2517a3,(U)ctx,0,0,0);
 for(y=(integer(s->y0)>>1)-3;y<=(integer(s->y1)>>1)+3;y++)for(x=(integer(s->x0)>>1)-3;x<=(integer(s->x1)>>1)+3;x++){
  U cell=tile(d,x,y),original;if(!bg_span_inside(s,x*2+1,y*2+1,5,3))continue;if(!cell||!P(cell,0)||!eq((W*)P(P(cell,0),8),"paws_engineer_bridge01")||bridge_covered_elsewhere(d,index,x,y))continue;
  original=bridge_span_original(s,x,y);if(!original)original=bridge_original_at(d,x,y);if(!original)continue;
  xy[0]=(U)x;xy[1]=(U)y;invoke(d,0x2517f9,(U)ctx,2,(U)xy,original);count++;
 }
 invoke(d,0x25185b,(U)ctx,1,0,0);invoke(d,0x20d4b,(U)(ctx+3),0,0,0);invoke(d,0x20d4b,(U)(ctx+5),0,0,0);
 for(y=(integer(s->y0)>>1)-3;y<=(integer(s->y1)>>1)+3;y++)for(x=(integer(s->x0)>>1)-3;x<=(integer(s->x1)>>1)+3;x++){
  U cell=tile(d,x,y),original,changes[4],args[3];if(!cell||!P(cell,0)||!eq((W*)P(P(cell,0),8),"paws_engineer_bridge01")||!bg_span_inside(s,x*2+1,y*2+1,5,3)||bridge_covered_elsewhere(d,index,x,y))continue;
  original=bridge_span_original(s,x,y);if(!original)original=bridge_original_at(d,x,y);if(!original)continue;changes[0]=changes[1]=changes[2]=changes[3]=0;args[0]=original;args[1]=0;args[2]=(U)changes;((NativeCall)d->call)(d->image+0x24a522,cell,3,args);
 }
 return count;
}
static int bridge_safe_landing(Roads*d,int x,int y,int margin){int xx,yy;float z=bridge_height(d,x,y);if(!finite(z)||z<0||z>100)return 0;
 for(yy=y-margin;yy<=y+margin;yy++)for(xx=x-margin;xx<=x+margin;xx++){U c=tile(d,xx,yy);float h;if(!c||(P(c,0x20)&0x100)||(P(c,0x20)&0x70)==0x20||(P(c,0)&&eq((W*)P(P(c,0),8),"paws_engineer_bridge01")))return 0;h=bridge_height(d,xx,yy);if(!finite(h)||bg_abs(h-z)>1.5f)return 0;}return 1;}
static int bridge_landing(Roads*d,BridgeGeometry*g,float x,float y,U count,float*out){int side,r,dx,dy,margin=2;float best=1e20f;U found=0;if(count>16)margin=3;if(count>36)margin=4;
 for(side=-1;side<=1;side+=2){int bx=integer((g->x+g->ux*(g->half+6)*side)*.5f),by=integer((g->y+g->uy*(g->half+6)*side)*.5f);
  for(r=0;r<=32;r++){U ring=0;for(dy=-r;dy<=r;dy++)for(dx=-r;dx<=r;dx++){int xx=bx+dx,yy=by+dy;float xxw=xx*2+1,yyw=yy*2+1,score=(xxw-x)*(xxw-x)+(yyw-y)*(yyw-y);if((dx!=-r&&dx!=r&&dy!=-r&&dy!=r)||!bridge_safe_landing(d,xx,yy,margin))continue;ring=1;if(score<best){best=score;out[0]=xxw;out[1]=yyw;out[2]=bridge_height(d,xx,yy);found=1;}}if(ring)break;}
 }return found;
}
static void bridge_relocate(Roads*d,U a,float*x){U flags=P(a,8),mind=P(a,0x70),fn,args[3];P(a,8)=flags|0x40000000;m1(d,0x23e242,a,(U)x);P(a,8)=flags;
 /* Stock portal deployment takes x, y, optional portal actor (RET 12).
  * Give each member its actual safe point, clearing its previous deck path. */
 if(mind&&P(mind,0)&&(fn=P(P(mind,0),0x19c))){args[0]=P(x,0);args[1]=P(x,4);args[2]=0;((NativeCall)d->call)(fn,mind,3,args);}
}
static void bridge_group_relocate(Roads*d,U a,float*destination){U org=P(a,0x7c),n=org?P(org,0x2c):0,list=org?P(org,0x28):0,j,cols=1;if(!n||n>64||!list)return;while(cols*cols<n)cols++;
 command(d,a,"stop",0,0);bridge_relocate(d,a,destination);
 for(j=0;j<n;j++){U member=P(list,j*4);float at[3];if(!member||(P(member,8)&3))continue;at[0]=destination[0]+((float)(j%cols)-(float)(cols-1)*.5f)*1.5f;at[1]=destination[1]+((float)(j/cols)-(float)((n+cols-1)/cols-1)*.5f)*1.5f;at[2]=bridge_height(d,integer(at[0])>>1,integer(at[1])>>1);bridge_relocate(d,member,at);}
 command(d,a,"stop",0,0);
}
/* A disappearing deck evacuates each whole company to one dry bank. The
 * native actor setter updates spatial ownership; a native stop cancels stale
 * paths before water is restored. No member may be sent to the other bank. */
static int bridge_evacuate(Roads*d,BridgeSpan*s){U reg=P(d->image,0x5ef72c),i;BridgeGeometry g=bg_span(s);if(!reg)return 0;
 for(i=1;i<65536;i++){U a=P(reg,0x20004+i*4),org,list,n,j,touched=0;float destination[3];
  if(!a||P(a,0)!=d->image+0x4e5c58||(P(a,8)&0x1003))continue;org=P(a,0x7c);if(!org||P(org,4)!=a)continue;n=P(org,0x2c);list=P(org,0x28);if(!n||n>64||!list)continue;
  if(bg_inside(&g,F(a,0x20),F(a,0x24),3.3f,1))touched=1;
  for(j=0;j<n&&!touched;j++){U member=P(list,j*4);if(member&&!(P(member,8)&0x1003)&&bg_inside(&g,F(member,0x20),F(member,0x24),3.3f,1))touched=1;}
  if(!touched)continue;if(!bridge_landing(d,&g,F(a,0x20),F(a,0x24),n,destination))return 0;
  bridge_group_relocate(d,a,destination);
 }
 return 1;
}
EXPORT U bridge_evacuate_check(Roads*d,U index){return index<d->bridgeCount?bridge_evacuate(d,&d->spans[index]):0;}
static U bridge_maintenance(Roads*d){U i=0,dirty=0,k;
 while(i<d->bridgeCount){BridgeSpan*s=&d->spans[i];U a=actor(d,s->id),j;
  if(a&&!(P(a,8)&3)){i++;continue;}
  if(s->opened){if(!bridge_evacuate(d,s)){i++;continue;}if(bridge_close(d,i))dirty=1;s->opened=0;}
  /* A detached native corpse still grounds its visual for the stock sinking
   * effect. Retain only its original deck anchor, never a walkable corridor. */
  if(!d->bridgeDeathTime[i])d->bridgeDeathTime[i]=F(d->world,0xe8);
  if(F(d->world,0xe8)-d->bridgeDeathTime[i]<30){i++;continue;}
  for(j=i+1;j<d->bridgeCount;j++)d->bridgeDeathTime[j-1]=d->bridgeDeathTime[j];
  for(j=i+1;j<d->bridgeCount;j++)for(k=0;k<sizeof(BridgeSpan)/4;k++)P(&d->spans[j-1],k*4)=P(&d->spans[j],k*4);d->bridgeCount--;
 }return dirty;
}
