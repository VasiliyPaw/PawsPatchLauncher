/* ANSI x86 declarations; the small bundled TCC SDK omits tlhelp32.h. */
#define TH32CS_SNAPPROCESS 0x2
#define TH32CS_SNAPMODULE 0x8
#define TH32CS_SNAPMODULE32 0x10
typedef struct {
 DWORD dwSize,cntUsage,th32ProcessID; ULONG_PTR th32DefaultHeapID;
 DWORD th32ModuleID,cntThreads,th32ParentProcessID; LONG pcPriClassBase;
 DWORD dwFlags; CHAR szExeFile[MAX_PATH];
} PROCESSENTRY32;
typedef struct {
 DWORD dwSize,th32ModuleID,th32ProcessID,GlblcntUsage,ProccntUsage;
 BYTE *modBaseAddr; DWORD modBaseSize; HMODULE hModule;
 CHAR szModule[256],szExePath[MAX_PATH];
} MODULEENTRY32;
__declspec(dllimport) HANDLE WINAPI CreateToolhelp32Snapshot(DWORD,DWORD);
__declspec(dllimport) BOOL WINAPI Process32First(HANDLE,PROCESSENTRY32*);
__declspec(dllimport) BOOL WINAPI Process32Next(HANDLE,PROCESSENTRY32*);
__declspec(dllimport) BOOL WINAPI Module32First(HANDLE,MODULEENTRY32*);
__declspec(dllimport) BOOL WINAPI Module32Next(HANDLE,MODULEENTRY32*);
