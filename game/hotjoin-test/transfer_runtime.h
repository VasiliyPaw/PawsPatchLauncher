#include "transfer_boundary.h"
#include "r2_payload.h"
#include "r2_guards.h"
static int transferFast=1;
static uintptr_t transferR2;
static int transferSettingsVerified;
#include "composed_runtime.h"
static void transfer_select_fixture(void) {
 wchar_t *text=0;struct {uintptr_t vtable;wchar_t *name;} order={0,0};uintptr_t a=word(base+0x5f3fec);
 if(word(word(base+0x5f3fe4)+0xf0)!=1||word(a+0x2e4)!=a||!transfer_settings_ok())return;
 ((StringFn)(base+0x205de))(&text,0,L"Save/HotJoinBoundary.RSG");if(!text)return;
 ((CreatorSettingsFn)(base+0x121bd0))(&order,0,&text);
 ((BoolFn)(base+0x122822))(&order,0,0);
 if(order.name)((ReleaseFn)(base+0x21375))((char*)order.name-16,0);
 ((ReleaseFn)(base+0x21375))((char*)text-16,0);
 host->log("hotjoin-lab","NATIVE_TRANSFER_FIXTURE_SELECTED stock saved-map order; private lab file only");
}
static int transfer_settings_ok(void) {
 uintptr_t registry=word(base+0x5f94d0);unsigned i;const unsigned values[3]={20,64,256};
 if(!transferFast)return 1;
 for(i=0;i<3;i++)if(!readable(word(registry+0x120+i*4),4)||word(word(registry+0x120+i*4))!=values[i])return 0;
 if(!transferSettingsVerified){transferSettingsVerified=1;host->log("hotjoin-lab","FAST_TRANSFER_R2_LIVE_SETTINGS 20/64/256 verified; original lobby core unchanged");}
 return 1;
}
static int transfer_fast_install(void) {
 unsigned char expected[2048],*code,*site;unsigned i,j,value;int delta;DWORD old,ignored;
 const unsigned rvas[3]={0x151936,0x1500f6,0x1501d1},offsets[3]={0,256,512},sizes[3]={8,7,7};
 wchar_t flag[8]={0};GetEnvironmentVariableW(L"PAWS_HOTJOIN_FAST",flag,8);
 if(flag[0]==L'0')transferFast=0;
 if(composedMode)return composed_r2();
 if(!transferFast)return 1;
 for(i=0;i<sizeof(hj_r2_guards)/sizeof(hj_r2_guards[0]);i++){
  if(hj_r2_guards[i].size>sizeof(expected))return 0;
  memcpy(expected,hj_r2_guards[i].bytes,hj_r2_guards[i].size);
  for(j=0;j<hj_r2_guards[i].count;j++){
   unsigned off=hj_r2_guards[i].fixes[j];memcpy(&value,expected+off,4);value+=(unsigned)base-0x460000u;memcpy(expected+off,&value,4);
  }
  if(memcmp((void*)(base+hj_r2_guards[i].rva),expected,hj_r2_guards[i].size)){
   host->log("hotjoin-lab","FAST_TRANSFER_R2_GUARD_REFUSED rva=%x",hj_r2_guards[i].rva);return 0;
  }
 }
 code=VirtualAlloc(0,8192,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);if(!code)return 0;
 memcpy(code,hj_r2_payload,sizeof(hj_r2_payload));
 for(i=0;i<sizeof(hj_r2_fixes)/sizeof(hj_r2_fixes[0]);i++){
  unsigned off=hj_r2_fixes[i].offset;memcpy(&value,code+off,4);
  value+=hj_r2_fixes[i].image*((unsigned)base-0x400000u)+hj_r2_fixes[i].cave*((unsigned)(uintptr_t)code-0x10000000u);
  memcpy(code+off,&value,4);
 }
 if(!VirtualProtect(code,4096,PAGE_EXECUTE_READ,&old)){VirtualFree(code,0,MEM_RELEASE);return 0;}
 if(!VirtualProtect((void*)(base+0x150000),0x2000,PAGE_EXECUTE_READWRITE,&old)){VirtualFree(code,0,MEM_RELEASE);return 0;}
 for(i=0;i<3;i++){
  site=(unsigned char*)(base+rvas[i]);site[0]=0xe9;delta=(int)((uintptr_t)(code+offsets[i])-(uintptr_t)(site+5));memcpy(site+1,&delta,4);
  for(j=5;j<sizes[i];j++)site[j]=0x90;
 }
 VirtualProtect((void*)(base+0x150000),0x2000,old,&ignored);
 FlushInstructionCache(GetCurrentProcess(),code,4096);FlushInstructionCache(GetCurrentProcess(),(void*)(base+0x150000),0x2000);
 transferR2=(uintptr_t)code;
 host->log("hotjoin-lab","FAST_TRANSFER_R2_READY originalLobbyCoreSha256=%s guards=15; fileBudgetBytes=1200 maxPacketsPerPeerPerPass=16 stopBurstWhenDrained=true receiveAckPerPass=1 stockBandwidthLimits=true",HJ_R2_SOURCE_SHA256);
 return 1;
}
static int transfer_boundary_install(void) {
 static const unsigned char original[2][7]={
  {0x8b,0xc1,0x99,0xf7,0xfe,0x8b,0xf2},
  {0x8b,0xc6,0x99,0xf7,0xff,0x8b,0xfa}
 };
 const unsigned rvas[2]={0x159524,0x1599bf};
 unsigned char *code,*site;unsigned i;int delta;DWORD old,ignored;
 for(i=0;i<2;i++)if(memcmp((void*)(base+rvas[i]),original[i],7))return 0;
 if(!transfer_fast_install())return 0;
 code=VirtualAlloc(0,32,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
 if(!code)return 0;
 for(i=0;i<2;i++){
  unsigned char *stub=code+16*i;
  memcpy(stub,i?hj_transfer_receiver_tail:hj_transfer_sender_tail,11);
  stub[11]=0xe9;delta=(int)(base+rvas[i]+7-(uintptr_t)(stub+16));memcpy(stub+12,&delta,4);
 }
 if(!VirtualProtect(code,32,PAGE_EXECUTE_READ,&old)){
  VirtualFree(code,0,MEM_RELEASE);return 0;
 }
 /* Both native sites are in one page. Preflight and acquire its protection
  * once before changing either, so allocation/protection failure patches none. */
 if(!VirtualProtect((void*)(base+rvas[0]),rvas[1]+7-rvas[0],PAGE_EXECUTE_READWRITE,&old)){
  VirtualFree(code,0,MEM_RELEASE);return 0;
 }
 for(i=0;i<2;i++){
  site=(unsigned char*)(base+rvas[i]);site[0]=0xe9;
  delta=(int)((uintptr_t)(code+16*i)-(uintptr_t)(site+5));memcpy(site+1,&delta,4);site[5]=site[6]=0x90;
 }
 VirtualProtect((void*)(base+rvas[0]),rvas[1]+7-rvas[0],old,&ignored);
 FlushInstructionCache(GetCurrentProcess(),code,32);
 FlushInstructionCache(GetCurrentProcess(),(void*)(base+rvas[0]),rvas[1]+7-rvas[0]);
 host->log("hotjoin-lab","NATIVE_FILE_LAST_BLOCK_FIXED sender and receiver; exact multiples retain full block; native CRC unchanged");
 return 1;
}
