/* Owned 32-bit Windows test process. Contains no game code or game data. */
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>
int main(int argc,char**argv){
 unsigned char*image,*entry;unsigned i;char done[2048];
 unsigned char original[]={0xb8,0x68,0x24,0x57,0x13,0xc2,0x20,0};
 unsigned char guard[]={0xe8,0x8c,0x87,0xd5,0xff};
 if(argc!=2)return 2;
 image=VirtualAlloc((void*)0x15000000,0x700000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);if(!image)return 3;
 memcpy(image+0x1e96a,original,sizeof(original));
 entry=image+0x2c61d9-21;
 for(i=0;i<8;i++){entry[i*2]=0x6a;entry[i*2+1]=0;}
 entry[16]=0xb9;*(unsigned*)(entry+17)=0x55667788;
 memcpy(image+0x2c61d9,guard,5);image[0x2c61de]=0xc3;
 {
  const wchar_t*ids[]={L"paws_voice_en_swordsman_select",L"paws_voice_ru_swordsman_select",L"paws_voice_de_swordsman_select",L"paws_voice_fr_swordsman_select"};
  unsigned db=(unsigned)image+0x610000,collection=(unsigned)image+0x611000,buckets=(unsigned)image+0x612000,j,h,slot,obj,node;
  *(unsigned*)(image+0x5f3fb4)=db;*(unsigned*)(db+0x584)=collection;*(unsigned*)(collection+0x30)=buckets;*(unsigned*)(collection+0x34)=64;
  for(j=0;j<4;j++){
   const wchar_t*p=ids[j];h=0;while(*p){unsigned c=*p++;if(c>='a'&&c<='z')c-=32;h=h*33+c;}
   obj=(unsigned)image+0x620000+j*0x100;node=(unsigned)image+0x630000+j*0x100;
   *(unsigned*)(obj+8)=(unsigned)image+0x640000+j*0x100;memcpy((void*)(*(unsigned*)(obj+8)),ids[j],(wcslen(ids[j])+1)*2);
   slot=buckets+(h%64)*4;*(unsigned*)node=obj;*(unsigned*)(node+4)=*(unsigned*)slot;*(unsigned*)slot=node;
  }
 }
 sprintf(done,"%s.done",argv[1]);printf("READY %u\n",(unsigned)image);fflush(stdout);
 for(i=0;i<30000;i++){
  if(((unsigned(*)(void))entry)()!=0x13572468)return 4;
  if(GetFileAttributes(done)!=INVALID_FILE_ATTRIBUTES){printf("NATIVE_CALLS_OK %u\n",i);fflush(stdout);return 0;}
  Sleep(1);
 }
 return 5;
}
