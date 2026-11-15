/* Add independent rules to the installed native map dialog. Its original
 * climate/profile list and mixed-biome configuration remain authoritative. */
typedef unsigned int U;
typedef unsigned short W;
#define P(a,o) (*(U*)((U)(a)+(o)))
#define FAST __attribute__((fastcall))
#define EXPORT __attribute__((dllexport))
typedef U (FAST*M0)(U,U);
typedef U (FAST*M1)(U,U,U);
typedef U (FAST*M2)(U,U,U,U);
typedef U (FAST*M3)(U,U,U,U,U);
typedef U (FAST*M5)(U,U,U,U,U,U,U);
typedef U (*C2)(U,U);
typedef U (*C3)(U,U,U);
typedef U (*C4)(U,U,U,U);
typedef struct Data Data;
typedef struct{Data*d;U menu,rivers,riverLabel,shape,shapeLabel,busy,initialized,maximum,sizeKey;}Menu;
struct Data{U image,language,creates,populates,error,reserved;Menu menus[4];U pendingOperation,pendingValue,settingsGet,settingsPut;};
static Data*menu_data;
static U m0(Data*d,U r,U self){return ((M0)(d->image+r))(self,0);}
static U m1(Data*d,U r,U self,U a){return ((M1)(d->image+r))(self,0,a);}
static U m2(Data*d,U r,U self,U a,U b){return ((M2)(d->image+r))(self,0,a,b);}
static U str(Data*d,const W*s){U out=0;m1(d,0x205de,(U)&out,(U)s);return out;}
static void release(Data*d,U s){if(s)m0(d,0x21375,s-16);}
static int same(const W*w,const char*s){U i,a,b;if(!w)return 0;for(i=0;i<160;i++){a=w[i];b=(unsigned char)s[i];if(a>='A'&&a<='Z')a+=32;if(b>='A'&&b<='Z')b+=32;if(a!=b)return 0;if(!a)return 1;}return 0;}
static int same_w(const W*a,const W*b){U i;if(!a||!b)return 0;for(i=0;i<160;i++){if(a[i]!=b[i])return 0;if(!a[i])return 1;}return 0;}
static Menu*context(Data*d,U menu){U i;for(i=0;i<4;i++)if(d->menus[i].menu==menu)return &d->menus[i];return 0;}
static U rule(U rules,const char*name){U i,items=P(rules,0xc),count=P(rules,0x10);if(!items||count>256)return 0;for(i=0;i<count;i++){U p=items+i*12,def=P(p,0);if(def&&same((W*)P(def,8),name))return p;}return 0;}
static U maximum(Data*d,U menu,U*key){U drop=P(menu,0x138),item=drop?m0(d,0x2a22d2,P(drop,0x6c)):0,ptr;W*s;int w=0,h=0;
 if(item){ptr=((M0)P(P(item,0),8))(item,0);s=ptr?(W*)P(ptr,0):0;if(s){while(*s>='0'&&*s<='9')w=w*10+*s++-'0';while(*s&&(*s<'0'||*s>'9'))s++;while(*s>='0'&&*s<='9')h=h*10+*s++-'0';}}
 if(key)*key=0;if(w<128||h<128||w>4096||h>4096)return 1;if(key)*key=(U)w*4096+(U)h;w=(w<h?w:h)/200;return w>10?10:w<1?1:(U)w;
}
static void populate(Menu*m,U widget,U record,U max,U random){Data*d=m->d;U def=P(record,0),values=P(def,0x34),i,index=P(record,8);
 if(index>max&&index!=random){index=max;m2(d,0x296c07,m->menu+0xfc,def,index);}
 m0(d,0x2a2a1e,widget);
 for(i=0;i<=max;i++)((M3)(d->image+0x2a294a))(widget,0,values+i*8+4,values+i*8,1);
 if(random<18)((M3)(d->image+0x2a294a))(widget,0,values+random*8+4,values+random*8,1);
 m1(d,0x2a2a38,widget,index==random?max+1:index);
}
EXPORT void menu_settings(Data*d,U get,U put){d->settingsGet=get;d->settingsPut=put;}
EXPORT void menu_remember(Data*d,U menu){Menu*m=context(d,menu);U r,s;if(!m||!d->settingsPut||!m->sizeKey)return;r=rule(menu+0xfc,"PawsRivers");s=rule(menu+0xfc,"PawsMapShape");if(r)((C3)d->settingsPut)(0,m->sizeKey,P(r,8));if(s)((C3)d->settingsPut)(1,0,P(s,8));}
EXPORT void menu_rivers_refresh(Data*d,U menu){Menu*m=context(d,menu);U r,s,key,value;if(!m||m->busy)return;r=rule(menu+0xfc,"PawsRivers");s=rule(menu+0xfc,"PawsMapShape");if(!r||!s)return;
 m->busy=1;m->maximum=maximum(d,menu,&key);
 if(d->settingsGet&&key){value=((C3)d->settingsGet)(0,key,m->sizeKey&&m->sizeKey!=key?17:P(r,8));if(value<=17&&value!=P(r,8))m2(d,0x296c07,menu+0xfc,P(r,0),value);value=((C3)d->settingsGet)(1,0,P(s,8));if(value<=3&&value!=P(s,8))m2(d,0x296c07,menu+0xfc,P(s,0),value);}
 m->sizeKey=key;populate(m,m->rivers,r,m->maximum,17);populate(m,m->shape,s,3,99);m->busy=0;d->populates++;
}
static void changed(Menu*m,U value,const char*name){Data*d=m->d;U record,def,i,n;if(!m->busy&&(record=rule(m->menu+0xfc,name))){def=P(record,0);n=P(def,0x38);if(n<=18)for(i=0;i<n;i++)if(same_w((W*)value,(W*)P(P(def,0x34)+i*8,0))){if(name[4]=='M'||i<=m->maximum||i==17){m2(d,0x296c07,m->menu+0xfc,def,i);menu_remember(d,m->menu);m0(d,0x11ba60,m->menu);}break;}}release(d,value);}
static void FAST rivers_changed(Menu*m,U unused,U value){changed(m,value,"PawsRivers");}
static void FAST shape_changed(Menu*m,U unused,U value){changed(m,value,"PawsMapShape");}
EXPORT void FAST menu_qa_dispatch(U menu,U unused,U arguments);
EXPORT void menu_create(Data*d,U menu){Menu*m=0;U i,name,action,help;menu_data=d;for(i=0;i<4;i++)if(!d->menus[i].menu){m=&d->menus[i];break;}if(!m){d->error=1;return;}m->d=d;m->menu=menu;m->busy=1;
 name=str(d,(W*)L"PawRivers");action=((C3)(d->image+0x12bb94))((U)m,(U)rivers_changed,0);m->rivers=((C4)(d->image+0x2a7b37))(0,(U)&name,0,action);m2(d,0x2b7486,menu,m->rivers,0);release(d,name);
 name=str(d,(W*)L"PawRiversLabel");m->riverLabel=((C2)(d->image+0x81d30))((U)&name,0);m2(d,0x2b7486,menu,m->riverLabel,0);release(d,name);
 name=str(d,(W*)L"PawMapShape");action=((C3)(d->image+0x12bb94))((U)m,(U)shape_changed,0);m->shape=((C4)(d->image+0x2a7b37))(0,(U)&name,0,action);m2(d,0x2b7486,menu,m->shape,0);release(d,name);
 name=str(d,(W*)L"PawMapShapeLabel");m->shapeLabel=((C2)(d->image+0x81d30))((U)&name,0);m2(d,0x2b7486,menu,m->shapeLabel,0);release(d,name);
 name=str(d,(W*)L"PawsRiverAction");help=str(d,(W*)L"");((M5)(d->image+0x11bcd9))(menu,0,(U)&name,(U)menu_qa_dispatch,0,(U)&help,0);release(d,name);release(d,help);
 m->busy=0;d->creates++;
}
EXPORT void menu_populate(Data*d,U menu){Menu*m=context(d,menu);U widgets[4],i,parent;if(!m)return;
 if(!m->initialized){widgets[0]=m->rivers;widgets[1]=m->riverLabel;widgets[2]=m->shape;widgets[3]=m->shapeLabel;for(i=0;i<4;i++){parent=menu;m2(d,0x2b74f9,parent,widgets[i],1);m2(d,0x2b7486,parent,widgets[i],0);}m->initialized=1;}
 menu_rivers_refresh(d,menu);
}
EXPORT void menu_destroy(Data*d,U menu){Menu*m=context(d,menu);U i;if(m)for(i=0;i<sizeof(Menu)/4;i++)((U*)m)[i]=0;}
EXPORT U menu_rivers_qa(Data*d,U operation,U value){Menu*m=0;U i,r;for(i=0;i<4;i++)if(d->menus[i].menu){m=&d->menus[i];break;}if(!m)return 0;
 if((operation>=1&&operation<=3)||operation==6||operation==7){d->pendingOperation=operation;d->pendingValue=value;}
 if(operation==4)return m->maximum;if(operation==5){r=rule(m->menu+0xfc,"PawsRivers");return r?P(r,8):99;}return m->menu;
}
EXPORT void FAST menu_qa_dispatch(U menu,U unused,U arguments){Data*d=menu_data;Menu*m=d?context(d,menu):0;U op,value,r,def,id,mgr,i,n;const char*profiles[]={"rmc_temperate03","rmc_arctic03","rmc_desert03","rmc_cursed03","paws_mixed_biomes"};if(!m)return;
 op=d->pendingOperation;value=d->pendingValue;d->pendingOperation=0;
 if(op==7&&value<3){r=rule(menu+0xfc,"FogOfWar");if(r){m2(d,0x296c07,menu+0xfc,P(r,0),value);m0(d,0x11ba60,menu);}}
 if(op==1||op==6){r=rule(menu+0xfc,op==1?"PawsRivers":"PawsMapShape");if(!r||value>(op==1?17:3)||(op==1&&value>m->maximum&&value!=17))return;def=P(r,0);id=P(P(def,0x34)+value*8,0);changed(m,str(d,(W*)id),op==1?"PawsRivers":"PawsMapShape");menu_rivers_refresh(d,menu);}
 if(op==2){U drop=P(menu,0x138),list=drop?P(drop,0x6c):0;if(list&&value<P(list,0x70)){m1(d,0x2a2a38,drop,value);m1(d,0x11a678,menu,0);menu_rivers_refresh(d,menu);}}
 if(op==3&&value<5){W name[48];for(i=0;profiles[value][i];i++)name[i]=(W)profiles[value][i];name[i]=0;m1(d,0x11b0f1,menu,str(d,name));menu_rivers_refresh(d,menu);}
}

/* Native lobby map data may still contain profile defaults until the map
 * dialog's OK runs. Merge the saved native rule preferences into a RANDOM_MAP
 * immediately before launching, without touching saves or authored scenarios. */
static int map_integer(float v){int i;__asm__ volatile(".byte 0xf3,0x0f,0x2c,0x00":"=a"(i):"a"(&v));return i;}
EXPORT U menu_launch_settings(Data*d){U session,info,prefs,r,key,value,maximum;int w,h;
 if(!d||(session=P(d->image,0x5f3fe4))==0||(P(session,0xf0)!=1&&P(session,0xf0)!=2)||*(unsigned char*)(session+0x100)||P(session,0x64)!=0)return 0;
 info=P(session,0x80);if(!info||!P(info,0x50)||!rule(info+0x20,"FogOfWar"))return 0;
 prefs=P(d->image,0x5f9a0c);if(prefs)m1(d,0x142fe0,prefs,info+0x20);
 w=map_integer(*(float*)(info+0x3c));h=map_integer(*(float*)(info+0x40));if(w<128||h<128||w>4096||h>4096)return 1;
 key=(U)w*4096+(U)h;maximum=(U)((w<h?w:h)/200);if(maximum<1)maximum=1;if(maximum>10)maximum=10;
 if(d->settingsGet){
  r=rule(info+0x20,"PawsRivers");if(r&&!*(unsigned char*)(r+4)){value=((C3)d->settingsGet)(0,key,P(r,8));if(value<=17){if(value!=17&&value>maximum)value=maximum;m2(d,0x296c07,info+0x20,P(r,0),value);}}
  r=rule(info+0x20,"PawsMapShape");if(r&&!*(unsigned char*)(r+4)){value=((C3)d->settingsGet)(1,0,P(r,8));if(value<=3)m2(d,0x296c07,info+0x20,P(r,0),value);}
 }return 1;
}
