#include <assert.h>
#include <stdio.h>
#include <string.h>
typedef unsigned U;
#include "recipe_cache.h"
static RecipeCacheEntry table[131072];
int main(void){U i,j,key,recipe;RecipeCacheEntry*e;
 for(i=0;i<65536;i++){key=0x100000+(i/166)*0x80;recipe=i%166;e=recipe_cache_find(table,131071,key,recipe);assert(e&&!e->original);recipe_cache_publish(e,key,recipe,i+1);}
 for(j=0;j<5;j++)for(i=65536;i;i--){key=0x100000+((i-1)/166)*0x80;recipe=(i-1)%166;e=recipe_cache_find(table,131071,key,recipe);assert(e&&e->value==i);}
 /* A failed load cannot turn a miss into a cached success. */
 e=recipe_cache_find(table,131071,0xffff00,165);assert(e&&!e->original);assert(recipe_cache_find(table,131071,0xffff00,165)==e&&!e->original);
 assert(!recipe_cache_find(table,131071,0,0));
 {RecipeCacheEntry tiny[2]={{0}};for(i=0;i<2;i++){e=recipe_cache_find(tiny,1,i+1,9);assert(e);recipe_cache_publish(e,i+1,9,i+7);}assert(!recipe_cache_find(tiny,1,3,9));assert(recipe_cache_find(tiny,1,1,9)->value==7);}
 puts("PASS: 65536 recipes, repeated hits, collisions, failed-load miss, saturation");return 0;
}
