/* Private composition adapter. Refuse unknown hook chains; never overwrite
 * an installed color extension or stack a second copy of the R2 transport. */
static uintptr_t composed_branch(unsigned rva) {
 uintptr_t p=base+rva;if(byte(p)!=0xe9)return 0;
 return p+5+(int)word(p+1);
}
static int composed_color_wrapper(uintptr_t target,unsigned nativeRva,uintptr_t cave) {
 static const unsigned char prefix[]={0x56,0x57,0x8b,0x74,0x24,0x0c,0x89,0xcf,0x56,0xe8};
 static const unsigned char middle[]={0x9c,0x60,0x89,0xf9,0x89,0xf2,0xe8};
 static const unsigned char end[]={0x61,0x9d,0x5f,0x5e,0xc2,0x04,0x00};
 uintptr_t extension;
 if(!readable(target,32)||memcmp((void*)target,prefix,sizeof(prefix))||memcmp((void*)(target+14),middle,sizeof(middle))||memcmp((void*)(target+25),end,sizeof(end)))return 0;
 if(target+14+(int)word(target+10)!=base+nativeRva)return 0;
 extension=target+25+(int)word(target+21);
 return extension>=cave&&extension<cave+270336;
}
static int composed_prepare(void) {
 uintptr_t writer=composed_branch(0x152b5a),reader=composed_branch(0x152b86),cave;
 if(byte(base+0x152b5a)==0xe8&&byte(base+0x152b86)==0xe8&&
    base+0x152b5f+(int)word(base+0x152b5b)==base+0x16775c&&
    base+0x152b8b+(int)word(base+0x152b87)==base+0x16797a){
  sessionWriteTarget=base+0x16775c;sessionReadTarget=base+0x16797a;return 1;
 }
 if(writer==base+0x16775c&&reader==base+0x16797a){sessionWriteTarget=writer;sessionReadTarget=reader;return 1;}
 if(!writer||writer<0x32000)return 0;cave=writer-0x32000;
 if(reader!=cave+0x33000||!composed_color_wrapper(writer,0x16775c,cave)||!composed_color_wrapper(reader,0x16797a,cave))return 0;
 sessionWriteTarget=writer;sessionReadTarget=reader;sessionAppendTarget=writer+25+(int)word(writer+21);
 host->log("hotjoin-lab","COMPOSED_COLOR_PRIVATE_WIRE_CHAINED verified native serializer and palette extension; real session identity retained");
 return 1;
}
static int composed_r2(void) {
 unsigned char expected[768];uintptr_t cave=composed_branch(0x151936);unsigned i,j,value;
 const unsigned sites[3]={0x151936,0x1500f6,0x1501d1},offsets[3]={0,256,512},sizes[3]={8,7,7};
 if(!cave||!readable(cave,sizeof(expected)))return 0;
 memcpy(expected,hj_r2_payload,sizeof(expected));
 for(i=0;i<sizeof(hj_r2_fixes)/sizeof(hj_r2_fixes[0]);i++){
  unsigned off=hj_r2_fixes[i].offset;memcpy(&value,expected+off,4);
  value+=hj_r2_fixes[i].image*((unsigned)base-0x400000u)+hj_r2_fixes[i].cave*((unsigned)cave-0x10000000u);memcpy(expected+off,&value,4);
 }
 if(memcmp((void*)cave,expected,sizeof(expected)))return 0;
 for(i=0;i<3;i++){
  if(composed_branch(sites[i])!=cave+offsets[i])return 0;
  for(j=5;j<sizes[i];j++)if(byte(base+sites[i]+j)!=0x90)return 0;
 }
 transferR2=cave;
 host->log("hotjoin-lab","FAST_TRANSFER_R2_REUSED verified byte-identical installed core; second installer skipped");
 return 1;
}
