/* Presentation reads the same serialized phase and fixed simulation time as
 * world-options/biomes.c; it never changes lighting, WorldRules or game time. */
static U dayWidget,dayOwner,dayVE;static int dayMinute=-2;
static U dayLightWorld,dayLightColors[9];static int dayLightMinute=-1;
static int day_id(U text,const char*id){unsigned i=0,a,b;if(!text)return 0;do{a=*(unsigned short*)(text+i*2);b=(unsigned char)id[i];if(a>='A'&&a<='Z')a+=32;if(b>='A'&&b<='Z')b+=32;if(a!=b)return 0;if(!a)return 1;}while(++i<160);return 0;}
static U day_rule(U world,const char*id){U table=P(world,0x18),n=P(world,0x1c),i;if(!table||n>256)return 0;for(i=0;i<n;i++){U record=table+i*12,data=P(record,0);if(data&&day_id(P(data,8),id))return record;}return 0;}
/* Random static Sun keeps the enum value 'sun_random'. Recover its selected
 * profile from the actual serialized lighting instead of hiding the clock or
 * inventing a moving day cycle for an otherwise static match. */
static int day_lighting_minutes(U world){U db=P(base,0x5f3fb4),i,j,changed=dayLightWorld!=world;float best=0;int result=-1;
 static const wchar_t*names[]={L"sun_morning",L"sun_default",L"sun_dusk",L"sun_night"};static const int minutes[]={360,720,1080,0};
 if(!world||!db)return -1;
 for(i=0;i<9;i++)if(dayLightColors[i]!=P(world,0x84+i*4))changed=1;if(!changed)return dayLightMinute;
 for(i=0;i<4;i++){U profile=((Get1)(base+0x2edb9))(db+0x73c,0,(U)names[i]);float distance=0;if(!profile)continue;
  for(j=0;j<9;j++){float d=F(world,0x84+j*4)-F(profile,0x18+j*4);distance+=d*d;}
  if(!(distance>=0&&distance<1e12f))continue;if(result<0||distance<best){result=minutes[i];best=distance;}
 }
 dayLightWorld=world;for(i=0;i<9;i++)dayLightColors[i]=P(world,0x84+i*4);dayLightMinute=result;return result;
}
static int __cdecl day_minutes(U world){U sun,data,index,id,phase;float seconds;if(!world)return -1;if(!(sun=day_rule(world,"Sun")))return day_lighting_minutes(world);
 data=P(sun,0);index=P(sun,8);if(P(data,0x20)!=3||index>=P(data,0x38)||index>128||!P(data,0x34))return -1;id=P(P(data,0x34),index*8);
 if(day_id(id,"paws_dynamic_sun")){U rule=day_rule(world,"PawsDayPhase");if(!rule||P(P(rule,0),0x20)!=1)return -1;
  seconds=F(world,0xe8);if(!(seconds>=0&&seconds<200000000.f))return -1;
  phase=(((U)(seconds*16.f))%9600+P(rule,8)%9600)%9600;return (int)((phase*1440/9600+360)%1440);
 }
 if(day_id(id,"sun_morning"))return 360;if(day_id(id,"sun_default")||day_id(id,"sun_afternoon"))return 720;if(day_id(id,"sun_dusk"))return 1080;if(day_id(id,"sun_night"))return 0;if(day_id(id,"sun_random"))return day_lighting_minutes(world);return -1;
}
/* A phase transition can temporarily fail match() while the native Game HUD
 * stays alive. Resolve by template identity in its owned child list instead of
 * trusting a cached pointer or creating a second label after such a transition.
 * Detach/destroy duplicates through the same native path as HUD destruction. */
static U __cdecl day_existing(U ui){U node=P(ui,0x28),found=0,steps=0;typedef U(FC*Detach)(U,U,U,U);
 while(node&&steps++<4096){U child=P(node,0),next=P(node,8);
  if(child&&P(child,0)==base+0x504d88&&day_id(P(child,0x1c),"PawsDayClock")&&day_id(P(child,0x18),"UI/Game/paws_day_clock.tgi")){
   if(!found)found=child;
   else if(((Detach)(base+0x2b74f9))(ui,0,child,1))((Void1)P(P(child,0),4))(child,0,1);
  }
  node=next;
 }
 return found;
}
static void day_clock_tick(void){U ui,ve,existing,depth=0;int minute;wchar_t text[16],*owned=0;
 typedef U(__cdecl*Create)(U,U);typedef void(FC*String)(U,U,const wchar_t*);
 if(!match()){dayOwner=dayWidget=dayVE=mapWidget=0;dayMinute=-2;return;}
 /* GameUI is the simulation/view controller, not the native HUD widget.
  * Follow the live minimap's parent chain to the owning Game interface. */
 for(ui=mapWidget;ui&&depth++<32&&P(ui,0)!=base+0x48e090;ui=P(ui,8)){}
 if(!ui||P(ui,0)!=base+0x48e090)return;
 if(dayOwner!=ui){dayOwner=ui;dayWidget=dayVE=0;dayMinute=-2;}
 existing=day_existing(ui);if(existing!=dayWidget){dayWidget=existing;dayVE=0;dayMinute=-2;}
 if(!dayWidget){
  ((String)(base+0x205de))((U)&owned,0,L"UI/Game/paws_day_clock.tgi:PawsDayClock");
  dayWidget=((Create)(base+0x81d30))((U)&owned,0);
  ((Void0)(base+0x21375))((U)owned-16,0);owned=0;
  if(!dayWidget)return;
  ((Void1)P(P(ui,0),0xd0))(ui,0,dayWidget);
  ((Void0)P(P(dayWidget,0),0x10))(dayWidget,0);
  ((Get1)P(P(dayWidget,0),0x1c))(dayWidget,0,0);
  host->log("ui-scout-test","DAY_CLOCK_CREATED widget=%x",dayWidget);
 }
 ve=P(dayWidget,0x6c);if(!ve)return;minute=day_minutes(P(base,0x5f3fb8));
 if(ve==dayVE&&minute==dayMinute)return;
 if(minute>=0)swprintf(text,L"%02d:%02d",minute/60,minute%60);else wcscpy(text,L"--:--");
 ((String)(base+0x205de))((U)&owned,0,text);((Void1)(base+0x2adad2))(ve,0,(U)&owned);((Void0)(base+0x21375))((U)owned-16,0);
 if(ve!=dayVE||dayMinute<0||minute<0)host->log("ui-scout-test","DAY_CLOCK_SHOWN time=%ls",text);
 dayVE=ve;dayMinute=minute;
}
