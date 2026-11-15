/* Private 1.3.72 siege r6. Supplement native frontal-wall targeting, retain
 * individual city orders in group support, and recover lost group orders. */
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <wchar.h>
#include <string.h>
#include <math.h>
#include "geometry.h"
#define U unsigned
#define P(a,o) (*(U*)((uintptr_t)(a)+(o)))
#define B(a,o) (*(unsigned char*)((uintptr_t)(a)+(o)))
#define F(a,o) (*(float*)((uintptr_t)(a)+(o)))
#define FAST __attribute__((fastcall))
typedef U(FAST*M0)(U,U);typedef U(FAST*M1)(U,U,U);typedef U(FAST*M2)(U,U,U,U);
typedef struct{U api;uintptr_t exeBase;const wchar_t*gameDir,*modsDir;void(__cdecl*log)(const char*,const char*,...);}Host;
static U image,calls,admitted,wallAdded,engaged,kept,rescued;static const Host*host;static int installed,enabled=1,wallEnabled=1;static DWORD sampled;
static U m0(U rv,U a){return((M0)(image+rv))(a,0);}static U m1(U rv,U a,U b){return((M1)(image+rv))(a,0,b);}
static U actor(U id){U r=P(image,0x5ef72c);return r&&id?m1(0x21117,r,id):0;}
static U v0(U a,U off){return((M0)P(P(a,0),off))(a,0);}
static U command_kind(U c){return c&&P(c,8)?P(P(c,8),12):~0u;}
static int same_attack(U c,U target){return command_kind(c)==5&&(P(c,12)&0x41)==0x41&&P(c,16)==target;}
static U city_attack(U g){U c=P(g,0x1ac),a,home;
 if(command_kind(c)!=5||(P(c,12)&0x41)!=0x41)return 0;a=actor(P(c,16));
 if(!a||(P(a,8)&3)||P(a,0x90))return 0;home=m0(0x2282d0,a);
 return home&&P(home,0x98)&&P(P(home,0x98),0x28)?P(c,16):0;
}
static void FAST support_combat(U g,U unused){U id,i,a,mind,head,state;
 if(enabled&&P(g,0x1c0)==2&&(id=city_attack(g))!=0&&P(g,0x194)<=256){
  /* Native path failure may leave a still-grouped city attacker asleep with
   * no command, outside the cached movement cohort. Re-deliver only the
   * group's retained user order, on the existing native support cadence. */
  for(i=0;i<P(g,0x194)&&i<256;i++){
   a=actor(P(P(g,0x190),16*i));mind=a?P(a,0x70):0;
   if(!mind||(P(a,8)&3)||P(a,0x168)!=P(g,0x14)||P(mind,0x20)||P(mind,0x108)!=id)continue;
   head=P(mind,0x10);state=head?P(head,0):0;
   if(state&&P(state,0)==image+0x4f4d98){rescued++;((M2)(image+0x232cca))(g,0,i,g+0x1ac);}
  }
 }
 m0(0x232552,g);
}
static U FAST keep_attack(U g,U unused,U index,U incoming){U id,a,mind,c;
 if(enabled&&(id=city_attack(g))!=0&&index<P(g,0x194)){
  a=actor(P(P(g,0x190),index*16));mind=a?P(a,0x70):0;
  if(mind&&P(a,0x168)==P(g,0x14)){
   c=P(mind,0x20);if(same_attack(c,id)){kept++;return 1;}
   if(!c){rescued++;return((M2)(image+0x232cca))(g,0,index,g+0x1ac);}
  }
 }
 return((M2)(image+0x232cca))(g,0,index,incoming);
}
static U FAST group_combat(U g,U unused){U native=m0(0x233035,g),cmd,target,home,n,i,a,mind,current;
 calls++;if((native&255)||!enabled||P(g,0x1c0)!=1)return native;
 cmd=P(g,0x1ac);if(command_kind(cmd)!=5||(P(cmd,12)&0x41)!=0x41)return native;
 target=P(cmd,16);a=actor(target);if(!a||(P(a,8)&3)||P(a,0x90))return native;
 home=m0(0x2282d0,a);if(!home||!P(home,0x98)||P(P(home,0x98),0x28)==0)return native;
 n=P(g,0x194);if(!n||n>256||!P(g,0x190))return native;
 for(i=0;i<n;i++){
  a=actor(P(P(g,0x190),i*16));if(!a||(P(a,8)&3)||P(a,0x168)!=P(g,0x14)||!(P(a,0x100)&0x10)||!P(a,0x7c)||(mind=P(a,0x70))==0)continue;
  if(!same_attack(P(mind,0x20),target))continue;
  /* Native target resolution, including the active Siege state and walls;
   * do not inspect stale target slots or start combat from proximity alone. */
  current=v0(mind,0x4c);if(!current||(P(current,8)&3))continue;
  if(P(current,0x14)!=target&&(!P(current,0x90)||m0(0x2282d0,current)!=home))continue;
  admitted++;return 1;
 }
 return native;
}
/* The native path-based wall filter can miss a reachable frontal wall. Use
 * native footprint shapes and CanTouch checks to engage a blocking front
 * part without replacing the original city order. Open rays retain native
 * continuation through a breach. No weapon ranges or map flags are changed. */
static void FAST siege_think(U state,U unused){U mind,company,target,home,set,n,i,a,shape,type,best=0,id;float range,dx,dy,d,hit,bestHit=2,hx,hy;
 if(!wallEnabled||P(state,0xc)!=2||B(state,0x20)||B(state,0x21))goto native;
 mind=P(state,4);company=mind?P(mind,4):0;target=actor(P(state,0x10));home=actor(P(state,0x14));
 if(!company||!P(company,0x7c)||!target||(P(target,8)&3)||P(target,0x90)||!home||(set=P(home,0x98))==0)goto native;
 if(m1(0x270f96,state,target)!=home||P(company,0x150)<5||!P(P(company,0x14c),16))goto native;
 range=F(P(P(company,0x14c),16),8);if(!(range>0&&range<256))goto native;
 n=P(set,0x28);if(!n||n>512||!P(set,0x24))goto native;
 for(i=0;i<n;i++){
  a=P(P(set,0x24),4*i);if(!a||(P(a,8)&3)||!P(a,0x90)||!( ((M1)P(P(company,0),0x16c))(company,0,a)&255))continue;
  dx=F(a,0x20)-F(company,0x20);dy=F(a,0x24)-F(company,0x24);d=dx*dx+dy*dy;
  if(d>(range+16)*(range+16))continue;
  shape=v0(a,0xc);if(!shape)continue;type=P(shape,0);hx=F(shape,type==1?4:16);hy=F(shape,20);
  if(!frontage(type,hx,hy,F(a,0x20),F(a,0x24),F(a,0x2c),F(a,0x30),F(company,0x20),F(company,0x24),F(target,0x20),F(target,0x24),&hit)||hit>=bestHit)continue;
  if(!(m1(0x275a71,mind,a)&255))continue;
  best=a;bestHit=hit;
 }
 if(best){U node=P(state,0x18),found=0,count=0;id=P(best,0x14);
  while(node&&count++<1024){if(P(node,0)==id){found=1;break;}node=P(node,4);}
  if(node&&count>=1024)goto native;
  if(!found){m1(0x1e8eb9,state+0x18,(U)&id);wallAdded++;}
  if(((M1)P(P(mind,0),0xf4))(mind,0,best)&255){engaged++;return;}
 }
native:m0(0x270c4b,state);
}
static const U sites[5]={0x2324e5,0x23276b,0x23268d,0x2326d6,0x23195b};
static const U targets[5]={0x233035,0x233035,0x232cca,0x232cca,0x232552};static unsigned char before[5][5];
static int patch_size(U at,const void*bytes,U size){DWORD old,tmp;if(!VirtualProtect((void*)at,size,PAGE_EXECUTE_READWRITE,&old))return 0;memcpy((void*)at,bytes,size);FlushInstructionCache(GetCurrentProcess(),(void*)at,size);VirtualProtect((void*)at,size,old,&tmp);return !memcmp((void*)at,bytes,size);}
static int patch(U at,const void*bytes){return patch_size(at,bytes,5);}
static int install(void){U i,j;unsigned char b[5];
 if(P(image,0x4f4e88)!=image+0x270c4b){host->log("siege","native Siege Think slot mismatch");return 0;}
 for(i=0;i<5;i++){b[0]=0xe8;P(b,1)=targets[i]-sites[i]-5;if(memcmp((void*)(image+sites[i]),b,5)){host->log("siege","guard rejected %X",sites[i]);return 0;}memcpy(before[i],b,5);}
 for(i=0;i<5;i++){b[0]=0xe8;P(b,1)=(U)(i<2?group_combat:i<4?keep_attack:support_combat)-(image+sites[i]+5);if(!patch(image+sites[i],b)){for(j=0;j<=i;j++)patch(image+sites[j],before[j]);return 0;}}
 {U fn=(U)siege_think;if(!patch_size(image+0x4f4e88,&fn,4)){fn=image+0x270c4b;patch_size(image+0x4f4e88,&fn,4);for(j=0;j<5;j++)patch(image+sites[j],before[j]);return 0;}}
 host->log("siege","READY r6: wall frontage, retained city orders, scoped native recovery of asleep group attackers");return 1;
}
__declspec(dllexport)int __cdecl K2Plugin_Start(const Host*h){wchar_t marker[MAX_PATH];if(!h||h->api!=1||wcslen(h->gameDir)>MAX_PATH-40)return 1;swprintf(marker,L"%ls\\paws_runtime.marker",h->gameDir);if(GetFileAttributesW(marker)==INVALID_FILE_ATTRIBUTES)return 1;image=h->exeBase;host=h;return 0;}
#ifdef SIEGE_QA
/* Emulator entry, absent from the user DLL. Exercises these exact functions. */
__declspec(dllexport)U __cdecl qa_entry(U action,U a,U b,U c){
 if(action==0){image=a;enabled=b?1:0;wallEnabled=c?1:0;return 1;}
 if(action==1)return group_combat(a,0);
 if(action==2)return keep_attack(a,0,b,c);
 if(action==3){support_combat(a,0);return 1;}
 if(action==4){siege_think(a,0);return 1;}
 return 0;
}
#endif
__declspec(dllexport)void __cdecl K2Plugin_Tick(void){
 if(!installed){FILETIME creation,exit,kernel,user;ULARGE_INTEGER ticks;wchar_t name[160];HANDLE event;
  if(!GetProcessTimes(GetCurrentProcess(),&creation,&exit,&kernel,&user))return; ticks.LowPart=creation.dwLowDateTime;ticks.HighPart=creation.dwHighDateTime;ticks.QuadPart+=504911232000000000ULL;
  swprintf(name,L"Local\\PawPresentationReady-%lu-%I64u",GetCurrentProcessId(),ticks.QuadPart);event=OpenEventW(SYNCHRONIZE,FALSE,name);if(!event)return;
  if(WaitForSingleObject(event,0)!=WAIT_OBJECT_0){CloseHandle(event);return;}CloseHandle(event);
  installed=install()?1:-1;return;}if(installed<0)return;
#ifdef SIEGE_QA
 if(GetTickCount()-sampled>200){FILE*f;sampled=GetTickCount();enabled=GetPrivateProfileIntA("Siege","Enabled",1,".\\Mods\\siege-qa.ini")?1:0;wallEnabled=GetPrivateProfileIntA("Siege","Walls",1,".\\Mods\\siege-qa.ini")?1:0;
 f=fopen("Mods/siege-state.json","wb");if(f){fprintf(f,"{\"pid\":%lu,\"enabled\":%d,\"wallEnabled\":%d,\"calls\":%u,\"admitted\":%u,\"wallAdded\":%u,\"engaged\":%u,\"kept\":%u,\"rescued\":%u}",GetCurrentProcessId(),enabled,wallEnabled,calls,admitted,wallAdded,engaged,kept,rescued);fclose(f);}}
#endif
}
