/* Restricted fast path for native TGI value/node-name extraction. Block
 * comments and unexpected cursors retain the complete original routine.
 * The native substring allocator, trailing trim and reference counting stay.
 */
typedef struct {int start,count,cursor;} TokenSpan;
static int token_span(const wchar_t*text,int length,int cursor,int node,TokenSpan*out){
 int i=cursor,quoted,first=1;
 if(length<0||length>1048576||cursor<0||cursor>length)return 0;
 quoted=i<length&&text[i]=='"';out->start=cursor;
 for(;i<length;i++){
  unsigned c=text[i];
  if(node){if(c==']')break;}
  else{
   if(!first&&c=='"')quoted=0;
   else if(!quoted&&c==';'){out->count=i-cursor;out->cursor=i>0?i-1:i;return 1;}
   first=0;
  }
  if(c=='/'&&i+1<length&&text[i+1]=='*')return 0;
 }
 out->count=i-cursor;out->cursor=i;return 1;
}
#ifndef TOKEN_SCAN_ONLY
typedef unsigned(FC*Token1)(void*,void*,unsigned);
typedef unsigned(FC*Token3)(void*,void*,unsigned,unsigned,unsigned);
typedef unsigned(FC*Token0)(void*,void*);
static unsigned tokensEnabled,tokensValidate,tokensDiagnostic,tokensFast[2],tokensFallback[2],tokensCompared,tokensMismatch;
static unsigned tokenDigest=2166136261u;
static void tokens_init(void){char v[4];tokensEnabled=GetEnvironmentVariableA("PAWS_STARTUP_TOKENS",v,4)==1&&v[0]=='1';tokensValidate=GetEnvironmentVariableA("PAWS_STARTUP_TOKENS_VALIDATE",v,4)==1&&v[0]=='1';tokensDiagnostic=GetEnvironmentVariableA("PAWS_STARTUP_TOKEN_DIGEST",v,4)==1&&v[0]=='1';}
static unsigned FC token_extract(void*s,void*d,unsigned output,unsigned node){
 unsigned nativeRva=node?0x1bf075:0x1bf21d;int*lex=(int*)s;wchar_t*line=(wchar_t*)lex[2];TokenSpan span;unsigned result;
 if(!tokensEnabled||!token_span(line,*(int*)((char*)line-12),lex[3],node,&span)){
  if(tokensEnabled)tokensFallback[node]++;
  result=((Token1)(base+nativeRva))(s,d,output);
 }else{
  int originalState[10];unsigned originalText=0;
  if(tokensValidate){memcpy(originalState,s,40);((Token1)(base+nativeRva))(originalState,d,(unsigned)&originalText);}
  ((Token3)(base+0x4bef4))(&lex[2],d,output,span.start,span.count);
  ((Token0)(base+0x497cd))((void*)output,d);lex[3]=span.cursor;tokensFast[node]++;result=output;
  if(tokensValidate){unsigned actual=*(unsigned*)output;int len=*(int*)(actual-12);tokensCompared++;
   if(memcmp(originalState,s,40)||len!=*(int*)(originalText-12)||memcmp((void*)actual,(void*)originalText,(len+1)*2)){
    tokensMismatch++;((Token0)(base+0x21375))((void*)(actual-16),d);*(unsigned*)output=originalText;memcpy(s,originalState,40);
   }else ((Token0)(base+0x21375))((void*)(originalText-16),d);
  }
 }
 if(tokensDiagnostic){unsigned p=*(unsigned*)output;int n=*(int*)(p-12),i;unsigned short*t=(unsigned short*)p;tokenDigest=(tokenDigest^(unsigned)n)*16777619u;for(i=0;i<n;i++)tokenDigest=(tokenDigest^t[i])*16777619u;tokenDigest=(tokenDigest^(unsigned)lex[3])*16777619u;}
 return result;
}
#endif
