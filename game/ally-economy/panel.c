/* Presentation only. Runs on the game's UI thread, reuses EconomicImpact's
 * resource widgets, native economy calculation and native slide animation.
 * No simulation, orders, diplomacy, resource or save writes. */
typedef unsigned int U;
typedef unsigned short W;
#define P(a,o) (*(U*)((U)(a)+(o)))
#define B(a,o) (*(unsigned char*)((U)(a)+(o)))
#define FAST __attribute__((fastcall))
#define EXPORT __attribute__((dllexport))
typedef U (FAST *M0)(U,U);
typedef U (FAST *M1)(U,U,U);
typedef U (*C5)(U,U,U,U,U);
typedef U (*C6)(U,U,U,U,U,U);
int __attribute__((stdcall)) _dllstart(void*a,U b,void*c){return 1;}
typedef struct {U image,bar,world,mode,owner;U rgb[3];U transitions,frames;} Data;
static U m0(Data*d,U r,U s){return ((M0)(d->image+r))(s,0);}
static U m1(Data*d,U r,U s,U a){return ((M1)(d->image+r))(s,0,a);}
static int live(Data*d,U a){U reg=P(d->image,0x5ef72c),id;if(!reg||!a)return 0;id=P(a,0x14);return id&&P(reg,0x20004+4*(id&65535))==a;}
static void dirty(U bar){U n=P(bar,0x78),list=P(bar,0x74),i;if(!list||n>64)return;for(i=0;i<n;i++){U w=P(list,4*i);if(w)B(w,0x89)=1;}}
static U ally(Data*d){
 U manager=P(d->image,0x5f3fc0),ui=P(d->image,0x5f3fbc),local,sel,k;
 if(P(d->image,0x5f9218)!=2||!P(d->image,0x5f3fb8)||!manager||!ui)return 0;
 /* Strict local player query: observers must not use selected kingdom as
  * their own player and accidentally gain enemy information. */
 local=m0(d,0x2be624,manager);if(!live(d,local))return 0;
 sel=P(ui,0x13c);if(!sel||(sel=P(sel,8))==0||(sel=P(sel,0))==0)return 0;
 /* Same primary selected actor and virtual owner lookup as native UI. */
 k=m0(d,0x2e1071,sel);if(!live(d,k)||k==local)return 0;
 if(((M1)P(P(k,0),0x144))(k,0,local)!=1)return 0;
 return k;
}
static int forecast(U bar){U source=P(bar,0xd0);return B(bar,0xd8)&&(B(bar,0xd9)||(source&&(P(source,0x24)&8)&&!B(bar,0xda)));}
EXPORT void reset(U image,Data*d,U bar){d->image=image;if(d->bar==bar){d->bar=0;d->mode=0;d->owner=0;d->world=0;}}
EXPORT void tick(U image,Data*d,U bar){
 U k=0,i,world=P(image,0x5f3fb8);int changed;
 d->image=image;d->frames++;
 if(d->bar!=bar||d->world!=world){
  if(d->bar==bar&&d->mode){P(bar,0xa0)=0;B(bar,0x80)=0;dirty(bar);}
  d->bar=bar;d->world=world;d->mode=0;d->owner=0;
 }
 if(forecast(bar)){
  if(d->mode){P(bar,0xa0)=0;B(bar,0x80)=0;dirty(bar);d->mode=0;d->owner=0;d->transitions++;}
  /* Forecast vectors may have just been set by a hover callback: retain them. */
  m0(d,0xbfbf0,bar);return;
 }
 k=ally(d);
 if(k){
  changed=d->mode!=1||d->owner!=P(k,0x14);
  if(changed){
   m0(d,0xbf6ea,bar);m0(d,0xbf7cf,bar);B(bar,0xd8)=0;P(bar,0xd0)=0;
   for(i=0;i<3;i++)d->rgb[i]=0x3f800000; /* ordinary white, independent of kingdom color */
   dirty(bar);d->transitions++;
  }
  d->mode=1;d->owner=P(k,0x14);P(bar,0xa0)=d->owner;B(bar,0x80)=1;
  m0(d,0xbf01f,bar);m1(d,0xbfd31,bar,1);return;
 }
 if(d->mode){
  /* Slide away using the last already displayed values. Never keep reading
   * the previous kingdom after selection/diplomacy changes or destruction. */
  d->mode=2;m1(d,0xbfd31,bar,0);m0(d,0x2b61c8,bar);
  if(!(P(bar,0x24)&0x20000)){
   m1(d,0x2b7271,bar,0);P(bar,0xa0)=0;B(bar,0x80)=0;B(bar,0xd8)=0;
   dirty(bar);d->mode=0;d->owner=0;d->transitions++;
  }
  return;
 }
 m0(d,0xbfbf0,bar);
}
static int resource(Data*d,U w){U i,n,list;if(!d->mode||!d->bar)return 0;n=P(d->bar,0x78);list=P(d->bar,0x74);if(!list||n>64)return 0;for(i=0;i<n;i++)if(P(list,4*i)==w)return 1;return 0;}
EXPORT void resource_tick(U image,Data*d,U w){
 U text=0,colored=0,def,net,cap,len,label,start;W* chars;
 d->image=image;
 if(!resource(d,w)){m0(d,0xbf939,w);return;}
 m0(d,0x2b61c8,w);if(!B(w,0x89))return;
 def=P(w,0x78);label=P(w,0x74);if(!def||!label)return;
 net=P(w,0x7c);if((net&0x7fffffff)==0)net=0;
 if(P(def,0x18)==2){
  cap=P(w,0x84);if((cap&0x7fffffff)==0)cap=0;
  ((C5)(image+0x2bcd9f))((U)&text,def,net,cap,0);
 }else ((C6)(image+0x2bcd63))((U)&text,def,net,0,B(w,0x88)&&P(def,0x18)==0,P(w,0x80));
 /* Native formatters, including the fractional KP patch, produce the same
  * icon + numbers as the top row. No red negative-value markup in ally mode.
  * Color only the numeric suffix; leave the resource icon untouched. */
 if(text){
  len=P(text,-12);chars=(W*)text;start=0;
  while(start<len&&chars[start]!='+'&&chars[start]!='-'&&(chars[start]<'0'||chars[start]>'9'))start++;
  if(start<len)((C5)(image+0x1ada8c))((U)&colored,(U)&text,start,len-start,(U)d->rgb);
  ((M1)P(P(label,0),0xc8))(label,0,colored?(U)&colored:(U)&text);
  if(colored)m0(d,0x21375,colored-16);
  m0(d,0x21375,text-16);
 }
 B(w,0x89)=0;
}
