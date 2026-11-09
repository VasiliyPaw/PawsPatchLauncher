"""QA-only native UI selection and read-only world observer, never shipped."""
import subprocess
from context import *

def main():
 out=OUT/'qa-rig-r3';out.mkdir(exist_ok=False);source=(REPO/'game/reconnect-test/rig_input.c').read_text()
 header=(REPO/'game/hotjoin-test/world_options_qa.h').read_text();header=header[header.index('static unsigned testWorldVisited'):header.index('static void test_world_sample')];header=header.replace('host->log(', 'writeLog(').replace('name=word(widget+4);','name=word(widget+4);if(!readable(name,2)||!*(wchar_t*)name)name=word(widget+0x1c);')
 header=header.replace('((DisconnectFn)(base+0x296c07))((void*)rules,0,(int)data,(int)index);changed++;','((DisconnectFn)(base+0x296c07))((void*)rules,0,(int)data,(int)index);{unsigned q;for(q=0;q<word(rules+0x10);q++){uintptr_t r=word(rules+0xc)+q*12;if(word(r)==data)writeLog("world-options-qa","CLONE_VALUE rule=%ls value=%u editable=%u",(wchar_t*)word(data+8),word(r+8),byte(widget+0xb8));}}changed++;')
 addition='''
#include <stdio.h>
static uintptr_t word(uintptr_t p){return *(uintptr_t*)p;}
static unsigned byte(uintptr_t p){return *(unsigned char*)p;}
static int readable(uintptr_t p,unsigned n){MEMORY_BASIC_INFORMATION m;return p&&VirtualQuery((void*)p,&m,sizeof(m))&&m.State==MEM_COMMIT&&!(m.Protect&(PAGE_GUARD|PAGE_NOACCESS))&&p+n>=p&&p+n<=(uintptr_t)m.BaseAddress+m.RegionSize;}
typedef void(FC*DisconnectFn)(void*,void*,int,int);
'''+header+'''
static wchar_t observedPath[MAX_PATH];static DWORD observedAt;
static void observe(void){uintptr_t w=word(base+0x5f3fb8),table,data,entry,ws;unsigned i,n,tick;FILE*f;DWORD now=GetTickCount();
 if(now-observedAt<100||!w||!readable(w,0x100))return;observedAt=now;tick=word(w+0xe4);ws=word(base+0x5f3ff4);
 f=_wfopen(observedPath,L"a");if(!f)return;fprintf(f,"{\\"tick\\":%u,\\"seconds\\":%.4f,\\"worldIndex\\":%u,\\"worldCrc\\":%u,\\"colors\\":[",tick,*(float*)(w+0xe8),readable(ws,0x18)?word(ws+0x14):0,readable(ws,0xc)?word(ws+8):0);
 for(i=0;i<9;i++)fprintf(f,"%s%.8f",i?",":"",*(float*)(w+0x84+i*4));fprintf(f,"],\\"rules\\":{");table=word(w+0x18);n=word(w+0x1c);if(n>256)n=0;
 for(i=0;i<n;i++){entry=table+i*12;data=word(entry);if(data&&readable(data,0x24))fprintf(f,"%s\\"%ls\\":%u",i?",":"",(wchar_t*)word(data+8),word(entry+8));}
 fprintf(f,"},\\"tickAfter\\":%u}\\n",word(w+0xe4));fclose(f);
}
static int qa_option_request(const Host*h,unsigned id){wchar_t path[MAX_PATH],request[160];char bytes[400];FILE*f;size_t n;
 swprintf(path,L"%ls\\\\rig-request-%u.txt",h->modsDir,id);f=_wfopen(path,L"rb");if(!f)return 0;n=fread(bytes,1,399,f);fclose(f);bytes[n]=0;
 if(strncmp(bytes,"!world-option ",14))return 0;mbstowcs(request,bytes+14,159);request[159]=0;test_world_option(request);return 1;
}
static const Host*qaHost;
'''
 anchor='__declspec(dllexport) int __cdecl K2Plugin_Start';source=source.replace(anchor,addition+anchor,1)
 source=source.replace('if(!host||host->api!=1)return 1;base=', 'if(!host||host->api!=1)return 1;qaHost=host;swprintf(observedPath,L"%ls\\\\pure-world.jsonl",host->modsDir);base=')
 source=source.replace('inTick=1;','inTick=1;observe();',1)
 source=source.replace('writeLog("rig-input","dispatch request %u",id);Run(console,command);','writeLog("rig-input","dispatch request %u",id);if(!qa_option_request(qaHost,id))Run(console,command);')
 (out/'rig_input.c').write_text(source);subprocess.run(list(map(str,[TCC,'-shared','-Wall','-Werror',out/'rig_input.c','-o',out/'rig_input.dll','-lkernel32','-luser32'])),check=True)
 # Established reflection harness installs the unmodified packaged Pure helper.
 shutil=__import__('shutil');artifacts=WS/'outputs/release-saves-20261013';shutil.copy2(artifacts/'InstalledHarness.exe',out/'InstalledHarness.exe');(out/'native').mkdir();shutil.copy2(artifacts/'native/shfolder.dll',out/'native/shfolder.dll')
 write(out/'build.json',dict(fixtureOnly=True,productionRuntimeUnchanged=True,input='native console plus native UI enum clone',observation='read-only colors/rules/checksum snapshots; tickAfter detects concurrent samples',sources={str(out/'rig_input.c'):sha(out/'rig_input.c')},dllSha256=sha(out/'rig_input.dll')));print('PURE_QA_ONLY_RIG_BUILT')
if __name__=='__main__':main()
