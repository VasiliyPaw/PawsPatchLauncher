/* Eliminate the repeated lookup only in the verified native missing-field
 * branch. Audited clones copy field data without changing the destination. */
typedef unsigned(FC*Lookup1)(void*,void*,unsigned);
static unsigned lookupEnabled,lookupValidate,lookupDiagnostic,lookupChecks,lookupSkipped,lookupCompared,lookupMismatch,lookupFallback;
static DWORD lookupThread;
static unsigned lookupTypes[32],lookupTypeCounts[32],lookupTypeCount;
#ifndef LOOKUP_NATIVE
#define LOOKUP_NATIVE(rva,type) ((type)(base+(rva)))
#endif
static void lookup_init(void){char v[4];lookupThread=GetCurrentThreadId();lookupEnabled=GetEnvironmentVariableA("PAWS_STARTUP_LOOKUP",v,4)==1&&v[0]=='1';lookupValidate=GetEnvironmentVariableA("PAWS_STARTUP_LOOKUP_VALIDATE",v,4)==1&&v[0]=='1';lookupDiagnostic=GetEnvironmentVariableA("PAWS_STARTUP_LOOKUP_DIAG",v,4)==1&&v[0]=='1';}
/* Audited clones allocate a new field and retain/copy its name and value only.
 * Their constructors never receive or modify the destination node/map. */
static const unsigned lookupVtables[]={0x4cf558,0x4cfc18,0x4cf12c,0x4cec00,0x4ce97c,0x4cf7d8,0x4cfa9c,0x4cee90,0x4cf2ac};
static const unsigned lookupClones[]={0x1bd2eb,0x1bd334,0x1bd043,0x1bd11f,0x1bd1db,0x1bd2a2,0x1bd245,0x1bd0a0,0x1bd171};
#ifndef LOOKUP_AUDITED
static int lookup_clone_audited(unsigned vt,unsigned clone){unsigned i;for(i=0;i<9;i++)if(vt==base+lookupVtables[i]&&clone==base+lookupClones[i]&&*(unsigned*)(vt+0x4c)==base+(i==1?0x21250:0x21230))return 1;return 0;}
#define LOOKUP_AUDITED(vt,clone) lookup_clone_audited(vt,clone)
#endif
/* Replaces only: call [eax+50]; push eax; mov ecx,edi; call AddField.
 * Caller has ECX=source field; our thunk pushes EDI=destination node. */
static unsigned FC lookup_clone_add(void*source,void*d,unsigned node){
 typedef unsigned(FC*Clone0)(void*,void*);
 unsigned vt=*(unsigned*)source,clone=*(unsigned*)(vt+0x50),field,ready=0,i,name=*((unsigned*)source+1);
 int own=GetCurrentThreadId()==lookupThread;
 if(own){
  if(lookupDiagnostic){unsigned rva=clone-base;for(i=0;i<lookupTypeCount&&lookupTypes[i]!=rva;i++);if(i==lookupTypeCount&&i<32)lookupTypes[lookupTypeCount++]=rva;if(i<32)lookupTypeCounts[i]++;}
  if(lookupEnabled){lookupChecks++;ready=LOOKUP_AUDITED(vt,clone);}
 }
 field=((Clone0)clone)(source,d); /* Original allocation/ownership always retained. */
 if(ready&&*(unsigned*)(field+4)!=name)ready=0;
 if(ready&&lookupValidate){unsigned native=LOOKUP_NATIVE(0x4dd02,Lookup1)((void*)node,d,name);lookupCompared++;if(native&255){lookupMismatch++;ready=0;}}
 if(ready){lookupSkipped++;return LOOKUP_NATIVE(0x2ea23,Lookup1)((void*)(node+0x40),d,field);}
 if(own&&lookupEnabled)lookupFallback++;
 return LOOKUP_NATIVE(0x1b88ec,Lookup1)((void*)node,d,field);
}
