#include <stdio.h>
#include <wchar.h>
#include "water_materials.h"
int main(void){unsigned i,j,mask=0;const wchar_t*required[]={L"arctic_snowswamp",L"temperate_mist_swamp",L"cursed_mist_swamp",L"desert_quicksand",L"cursed_river",L"arctic_lakefrozen",L"desert_waterblood"};
 if(TYPES>32)return 1;
 for(i=0;i<TYPES;i++){if(!names[i]||climate_for_kind[i]>3)return 2;for(j=0;j<i;j++)if(!wcscmp(names[i],names[j]))return 3;mask|=1u<<i;}
 if(mask!=((1u<<TYPES)-1u))return 4;
 for(i=0;i<sizeof(required)/sizeof(required[0]);i++){for(j=0;j<TYPES;j++)if(!wcscmp(required[i],names[j]))break;if(j==TYPES)return 5;}
 printf("WATER_MATERIALS_PASS %u unique classes, 32-bit coverage, all wetland/ice families\n",TYPES);return 0;
}
