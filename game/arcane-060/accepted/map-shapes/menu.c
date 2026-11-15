/* Local prototype. Native UI thread only. No simulation changes here. */
#include <stddef.h>
#include "profiles.h"
#include "menu_text.h"
typedef unsigned int U;
#define P(a,o) (*(U*)((U)(a)+(o)))
#define FAST __attribute__((fastcall))
#define EXPORT __attribute__((dllexport))
typedef U (FAST *M0)(U,U);
typedef U (FAST *M1)(U,U,U);
typedef U (FAST *M2)(U,U,U,U);
typedef U (FAST *M3)(U,U,U,U,U);
typedef U (FAST *M4)(U,U,U,U,U,U);
typedef U (FAST *M5)(U,U,U,U,U,U,U);
typedef U (*C2)(U,U);
typedef U (*C3)(U,U,U);
typedef U (*C4)(U,U,U,U);
typedef struct Data Data;
typedef struct {Data*d;U menu,widget,labels[2],busy,climate,initialized,rivers,riverLabel,riverBusy,riverMax;} Menu;
struct Data {U image,language,creates,populates,error,reserved;Menu menus[4];U pendingOperation,pendingValue;};
static Data*menu_data;
static void FAST river_qa_dispatch(U menu,U unused,U arguments);
static U m0(Data*d,U r,U self){return ((M0)(d->image+r))(self,0);}
static U m1(Data*d,U r,U self,U a){return ((M1)(d->image+r))(self,0,a);}
static U m2(Data*d,U r,U self,U a,U b){return ((M2)(d->image+r))(self,0,a,b);}
static U str(Data*d,const wchar_t*s){U out=0;m1(d,0x205de,(U)&out,(U)s);return out;}
static void release(Data*d,U s){if(s)m0(d,0x21375,s-16);}
static U lang(Data*d){return d->language<6?d->language:0;}
static U manager(Data*d){U db=P(d->image,0x5f3fb4);return db?P(db,0x58c):0;}
static int decode(U r,int*s,int*c){return r&&profile_decode((void*)P(r,8),s,c);}
static U find(Data*d,int shape,int climate){U mgr=manager(d),i,n,r;if(!mgr)return 0;n=P(mgr,0x28);if(n>1024)return 0;for(i=0;i<n;i++){r=P(P(mgr,0x24),i*4);if(r&&profile_match((void*)P(r,8),profile_ids[shape][climate]))return r;}return 0;}
static Menu* context(Data*d,U menu){U i;for(i=0;i<4;i++)if(d->menus[i].menu==menu)return &d->menus[i];return 0;}
static U river_rule(U rules){U i,n=P(rules,0x10),items=P(rules,0xc);if(!items||n>256)return 0;for(i=0;i<n;i++){U p=items+i*12,def=P(p,0);if(def&&(profile_match((void*)P(def,8),"PawsRivers")||profile_match((void*)P(def,8),"pawsrivers")))return p;}return 0;}
static U river_max(Data*d,U menu){U drop=P(menu,0x138),item=drop?m0(d,0x2a22d2,P(drop,0x6c)):0,ptr;const wchar_t*s;int w=0,h=0;
 if(item){ptr=((M0)P(P(item,0),8))(item,0);s=ptr?(const wchar_t*)P(ptr,0):0;if(s){while(*s>='0'&&*s<='9')w=w*10+*s++-'0';while(*s&&(*s<'0'||*s>'9'))s++;while(*s>='0'&&*s<='9')h=h*10+*s++-'0';}}
 if(w<128||h<128||w>4096||h>4096)return 1;
 w=(w<h?w:h)/128;return w<1?1:w>16?16:(U)w;
}
EXPORT void menu_rivers_refresh(Data*d,U menu){Menu*m=context(d,menu);U rule,def,values,i,index,max;
 if(!m||!m->rivers||m->riverBusy||!(rule=river_rule(menu+0xfc)))return;
 m->riverBusy=1;def=P(rule,0);values=P(def,0x34);max=river_max(d,menu);index=P(rule,8);m->riverMax=max;
 if(index>max&&index!=17){index=max;m2(d,0x296c07,menu+0xfc,def,index);}
 m0(d,0x2a2a1e,m->rivers);
 for(i=0;i<=max;i++)((M3)(d->image+0x2a294a))(m->rivers,0,values+i*8+4,values+i*8,1);
 ((M3)(d->image+0x2a294a))(m->rivers,0,values+17*8+4,values+17*8,1);
 m1(d,0x2a2a38,m->rivers,index==17?max+1:index);m->riverBusy=0;
}
static void FAST rivers_changed(Menu*m,U unused,U value){Data*d=m->d;U rule,def,i=99,k;const wchar_t*s=(const wchar_t*)value;const char*prefix="paws_rivers_";
 if(!m->riverBusy&&(rule=river_rule(m->menu+0xfc))){def=P(rule,0);
  if(profile_match(s,"paws_rivers_random"))i=17;
  else if(s){for(k=0;k<12&&s[k]==prefix[k];k++);if(k==12){i=0;for(;s[k]>='0'&&s[k]<='9';k++)i=i*10+s[k]-'0';if(s[k])i=99;}}
  if(i<=m->riverMax||i==17){m2(d,0x296c07,m->menu+0xfc,def,i);m0(d,0x11ba60,m->menu);}
 }release(d,value);
}
static void choose(Menu*m,int shape){Data*d=m->d;U list=P(m->menu,0xb4),r,id,label,i,selected=0,index;
 /* Native list owns copied labels/IDs. Native callback owns its value argument. */
 m0(d,0x2a193c,list);
 for(i=0;i<4;i++){r=find(d,i,m->climate);if(!r)continue;label=str(d,shape_names[lang(d)][i]);
  ((M4)(d->image+0x2a15d7))(list,0,(U)&label,r+8,1,0);release(d,label);if((int)i==shape)selected=r;}
 if(!selected)selected=find(d,0,m->climate);
 if(!selected){d->error=2;return;}
 id=P(selected,8);m1(d,0x11b0f1,m->menu,str(d,(const wchar_t*)id));
 index=m1(d,0x2a1f84,list,(U)&id);m2(d,0x2a1fef,list,index,0);
 d->populates++;
}
static void FAST changed(Menu*m,U unused,U value){Data*d=m->d;int shape=0,climate=0,i;
 if(!m->busy){for(i=0;i<3;i++)if(profile_match((void*)value,climate_ids[i])){
   decode(P(m->menu,0x160),&shape,&climate);m->busy=1;m->climate=i;choose(m,shape);m->busy=0;break;}}
 release(d,value);
}
EXPORT void menu_create(Data*d,U menu){U i,name,action,w;Menu*m=0;
 for(i=0;i<4;i++)if(!d->menus[i].menu){m=&d->menus[i];break;}
 if(!m){d->error=1;return;}menu_data=d;m->d=d;m->menu=menu;m->busy=1;
 {U command=str(d,L"PawsRiverAction"),help=str(d,L"");((M5)(d->image+0x11bcd9))(menu,0,(U)&command,(U)river_qa_dispatch,0,(U)&help,0);release(d,command);release(d,help);}
 name=str(d,L"PawClimate");action=((C3)(d->image+0x12bb94))((U)m,(U)changed,0);
 w=((C4)(d->image+0x2a7b37))(0,(U)&name,0,action);m->widget=w;m2(d,0x2b7486,menu,w,0);release(d,name);
 for(i=0;i<2;i++){name=str(d,i?L"PawShapeLabel":L"PawClimateLabel");w=((C2)(d->image+0x81d30))((U)&name,0);m->labels[i]=w;m2(d,0x2b7486,menu,w,0);release(d,name);}
 name=str(d,L"PawRivers");action=((C3)(d->image+0x12bb94))((U)m,(U)rivers_changed,0);
 m->rivers=((C4)(d->image+0x2a7b37))(0,(U)&name,0,action);m2(d,0x2b7486,P(menu,0x150),m->rivers,0);release(d,name);
 name=str(d,L"PawRiversLabel");m->riverLabel=((C2)(d->image+0x81d30))((U)&name,0);m2(d,0x2b7486,P(menu,0x150),m->riverLabel,0);release(d,name);
 m->busy=0;d->creates++;
}
EXPORT void menu_populate(Data*d,U menu){Menu*m=context(d,menu);U current,temp[12],i,id,label,index,session;int shape=0,climate=0;
 if(!m){m0(d,0x11b8b8,menu);return;}
 m->busy=1;session=P(d->image,0x5f3fe4);current=session?m0(d,0x167487,session):0;decode(current,&shape,&climate);m->climate=climate;
 m1(d,0x2a517f,(U)temp,m->widget);
 for(i=0;i<3;i++){label=str(d,climate_names[lang(d)][i]);id=str(d,climate_wids[i]);((M3)(d->image+0x2a502e))((U)temp,0,(U)&label,(U)&id,0);release(d,id);release(d,label);}
 m0(d,0x2a51b1,(U)temp);m0(d,0x2a51a6,(U)temp);
 id=str(d,climate_wids[climate]);index=m1(d,0x2a1f84,P(m->widget,0x6c),(U)&id);m1(d,0x2a2a38,m->widget,index);release(d,id);
 choose(m,shape);
 if(!m->initialized){m2(d,0x2b74f9,menu,m->widget,1);m2(d,0x2b7486,menu,m->widget,0);for(i=0;i<2;i++){m2(d,0x2b74f9,menu,m->labels[i],1);m2(d,0x2b7486,menu,m->labels[i],0);}m2(d,0x2b74f9,P(menu,0x150),m->rivers,1);m2(d,0x2b7486,P(menu,0x150),m->rivers,0);m2(d,0x2b74f9,P(menu,0x150),m->riverLabel,1);m2(d,0x2b7486,P(menu,0x150),m->riverLabel,0);m->initialized=1;}
 menu_rivers_refresh(d,menu);m->busy=0;
}
EXPORT void menu_destroy(Data*d,U menu){Menu*m=context(d,menu);U i;if(m)for(i=0;i<sizeof(Menu)/4;i++)((U*)m)[i]=0;}
/* Intent-only QA entry: the private driver calls the same native selection
 * handlers as the visible controls. The normal plugin exposes no transport. */
EXPORT U menu_rivers_qa(Data*d,U operation,U value){Menu*m=0;U i,rule;for(i=0;i<4;i++)if(d->menus[i].menu){m=&d->menus[i];break;}if(!m)return 0;
 if(operation>=1&&operation<=3){d->pendingOperation=operation;d->pendingValue=value;}
 if(operation==4)return m->riverMax;
 if(operation==5){rule=river_rule(m->menu+0xfc);return rule?P(rule,8):99;}
 return m->menu;
}
static void FAST river_qa_dispatch(U menu,U unused,U arguments){Data*d=menu_data;Menu*m=d?context(d,menu):0;U operation,value,rule,def,id;if(!m)return;
 operation=d->pendingOperation;value=d->pendingValue;d->pendingOperation=0;
 if(operation==1){rule=river_rule(menu+0xfc);if(!rule||value>17||(value>m->riverMax&&value!=17))return;def=P(rule,0);id=P(P(def,0x34)+value*8,0);rivers_changed(m,0,str(d,(const wchar_t*)id));menu_rivers_refresh(d,menu);}
 if(operation==2){m1(d,0x2a2a38,P(menu,0x138),value);m1(d,0x11a678,menu,0);menu_rivers_refresh(d,menu);}
 if(operation==3&&value<12){m->busy=1;m->climate=value/4;choose(m,value%4);m->busy=0;menu_rivers_refresh(d,menu);}
}
