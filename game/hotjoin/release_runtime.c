/* Arcane beta runtime. The helper supplies verified paths and the main thread;
 * no laboratory command files, environment switches or loader proxy are used. */
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include <wchar.h>
typedef struct {unsigned magic,features,mainThread,reserved;wchar_t log[MAX_PATH],data[MAX_PATH];} PawHotJoinConfig;
static PawHotJoinConfig releaseConfig;
static wchar_t releaseDocuments[MAX_PATH],releaseGame[MAX_PATH],releaseMods[MAX_PATH];
static DWORD WINAPI release_environment(const wchar_t *name,wchar_t *out,DWORD cap) {
 const wchar_t *value=L"";DWORD length;
 if(!wcscmp(name,L"PAWS_TEST_DOCUMENTS"))value=releaseDocuments;
 else if(!wcscmp(name,L"PAWS_HOTJOIN_LAB"))value=L"coordinated";
 else if(!wcscmp(name,L"PAWS_HOTJOIN_AUTO")||!wcscmp(name,L"PAWS_HOTJOIN_MULTI")||!wcscmp(name,L"PAWS_HOTJOIN_RECOVER"))value=L"1";
 length=(DWORD)wcslen(value);if(cap>length){memcpy(out,value,(length+1)*2);return length;}
 return length+1;
}
#define GetEnvironmentVariableW release_environment
#define PAWS_HOTJOIN_RELEASE 1
#include "../hotjoin-test/lab.c"
#undef GetEnvironmentVariableW

typedef BOOL (WINAPI *PawPeekFn)(MSG*,HWND,UINT,UINT,UINT);
static PawPeekFn releasePeek;
static Host releaseHost;
static DWORD releaseLastTick;
__declspec(dllexport) volatile LONG PawHotJoinFeatures;
__declspec(dllexport) volatile LONG PawSaveBusy;
static void __cdecl release_log(const char *module,const char *format,...) {
 char text[1400];va_list args;SYSTEMTIME t;int n,m;HANDLE file;DWORD written;(void)module;
 GetLocalTime(&t);n=_snprintf(text,sizeof(text),"%04u-%02u-%02u %02u:%02u:%02u hotjoin: ",t.wYear,t.wMonth,t.wDay,t.wHour,t.wMinute,t.wSecond);
 if(n<0)return;va_start(args,format);m=_vsnprintf(text+n,sizeof(text)-n-3,format,args);va_end(args);
 if(m<0)m=(int)sizeof(text)-n-3;n+=m;text[n++]='\r';text[n++]='\n';
 file=CreateFileW(releaseConfig.log,FILE_APPEND_DATA,FILE_SHARE_READ|FILE_SHARE_WRITE,0,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,0);
 if(file==INVALID_HANDLE_VALUE)return;WriteFile(file,text,(DWORD)n,&written,0);CloseHandle(file);
}
static BOOL WINAPI release_peek(MSG *msg,HWND window,UINT first,UINT last,UINT remove) {
 BOOL result=releasePeek(msg,window,first,last,remove);DWORD error=GetLastError(),now=GetTickCount();
 if(GetCurrentThreadId()==mainThread&&now-releaseLastTick>=50){
  releaseLastTick=now;K2Plugin_Tick();
  InterlockedExchange(&PawSaveBusy,(autoStage||hostJoinPending||clientSnapshot)?1:0);
 }
 SetLastError(error);return result;
}
static DWORD release_install(const PawHotJoinConfig *cfg) {
 uintptr_t peb,image;wchar_t *slash;DWORD old,ignored;HMODULE user32;unsigned length;
 if(PawHotJoinFeatures||!cfg||cfg->magic!=0x314a4850u||cfg->features!=1||!cfg->mainThread)return 10;
 memcpy(&releaseConfig,cfg,sizeof(releaseConfig));releaseConfig.log[MAX_PATH-1]=releaseConfig.data[MAX_PATH-1]=0;
 length=(unsigned)wcslen(releaseConfig.data);
 if(length<13||length>=155||_wcsicmp(releaseConfig.data+length-12,L"\\Kohan2\\data"))return 11;
 memcpy(releaseDocuments,releaseConfig.data,(length-12)*2);releaseDocuments[length-12]=0;
 __asm__("movl %%fs:0x30, %0" : "=r"(peb));image=*(uintptr_t*)(peb+8);
 if(*(unsigned short*)image!=0x5a4d)return 12;
 if(!GetModuleFileNameW(0,releaseGame,MAX_PATH)||(slash=wcsrchr(releaseGame,L'\\'))==0)return 13;
 *slash=0;if(wcslen(releaseGame)>MAX_PATH-40)return 14;
 swprintf(releaseMods,L"%ls\\Mods",releaseGame);
 base=image;user32=GetModuleHandleW(L"user32.dll");releasePeek=(PawPeekFn)word(image+0x5d4314);
 if(!user32||(releasePeek!=(PawPeekFn)GetProcAddress(user32,"PeekMessageA")&&releasePeek!=(PawPeekFn)GetProcAddress(user32,"PeekMessageW")))return 15;
 releaseHost.api=1;releaseHost.exeBase=image;releaseHost.gameDir=releaseGame;releaseHost.modsDir=releaseMods;releaseHost.log=release_log;
 notice_init();startPrepared=1;composedMode=1;sessionWriteTarget=image+0x16775c;sessionReadTarget=image+0x16797a;
 if(K2Plugin_Start(&releaseHost))return 20;
 mainThread=cfg->mainThread;
 if(!VirtualProtect((void*)(image+0x5d4314),4,PAGE_READWRITE,&old))return 21;
 *(PawPeekFn*)(image+0x5d4314)=release_peek;
 VirtualProtect((void*)(image+0x5d4314),4,old,&ignored);
 InterlockedExchange(&PawHotJoinFeatures,1);
 release_log("hotjoin","HOTJOIN_READY revision=1 protocol=R; native auth, version and CRC checks retained");return 0;
}
typedef struct {volatile LONG ready,go;DWORD result;PawHotJoinConfig config;} PawHotJoinRequest;
__declspec(dllexport) DWORD WINAPI PawInstallQueued(void *raw) {
 PawHotJoinRequest *request=raw;DWORD result;if(!request)return 30;
 InterlockedExchange(&request->ready,1);while(!request->go)Sleep(1);
 result=release_install(&request->config);request->result=result;
 InterlockedExchange(&request->ready,2);return result;
}
BOOL WINAPI DllMain(HINSTANCE instance,DWORD reason,LPVOID unused){(void)instance;(void)reason;(void)unused;return TRUE;}
