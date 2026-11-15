/* The visible bottom is a terrain RTT, distinct from the animated water mesh.
 * Substitute copied definitions only in that renderer's private entry cache. */
#include "water_floor_sources.h"
typedef struct{U original,recipe;unsigned char definition[0x44];}FloorClone;
#include "recipe_cache.h"
static RecipeCacheEntry floorCache[32768],floorDefinitionCache[2048];
static FloorClone floorClones[16384];static U floorCloneCount,floorEntries,floorChunks;
static const unsigned char climate_for_kind[TYPES]={0,1,2,3,0,1,0,1,2,3};
static U floor_variant(U original,U recipe,U own){U i,key=0,resource,load;int known=0;wchar_t path[220];FloorClone*c;RecipeCacheEntry*cached,*info;
 cached=recipe_cache_find(floorCache,32767,original,recipe);if(cached&&cached->original)return cached->value;
 if(floorCloneCount==16384)return original;
 info=recipe_cache_find(floorDefinitionCache,2047,original,0);if(info&&info->original)known=info->value-1;else{for(i=0;i<sizeof(floor_sources)/sizeof(floor_sources[0]);i++)if(!wcscmp((wchar_t*)P(original,8),floor_sources[i].id)){known=1;break;}recipe_cache_publish(info,original,0,known+1);}
 if(!known||!floor_palette[recipe-1][own])swprintf(path,L"Textures/PawsWaterFloor/shared_%u.png",recipe);
 else swprintf(path,L"Textures/PawsWaterFloor/%ls_%u.png",(wchar_t*)P(original,8),recipe);
 ((M1)(base+0x205de))((U)&key,0,(U)path);resource=((U(__cdecl*)(U,U))(base+0x1c586f))((U)&key,0);if(key)((M0)(base+0x21375))(key-16,0);if(!resource){violations++;return original;}
 load=P(P(resource,0),0x10);((M2)load)(resource,0,1,1);
 c=&floorClones[floorCloneCount++];c->original=original;c->recipe=recipe;memcpy(c->definition,(void*)original,0x44);P(c->definition,0x20)=resource;P(c->definition,0x18)=P(original,0x18)*1024+recipe;recipe_cache_publish(cached,original,recipe,(U)c->definition);return (U)c->definition;
}
/* One recipe function is shared by preloading and the live renderer. */
static U floor_recipe(int gx,int gy,U original,U*ownOut){U j,k,q[4],previous,next,hash,own;float weights[4],sum=0,cumulative=0,dither;int slot=kind(P(original,0x1c));if(slot<0)return 0;own=climate_for_kind[slot];*ownOut=own;
 for(j=0;j<4;j++)weights[j]=0;for(k=0;k<typeCount;k++){float w=weight(gx,gy,k);weights[climate_for_kind[kind(defs[k])]]+=w;sum+=w;}if(sum<.000001f||weights[own]>=sum-.000001f)return 0;
 hash=gx*0x9e3779b9u+gy*0x85ebca6bu;hash^=hash>>16;hash*=0x7feb352du;hash^=hash>>15;dither=(float)(hash&65535)/65536.f;previous=0;
 for(j=0;j<3;j++){cumulative+=weights[j]*8/sum;next=(U)(cumulative+dither);if(next>8)next=8;q[j]=next-previous;previous=next;}q[3]=8-previous;if(q[own]==8)return 0;return floor_lookup[q[0]*81+q[1]*9+q[2]];
}
static void prewarm_floor(U map){U i,n=width*height,tiles=P(map,0x28),before=floorCloneCount,failures=0;DWORD began=GetTickCount();PrewarmBudget budget;prewarm_budget_begin(&budget);
 for(i=0;i<n;i++){U cell=tiles+i*48,original=P(cell,0),own=0,recipe;RecipeCacheEntry*e;if(!original||(P(cell,0x20)&0x170)!=0x120)continue;recipe=floor_recipe(i%width,i/width,original,&own);if(!recipe)continue;e=recipe_cache_find(floorCache,32767,original,recipe);if(e&&e->original)continue;if(!prewarm_budget_allow(&budget))break;if(floor_variant(original,recipe,own)==original)failures++;}
 host->log("water-wide","PREWARM floor %u new clones, %u failures, %lu ms, memoryLimited=%u",floorCloneCount-before,failures,GetTickCount()-began,budget.limited);
}
static void __cdecl blend_floor(U chunk){U grid,n,ox,oy,x,y,entry,cell,original,code,own;int gx,gy;
 if(!chunk||!prepare())return;grid=P(chunk,0x88);n=P(chunk,0xd0);if(!grid||!n||n>64)return;ox=P(chunk,0xac)*n;oy=P(chunk,0xb0)*n;
 for(y=0;y<n+2;y++)for(x=0;x<n+2;x++){gx=(int)ox+(int)x-1;gy=(int)oy+(int)y-1;if(gx<0||gy<0||gx>=(int)width||gy>=(int)height)continue;
  entry=grid+(y*(n+2)+x)*20;cell=P(entry,4);if(!cell||(P(cell,0x20)&0x170)!=0x120||!(original=P(cell,0)))continue;
  code=floor_recipe(gx,gy,original,&own);if(!code)continue;P(entry,0)=floor_variant(original,code,own);floorEntries++;
 }floorChunks++;
}
