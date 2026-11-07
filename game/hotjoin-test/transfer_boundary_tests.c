#include <windows.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "transfer_boundary.h"
typedef unsigned (__cdecl *TailFn)(unsigned,unsigned);
static TailFn make_tail(int receiver,int fixed) {
 static const unsigned char sender_prefix[]={0x56,0x8b,0x4c,0x24,0x08,0x8b,0x74,0x24,0x0c};
 static const unsigned char receiver_prefix[]={0x56,0x57,0x8b,0x74,0x24,0x0c,0x8b,0x7c,0x24,0x10};
 static const unsigned char sender_suffix[]={0x8b,0xc6,0x5e,0xc3};
 static const unsigned char receiver_suffix[]={0x8b,0xc7,0x5f,0x5e,0xc3};
 unsigned char *code=VirtualAlloc(0,64,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
 const unsigned char *body=receiver?hj_transfer_receiver_tail:hj_transfer_sender_tail;
 unsigned n=receiver?sizeof(receiver_prefix):sizeof(sender_prefix);DWORD old;
 assert(code);
 memcpy(code,receiver?receiver_prefix:sender_prefix,n);
 if(fixed){memcpy(code+n,body,11);n+=11;}
 else {memcpy(code+n,body,5);memcpy(code+n+5,body+9,2);n+=7;}
 memcpy(code+n,receiver?receiver_suffix:sender_suffix,receiver?sizeof(receiver_suffix):sizeof(sender_suffix));
 assert(VirtualProtect(code,64,PAGE_EXECUTE_READ,&old));FlushInstructionCache(GetCurrentProcess(),code,64);
 return (TailFn)code;
}
int main(void) {
 const unsigned sizes[]={1,2,63,64,65,127,128,129,223936,223960,224000,224001};
 const unsigned blocks[]={1,2,64,256};unsigned i,j,total,block,parts,expected,bytes,kind;
 for(kind=0;kind<2;kind++){
  TailFn original=make_tail(kind,0),fixed=make_tail(kind,1);
  for(i=0;i<sizeof(sizes)/sizeof(sizes[0]);i++)for(j=0;j<sizeof(blocks)/sizeof(blocks[0]);j++){
   total=sizes[i];block=blocks[j];parts=(total+block-1)/block;
   expected=total-(parts-1)*block;
   assert(original(total,block)==total%block);
   assert(fixed(total,block)==expected);
   bytes=(parts-1)*block+fixed(total,block);assert(bytes==total);
  }
  assert(original(224000,64)==0&&fixed(224000,64)==64);
  VirtualFree((void*)original,0,MEM_RELEASE);VirtualFree((void*)fixed,0,MEM_RELEASE);
 }
 puts("PASS: actual x86 sender/receiver tail instructions, partial/exact blocks, 224000-byte regression; original truncation reproduced");
 return 0;
}
