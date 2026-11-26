#include <stdio.h>
#include "water_depth.h"
int main(void){unsigned shape,river,native,flags,d,checks=0;float last=0;
 /* Existing tiny lake/bog/ice/quicksand cells must not enter the river cut.
  * Test every combination of shape/rivers and native material flags. */
 for(shape=0;shape<6;shape++)for(native=0;native<2;native++)for(river=0;river<2;river++)for(flags=0;flags<0x400;flags++){
  int actual=water_depth_generated(shape,native,river,flags);
  int expected=((flags&0x170)==0x120)&&(river||(!native&&shape));
  if(actual!=expected)return 1;
  if((flags&0x170)!=0x120&&actual)return 2;
  if(native&&!river&&actual)return 3;
  if(!shape&&!river&&actual)return 4;
  checks++;
 }
 for(d=1;d<=128;d++){float v=water_bed_target(d);if(v>-.5f||v< -1.5f||v>last)return 5;last=v;}
 if(water_bed_target(1)!=-.5f||water_bed_target(2)!=-.75f||water_bed_target(64)!=-1.5f)return 6;
 printf("WATER_DEPTH_PASS %u material/shape/river combinations; native puddles preserved; generated channel remains submerged\n",checks);return 0;
}
