#ifndef PAWS_MAP_PROFILES_H
#define PAWS_MAP_PROFILES_H
/* Stable IDs: keep the original temperate prototype saves readable. */
static const char *profile_ids[4][3]={
 {"rmc_temperate03","rmc_arctic03","rmc_desert03"},
 {"paws_shape_pangaea","paws_shape_pangaea_arctic","paws_shape_pangaea_desert"},
 {"paws_shape_mediterranean","paws_shape_mediterranean_arctic","paws_shape_mediterranean_desert"},
 {"paws_shape_rivers","paws_shape_rivers_arctic","paws_shape_rivers_desert"}
};
static int profile_match(const unsigned short *w,const char *a){int i;if(!w)return 0;for(i=0;i<80&&a[i];i++)if(w[i]!=(unsigned char)a[i])return 0;return !a[i]&&!w[i];}
static int profile_decode(const unsigned short *id,int *shape,int *climate){int s,c;for(s=0;s<4;s++)for(c=0;c<3;c++)if(profile_match(id,profile_ids[s][c])){*shape=s;*climate=c;return 1;}return 0;}
#endif
