/* The render whitelist deliberately includes passable WaterTerrain classes.
 * Their native land/water flags and movement properties remain untouched. */
#define WATER_MATERIALS(X) \
 X(temperate_lake,0) X(arctic_lake,1) X(desert_lake,2) X(cursed_lake,3) \
 X(temperate_river,0) X(arctic_river,1) X(paws_river_temperate,0) X(paws_river_arctic,1) \
 X(paws_river_desert,2) X(paws_river_cursed,3) X(cursed_river,3) \
 X(arctic_lakefrozen,1) X(arctic_snowswamp,1) X(temperate_marsh,0) X(temperate_mist_swamp,0) \
 X(cursed_marsh,3) X(cursed_mist_swamp,3) X(desert_quicksand,2) X(desert_lakemurky,2) \
 X(arctic_watershadow,1) X(desert_watershadow,2) X(desert_waterblood,2)
#define WATER_COUNT(id,climate) +1
enum { TYPES = 0 WATER_MATERIALS(WATER_COUNT) };
#undef WATER_COUNT
#define WATER_NAME(id,climate) L## #id,
static const wchar_t*names[TYPES]={WATER_MATERIALS(WATER_NAME)};
#undef WATER_NAME
#define WATER_CLIMATE(id,climate) climate,
static const unsigned char climate_for_kind[TYPES]={WATER_MATERIALS(WATER_CLIMATE)};
#undef WATER_CLIMATE
