/* Private marked sandbox only. Wraps the tested native mechanics; does not
 * modify the installed executable. QA command transport is compiled separately. */
#include <windows.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <wchar.h>
#include <stdlib.h>
#define P(a,o) (*(unsigned*)((uintptr_t)(a)+(o)))
#define F(a,o) (*(float*)((uintptr_t)(a)+(o)))
#define FC __attribute__((fastcall))
typedef struct {unsigned api;uintptr_t exeBase;const wchar_t*gameDir,*modsDir;void (__cdecl *log)(const char*,const char*,...);} Host;
#include "plugin_data.h"
static unsigned base,cave;static const Host*owner;static int deferred,installing;
#ifdef MAP_SETTINGS
static wchar_t settingsPath[MAX_PATH];
static unsigned map_get(unsigned kind,unsigned key,unsigned fallback){wchar_t name[32];if(kind)swprintf(name,L"Shape");else swprintf(name,L"%ux%u",key/4096,key%4096);return GetPrivateProfileIntW(kind?L"Map":L"Rivers",name,fallback,settingsPath);}
static unsigned map_put(unsigned kind,unsigned key,unsigned value){wchar_t name[32],number[16];if(kind)swprintf(name,L"Shape");else swprintf(name,L"%ux%u",key/4096,key%4096);swprintf(number,L"%u",value);return WritePrivateProfileStringW(kind?L"Map":L"Rivers",name,number,settingsPath);}
#endif
#define MAX_HOOKS 128
static unsigned char oldBytes[MAX_HOOKS][8];
static int write_hook(unsigned at,const void*bytes,unsigned size){DWORD old,unused;
 if(!VirtualProtect((void*)at,size,PAGE_EXECUTE_READWRITE,&old))return 0;
 memcpy((void*)at,bytes,size);FlushInstructionCache(GetCurrentProcess(),(void*)at,size);
 VirtualProtect((void*)at,size,old,&unused);return 1;
}
static int install(const Host*h){unsigned i,j,n=sizeof(hooks)/sizeof(hooks[0]),priorTerrain=0;wchar_t marker[MAX_PATH];DWORD old;
 if(!h||h->api!=1||n>MAX_HOOKS||wcslen(h->gameDir)>MAX_PATH-40)return 1;
 swprintf(marker,L"%ls\\paws_runtime.marker",h->gameDir);if(GetFileAttributesW(marker)==INVALID_FILE_ATTRIBUTES)return 1;
 owner=h;base=h->exeBase;
 for(i=0;i<n;i++){
  unsigned char expected[8];memcpy(expected,hooks[i].before,hooks[i].size);
  if(hooks[i].pointer)*(unsigned*)expected+=base-0x460000;
  if(memcmp((void*)(base+hooks[i].site),expected,hooks[i].size)){
#ifdef INSTALLED_RIVERS
   if(hooks[i].site==0x25697a&&*(unsigned char*)(base+hooks[i].site)==0xe8){
    MEMORY_BASIC_INFORMATION info;priorTerrain=base+hooks[i].site+5+*(int*)(base+hooks[i].site+1);
    if(!VirtualQuery((void*)priorTerrain,&info,sizeof(info))||info.State!=MEM_COMMIT||!(info.Protect&0xf0)||*(unsigned short*)priorTerrain!=0x609c){h->log("bridges","installed terrain chain rejected");return 1;}
    memcpy(expected,(void*)(base+hooks[i].site),hooks[i].size);
   }else
#endif
   {h->log("bridges","guard rejected site %X",hooks[i].site);return 1;}
  }
  memcpy(oldBytes[i],expected,hooks[i].size);
 }
 cave=(unsigned)VirtualAlloc(0,ALLOCATION,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);if(!cave)return 1;
 memcpy((void*)cave,payload,sizeof(payload));
 for(i=0;i<sizeof(fixups)/sizeof(fixups[0]);i++)P(cave,fixups[i].offset)+=fixups[i].image*(base-0x460000)+fixups[i].cave*(cave-0x10000000);
 P(cave,STATE)=base;P(cave,STATE+4)=cave+ADAPTER;
 P(cave,STATE+72)=priorTerrain;
 P(cave,UISTATE)=base;P(cave,UISTATE+4)=1;

 P(cave,ROADSTATE)=base;P(cave,ROADSTATE+4)=cave+ADAPTER;P(cave,ROADSTATE+8)=1;
 /* .text and wrappers are RX; TCC's mutable .data and the job state stay RW. */
 for(i=0;i<sizeof(executable)/sizeof(executable[0]);i++)if(!VirtualProtect((void*)(cave+executable[i][0]),executable[i][1],PAGE_EXECUTE_READ,&old))goto fail;
 FlushInstructionCache(GetCurrentProcess(),(void*)cave,sizeof(payload));
 ((void(*)(unsigned))(cave+ROAD_BIND))(cave+ROADSTATE);
#ifdef MAP_SETTINGS
 swprintf(settingsPath,L"%ls\\Mods\\PawsMapSettings.ini",h->gameDir);
 ((void(*)(unsigned,unsigned,unsigned))(cave+MAP_SETTINGS))(cave+UISTATE,(unsigned)map_get,(unsigned)map_put);
#endif
 for(i=0;i<n;i++){
  unsigned char patch[8];memset(patch,0x90,sizeof(patch));
  if(hooks[i].pointer)*(unsigned*)patch=cave+hooks[i].entry;
  else{patch[0]=0xe8;*(unsigned*)(patch+1)=cave+hooks[i].entry-(base+hooks[i].site+5);}
  if(!write_hook(base+hooks[i].site,patch,hooks[i].size)){
   for(j=0;j<i;j++)write_hook(base+hooks[j].site,oldBytes[j],hooks[j].size);
   goto fail;
  }
 }
 h->log("bridges","READY %u hooks, code %X, state %X",n,cave,cave+ROADSTATE);return 0;
fail:
 VirtualFree((void*)cave,0,MEM_RELEASE);cave=0;return 1;
}
__declspec(dllexport) int __cdecl K2Plugin_Start(const Host*h){
#ifdef INSTALLED_RIVERS
 wchar_t marker[MAX_PATH];if(!h||h->api!=1||wcslen(h->gameDir)>MAX_PATH-40)return 1;
 swprintf(marker,L"%ls\\paws_runtime.marker",h->gameDir);if(GetFileAttributesW(marker)==INVALID_FILE_ATTRIBUTES)return 1;
 owner=h;base=h->exeBase;deferred=1;h->log("bridges","waiting for the installed runtime readiness");return 0;
#else
 return install(h);
#endif
}
static int ready(void){
 if(installing)return 0;
#ifdef INSTALLED_RIVERS
 if(!cave&&deferred==1){FILETIME creation,exit,kernel,user;ULARGE_INTEGER ticks;wchar_t name[160];HANDLE event;
  if(!GetProcessTimes(GetCurrentProcess(),&creation,&exit,&kernel,&user))return 0;
  ticks.LowPart=creation.dwLowDateTime;ticks.HighPart=creation.dwHighDateTime;ticks.QuadPart+=504911232000000000ULL;
  swprintf(name,L"Local\\PawPresentationReady-%lu-%I64u",GetCurrentProcessId(),ticks.QuadPart);
  event=OpenEventW(SYNCHRONIZE,FALSE,name);if(!event)return 0;
  if(WaitForSingleObject(event,0)!=WAIT_OBJECT_0){CloseHandle(event);return 0;}CloseHandle(event);
  deferred=2;installing=1;if(install(owner)){deferred=3;owner->log("bridges","installed extension rejected; original runtime preserved");}installing=0;
 }
#endif
 return cave!=0;
}
#ifdef PAWS_BRIDGE_QA
static unsigned serial;static DWORD sampled;static int busy;
typedef void*(FC *StringFn)(void*,void*,const wchar_t*);
typedef void(FC *RunFn)(void*,void*,void*,int);
typedef void(FC *ReleaseFn)(void*,void*);
static void run(const char*command){wchar_t wide[2048],*text=0;unsigned console;
 console=P(base,*(unsigned*)(base+0x13df08)-base);if(!console)return;
 if(mbstowcs(wide,command,2047)==(size_t)-1)return;wide[2047]=0;
 ((StringFn)(base+0x205de))(&text,0,wide);
 if(text){((RunFn)(base+0x1f9963))((void*)console,0,&text,0);((ReleaseFn)(base+0x21375))((char*)text-16,0);}
}
#ifdef RIVER_DISPATCH
static void river_action(unsigned operation,unsigned value){
 unsigned menu=((unsigned(*)(unsigned,unsigned,unsigned))(cave+RIVER_MENU))(cave+UISTATE,operation,value);
 if(menu)((void(FC*)(unsigned,unsigned,unsigned))(cave+RIVER_DISPATCH))(menu,0,0);
}
#endif
static void snapshot(void){FILE*f=fopen("Mods/bridge-state.tmp","wb");unsigned world=P(base,0x5f3fb8),reg=P(base,0x5ef72c),i,k,n,table=P(base,0x5efa8c),count=table?P(table,0x28):0,first=1;
 if(!f)return;
#ifdef RIVER_MENU
 fprintf(f,"{\"generator\":{\"shape\":%u,\"seed\":%u,\"width\":%u,\"height\":%u,\"result\":%u,\"phase\":%u,\"rivers\":%u,\"riverCells\":%u},\"riverMenu\":{\"self\":%u,\"maximum\":%u,\"selected\":%u},",P(cave,STATE+16),P(cave,STATE+20),P(cave,STATE+24),P(cave,STATE+28),P(cave,STATE+32),P(cave,STATE+52),P(cave,STATE+64),P(cave,STATE+68),((unsigned(*)(unsigned,unsigned,unsigned))(cave+RIVER_MENU))(cave+UISTATE,0,0),((unsigned(*)(unsigned,unsigned,unsigned))(cave+RIVER_MENU))(cave+UISTATE,4,0),((unsigned(*)(unsigned,unsigned,unsigned))(cave+RIVER_MENU))(cave+UISTATE,5,0));
 fprintf(f,"\"pid\":%lu,\"serial\":%u,\"mode\":%u,\"world\":%u,\"time\":%.3f,\"painted\":%u,\"completed\":%u,\"rejected\":%u,\"built\":%u,\"failed\":%u,\"resources\":[",GetCurrentProcessId(),serial,P(base,0x5f9218),world,world?F(world,0xe8):0,P(cave,ROADSTATE+24),P(cave,ROADSTATE+20),P(cave,ROADSTATE+28),P(cave,ROADSTATE+((unsigned(*)(unsigned))(cave+FIELD))(4)),P(cave,ROADSTATE+((unsigned(*)(unsigned))(cave+FIELD))(5)));
#else
 fprintf(f,"{\"pid\":%lu,\"serial\":%u,\"mode\":%u,\"world\":%u,\"time\":%.3f,\"painted\":%u,\"completed\":%u,\"rejected\":%u,\"built\":%u,\"failed\":%u,\"resources\":[",GetCurrentProcessId(),serial,P(base,0x5f9218),world,world?F(world,0xe8):0,P(cave,ROADSTATE+24),P(cave,ROADSTATE+20),P(cave,ROADSTATE+28),P(cave,ROADSTATE+((unsigned(*)(unsigned))(cave+FIELD))(4)),P(cave,ROADSTATE+((unsigned(*)(unsigned))(cave+FIELD))(5)));
#endif
 if(table&&count<=16)for(i=0;i<count;i++){unsigned rd=P(P(table,0x24),i*4);fprintf(f,"%s\"%ls\"",i?",":"",(wchar_t*)P(rd,8));}
 fprintf(f,"],\"riverRepairs\":%u,\"riverGaps\":%u,\"preview\":{\"count\":%u,\"valid\":%u},\"extra\":[",P(cave,STATE+76),P(cave,STATE+80),P(cave,ROADSTATE+((unsigned(*)(unsigned))(cave+FIELD))(10)),P(cave,ROADSTATE+((unsigned(*)(unsigned))(cave+FIELD))(10)+4));
 fprintf(f,"],\"gameInterface\":%u,\"error\":%u,\"actors\":[",P(cave,ROADSTATE+((unsigned(*)(unsigned))(cave+FIELD))(9)),P(cave,ROADSTATE+((unsigned(*)(unsigned))(cave+FIELD))(6)));
 if(world&&reg&&P(base,0x5f9218)==2)for(i=1;i<65536;i++){
  unsigned a=P(reg,0x20004+i*4),def,org,elementFirst=1;wchar_t*name;
  if(!a||P(a,0)!=base+0x4e5c58||(P(a,8)&3)||!(def=P(a,4)))continue;
  name=(wchar_t*)P(def,8);org=P(a,0x7c);
  if(!name||(!org&&wcsncmp(name,L"paws_bridge_",12)))continue;
  fprintf(f,"%s{\"id\":%u,\"name\":\"%ls\",\"owner\":%u,\"x\":%.3f,\"y\":%.3f,\"z\":%.3f,\"economy\":%u,\"elements\":[",first?"":",",P(a,0x14),name,P(a,0xe8),F(a,0x20),F(a,0x24),F(a,0x28),P(a,0x84));first=0;
  if(org&&P(org,0x2c)<64)for(k=0;k<P(org,0x2c);k++){
   unsigned u=P(P(org,0x28),k*4),ud=u?P(u,4):0;
   if(u&&ud){fprintf(f,"%s{\"id\":%u,\"name\":\"%ls\",\"x\":%.3f,\"y\":%.3f,\"z\":%.3f}",elementFirst?"":",",P(u,0x14),(wchar_t*)P(ud,8),F(u,0x20),F(u,0x24),F(u,0x28));elementFirst=0;}
  }
  fprintf(f,"]}");
 }
 fprintf(f,"],\"kingdoms\":[");first=1;
 if(world&&P(base,0x5f9218)==2&&(n=P(world,0x154))<=96&&count<=16)for(i=0;i<n;i++){
  unsigned kingdom=P(P(world,0x150),i*4),nation=kingdom?P(kingdom,0x240):0,pr=kingdom?P(kingdom,0x1a8):0,up=kingdom?P(kingdom,0x1c0):0;
  if(!kingdom||!nation||!pr||!up)continue;
  fprintf(f,"%s{\"ptr\":%u,\"id\":%u,\"nation\":\"%ls\",\"upkeep\":[",first?"":",",(unsigned)kingdom,P(kingdom,0x14),(wchar_t*)P(nation,8));first=0;
  for(k=0;k<count;k++)fprintf(f,"%s%.3f",k?",":"",F(up,k*4));
  fprintf(f,"],\"production\":[");for(k=0;k<count;k++)fprintf(f,"%s%.3f",k?",":"",F(pr,k*4));fprintf(f,"]}");
 }
 fprintf(f,"]}");fclose(f);MoveFileExA("Mods/bridge-state.tmp","Mods/bridge-state.json",MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH);
}
__declspec(dllexport) void __cdecl K2Plugin_Tick(void){FILE*f;char text[2048],*command;unsigned request,id,x0,y0,x1,y1,n,i,points[32];float x,y;
 if(busy||!ready())return;busy=1;
 if(GetTickCount()-sampled<200){busy=0;return;}sampled=GetTickCount();
 f=fopen("Mods/bridge-command.txt","rb");
 if(f){unsigned size=fread(text,1,sizeof(text)-1,f);fclose(f);text[size]=0;request=(unsigned)strtoul(text,&command,10);
  if(request>serial){serial=request;while(*command==' ')command++;
#ifdef FIXTURE_FIELD
   if(!strcmp(command,"!peace-fixture"))P(cave,ROADSTATE+((unsigned(*)(void))(cave+FIXTURE_FIELD))())=2;else
   if(!strcmp(command,"!river-fixture"))P(cave,ROADSTATE+((unsigned(*)(void))(cave+FIXTURE_FIELD))())=1;else
#endif
#ifdef ART_REQUEST
   {unsigned wood;
   if(sscanf(command,"!art %u %u %u %u %u %u",&id,&wood,&x0,&y0,&x1,&y1)==6){
    n=(unsigned)(abs((int)x1-(int)x0)+abs((int)y1-(int)y0)+1);
    if(wood<=1&&(x0==x1||y0==y1)&&n>=5&&n<=32){for(i=0;i<n;i++)points[i]=(x0+(x1>x0?i:x1<x0?-(int)i:0))|((y0+(y1>y0?i:y1<y0?-(int)i:0))<<16);
     ((unsigned(*)(unsigned,unsigned,unsigned*,unsigned,unsigned))(cave+ART_REQUEST))(cave+ROADSTATE,id,points,n,wood);}
   }else
#endif
   if(sscanf(command,"!ai-probe %u %u",&x0,&y0)==2){DWORD started=GetTickCount();FILE*report;
    n=((unsigned(*)(unsigned,int,int,unsigned*))(cave+AUTO_CHECK))(cave+ROADSTATE,(int)x0,(int)y0,points);
    report=fopen("Mods/ai-probe.json","wb");if(report){fprintf(report,"{\"x\":%u,\"y\":%u,\"milliseconds\":%lu,\"points\":[",x0,y0,(unsigned long)(GetTickCount()-started));for(i=0;i<n;i++)fprintf(report,"%s%u",i?",":"",points[i]);fprintf(report,"]}");fclose(report);}
   }else if(sscanf(command,"!bridge %u %u %u %u %u",&id,&x0,&y0,&x1,&y1)==5||sscanf(command,"!owner %u %u %u %u %u",&id,&x0,&y0,&x1,&y1)==5){
    n=(unsigned)(abs((int)x1-(int)x0)+abs((int)y1-(int)y0)+1);
    if((x0==x1||y0==y1)&&n>=5&&n<=32){for(i=0;i<n;i++)points[i]=(x0+(x1>x0?i:x1<x0?-(int)i:0))|((y0+(y1>y0?i:y1<y0?-(int)i:0))<<16);
     ((unsigned(*)(unsigned,unsigned,unsigned*,unsigned))(cave+(command[1]=='o'?OWNER_REQUEST:REQUEST)))(cave+ROADSTATE,id,points,n);}
   }else if(sscanf(command,"!preview %f %f %u",&x,&y,&id)==3)((unsigned(*)(unsigned,float,float,unsigned))(cave+PREVIEW))(cave+ROADSTATE,x,y,id);
   else if(sscanf(command,"!attack %u %u",&id,&x0)==2)((unsigned(*)(unsigned,unsigned,unsigned))(cave+ATTACK_REQUEST))(cave+ROADSTATE,id,x0);
   else if(sscanf(command,"!health %u %f",&id,&x)==2)((unsigned(*)(unsigned,unsigned,float))(cave+HEALTH_REQUEST))(cave+ROADSTATE,id,x);
   else if(sscanf(command,"!npc-attack %u %u",&id,&x0)==2)((unsigned(*)(unsigned,unsigned,unsigned,float,float))(cave+ACTOR_FIXTURE))(cave+ROADSTATE,id,0,(float)x0,0);
   else if(sscanf(command,"!relocate %u %f %f",&id,&x,&y)==3)((unsigned(*)(unsigned,unsigned,unsigned,float,float))(cave+ACTOR_FIXTURE))(cave+ROADSTATE,id,1,x,y);
   else if(sscanf(command,"!site %u %f %f",&id,&x,&y)==3)((unsigned(*)(unsigned,unsigned,unsigned,float,float))(cave+ACTOR_FIXTURE))(cave+ROADSTATE,id,2,x,y);
   else if(sscanf(command,"!rapid %u %f",&id,&x)==2)((unsigned(*)(unsigned,unsigned,unsigned,float,float))(cave+ACTOR_FIXTURE))(cave+ROADSTATE,id,3,x,0);
   else if(sscanf(command,"!raze %u",&id)==1)((unsigned(*)(unsigned,unsigned,unsigned,float,float))(cave+ACTOR_FIXTURE))(cave+ROADSTATE,id,4,0,0);
   else if(sscanf(command,"!repair %u %u",&id,&x0)==2)((unsigned(*)(unsigned,unsigned,unsigned,float,float))(cave+ACTOR_FIXTURE))(cave+ROADSTATE,id,5,(float)x0,0);
   else if(sscanf(command,"!queue-move %u %f %f",&id,&x,&y)==3)((unsigned(*)(unsigned,unsigned,unsigned,float,float))(cave+ACTOR_FIXTURE))(cave+ROADSTATE,id,6,x,y);
   else if(sscanf(command,"!move %u %f %f",&id,&x,&y)==3)((unsigned(*)(unsigned,unsigned,float,float))(cave+MOVE))(cave+ROADSTATE,id,x,y);
   else if(sscanf(command,"!npc-move %u %f %f",&id,&x,&y)==3)((unsigned(*)(unsigned,unsigned,float,float))(cave+MOVE_FIXTURE))(cave+ROADSTATE,id,x,y);
   else {
#ifdef RIVER_MENU
    if(sscanf(command,"!rivers %u",&id)==1)river_action(1,id);
    else if(sscanf(command,"!mapsize %u",&id)==1)river_action(2,id);
    else if(sscanf(command,"!mapprofile %u",&id)==1)river_action(3,id);
    else if(sscanf(command,"!shape %u",&id)==1)river_action(6,id);
    else if(sscanf(command,"!fog %u",&id)==1)river_action(7,id);
    else run(command);
#else
    run(command);
#endif
   }
#ifdef ART_REQUEST
   }
#endif
   owner->log("bridges-qa","request %u: %s",serial,command);
  }
 }
 snapshot();busy=0;
}
#else
__declspec(dllexport) void __cdecl K2Plugin_Tick(void){ready();}
#endif
