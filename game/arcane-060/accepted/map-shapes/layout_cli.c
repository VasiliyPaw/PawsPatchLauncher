#include <stdio.h>
#include <stdlib.h>
#include "shapes.h"
int main(int argc,char **argv){int w,h,k;U seed;unsigned char *m;FILE *f;if(argc!=6&&argc!=7)return 2;w=atoi(argv[1]);h=atoi(argv[2]);k=atoi(argv[3]);seed=(U)strtoul(argv[4],0,0);if(w<64||h<64||w>1024||h>1024)return 3;m=(unsigned char*)malloc(w*h);if(!m)return 4;if(argc==7)printf("Rivers: %d\n",river_paths(m,0,w,h,seed,atoi(argv[6])));else if(!make_mask(m,w,h,seed,k))return 5;f=fopen(argv[5],"wb");if(!f)return 6;fwrite(m,1,w*h,f);fclose(f);free(m);return 0;}
