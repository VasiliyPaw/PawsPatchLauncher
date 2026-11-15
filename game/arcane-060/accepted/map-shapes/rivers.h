/* Seeded river paths in terrain-cell coordinates. No simulation RNG or clocks. */
static int river_limit(int w,int h){int n=(w<h?w:h)/100;return n<1?1:n>10?10:n;}
static int river_count(int w,int h,U seed,int selected){int limit=river_limit(w,h);return selected<0?(int)(mix(seed^0x68bc21ebU)%(U)(limit+1)):selected>limit?limit:selected;}
static U river_random(U*s){*s=mix(*s+0x9e3779b9U);return *s;}
static int river_clamp(int v,int hi){return v<1?1:v>=hi-1?hi-2:v;}
static int river_inset(int v,int hi,int margin){return v<margin?margin:v>=hi-margin?hi-margin-1:v;}
static int river_lerp(int a,int b,int t){return (a*(256-t)+b*t)/256;}
/* Retain sub-cell precision through all interpolation stages. Rounding each
 * stage to a terrain cell made otherwise smooth curves zigzag visibly. */
static int river_bezier(int a,int b,int c,int d,int t){a*=256;b*=256;c*=256;d*=256;return (river_lerp(river_lerp(river_lerp(a,b,t),river_lerp(b,c,t),t),river_lerp(river_lerp(b,c,t),river_lerp(c,d,t),t),t)+128)/256;}
typedef struct {const float*base,*delta;int width,height,shift,pad;} RiverRelief;
/* Complete a channel through an already submerged connected depression.
 * Positive ground is a real bank, and existing seas/lakes stop this flood.
 * This is deterministic and cannot invent a cut through a mountain. */
static U river_fill_depressions(unsigned char*m,const unsigned char*sea,int w,int h,const RiverRelief*q,U*queue){U head=0,tail=0,added=0,i;int x,y;
 if(!q||!q->base||!queue||q->shift>4||q->width<1||q->height<1)return 0;
 for(i=0;i<(U)(w*h);i++)if(m[i])queue[tail++]=i;
 while(head<tail){U here=queue[head++];int k;const int ox[4]={-1,1,0,0},oy[4]={0,0,-1,1};x=here%w;y=here/w;
  for(k=0;k<4;k++){int xx=x+ox[k],yy=y+oy[k],hx,hy;U at;float z;
   if(xx<1||yy<1||xx+1>=w||yy+1>=h)continue;at=yy*w+xx;if(m[at]||(sea&&sea[at]))continue;
   hx=(xx*2+1+q->pad)>>q->shift;hy=(yy*2+1+q->pad)>>q->shift;if(hx<0||hy<0||hx>=q->width||hy>=q->height)continue;
   z=q->base[hy*q->width+hx]+(q->delta?q->delta[hy*q->width+hx]:0);if(!(z<-.1f&&z> -100))continue;
   m[at]=1;queue[tail++]=at;added++;
  }
 }return added;
}
static int river_elevation(const RiverRelief*q,int x,int y){int hx,hy,out;float z;if(!q||!q->base)return 0;hx=(x*2+1+q->pad)>>q->shift;hy=(y*2+1+q->pad)>>q->shift;if(hx<0||hy<0||hx>=q->width||hy>=q->height)return 0;z=q->base[hy*q->width+hx]+(q->delta?q->delta[hy*q->width+hx]:0);if(z<2)return 0;if(z>100)z=100;z*=16;__asm__ volatile(".byte 0xf3,0x0f,0x2c,0x00":"=a"(out):"a"(&z));return out;}
/* Smooth signed lobes: zero displacement and zero tangent at each endpoint. */
static int river_wave(int t,int lobes,int amplitude){int phase=t*lobes,k=phase/256,u=phase%256,bell=u*(256-u)/16;bell=bell*bell/1024;return (k&1?-1:1)*amplitude*bell/1024;}
static void river_point(int x0,int y0,int bx,int by,int cx,int cy,int x1,int y1,int t,int lobes,int amplitude,int w,int h,int*x,int*y){int dx=x1-x0,dy=y1-y0,den=ab(dx)+ab(dy),wave=river_wave(t,lobes,amplitude);*x=river_clamp(river_bezier(x0,bx,cx,x1,t)-(den?dy*wave/den:0),w);*y=river_clamp(river_bezier(y0,by,cy,y1,t)+(den?dx*wave/den:0),h);}
static int river_contact(const unsigned char*m,int w,int h,int x,int y,int radius,int tag){int dx,dy;
 if(!m)return 0;for(dy=-radius;dy<=radius;dy++)for(dx=-radius;dx<=radius;dx++){int xx=x+dx,yy=y+dy;if(dx*dx+dy*dy>radius*radius||xx<1||yy<1||xx>=w-1||yy>=h-1)continue;if(m[yy*w+xx]&&m[yy*w+xx]!=tag)return 1;}return 0;
}
static int river_stamp(unsigned char*m,const unsigned char*sea,int w,int h,int x,int y,int radius,int tag){int dx,dy,added=0;
 for(dy=-radius;dy<=radius;dy++)for(dx=-radius;dx<=radius;dx++){
  int xx=x+dx,yy=y+dy;if(dx*dx+dy*dy>radius*radius+1||xx<1||yy<1||xx>=w-1||yy>=h-1)continue;
  if((!sea||!sea[yy*w+xx])&&!m[yy*w+xx]){m[yy*w+xx]=(unsigned char)tag;added++;}
 }return added;
}
/* A confluence must overlap the existing wet cells, not stop one cell short.
 * The previous contact radius detected another river before the stamp reached
 * it, leaving a dry strip which native shore transitions made even wider. */
static int river_join(unsigned char*m,const unsigned char*sea,int w,int h,int x,int y,int radius,int tag){int dx,dy,best=10000,bx=x,by=y,k,parts,added=0;
 for(dy=-radius-2;dy<=radius+2;dy++)for(dx=-radius-2;dx<=radius+2;dx++){int xx=x+dx,yy=y+dy,d=dx*dx+dy*dy;if(xx<1||yy<1||xx>=w-1||yy>=h-1||d>=best)continue;if((m[yy*w+xx]&&m[yy*w+xx]!=tag)||(sea&&sea[yy*w+xx])){best=d;bx=xx;by=yy;}}
 parts=max(ab(bx-x),ab(by-y));for(k=0;k<=parts;k++)added+=river_stamp(m,sea,w,h,parts?x+(bx-x)*k/parts:x,parts?y+(by-y)*k/parts:y,radius,tag);return added;
}
/* Smooth non-looping courses. Later rivers stop at their first confluence,
 * never continue through another channel as an X crossing. Narrow tributaries
 * join wider parent rivers; inland sources taper, inland mouths form pools.
 * This is a seeded visual drainage network, not a terrain-flow simulation. */
static int river_paths_relief(unsigned char*m,const unsigned char*sea,int w,int h,U seed,int selected,const RiverRelief*relief){
 int n=river_count(w,h,seed,selected),r,i,x0,y0,x1,y1,bx,by,cx,cy,t,x,y,px,py,steps,j,mode,radius,attempt,built=0,shortside=w<h?w:h,margin=3;
 int joinX[10],joinY[10],joinRadius[10],sourceX[10],sourceY[10];U random=seed^0xb5297a4dU;
 for(i=0;i<w*h;i++)m[i]=0;
 for(r=0;r<n;r++)for(attempt=0;attempt<64;attempt++){
  int parent=-1,dx,dy,den,offset,end=256,added=0,tag=built+1,stop=0,lobes,amplitude;
  {int candidates=0,best=-1;
   for(j=0;j<256;j++){int xx=margin+(int)(river_random(&random)%(U)(w-margin*2)),yy=margin+(int)(river_random(&random)%(U)(h-margin*2)),score=w*w+h*h,k;
    if(river_contact(sea,w,h,xx,yy,5,255)||river_contact(m,w,h,xx,yy,5,255))continue;
    for(k=0;k<built;k++){int dd=(xx-sourceX[k])*(xx-sourceX[k])+(yy-sourceY[k])*(yy-sourceY[k]);if(dd<score)score=dd;}
    if(score>best){best=score;x0=xx;y0=yy;}if(++candidates>=(built?4:1))break;
   }if(!candidates)continue;
  }
  x1=margin+(int)(river_random(&random)%(U)(w-margin*2));y1=margin+(int)(river_random(&random)%(U)(h-margin*2));
  mode=(int)(river_random(&random)%10);
  if(built&&river_random(&random)%100<45){parent=(int)(river_random(&random)%(U)built);x1=joinX[parent];y1=joinY[parent];}
  else if(mode<2){
   if(river_random(&random)&1){if(!river_contact(sea,w,h,1,y0,5,255)&&!river_contact(m,w,h,1,y0,5,255))x0=1;x1=w-2;}
   else{if(!river_contact(sea,w,h,x0,1,5,255)&&!river_contact(m,w,h,x0,1,5,255))y0=1;y1=h-2;}
  }else if(mode<5){switch(river_random(&random)%4){case 0:x1=1;break;case 1:x1=w-2;break;case 2:y1=1;break;default:y1=h-2;}}
  dx=x1-x0;dy=y1-y0;den=ab(dx)+ab(dy);if(den<shortside/4)continue;
  /* Some courses remain almost straight; others have broad smooth meanders. */
  lobes=1+(int)(river_random(&random)%4);amplitude=(int)(river_random(&random)%(U)(shortside/18+1));
  offset=(int)(river_random(&random)%(U)(shortside/3+1))-shortside/6;
  bx=river_clamp(x0+dx/3-dy*offset/den,w);by=river_clamp(y0+dy/3+dx*offset/den,h);
  offset=(int)(river_random(&random)%(U)(shortside/3+1))-shortside/6;
  cx=river_clamp(x0+dx*2/3-dy*offset/den,w);cy=river_clamp(y0+dy*2/3+dx*offset/den,h);
  if(parent<0&&mode>=5){bx=river_inset(bx,w,margin);cx=river_inset(cx,w,margin);by=river_inset(by,h,margin);cy=river_inset(cy,h,margin);}
  /* Half the rivers retain their chosen course, including mountain gorges.
   * The other half prefer lower ground among several broad alternative bends. */
  if(relief&&(river_random(&random)&1)){
   int best=0x7fffffff,k,q,nbx=bx,nby=by,ncx=cx,ncy=cy;
   for(k=-3;k<=3;k++){int obx=river_clamp(bx-dy*k*shortside/(den*14),w),oby=river_clamp(by+dx*k*shortside/(den*14),h),ocx=river_clamp(cx-dy*k*shortside/(den*14),w),ocy=river_clamp(cy+dx*k*shortside/(den*14),h),score=ab(k)*12;
    for(q=24;q<240;q+=12){int qx,qy,z;river_point(x0,y0,obx,oby,ocx,ocy,x1,y1,q,lobes,amplitude,w,h,&qx,&qy);z=river_elevation(relief,qx,qy);score+=z+z*z/128;}
    if(score<best){best=score;nbx=obx;nby=oby;ncx=ocx;ncy=ocy;}
   }bx=nbx;by=nby;cx=ncx;cy=ncy;
  }
  radius=parent>=0?(joinRadius[parent]>3?3:joinRadius[parent]):3+(int)(river_random(&random)%2);px=x0;py=y0;
  for(t=0;t<=256&&!stop;t++){
   int rad=t<12&&radius>3?3:radius;
   river_point(x0,y0,bx,by,cx,cy,x1,y1,t,lobes,amplitude,w,h,&x,&y);
   steps=ab(x-px)>ab(y-py)?ab(x-px):ab(y-py);
   for(j=0;j<=steps;j++){
    int xx=steps?px+(x-px)*j/steps:x,yy=steps?py+(y-py)*j/steps:y;
    if(sea&&sea[yy*w+xx]){added+=river_join(m,sea,w,h,xx,yy,rad,tag);stop=1;end=t;break;}
    if(river_contact(m,w,h,xx,yy,rad+1,tag)){added+=river_join(m,sea,w,h,xx,yy,rad,tag);stop=1;end=t;break;}
    added+=river_stamp(m,sea,w,h,xx,yy,rad,tag);
   }px=x;py=y;
  }
  /* Retry a source that immediately hits a coast or another river. A tiny
   * disconnected pool must not consume one of the requested river slots. */
  if(added<12||den*end/256<shortside/10){for(i=0;i<w*h;i++)if(m[i]==tag)m[i]=0;continue;}
  if(!stop&&parent<0&&mode>=5)river_stamp(m,sea,w,h,x1,y1,radius+1,tag);
  /* A rare side channel leaves and rejoins this river, forming a floodplain
   * island. Validate the entire branch before painting; never cut an X into
   * an unrelated river or a coastline. Branches share the river count budget. */
  if(end>208&&den>shortside/3&&shortside>=128&&river_random(&random)%100<22){
   int side=(river_random(&random)&1)?1:-1,ok=1,branch[145][2],q;
   for(q=0;q<=144;q++){int wave=river_wave(q*256/144,1,(radius*4+4)*side),qx,qy;river_point(x0,y0,bx,by,cx,cy,x1,y1,56+q,lobes,amplitude,w,h,&qx,&qy);qx=river_clamp(qx-dy*wave/den,w);qy=river_clamp(qy+dx*wave/den,h);branch[q][0]=qx;branch[q][1]=qy;
    if(river_contact(sea,w,h,qx,qy,radius,255)||river_contact(m,w,h,qx,qy,radius+1,tag))ok=0;
   }
   if(ok)for(q=0;q<=144;q++){int qx=branch[q][0],qy=branch[q][1],lastx=q?branch[q-1][0]:qx,lasty=q?branch[q-1][1]:qy,k,parts=max(ab(qx-lastx),ab(qy-lasty));for(k=0;k<=parts;k++)river_stamp(m,sea,w,h,parts?lastx+(qx-lastx)*k/parts:qx,parts?lasty+(qy-lasty)*k/parts:qy,radius>3?3:radius,tag);}
  }
  river_point(x0,y0,bx,by,cx,cy,x1,y1,end*(64+(int)(river_random(&random)%129))/256,lobes,amplitude,w,h,&joinX[built],&joinY[built]);joinRadius[built]=radius;sourceX[built]=x0;sourceY[built]=y0;
  built++;break;
 }
 for(i=0;i<w*h;i++)m[i]=m[i]?1:0;
 return built;
}
static int river_paths(unsigned char*m,const unsigned char*sea,int w,int h,U seed,int selected){return river_paths_relief(m,sea,w,h,seed,selected,0);}
