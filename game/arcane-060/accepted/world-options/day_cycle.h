/* A full cycle is 600 SIMULATED seconds. The start offset is a native,
 * serialized hidden integer world rule, initialized from the creator seed.
 * All interpolation uses the simulation thread's fixed tick time. */
#ifndef PAWS_DAY_CYCLE_SECONDS
#define PAWS_DAY_CYCLE_SECONDS 600u
#endif
#define DAY_CYCLE_TICKS (PAWS_DAY_CYCLE_SECONDS*16u)
#define DAY_SEGMENT_TICKS (DAY_CYCLE_TICKS/4u)
static U cycle_offset(U seed){return hash(seed^0xDA710617u)%DAY_CYCLE_TICKS;}
static void cycle_colors(U phase,const float *a,const float *b,float *out){
 U i;float t=(float)(phase%DAY_SEGMENT_TICKS)/(float)DAY_SEGMENT_TICKS;
 /* Smoothstep has zero slope at each anchor, including the cycle seam. */
 t=t*t*(3.0f-2.0f*t);
 for(i=0;i<9;i++)out[i]=a[i]+(b[i]-a[i])*t;
}
