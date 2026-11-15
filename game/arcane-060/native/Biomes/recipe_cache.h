/* Bounded, renderer-owned cache. Zero original denotes an unused slot.
 * Misses reserve nothing; publish only after a successful resource load. */
typedef struct{U original,recipe,value;}RecipeCacheEntry;
static RecipeCacheEntry*recipe_cache_find(RecipeCacheEntry*table,U mask,U original,U recipe){
 U i,start;if(!original)return 0;i=((original>>4)^(recipe*0x9e3779b9u));i^=i>>16;i*=0x7feb352du;i^=i>>15;i&=mask;start=i;
 do{RecipeCacheEntry*e=table+i;if(!e->original||(e->original==original&&e->recipe==recipe))return e;i=(i+1)&mask;}while(i!=start);return 0;
}
static void recipe_cache_publish(RecipeCacheEntry*e,U original,U recipe,U value){if(e){e->recipe=recipe;e->value=value;e->original=original;}}
