#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include "geometry.h"
static unsigned checks;
static void check(int b){checks++;if(!b){printf("FAILED %u\n",checks);exit(1);}}
int main(void){float t;int i;
 check(frontage(3,2.5f,.8f,20,0,1,0,60,0,0,0,&t)&&t>.63f&&t<.65f);
 check(!frontage(3,2.5f,.8f,20,5,1,0,60,0,0,0,&t));
 check(!frontage(3,2.5f,.8f,20,-5,1,0,60,0,0,0,&t));
 check(!frontage(3,2.5f,.8f,80,0,1,0,60,0,0,0,&t));
 check(!frontage(3,2.5f,.8f,-20,0,1,0,60,0,0,0,&t));
 check(frontage(1,1,0,20,1.6f,1,0,60,0,0,0,&t));
 check(!frontage(1,1,0,20,2,1,0,60,0,0,0,&t));
 check(!frontage(1,1,0,20,0,1,0,60,0,60,0,&t));
 check(!frontage(9,1,1,20,0,1,0,60,0,0,0,&t));
 for(i=0;i<3600;i++){
  float a=i*.00174532925f,ux=(float)sin(a),uy=(float)cos(a),x=20*uy,y=-20*ux;
  check(frontage(3,2.5f,.8f,x,y,ux,uy,60*uy,-60*ux,0,0,&t));
  check(!frontage(3,2.5f,.8f,x+3*ux,y+3*uy,ux,uy,60*uy,-60*ux,0,0,&t));
 }
 printf("{\"passed\":true,\"checks\":%u,\"rotations\":3600,\"breachKeptOpen\":true}\n",checks);return 0;
}
