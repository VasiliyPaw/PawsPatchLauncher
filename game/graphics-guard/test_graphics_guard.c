#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
int main(int argc,char**argv) {
    if(argc!=2)return 2;
    HMODULE dll=LoadLibraryA(argv[1]);
    if(!dll){printf("LoadLibrary failed %lu\n",GetLastError());return 3;}
    typedef int (WINAPI *TestFn)(void);
    TestFn test=(TestFn)GetProcAddress(dll,"PawGuardSelfTest");
    if(!test){printf("Missing selftest export %lu\n",GetLastError());return 4;}
    int errors=test();
    printf("15 range cases, 3 fake COM draw paths, 2 atomic replacement cases: errors=%d\n",errors);
    return errors?1:0;
}
