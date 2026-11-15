/* Native shapes: 1=circle, 2=square, 3=box. Actor direction is the
 * GeoObject basis used by RVA33378, not a model-space rotation guess. */
static int slab(float start,float delta,float lo,float hi,float*enter,float*leave){float a,b,t;
 if(delta>-0.000001f&&delta<0.000001f)return start>=lo&&start<=hi;
 a=(lo-start)/delta;b=(hi-start)/delta;if(a>b){t=a;a=b;b=t;}
 if(a>*enter)*enter=a;if(b<*leave)*leave=b;return *enter<=*leave;
}
static int frontage(unsigned type,float hx,float hy,float px,float py,float ux,float uy,float sx,float sy,float ex,float ey,float*hit){
 float x=sx-px,y=sy-py,dx=ex-sx,dy=ey-sy,t0=0,t1=1,a,b,c,t;
 const float padding=0.75f;
 if(type==1){if(!(hx>0&&hx<128))return 0;hx+=padding;a=dx*dx+dy*dy;if(!(a>0.000001f))return 0;b=x*dx+y*dy;c=x*x+y*y-hx*hx;
  if(c<=0){*hit=0;return 1;}t=b*b-a*c;if(t<0)return 0;t=(-b-(float)sqrt(t))/a;if(t<0||t>1)return 0;*hit=t;return 1;}
 if(type!=2&&type!=3)return 0;if(!(hx>0&&hy>0&&hx<128&&hy<128))return 0;
 a=x*uy-y*ux;b=x*ux+y*uy;c=dx*uy-dy*ux;t=dx*ux+dy*uy;
 if(!slab(a,c,-hx-padding,hx+padding,&t0,&t1)||!slab(b,t,-hy-padding,hy+padding,&t0,&t1))return 0;
 *hit=t0;return 1;
}
