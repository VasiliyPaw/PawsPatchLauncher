#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>
#include <math.h>
#include <stdlib.h>
#define U unsigned
#define P(a,o) (*(U*)((uintptr_t)(a)+(o)))
#define F(a,o) (*(float*)((uintptr_t)(a)+(o)))
#define B(a,o) (*(unsigned char*)((uintptr_t)(a)+(o)))
#define FAST __attribute__((fastcall))
typedef U (FAST *M0)(U,U);
typedef U (FAST *M1)(U,U,U);
typedef U (FAST *M2)(U,U,U,U);
typedef U (FAST *M4)(U,U,U,U,U,U);
typedef struct {U api;uintptr_t exeBase;const wchar_t*gameDir,*modsDir;void(__cdecl*log)(const char*,const char*,...);}Host;
#include "policy.h"
static const Host*host;static U image,world;static float clock_;static int installed,enabled=1;
static Alert alerts[ALERT_COUNT];static U impacts,registered,retained,expired,serial;static DWORD sampled;
static U m0(U rva,U self){return ((M0)(image+rva))(self,0);}
static U m1(U rva,U self,U arg){return ((M1)(image+rva))(self,0,arg);}
static U v0(U self,U offset){return ((M0)P(P(self,0),offset))(self,0);}
static U v1(U self,U offset,U arg){return ((M1)P(P(self,0),offset))(self,0,arg);}
static U actor(U id){U reg=P(image,0x5ef72c);return reg&&id?m1(0x21117,reg,id):0;}
static int alive(U a){return a&&!(P(a,8)&3);}
static U source_company(U a){U c=m0(0x20de66,a);return c&&(m0(0x20780a,a)&255)?c:a;}
static int civil(U home){U city=m0(0x2282d0,home);return city&&P(city,0x98)!=0;}
static void epoch(void){U w=P(image,0x5f3fb8);float now=w?F(w,0xe8):0;
 if(w!=world||now<clock_){memset(alerts,0,sizeof(alerts));world=w;}clock_=now;
}
static Alert*find(U home,U target){U i;for(i=0;i<ALERT_COUNT;i++)if(alerts[i].home==home&&alerts[i].target==target)return &alerts[i];return 0;}
static int active(Alert*a,U den,U target){U home=P(den,4);
 if(!enabled||!world||!alive(home)||!alive(target)||!B(den,0x20)||!civil(home))return 0;
 if(a->owner!=v0(home,0x108)||a->enemy!=v0(target,0x108))return 0;
 if(!(v1(target,0x140,a->owner)&255))return 0;
 return alert_position(a,F(home,0x20),F(home,0x24),F(target,0x20),F(target,0x24),clock_);
}
/* Replaces only the guard-radius test made by TickGuard. All later native
 * alive/hostility/visibility/member checks, and normal list removal remain. */
static U FAST keep_intruder(U den,U unused,U target){Alert*a;U native=m1(0x20c140,den,target);
 epoch();if(native&255)return native;
 a=find(P(P(den,4),0x14),target?P(target,0x14):0);
 if(a&&active(a,den,target)){retained++;return 1;}
 if(a)expired++;
 return native;
}
/* Called by BodyComponent::DealDamage after real damage is applied. The stock
 * helper resolves settlement children/walls to the owning center beforehand. */
static U FAST on_damage(U den,U unused,U damage){U source,home,owner,enemy,i;Alert*a=0;float dx,dy,r,normal;
 m1(0x20a558,den,damage);epoch();impacts++;
#ifdef MILITIA_QA
 if(damage&&F(damage,12)>0&&P(P(den,4),0x14)==52){FILE*f=fopen("Mods/siege-hits.jsonl","ab");U src=actor(P(damage,0)),company=src?m0(0x20de66,src):0;
  if(f){fprintf(f,"{\"time\":%.4f,\"home\":52,\"source\":%u,\"company\":%u,\"damage\":%.3f}\n",clock_,P(damage,0),company?P(company,0x14):0,F(damage,12));fclose(f);}}
#endif
 if(!enabled||!damage||!number(F(damage,12))||F(damage,12)<=0)return 0;
 home=P(den,4);if(!alive(home)||!B(den,0x20)||!civil(home))return 0;
 source=actor(P(damage,0));if(!alive(source))return 0;source=source_company(source);
 if(!alive(source)||!(P(source,8)&0x4000))return 0;
 owner=v0(home,0x108);enemy=v0(source,0x108);
 if(!owner||owner==enemy||!(v1(source,0x140,owner)&255))return 0;
 if(m1(0x20c140,den,source)&255)return 0;
 normal=F(P(home,4),0x368);if(!number(normal)||normal<=0)return 0;
 dx=F(source,0x20)-F(home,0x20);dy=F(source,0x24)-F(home,0x24);
 r=(float)sqrt(dx*dx+dy*dy);if(!number(r)||r>normal+MAX_EXTRA_RANGE)return 0;
 a=find(P(home,0x14),P(source,0x14));
 if(a&&a->owner==owner&&a->enemy==enemy&&clock_>=a->last&&clock_-a->last<=ALERT_LIFETIME){
  /* Refresh time, never the first engagement's distance cap. */
  if(!active(a,den,source))return 0;a->last=clock_;
 }else{
  if(!a)for(i=0;i<ALERT_COUNT;i++)if(!alerts[i].home||clock_<alerts[i].last||clock_-alerts[i].last>ALERT_LIFETIME){a=&alerts[i];break;}
  if(!a)return 0;
  a->home=P(home,0x14);a->target=P(source,0x14);a->owner=owner;a->enemy=enemy;
  a->x=F(source,0x20);a->y=F(source,0x24);a->limit2=sq(r+RETREAT_ALLOWANCE);a->last=clock_;
 }
 /* Native OnIntruder validates diplomacy/visibility and de-duplicates IDs. */
 m1(0x20a591,den,source);
 {U node=P(den,0x24),count=0;while(node&&count++<4096){if(P(node,0)==P(source,0x14)){registered++;return 1;}node=P(node,4);}}
 a->home=0;
 return 1;
}
typedef struct{U site,target;void*replacement;unsigned char old[5];}Hook;
static Hook hooks[2]={{0x202b98,0x20a558,on_damage,{0}},{0x20ad68,0x20c140,keep_intruder,{0}}};
static int patch(U at,const void*bytes){DWORD old,unused;if(!VirtualProtect((void*)at,5,PAGE_EXECUTE_READWRITE,&old))return 0;memcpy((void*)at,bytes,5);FlushInstructionCache(GetCurrentProcess(),(void*)at,5);VirtualProtect((void*)at,5,old,&unused);return !memcmp((void*)at,bytes,5);}
static int install(void){U i,j;unsigned char bytes[5];
 for(i=0;i<2;i++){U at=image+hooks[i].site;bytes[0]=0xe8;P(bytes,1)=hooks[i].target-hooks[i].site-5;
  if(memcmp((void*)at,bytes,5)){host->log("militia","guard rejected RVA %X",hooks[i].site);return 0;}memcpy(hooks[i].old,bytes,5);}
 for(i=0;i<2;i++){bytes[0]=0xe8;P(bytes,1)=(U)hooks[i].replacement-(image+hooks[i].site+5);
  if(!patch(image+hooks[i].site,bytes)){for(j=0;j<=i;j++)patch(image+hooks[j].site,hooks[j].old);return 0;}}
 host->log("militia","READY r1: retaliation only, 6-unit retreat allowance, 30-second idle expiry");return 1;
}
__declspec(dllexport)int __cdecl K2Plugin_Start(const Host*h){wchar_t marker[MAX_PATH];
 if(!h||h->api!=1||wcslen(h->gameDir)>MAX_PATH-40)return 1;
 swprintf(marker,L"%ls\\paws_runtime.marker",h->gameDir);if(GetFileAttributesW(marker)==INVALID_FILE_ATTRIBUTES)return 1;
 host=h;image=h->exeBase;return 0;
}
/* Disposable single-player fixture controls only; never installed/published. */
#ifdef MILITIA_QA
static U kingdom(U id){U i,n=P(world,0x154);if(n>96)return 0;for(i=0;i<n;i++){U p=P(P(world,0x150),i*4);if(p&&P(p,0x14)==id)return p;}return 0;}
#include "siege/fixture.h"
static void qa(void){FILE*f;U request,id,source,a,den;float amount,x,y;char cmd[128],name[80];
 f=fopen("Mods/militia-command.txt","rb");if(!f)return;
 if(fscanf(f,"%u %127[^\n]",&request,cmd)!=2||request<=serial){fclose(f);return;}fclose(f);serial=request;
 if(sscanf(cmd,"enabled %u",&id)==1){enabled=id?1:0;memset(alerts,0,sizeof(alerts));}
 if(!world||!P(image,0x5f3fe4)||B(P(image,0x5f3fe4),0x100))return;
 siege_fixture(cmd);
 if(sscanf(cmd,"spawn %79s %u %f %f",name,&id,&x,&y)==4&&kingdom(id)){
  U key=0,ctx[24],def;wchar_t wide[80];mbstowcs(wide,name,79);wide[79]=0;
  m1(0x205de,(U)&key,(U)wide);def=m1(0x2edb9,P(P(image,0x5f3fb4),0xc),key);
  if(def){memset(ctx,0,sizeof(ctx));m0(0x91a87,(U)ctx);ctx[1]=def;F(ctx,8)=x;F(ctx,12)=y;F(ctx,20)=1;ctx[10]=kingdom(id);
   a=m1(0x242eee,world,(U)ctx);host->log("militia-qa","spawn %s: actor %u",name,a?P(a,0x14):0);}
  else host->log("militia-qa","unknown spawn definition %s",name);
  if(key)m0(0x21375,key-16);
 }
 if(sscanf(cmd,"damage %u %u %f",&id,&source,&amount)==3&&(a=actor(id))!=0&&actor(source)&&amount>0&&amount<100){
  U data[7];U src=actor(source),kingdom=v0(src,0x108);memset(data,0,sizeof(data));data[0]=source;data[1]=kingdom?P(kingdom,0x14):0;F(data,12)=amount;data[5]=1;
  ((M4)(image+0x20285b))(P(a,0x60),0,(U)data,0,0,1);
 }
 if(sscanf(cmd,"toggle %u %u",&id,&source)==2&&(a=actor(id))!=0&&(den=P(a,0x88))!=0){
  /* Explicit single-player fixture state, never done by the gameplay hooks. */
  B(den,0x20)=source?1:0;
 }
 host->log("militia-qa","request %u: %s",request,cmd);
}
#endif
__declspec(dllexport)void __cdecl K2Plugin_Tick(void){
#ifdef MILITIA_QA
 FILE*f;U i;
#endif
 if(!installed){installed=install()?1:-1;return;}if(installed<0)return;
 if(GetTickCount()-sampled<200)return;sampled=GetTickCount();
 epoch();
#ifdef MILITIA_QA
 /* Private QA runs alongside another independently owned game. This is the
  * native RunWhenInactive setting (Settings[0x33]), not a world/sim patch. */
 if(world){U cfg=P(image,0x5f9480);if(cfg&&P(cfg,0xcc))B(P(cfg,0xcc),0)=1;if(cfg&&P(cfg,0x37c))B(P(cfg,0x37c),0)=0;}
 qa();
 f=fopen("Mods/militia-state.tmp","wb");if(!f)return;
 fprintf(f,"{\"pid\":%lu,\"serial\":%u,\"enabled\":%d,\"time\":%.3f,\"impacts\":%u,\"registered\":%u,\"retained\":%u,\"expired\":%u,\"alerts\":[",GetCurrentProcessId(),serial,enabled,clock_,impacts,registered,retained,expired);
 {int first=1;for(i=0;i<ALERT_COUNT;i++)if(alerts[i].home){Alert*a=&alerts[i];fprintf(f,"%s{\"home\":%u,\"target\":%u,\"limit2\":%.3f,\"last\":%.3f}",first?"":",",a->home,a->target,a->limit2,a->last);first=0;}}
 fprintf(f,"]}");fclose(f);MoveFileExA("Mods/militia-state.tmp","Mods/militia-state.json",MOVEFILE_REPLACE_EXISTING);
#endif
}
