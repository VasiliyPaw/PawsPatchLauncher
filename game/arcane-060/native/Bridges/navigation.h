/* Native low-level collision checks compare the saved static-map island IDs
 * before examining current terrain. A finished bridge reconnects those IDs
 * without destroying the AI's running analysis, fibres or region pointers. */
static U bridge_native_island(U c){U rect=P(c,0x10);return rect?P(rect,8):0;}
static int bridge_island_banks(Roads*d,BridgeSpan*s,U*left,U*right){U a=actor(d,s->id),c,cc;BridgeGeometry g=bg_span(s);
 if(!a||(P(a,8)&3)||(P(a,0x100)&0x200000)||!s->opened)return 0;
 c=tile(d,integer(g.x-g.ux*(g.half+1))>>1,integer(g.y-g.uy*(g.half+1))>>1);
 cc=tile(d,integer(g.x+g.ux*(g.half+1))>>1,integer(g.y+g.uy*(g.half+1))>>1);
 if(!c||!cc||(P(c,0x20)&0x100)||(P(cc,0x20)&0x100))return 0;
 *left=bridge_native_island(c);*right=bridge_native_island(cc);return 1;
}
static U bridge_island_key(Roads*d,U id){U i;for(i=0;i<d->islandCount;i++)if(d->islandKeys[i]==id)return i;i=d->islandCount++;d->islandKeys[i]=id;d->islandValues[i]=i;return i;}
static U bridge_island_root(Roads*d,U i){while(d->islandValues[i]!=i)i=d->islandValues[i];return i;}
/* Cache the small bridge connectivity graph once per simulation tick. No
 * native static regions are freed or replaced, including the main island 0. */
EXPORT void bridge_navigation_refresh(Roads*d){U i,left,right,a,b;d->islandCount=0;
 for(i=0;i<d->bridgeCount;i++)if(bridge_island_banks(d,&d->spans[i],&left,&right)&&left!=right){
  a=bridge_island_key(d,left);b=bridge_island_key(d,right);a=bridge_island_root(d,a);b=bridge_island_root(d,b);
  if(a!=b){if(d->islandKeys[a]<d->islandKeys[b])d->islandValues[b]=a;else d->islandValues[a]=b;}
 }
 for(i=0;i<d->islandCount;i++)d->islandValues[i]=bridge_island_root(d,i);
 for(i=0;i<d->islandCount;i++)d->islandValues[i]=d->islandKeys[d->islandValues[i]];
}
static U bridge_mapped_island(Roads*d,U value){U i;for(i=0;i<d->islandCount;i++)if(d->islandKeys[i]==value)return d->islandValues[i];return value;}
EXPORT U FAST bridge_walk_island(U cell,U unused){Roads*d=current;U original=bridge_native_island(cell),i,left,right,out=original;
 if(!d||!d->bridgeCount||d->world!=P(d->image,0x5f3fb8)||d->bridgeWorld!=d->world||!allowed(d))return original;
 if(P(cell,0)&&eq((W*)P(P(cell,0),8),"paws_engineer_bridge01")){
  U map=P(d->world,0x30),offset=cell-P(map,0x28),w=P(map,0x1c);float x,y;
  if(offset%0x30||offset/0x30>=w*P(map,0x20))return original;
  x=(offset/0x30%w)*2+1;y=(offset/0x30/w)*2+1;
  for(i=0;i<d->bridgeCount;i++){BridgeSpan*s=&d->spans[i];BridgeGeometry g=bg_span(s);
   if(bg_nav(&g,x,y)&&bridge_island_banks(d,s,&left,&right)){out=left<right?left:right;break;}
  }
 }
 return bridge_mapped_island(d,out);
}
EXPORT U FAST bridge_collision_island(U cell,U query){if(!query||!(P(query,0x3c)&0x100))return bridge_native_island(cell);return bridge_walk_island(cell,0);}
/* Company destination validation must use the same connected IDs as its
 * individual movers. Otherwise a point on the far bank is silently pulled
 * back, and reforming/engaging NPC companies keep retrying the old island. */
static U bridge_context_actor(U ctx){U mind=ctx?P(ctx,4):0;return mind?P(mind,4):0;}
EXPORT U FAST bridge_company_region(U region,U ctx){Roads*d=current;U raw=m0(d,0x1f5344,region),a=bridge_context_actor(ctx);if(!a||(P(a,8)&0x1000)||!allowed(d))return raw;return bridge_mapped_island(d,raw);}
EXPORT U FAST bridge_company_island(U cell,U ctx){U a=bridge_context_actor(ctx);if(!a||(P(a,8)&0x1000))return bridge_native_island(cell);return bridge_walk_island(cell,0);}
EXPORT U FAST bridge_path_island(U cell,U ctx){Roads*d=current;U raw=bridge_native_island(cell),source=P(ctx,0x8c);if(d&&allowed(d)&&bridge_walk_island(cell,0)==bridge_mapped_island(d,source))return source;return raw;}
/* A build preview and its queued order must choose the same reachable bank.
 * Euclidean distance alone can select a nearer landing across unbridged water. */
static U bridge_approach(Roads*d,U a,U*points,U n){U c,left,right,from,first,last;float dx,dy,d0,d1;
 c=tile(d,integer(F(a,0x20))>>1,integer(F(a,0x24))>>1);
 left=tile(d,points[0]&65535,points[0]>>16);right=tile(d,points[n-1]&65535,points[n-1]>>16);
 if(!c||!left||!right)return 0;
 from=bridge_walk_island(c,0);first=bridge_walk_island(left,0)==from;last=bridge_walk_island(right,0)==from;
 if(!first&&!last)return 0;if(!first)return 2;if(!last)return 1;
 dx=(points[0]&65535)*2+1-F(a,0x20);dy=(points[0]>>16)*2+1-F(a,0x24);d0=dx*dx+dy*dy;
 dx=(points[n-1]&65535)*2+1-F(a,0x20);dy=(points[n-1]>>16)*2+1-F(a,0x24);d1=dx*dx+dy*dy;
 return d1<d0?2:1;
}
EXPORT U bridge_approach_check(Roads*d,U a,U*points,U n){return bridge_approach(d,a,points,n);}
