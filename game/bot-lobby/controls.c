/* Host-only bulk bot controls. Runs on the native UI thread. All changes use
 * the existing player-row callbacks and their original replicated orders. */
#include <stddef.h>
typedef unsigned int U;
#define P(a,o) (*(U*)((U)(a)+(o)))
#define B(a,o) (*(unsigned char*)((U)(a)+(o)))
#define FAST __attribute__((fastcall))
#define EXPORT __attribute__((dllexport))
int __attribute__((stdcall)) _dllstart(void*a,U b,void*c){return 1;}
typedef U (FAST *M0)(U,U);
typedef U (FAST *M1)(U,U,U);
typedef U (FAST *M2)(U,U,U,U);
typedef U (FAST *M3)(U,U,U,U,U);
typedef U (*C2)(U,U);
typedef U (*C3)(U,U,U);
typedef U (*C4)(U,U,U,U);
typedef struct Data Data;
typedef struct {Data*d;U kind,widget,selected,generation,custom,customId,randomId,randomLabel;} Control;
typedef struct {U row,participant,player,generation[3];} Row;
struct Data {U image,language,menu,busy,enabled,signature,applications,skipped;Control c[3];U labels[3];Row rows[64];};
static U m0(Data*d,U r,U self){return ((M0)(d->image+r))(self,0);}
static U m1(Data*d,U r,U self,U a){return ((M1)(d->image+r))(self,0,a);}
static U m2(Data*d,U r,U self,U a,U b){return ((M2)(d->image+r))(self,0,a,b);}
static void zero(void*p,U n){unsigned char*q=p;while(n--)*q++=0;}
static int eq(U a,U b){unsigned short*x=(void*)a,*y=(void*)b;U i;if(!a||!b)return a==b;for(i=0;i<512;i++){if(x[i]!=y[i])return 0;if(!x[i])return 1;}return 0;}
static U str(Data*d,const wchar_t*s){U out=0;m1(d,0x205de,(U)&out,(U)s);return out;}
static void release(Data*d,U s){if(s)m0(d,0x21375,s-16);}
static int host(Data*d){U s=P(d->image,0x5f3fe4),conn=P(d->image,0x5f3fec);if(!s||!conn)return 0;
 return (P(s,0x60)==1||P(s,0x60)==2)&&P(s,0x64)!=2&&P(s,0x6c)!=5&&P(s,0x6c)!=3&&P(s,0x6c)!=4&&(unsigned char)m0(d,0x1490d5,conn);
}
static U bot(Data*d,U row){U p;if(!row||P(row,0xf8)==5||!P(row,0xf0)||!P(row,0xf4))return 0;p=P(row,0xec);
 return p&&B(p,0xc)&&P(p,4)==P(d->image,0x5f3fec)?p:0;
}
static int allowed_nation(U nation,U faction){U n,i,list;if(!nation||!faction)return 1;n=P(nation,0x4c);list=P(nation,0x48);if(n>64||!list)return 0;for(i=0;i<n;i++)if(P(list,i*4)==faction)return 1;return 0;}
static int allowed_faction(Data*d,U faction){U i,p,nation;if(d->c[0].selected>1)return allowed_nation(d->c[0].selected,faction);
 for(i=0;i<64;i++)if((p=bot(d,d->rows[i].row))!=0){nation=P(P(d->rows[i].row,0xf0),0x18);if(!allowed_nation(nation,faction))return 0;}return 1;
}
static U selected_id(Control*c){if(!c->selected)return c->customId;return c->selected==1?c->randomId:P(c->selected,8);}
static void select(Control*c){Data*d=c->d;U id=selected_id(c),idx=m1(d,0x2a1f84,P(c->widget,0x6c),(U)&id);if(!(unsigned char)m1(d,0x2a2a38,c->widget,idx))m0(d,0x2a2c7a,c->widget);}
static void add(Data*d,U temp,U label,U id){((M3)(d->image+0x2a502e))(temp,0,label,id,0);}
static void populate(Control*c){Data*d=c->d;U temp[12],db=P(d->image,0x5f3fb4),list,n,i,def,label;
 if(!db||!c->widget)return;
 if(c->kind==0){list=P(db,0x80);n=P(db,0x84);}else if(c->kind==1){list=P(db,0xcc);n=P(db,0xd0);}else{list=P(db,0x43c);n=P(db,0x440);}if(n>128)return;
 if(c->kind==1&&c->selected>1&&!allowed_faction(d,c->selected)){c->selected=0;c->generation++;}
 m1(d,0x2a517f,(U)temp,c->widget);add(d,(U)temp,(U)&c->custom,(U)&c->customId);
 if(c->kind!=2)add(d,(U)temp,(U)&c->randomLabel,(U)&c->randomId);
 for(i=0;i<n;i++){def=P(list,i*4);if(!def)continue;
  if(c->kind==0&&!B(def,0x68))continue;
  if(c->kind==1&&(!B(def,0x18)||!allowed_faction(d,def)))continue;
  label=def+0x10;if(c->kind==1&&P(def,0x44)&&P(P(def,0x44),-12))label=def+0x44;
  add(d,(U)temp,label,def+8);
 }
 m0(d,0x2a51b1,(U)temp);m0(d,0x2a51a6,(U)temp);select(c);
}
static void apply(Data*d,Row*r){U p=bot(d,r->row),i,id,owned,nation,choice;Control*c;if(!p){r->player=0;r->participant=0;return;}
 if(r->player!=p||r->participant!=P(p,0x20)){r->player=p;r->participant=P(p,0x20);zero(r->generation,sizeof(r->generation));}
 for(i=0;i<3;i++){c=&d->c[i];if(r->generation[i]==c->generation)continue;
  r->generation[i]=c->generation;choice=c->selected;if(!choice)continue;
  if(i==1&&choice>1){nation=P(P(r->row,0xf0),0x18);if(!allowed_nation(nation,choice)){d->skipped++;continue;}}
  id=selected_id(c);owned=str(d,(const wchar_t*)id);
  m1(d,i==0?0x1286cd:i==1?0x1287c1:0x128871,r->row,owned);d->applications++;
 }
}
static void FAST changed(Control*c,U unused,U value){Data*d=c->d;U i,n,list,db,def,choice=0,valid=0;
 if(!d->busy&&host(d)){
  if(eq(value,c->customId)){valid=1;choice=0;}else if(c->kind!=2&&eq(value,c->randomId)){valid=1;choice=1;}
  else {db=P(d->image,0x5f3fb4);if(c->kind==0){list=P(db,0x80);n=P(db,0x84);}else if(c->kind==1){list=P(db,0xcc);n=P(db,0xd0);}else{list=P(db,0x43c);n=P(db,0x440);}
   if(n<=128)for(i=0;i<n;i++){def=P(list,i*4);if(def&&eq(value,P(def,8))){valid=1;choice=def;break;}}
  }
  if(valid){d->busy=1;c->selected=choice;c->generation++;for(i=0;i<64;i++)if(d->rows[i].row)apply(d,&d->rows[i]);populate(&d->c[1]);d->busy=0;}
 }
 release(d,value);
}
static void create(Data*d,U menu){
 static const wchar_t*names[]={L"PawBotsRace",L"PawBotsFaction",L"PawBotsDifficulty"};
 static const wchar_t*labels[]={L"PawBotsRaceLabel",L"PawBotsFactionLabel",L"PawBotsDifficultyLabel"};
 static const wchar_t*custom[]={L"Custom",L"Пользовательский",L"Benutzerdefiniert",L"Personnalisé",L"Vlastní",L"Користувацький"};
 static const wchar_t*random[]={L"Random",L"Случайно",L"Zufällig",L"Aléatoire",L"Náhodně",L"Випадково"};
 U i,name,action,w;Control*c;d->menu=menu;d->busy=1;
 for(i=0;i<3;i++){
  c=&d->c[i];c->d=d;c->kind=i;c->selected=0;c->generation=0;
  c->custom=str(d,custom[d->language<6?d->language:0]);c->customId=str(d,L"paws_custom");c->randomId=str(d,(const wchar_t*)(d->image+0x4a95f4));c->randomLabel=str(d,random[d->language<6?d->language:0]);
  name=str(d,names[i]);action=((C3)(d->image+0x12bb94))((U)c,(U)changed,0);
  /* These controls do not belong to a selectable player row. */
  w=((C4)(d->image+0x2a7b37))(0,(U)&name,0,action);c->widget=w;m2(d,0x2b7486,menu,w,0);release(d,name);
  name=str(d,labels[i]);w=((C2)(d->image+0x81d30))((U)&name,0);d->labels[i]=w;m2(d,0x2b7486,menu,w,0);release(d,name);
 }
 d->busy=0;
}
/* Create children before the engine initializes the menu's visual tree.
 * Adding a dropdown from Tick invokes its OnAttach with no selected-label
 * visual yet. Populate only after the normal initialization has completed. */
EXPORT void menu_create(U image,Data*d,U menu){if(!d->image)d->image=image;if(!d->menu)create(d,menu);}
EXPORT void menu_tick(U image,Data*d,U menu){U i,enable,sig=0,p;if(d->menu!=menu||d->busy)return;
 enable=host(d);d->enabled=enable;d->busy=1;
 if(!d->c[0].generation)for(i=0;i<3;i++){
  d->c[i].generation=1;populate(&d->c[i]);
  /* Stock panels are created during Initialize, after these children. Put
   * initialized controls above the panel so its background cannot cover
   * their text or intercept their mouse input. Detach keeps widget alive. */
  m2(d,0x2b74f9,menu,d->c[i].widget,1);m2(d,0x2b7486,menu,d->c[i].widget,0);
  m2(d,0x2b74f9,menu,d->labels[i],1);m2(d,0x2b7486,menu,d->labels[i],0);
 }
 for(i=0;i<3;i++){m1(d,0x2b7271,d->c[i].widget,enable);m1(d,0x2b7271,d->labels[i],enable);m1(d,0x2b728f,d->c[i].widget,enable);}
 if(enable){for(i=0;i<64;i++)if((p=bot(d,d->rows[i].row))!=0)sig^=(P(p,0x20)*2654435761u)^P(P(d->rows[i].row,0xf0),0x18);if(sig!=d->signature){d->signature=sig;populate(&d->c[1]);}}
 d->busy=0;
}
EXPORT void row_tick(U image,Data*d,U row){U i;Row*r=0;if(!d->image)d->image=image;if(d->busy)return;for(i=0;i<64;i++)if(d->rows[i].row==row){r=&d->rows[i];break;}
 if(!r)for(i=0;i<64;i++)if(!d->rows[i].row){r=&d->rows[i];r->row=row;break;}
 if(r&&d->menu&&host(d)){d->busy=1;apply(d,r);d->busy=0;}
}
EXPORT void row_destroy(U image,Data*d,U row){U i;for(i=0;i<64;i++)if(d->rows[i].row==row)zero(&d->rows[i],sizeof(Row));}
EXPORT void menu_destroy(U image,Data*d,U menu){U i,lang=d->language;if(d->menu!=menu)return;for(i=0;i<3;i++){release(d,d->c[i].custom);release(d,d->c[i].customId);release(d,d->c[i].randomId);release(d,d->c[i].randomLabel);}zero(d,sizeof(Data));d->language=lang;d->image=image;}
EXPORT U data_size(void){return sizeof(Data);}
