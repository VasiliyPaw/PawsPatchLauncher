/* Reuse the native managed field-name string at the verified inheritance
 * call site. Cache its native hash ONLY until that temporary is released.
 * No persistent cache, map replacement, skipped clone or changed inheritance.
 */
typedef unsigned(__cdecl*FieldC1)(unsigned);
typedef unsigned(__cdecl*FieldC2)(unsigned,unsigned);
typedef unsigned(FC*Field1)(void*,void*,unsigned);
typedef unsigned(FC*Field0)(void*,void*);
#ifndef FIELD_NATIVE
#define FIELD_NATIVE(rva,type) ((type)(base+(rva)))
#endif
static unsigned fieldsEnabled,fieldsValidate,fieldsNames,fieldsCompared,fieldsHits,fieldsMismatch;
static unsigned fieldCurrent,fieldHash,fieldHashValid;static DWORD fieldThread;
static void fields_init(void){char v[4];fieldsEnabled=GetEnvironmentVariableA("PAWS_STARTUP_FIELDS",v,4)==1&&v[0]=='1';fieldsValidate=GetEnvironmentVariableA("PAWS_STARTUP_FIELDS_VALIDATE",v,4)==1&&v[0]=='1';fieldThread=GetCurrentThreadId();}
static unsigned FC field_name(void*s,void*d,unsigned name){unsigned expected=0,actual;
 if(!fieldsEnabled||GetCurrentThreadId()!=fieldThread)return FIELD_NATIVE(0x205de,Field1)(s,d,name);
 fieldCurrent=fieldHashValid=0;
 /* Field::name at +4 is already a managed native wide string. */
 if(fieldsValidate)FIELD_NATIVE(0x205de,Field1)(&expected,d,name);
 actual=FIELD_NATIVE(0x20d6b,FieldC1)(name-16)+16;*(unsigned*)s=actual;fieldsNames++;
 if(fieldsValidate){int n=*(int*)(actual-12);fieldsCompared++;
  if(n!=*(int*)(expected-12)||memcmp((void*)actual,(void*)expected,(n+1)*2)){
   fieldsMismatch++;FIELD_NATIVE(0x21375,Field0)((void*)(actual-16),d);*(unsigned*)s=expected;actual=expected;
  }else FIELD_NATIVE(0x21375,Field0)((void*)(expected-16),d);
 }
 fieldCurrent=actual;return(unsigned)s;
}
static unsigned FC field_release(void*s,void*d){
 if(GetCurrentThreadId()==fieldThread&&(uintptr_t)s+16==fieldCurrent)fieldCurrent=fieldHashValid=0;
 return FIELD_NATIVE(0x21375,Field0)(s,d);
}
static unsigned __cdecl field_hash(unsigned str){unsigned r;
 if(fieldsEnabled&&fieldCurrent&&*(unsigned*)str==fieldCurrent&&GetCurrentThreadId()==fieldThread){
  if(fieldHashValid){fieldsHits++;if(fieldsValidate){r=FIELD_NATIVE(0x211db,FieldC1)(str);if(r!=fieldHash){fieldsMismatch++;fieldHash=r;}}return fieldHash;}
  fieldHash=FIELD_NATIVE(0x211db,FieldC1)(str);fieldHashValid=1;return fieldHash;
 }
 return FIELD_NATIVE(0x211db,FieldC1)(str);
}
