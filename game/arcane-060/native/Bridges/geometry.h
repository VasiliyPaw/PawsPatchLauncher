static void*memmove(void*target,const void*source,unsigned size){unsigned char*d=target;const unsigned char*s=source;if(d<s){unsigned i;for(i=0;i<size;i++)d[i]=s[i];}else{while(size){--size;d[size]=s[size];}}return target;}
/* Shared oriented geometry for preview, native actors, navigation and floors. */
typedef struct {float x,y,ux,uy,half;} BridgeGeometry;
static float bg_abs(float a){return a<0?-a:a;}
static float bg_sqrt(float a){union{float f;U u;}r;int i;if(a<=0)return 0;r.f=a;r.u=(r.u>>1)+0x1fc00000;for(i=0;i<4;i++)r.f=.5f*(r.f+a/r.f);return r.f;}
static int bg_round(float a){return integer(a<0?a-.5f:a+.5f);}
static BridgeGeometry bg_end(float x,float y,float xx,float yy){BridgeGeometry g;float length=bg_sqrt((xx-x)*(xx-x)+(yy-y)*(yy-y));g.x=(x+xx)*.5f;g.y=(y+yy)*.5f;g.half=length*.5f;g.ux=length?(xx-x)/length:0;g.uy=length?(yy-y)/length:1;return g;}
static BridgeGeometry bg_points(U*p,U n){return bg_end((p[0]&65535)*2+1,(p[0]>>16)*2+1,(p[n-1]&65535)*2+1,(p[n-1]>>16)*2+1);}
static U bg_model(BridgeGeometry*g){float length=g->half;U n=(U)integer(length);if(length-(float)n>.001f)n++;return n+1;}
static int bg_inside(BridgeGeometry*g,float x,float y,float width,float extra){float dx=x-g->x,dy=y-g->y;return bg_abs(dx*g->ux+dy*g->uy)<=g->half+extra+.001f&&bg_abs(dx*g->uy-dy*g->ux)<=width+.001f;}
/* Keep navigation, restoration and saved-island matching on the same narrow
 * corridor. Native island checks must not be bypassed by widening the deck. */
static int bg_nav(BridgeGeometry*g,float x,float y){return bg_inside(g,x,y,3,2);}
/* Separating axes of two oriented decks, including crossings whose actor
 * centres are nowhere near the other bridge's centre line. */
static int bg_overlap(BridgeGeometry*a,BridgeGeometry*b,float width){float dx=b->x-a->x,dy=b->y-a->y,c=bg_abs(a->ux*b->ux+a->uy*b->uy),s=bg_abs(a->ux*b->uy-a->uy*b->ux);
 return bg_abs(dx*a->ux+dy*a->uy)<a->half+b->half*c+width*s&&bg_abs(dx*a->uy-dy*a->ux)<width+b->half*s+width*c&&bg_abs(dx*b->ux+dy*b->uy)<b->half+a->half*c+width*s&&bg_abs(dx*b->uy-dy*b->ux)<width+a->half*s+width*c;}
static void bg_bounds(BridgeGeometry*g,float width,float extra,int*l,int*r,int*t,int*b){float hx=bg_abs(g->ux)*(g->half+extra)+bg_abs(g->uy)*width,hy=bg_abs(g->uy)*(g->half+extra)+bg_abs(g->ux)*width;*l=integer((g->x-hx)*.5f)-1;*r=integer((g->x+hx)*.5f)+1;*t=integer((g->y-hy)*.5f)-1;*b=integer((g->y+hy)*.5f)+1;}
static U bg_line(int x,int y,int xx,int yy,U*out){int dx=xx-x,dy=yy-y,sx=dx<0?-1:1,sy=dy<0?-1:1,err,e;U n=0;if(dx<0)dx=-dx;if(dy<0)dy=-dy;if(dx>31||dy>31||x<0||y<0||xx<0||yy<0)return 0;err=dx-dy;for(;;){out[n++]=(U)x|((U)y<<16);if(x==xx&&y==yy)break;e=2*err;if(e>-dy){err-=dy;x+=sx;}if(e<dx){err+=dx;y+=sy;}}return n;}
static BridgeGeometry bg_actor(U a,U n,U axis){BridgeGeometry g;float ux=F(a,0x2c),uy=F(a,0x30),len=bg_sqrt(ux*ux+uy*uy);g.x=F(a,0x20);g.y=F(a,0x24);g.half=(float)(n-1);if(len<.1f){ux=0;uy=1;len=1;}g.ux=axis?uy/len:ux/len;g.uy=axis?-ux/len:uy/len;return g;}
static BridgeGeometry bg_span(BridgeSpan*s){BridgeGeometry g;g.x=(s->x0+s->x1)*.5f;g.y=(s->y0+s->y1)*.5f;g.ux=s->ux;g.uy=s->uy;g.half=s->half;return g;}
static int bg_span_inside(BridgeSpan*s,float x,float y,float width,float extra){BridgeGeometry g=bg_span(s);if(!g.ux&&!g.uy)return x>=s->x0&&x<=s->x1&&y>=s->y0&&y<=s->y1;return bg_inside(&g,x,y,width,extra);}
