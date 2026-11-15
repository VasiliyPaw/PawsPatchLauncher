/* Native saved bridge actors own the model and EconomyComponent. The cache is
 * derived from their IDs and saved positions, never from an external save file. */
static int bridge_prefix(const W*w,const char*s){U i;if(!w)return 0;for(i=0;s[i];i++)if(w[i]!=(W)s[i])return 0;return 1;}
/* Native construction requires its ordinary cost vector to remain intact.
 * Keep the unpaid/paid distinction in the already saved instance metadata. */
static int bridge_metadata_present(const W*w){return bridge_prefix(w,"paws_bridge_meta1|")||bridge_prefix(w,"paws_bridge_meta2|");}
static int bridge_paid(U a){W*w=(W*)P(a,0x18);return !bridge_metadata_present(w)||w[18]!='U';}
static void bridge_mark_paid(Roads*d,U a){U old=P(a,0x18),text,i;W*w=(W*)old,*out=d->metadataScratch;if(bridge_paid(a))return;
 for(i=0;i<32767&&w[i];i++)out[i]=w[i];if(i==32767)return;out[i]=0;out[18]='P';text=str(d,out);P(a,0x18)=text;release(d,old);
}
static void bridge_name(W*out,int wood,int axis,U n){const char*p=wood?"paws_bridge_wood_":"paws_bridge_stone_";U i=0;while(*p)out[i++]=(W)*p++;out[i++]=axis?'x':'y';out[i++]='_';out[i++]=(W)('0'+n/10);out[i++]=(W)('0'+n%10);out[i]=0;}
static U bridge_style(U kingdom){U nation=kingdom?P(kingdom,0x240):0;const W*name=nation?(W*)P(nation,8):0;
#ifdef PAWS_BRIDGE_UNDEAD
 if(eq(name,"Undead"))return 1;
#endif
#ifdef PAWS_BRIDGE_SHADOW
 if(eq(name,"Shadow"))return 2;
#endif
#ifdef PAWS_BRIDGE_HUMAN
 if(eq(name,"Human"))return 3;
#endif
#ifdef PAWS_BRIDGE_GAURI
 if(eq(name,"Gauri"))return 4;
#endif
#ifdef PAWS_BRIDGE_DRAUGA
 if(eq(name,"Drauga"))return 5;
#endif
#ifdef PAWS_BRIDGE_HAROUN
 if(eq(name,"Haroun"))return 6;
#endif
 return 0;
}
static const char*bridge_race(U style){switch(style){case 1:return "undead";case 2:return "shadow";case 3:return "human";case 4:return "gauri";case 5:return "drauga";case 6:return "haroun";default:return "";}}
static U bridge_style_def(U def){const W*w=def?(W*)P(def,8):0;U i,j;const char*r;
 if(!bridge_prefix(w,"paws_bridge_"))return 0;w+=12;for(i=1;i<=6;i++){r=bridge_race(i);for(j=0;r[j]&&w[j]==(W)r[j];j++);if(!r[j]&&w[j]=='_')return i;}return 0;
}
static const W*bridge_tail(U def){const W*w=def?(W*)P(def,8):0;const char*r;U style,i;if(!bridge_prefix(w,"paws_bridge_"))return 0;style=bridge_style_def(def);w+=12;if(style){r=bridge_race(style);for(i=0;r[i];i++)w++;w++;}return w;}
static U bridge_wood(U def){return bridge_prefix(bridge_tail(def),"wood_");}
static const W*bridge_menu(U style,U wood){switch(style){
 case 1:return wood?(const W*)L"paws_bridge_undead_wood_site":(const W*)L"paws_bridge_undead_stone_site";
 case 2:return wood?(const W*)L"paws_bridge_shadow_wood_site":(const W*)L"paws_bridge_shadow_stone_site";
 case 3:return wood?(const W*)L"paws_bridge_human_wood_site":(const W*)L"paws_bridge_human_stone_site";
 case 4:return wood?(const W*)L"paws_bridge_gauri_wood_site":(const W*)L"paws_bridge_gauri_stone_site";
 case 5:return wood?(const W*)L"paws_bridge_drauga_wood_site":(const W*)L"paws_bridge_drauga_stone_site";
 case 6:return wood?(const W*)L"paws_bridge_haroun_wood_site":(const W*)L"paws_bridge_haroun_stone_site";
 default:return wood?(const W*)L"paws_bridge_wood_site":(const W*)L"paws_bridge_stone_site";
}}
static void bridge_name_for(W*out,int wood,int axis,U n,U style){W basic[48];U i=0,j;const char*race=bridge_race(style);bridge_name(basic,wood,axis,n);
 if(!*race){for(i=0;basic[i];i++)out[i]=basic[i];out[i]=0;return;}
 for(i=0;i<12;i++)out[i]=basic[i];for(j=0;race[j];j++)out[i++]=(W)race[j];out[i++]='_';for(j=12;basic[j];j++)out[i++]=basic[j];out[i]=0;
}
static int bridge_kind(U def,U*n,U*axis){const W*w=def?(W*)P(def,8):0;U i=0,len;
 w=bridge_tail(def);
 if(bridge_prefix(w,"wood_"))i=5;
 else if(bridge_prefix(w,"stone_"))i=6;
 else return 0;
 if((w[i]!='x'&&w[i]!='y')||w[i+1]!='_'||w[i+2]<'0'||w[i+2]>'9'||w[i+3]<'0'||w[i+3]>'9'||w[i+4])return 0;
 len=(w[i+2]-'0')*10+w[i+3]-'0';if(len<5||len>32)return 0;
 *n=len;*axis=w[i]=='x';return 1;
}
static void bridge_bounds(BridgeSpan*s,U a,U n,U axis){BridgeGeometry g=bg_actor(a,n,axis);float hx=bg_abs(g.ux)*g.half+bg_abs(g.uy)*3.2f,hy=bg_abs(g.uy)*g.half+bg_abs(g.ux)*3.2f;
 s->x0=g.x-hx;s->x1=g.x+hx;s->y0=g.y-hy;s->y1=g.y+hy;s->ux=g.ux;s->uy=g.uy;s->half=g.half;s->level=F(a,0x28);s->id=P(a,0x14);s->originalCount=s->opened=0;
}
static void bridge_restore(Roads*d){U reg,i,a,n,axis,repaired=0;if(d->bridgeWorld==d->world)return;
 bridge_cache_clear(d);d->bridgeWorld=d->world;reg=P(d->image,0x5ef72c);if(!reg)return;
 for(i=1;i<65536&&d->bridgeCount<128;i++){
  a=P(reg,0x20004+i*4);if(!a||P(a,0)!=d->image+0x4e5c58||!bridge_kind(P(a,4),&n,&axis))continue;
  /* Upgrade old private saves: a static bridge is a ground structure. */
  P(a,8)&=~0x1000;
  /* Deck height is recoverable from saved endpoints and the unchanged banks.
   * This also upgrades early local fixtures whose object was grounded on load. */
  if(bridge_hm(d)){float pos[3],z0,z1,level;BridgeGeometry g=bg_actor(a,n,axis);
   pos[0]=F(a,0x20);pos[1]=F(a,0x24);
   z0=bridge_height(d,integer(pos[0]-g.ux*g.half)>>1,integer(pos[1]-g.uy*g.half)>>1);
   z1=bridge_height(d,integer(pos[0]+g.ux*g.half)>>1,integer(pos[1]+g.uy*g.half)>>1);
   level=(z0>z1?z0:z1)+.08f;
   if(finite(level)&&level>=.4f&&level<8.1f&&(F(a,0x28)<level-.001f||F(a,0x28)>level+.001f)){pos[2]=level;m1(d,0x23e242,a,(U)pos);}
  }
  {BridgeSpan*s=&d->spans[d->bridgeCount++];U text=P(a,0x18);bridge_bounds(s,a,n,axis);
   bridge_cache_capture(d,s,text);
   /* Old oversized instance IDs were discarded by the native loader. Restore
    * the surviving converted tiles from adjacent water, then persist a compact
    * record so the next save/load keeps the bridge's original wet footprint. */
   if(!(P(a,0x100)&0x200000)&&!bridge_prefix((W*)text,"paws_bridge_meta2|")){
    BridgeGeometry g=bg_span(s);U compact=bridge_metadata_geometry(d,&g,0);
    if(compact){P(a,0x18)=compact;if(text)release(d,text);bridge_cache_capture(d,s,compact);}
   }
   s->opened=!(P(a,0x100)&0x200000);
  }
  /* Older saves serialized command availability before razing was enabled. */
  m0(d,0x22a9ab,a);
 }
 for(i=0;i<d->bridgeCount;i++){BridgeSpan*s=&d->spans[i];repaired+=bridge_water(d,integer(s->x0)>>1,integer(s->x1)>>1,integer(s->y0)>>1,integer(s->y1)>>1);}
 if(repaired)invoke(d,0x2424b2,d->world,1,0,0);
 /* Save loading grounds actors before this bridge cache exists. Lift units
  * already standing on a saved deck once, including stationary formations. */
 for(i=1;i<65536;i++){U mover=P(reg,0x20004+i*4),j;if(!mover||P(mover,0)!=d->image+0x4e5c58||(P(mover,8)&0x1003)||(!P(mover,0x6c)&&!P(mover,0x7c)))continue;
  for(j=0;j<d->bridgeCount;j++){BridgeSpan*s=&d->spans[j];U owner=actor(d,s->id);float pos[3];if(!owner||!s->opened||!bg_span_inside(s,F(mover,0x20),F(mover,0x24),3.2f,0))continue;
   pos[0]=F(mover,0x20);pos[1]=F(mover,0x24);pos[2]=s->level+(bridge_wood(P(owner,4))?.1f:0);if(F(mover,0x28)<pos[2]-.001f)m1(d,0x23e242,mover,(U)pos);break;
  }
 }
}
/* Called only by the simulation-thread build transaction. */
static U bridge_object_create(Roads*d,U*pts,U n,U kingdom,float level,U construction,U wood){U defs=P(d->image,0x5f3fb4),def,key,ctx[24],a,i,axis=0,model;float position[3],direction[3];W name[48];BridgeGeometry g=bg_points(pts,n);
 d->bridgeError=1;if(!defs||!kingdom||d->bridgeCount>=128)return 0;
 model=bg_model(&g);if(model>32)return 0;
 bridge_name_for(name,wood,0,model,bridge_style(kingdom));
 d->bridgeError=2;key=str(d,name);def=m1(d,0x2edb9,P(defs,0xc),key);release(d,key);if(!def)return 0;
 for(i=0;i<24;i++)ctx[i]=0;
 m0(d,0x91a87,(U)ctx);ctx[1]=def;
 ctx[7]=bridge_metadata_make(d,pts,n,construction);if(!ctx[7])return 0;
 F(ctx,8)=(float)((pts[0]&65535)+(pts[n-1]&65535))+1;
 F(ctx,0xc)=(float)((pts[0]>>16)+(pts[n-1]>>16))+1;
 F(ctx,0x14)=g.ux;F(ctx,0x18)=g.uy;
 F(ctx,0x10)=level;ctx[0x28/4]=kingdom;ctx[0x38/4]=construction;
 d->bridgeError=3;a=invoke(d,0x242eee,d->world,1,(U)ctx,0);
 if(!a){release(d,ctx[7]);return 0;}
 d->bridgeError=4;if(P(a,0xe8)!=kingdom){invoke(d,0x24338e,d->world,1,a,0);release(d,ctx[7]);return 0;}
 d->bridgeError=5;if(!construction&&!P(a,0x84)){invoke(d,0x24338e,d->world,1,a,0);release(d,ctx[7]);return 0;}
 /* Native object initialization grounds land buildings onto the river bed.
  * Place the nonblocking bridge at its validated deck level via SetPosition3. */
 position[0]=(float)((pts[0]&65535)+(pts[n-1]&65535))+1;
 position[1]=(float)((pts[0]>>16)+(pts[n-1]>>16))+1;position[2]=level;
 direction[0]=g.ux;direction[1]=g.uy;direction[2]=0;m1(d,0x23e482,a,(U)direction);
 m1(d,0x23e242,a,(U)position);
 d->bridgeError=0;
 {BridgeSpan*s=&d->spans[d->bridgeCount];d->bridgeDeathTime[d->bridgeCount++]=0;bridge_bounds(s,a,model,axis);bridge_cache_capture(d,s,ctx[7]);s->opened=!construction;}
 release(d,ctx[7]);
 if(!construction)d->bridgeBuilt++;return a;
}
static U bridge_object(Roads*d,U*pts,U n,U kingdom,float level){return bridge_object_create(d,pts,n,kingdom,level,0,bridge_material(d,kingdom));}
/* Preserve ordinary height queries. Land actors get the saved deck height only
 * inside an actual finished bridge. Water/flying/terrain-only queries pass on. */
EXPORT U bridge_floor(Roads*d,U world,float*xy,U flags,U original){U i;union{float f;U u;}out;float x,y;
 if(!d||!world||world!=d->world||d->bridgeWorld!=world||(flags&7)!=2||!d->bridgeCount)return original;
 if(!allowed(d))return original;
 x=xy[0];y=xy[1];if(!finite(x)||!finite(y))return original;
 out.u=original;if(!finite(out.f))return original;
 for(i=0;i<d->bridgeCount;i++){BridgeSpan*s=&d->spans[i];U a;
  if(!bg_span_inside(s,x,y,3.2f,0))continue;
  a=actor(d,s->id);if(!a||((P(a,8)&3)||(P(a,0x100)&0x200000)))continue;
  {float deck=s->level+(bridge_wood(P(a,4))?.1f:0);
   if(deck>out.f)out.f=deck;
  }
 }return out.u;
}
EXPORT U bridge_material(Roads*d,U kingdom){U nation=kingdom?P(kingdom,0x240):0;return nation&&(eq((W*)P(nation,8),"Haroun")||eq((W*)P(nation,8),"haroun"));}
/* Selection must use the shared deck rectangle, never the model's 3-D
 * bounds (stone arches extend far below the deck, especially while rising). */
EXPORT U bridge_decal_tick(Roads*d,U self){U owner,def,n,axis,vfx,result;
 if(!d)return 0;result=m0(d,0x2d00af,self);vfx=P(self,0x10);owner=P(self,0x90);owner=owner?P(owner,0x14):0;
 /* Render-only approach pads: fixed dimensions, aligned to the real span,
  * with most of their inner half tucked under the bridge. Native projector
  * setters retain terrain conformity; no terrain, collision or actor writes. */
 if(allowed(d)&&owner&&vfx&&bridge_prefix((W*)P(vfx,8),"paws_bridge_ground_")&&P(owner,0)==d->image+0x4e5c58&&bridge_kind(P(owner,4),&n,&axis)){
  U projector=P(self,0xd4),args[2];BridgeGeometry g=bg_actor(owner,n,axis);float xy[2],direction[2],side=F(self,axis?0x38:0x3c)>0?-1:1;
  xy[0]=g.x+g.ux*(g.half-.8f)*side;xy[1]=g.y+g.uy*(g.half-.8f)*side;
  direction[0]=g.ux*side;direction[1]=g.uy*side;
  if(projector){
   float dx=F(projector,0x38)-F(projector,0x30),dy=F(projector,0x3c)-F(projector,0x34),length=bg_sqrt(dx*dx+dy*dy);
   if(length<.01f||(dx*direction[0]+dy*direction[1])/length<.9999f){args[0]=(U)direction;((NativeCall)d->call)(P(P(projector,0),0x3c),projector,1,args);}
   if(F(projector,0x74)!=8.f||F(projector,0x78)!=7.2f){F(args,0)=8.f;F(args,4)=7.2f;((NativeCall)d->call)(d->image+0x1a4474,projector,2,args);}
   args[0]=(U)xy;((NativeCall)d->call)(P(P(projector,0),0x38),projector,1,args);
  }
  return result;
 }
 if(allowed(d)&&owner&&vfx&&(eq((W*)P(vfx,8),"selected_square_vfx")||eq((W*)P(vfx,8),"focused_square_vfx"))){
  d->decalSelf=self;d->decalOwner=owner;d->decalCalls++;
  def=P(owner,0)==d->image+0x4e5c58?P(owner,4):0;
  if(bridge_kind(def,&n,&axis)){
   /* Run after native follow-owner sizing. Native projected textures size a
    * rectangle by the long side first; compensate its swapped texture axes
    * while keeping gameplay/picking widths unchanged. */
   m1(d,0x2d0749,self,def+0x38);
   m0(d,0x2d0779,self);d->decalMatches++;
  }
 }
 return result;
}
EXPORT U bridge_visual_floor(Roads*d,U ui,float*xy,U flags,U original,U view){U n,axis,i;union{float f;U u;}out;
 if(!d||ui!=P(d->image,0x5f3fbc))return original;
 /* Native VObject grounding also runs for a detached preview and while a
  * building rises. Raising only completed units leaves both buried in water.
  * Identify the bridge's own view, so a preview never becomes walkable land. */
 if(view&&allowed(d)&&((flags&7)==2||(flags&7)==3)&&bridge_kind(P(view,0x10),&n,&axis)){
  out.u=original;
  for(i=0;i<d->bridgeCount;i++){BridgeSpan*s=&d->spans[i];U a=actor(d,s->id);
   if((a&&P(a,0xc)==view)||((!a||(P(a,8)&3))&&bg_abs(xy[0]-(s->x0+s->x1)*.5f)<.5f&&bg_abs(xy[1]-(s->y0+s->y1)*.5f)<.5f)){
    out.f=s->level;return out.u;
   }
  }
  if(!P(view,0x14)&&d->previewCount>=5&&bridge_hm(d)){
   U p=d->previewPoints[0],q=d->previewPoints[d->previewCount-1];float z0=bridge_height(d,p&65535,p>>16),z1=bridge_height(d,q&65535,q>>16);
   out.f=(z0>z1?z0:z1)+.08f;return out.u;
  }
 }
 return bridge_floor(d,d->world,xy,flags,original);
}
/* Buildings normally substitute a health bar for selected_vfx. Add the stock
 * projected rectangle on the same selection edge, keeping the health bar.
 * Native deselection removes it by its definition key. No embedded meshes. */
EXPORT U FAST bridge_selection_tick(U view,U unused){Roads*d=current;U before=P(view,0x54),result=m0(d,0x2e4590,view),n,axis,def,fx,args[6];
 if(d&&allowed(d)&&!(before&0x800000)&&(P(view,0x54)&0x800000)&&P(view,0x14)&&bridge_kind(P(view,0x10),&n,&axis)){
  def=P(P(view,0x10),0x148);if(def){args[0]=def;args[1]=view;args[2]=0;args[3]=d->image+0x603694;args[4]=args[5]=0;
   fx=((NativeCall)d->call)(d->image+0x2ebc74,0,6,args);if(fx)P(fx,0x78)=def;
  }
 }return result;
}
