/* Execute the production field/bottom code against native-layout fixtures.
 * This exercises the actual classifier and prepare(), not a copy of its math. */
#include "water_wide.c"
#include <stdlib.h>

static void __cdecl quiet(const char*a,const char*b,...){(void)a;(void)b;}
static U alloc(U size){return (U)VirtualAlloc(0,size,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);}
static U make_variant(U index){U d=alloc(0x100),v=alloc(0x100);P(d,8)=(U)names[index];P(v,0x1c)=d;return v;}
static unsigned hash(const void*p,unsigned n){unsigned h=2166136261u;const unsigned char*b=p;while(n--)h=(h^*b++)*16777619u;return h;}
int main(void){U world,map,tiles,session,i,x,y,left=0,right=0,own=0,recipe,checks=0,variants[TYPES],before;float previous=0;Host fake={0};
 fake.log=quiet;host=&fake;prewarmEnabled=0;base=alloc(0x600000);world=alloc(0x1000);map=alloc(0x1000);session=alloc(0x1000);tiles=alloc(64*64*48);
 if(!base||!world||!map||!session||!tiles)return 1;
 P(base,0x5f3fb8)=world;P(base,0x5f3fe4)=session;P(session,0xf0)=2;P(world,0x30)=map;P(map,0x1c)=P(map,0x20)=64;P(map,0x28)=tiles;
 for(i=0;i<TYPES;i++){variants[i]=make_variant(i);if(!wcscmp(names[i],L"desert_quicksand"))left=i;if(!wcscmp(names[i],L"arctic_snowswamp"))right=i;}
 for(y=0;y<64;y++)for(x=0;x<64;x++){U cell=tiles+(y*64+x)*48;P(cell,0)=variants[x<32?left:right];P(cell,0x20)=0x20;}
 before=hash((void*)tiles,64*64*48);
 if(!prepare()||typeCount!=2)return 2;
 left=(U)index_of(P(variants[left],0x1c));right=(U)index_of(P(variants[right],0x1c));
 /* No discontinuity at the former hard boundary: bounded, monotonic field
  * and complementary weights all along the 49-cell transition. */
 for(x=8;x<57;x++){float a=weight(x,32,left),b=weight(x,32,right);if(a<0||b<0||a>1||b>1||a+b<.99999f||a+b>1.00001f||b<previous||b-previous>.041f)return 3;previous=b;checks++;}
 if(weight(31,32,left)<.48f||weight(31,32,left)>.52f)return 4;
 recipe=floor_recipe(31,32,P(tiles+(32*64+31)*48,0),&own);
 if(!recipe||own!=2||!floor_palette[recipe-1][1]||!floor_palette[recipe-1][2])return 5;
 if(hash((void*)tiles,64*64*48)!=before)return 6;
 checks+=4;
 /* More than 16 materials: the coverage bitset must retain every layer. */
 for(i=0;i<64*64;i++){P(tiles+i*48,0)=variants[i%TYPES];P(tiles+i*48,0x20)=i&1?0x20:0x120;}
 before=hash((void*)tiles,64*64*48);worldSeen=0;
 if(!prepare()||typeCount!=TYPES)return 7;
 for(i=0;i<TYPES;i++)if(index_of(P(variants[i],0x1c))<0)return 8;
 if(hash((void*)tiles,64*64*48)!=before)return 9;
 checks+=TYPES+2;
 /* Even a blocked cell is left native if its class is outside the explicit
  * WaterTerrain whitelist. No generic land renderer is promoted to water. */
 for(i=0;i<TYPES;i++)P(P(variants[i],0x1c),8)=(U)L"temperate_grass";
 worldSeen=0;if(prepare()||typeCount)return 10;checks++;
 printf("WATER_FIELD_PASS %u checks: production passable-wetland seam, floor recipe, all 22 layers, exact world isolation, unknown-material fallback\n",checks);
 return 0;
}
