/* Private QA experiment: persist only successful single-character measurements.
   Native font objects, Unicode coverage, texture packing and rasterization remain.
   The launcher binds the cache to content hashes of game/font dependencies. */
#define FMC_MAX 200000
#define FMC_GROUPS 32
typedef unsigned(FC*FmcMeasure)(void*,void*,unsigned,unsigned,unsigned,unsigned,unsigned,unsigned);
typedef unsigned(FC*FmcGlyphs)(void*,void*,unsigned,unsigned,unsigned,unsigned,unsigned,unsigned,unsigned,unsigned);
typedef int(WINAPI*FmcGet)(void*,void*);
typedef struct {wchar_t logical[48],family[48];unsigned range[5],font[3],graphics[12],format[4];float matrix[6];} FmcContext;
typedef struct {unsigned group,code,box[4];} FmcEntry;
typedef struct {unsigned magic,version,count,groups,checksum;char key[65];FmcContext ctx[FMC_GROUPS];} FmcHeader;
static FmcHeader fmcHead;static FmcEntry*fmcEntries;static FmcContext fmcCtx;
static unsigned fmcMode,fmcActive,fmcGroup,fmcCursor,fmcContextReady,fmcContextOK,fmcDisabled;
static unsigned fmcCalls,fmcHits,fmcCompared,fmcMismatch,fmcFallback,fmcLoaded,fmcWritten;
static wchar_t fmcPath[MAX_PATH],fmcLogical[48];static HMODULE fmcGdi;
static unsigned fmc_hash(const void*p,unsigned n,unsigned h){const unsigned char*b=p;while(n--)h=(h^*b++)*16777619u;return h;}
static int fmc_get(const char*name,void*obj,void*out){FmcGet fn=(FmcGet)GetProcAddress(fmcGdi,name);return fn&&fn(obj,out)==0;}
static int fmc_context(void*graphics,void*font,void*format){
 void*matrix=0;int ok=1;unsigned i;
 const char*fg[]={"GdipGetFontSize","GdipGetFontStyle","GdipGetFontUnit"};
 const char*gg[]={"GdipGetDpiX","GdipGetDpiY","GdipGetPageUnit","GdipGetPageScale","GdipGetTextRenderingHint","GdipGetTextContrast","GdipGetSmoothingMode","GdipGetPixelOffsetMode","GdipGetInterpolationMode","GdipGetCompositingMode","GdipGetCompositingQuality"};
 const char*sg[]={"GdipGetStringFormatFlags","GdipGetStringFormatAlign","GdipGetStringFormatLineAlign","GdipGetStringFormatTrimming"};
 int(WINAPI*create)(void**)=(void*)GetProcAddress(fmcGdi,"GdipCreateMatrix");
 int(WINAPI*destroy)(void*)=(void*)GetProcAddress(fmcGdi,"GdipDeleteMatrix");
 for(i=0;i<3;i++)ok&=fmc_get(fg[i],font,&fmcCtx.font[i]);
 for(i=0;i<11;i++)ok&=fmc_get(gg[i],graphics,&fmcCtx.graphics[i]);
 for(i=0;i<4;i++)ok&=fmc_get(sg[i],format,&fmcCtx.format[i]);
 if(!create||!destroy||create(&matrix))ok=0;
 if(matrix){ok&=fmc_get("GdipGetWorldTransform",graphics,matrix);ok&=fmc_get("GdipGetMatrixElements",matrix,fmcCtx.matrix);destroy(matrix);}
 return ok;
}
static void fmc_begin_original(void){char mode[16]={0},key[65];FILE*f;unsigned h;
 fmcMode=0;GetEnvironmentVariableA("PAWS_FONT_CACHE_MODE",mode,sizeof(mode));
 if(!strcmp(mode,"record"))fmcMode=1;else if(!strcmp(mode,"replay"))fmcMode=2;else if(!strcmp(mode,"validate"))fmcMode=3;
 if(!fmcMode)return;
 if(GetEnvironmentVariableA("PAWS_FONT_CACHE_KEY",key,sizeof(key))!=64||!GetEnvironmentVariableW(L"PAWS_FONT_CACHE_PATH",fmcPath,MAX_PATH)||fmcPath[0]!=L'G'||fmcPath[1]!=L':'){fmcDisabled=1;return;}
 fmcEntries=(FmcEntry*)VirtualAlloc(0,FMC_MAX*sizeof(FmcEntry),MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);if(!fmcEntries){fmcDisabled=1;return;}
 fmcGdi=GetModuleHandleA("GdiPlus.dll");fmcActive=1;
 if(fmcMode==1){memset(&fmcHead,0,sizeof(fmcHead));fmcHead.magic=0x36434d46;fmcHead.version=1;memcpy(fmcHead.key,key,65);return;}
 f=_wfopen(fmcPath,L"rb");if(!f){fmcDisabled=1;return;}
 if(fread(&fmcHead,sizeof(fmcHead),1,f)!=1||fmcHead.magic!=0x36434d46||fmcHead.version!=1||memcmp(fmcHead.key,key,65)||fmcHead.count>FMC_MAX||fmcHead.groups>FMC_GROUPS||fread(fmcEntries,sizeof(FmcEntry),fmcHead.count,f)!=fmcHead.count||fgetc(f)!=EOF){fmcDisabled=1;fclose(f);return;}fclose(f);
 h=fmc_hash(fmcHead.ctx,sizeof(fmcHead.ctx),2166136261u);h=fmc_hash(fmcEntries,fmcHead.count*sizeof(FmcEntry),h);
 if(h!=fmcHead.checksum){fmcDisabled=1;return;}fmcLoaded=1;
}
static void fmc_begin(void){char key[65];
 fmc_begin_original();
 if(fmcMode==2&&fmcDisabled&&fmcEntries&&GetEnvironmentVariableA("PAWS_FONT_CACHE_KEY",key,sizeof(key))==64){
  memset(&fmcHead,0,sizeof(fmcHead));fmcHead.magic=0x36434d46;fmcHead.version=1;memcpy(fmcHead.key,key,65);fmcMode=1;fmcDisabled=0;fmcActive=1;
 }
}
static unsigned FC fmc_measure(void*s,void*d,unsigned text,unsigned len,unsigned font,unsigned origin,unsigned fmt,unsigned out){
 unsigned r;FmcEntry*e;FmcMeasure native=(FmcMeasure)(base+0x184432);fmcCalls++;
 if(!fmcActive||fmcDisabled||GetCurrentThreadId()!=thread||len!=1||!text||!font||!fmt||!origin||!out||*(unsigned*)origin||*(unsigned*)(origin+4)||!fmcGroup||fmcGroup>FMC_GROUPS)goto fallback;
 if(!fmcContextReady){fmcContextReady=1;fmcContextOK=fmc_context(*(void**)s,*(void**)font,*(void**)fmt);
  if(fmcMode==1)fmcHead.ctx[fmcGroup-1]=fmcCtx;
  else fmcContextOK&=fmcGroup<=fmcHead.groups&&!memcmp(&fmcCtx,&fmcHead.ctx[fmcGroup-1],sizeof(fmcCtx));
 }
 if(!fmcContextOK){fmcDisabled=1;goto fallback;}
 if(fmcMode==1){if(fmcHead.count==FMC_MAX){fmcDisabled=1;goto fallback;}r=native(s,d,text,len,font,origin,fmt,out);if(r){fmcDisabled=1;return r;}e=&fmcEntries[fmcHead.count++];e->group=fmcGroup;e->code=*(unsigned short*)text;memcpy(e->box,(void*)out,16);return r;}
 if(fmcCursor>=fmcHead.count){fmcDisabled=1;goto fallback;}e=&fmcEntries[fmcCursor++];
 if(e->group!=fmcGroup||e->code!=*(unsigned short*)text){fmcDisabled=1;goto fallback;}
 if(fmcMode==3){r=native(s,d,text,len,font,origin,fmt,out);fmcCompared++;if(r||memcmp(e->box,(void*)out,16)){fmcMismatch++;fmcDisabled=1;}return r;}
 memcpy((void*)out,e->box,16);fmcHits++;return 0;
 fallback:fmcFallback++;return native(s,d,text,len,font,origin,fmt,out);
}
static unsigned FC fmc_glyphs(void*s,void*d,unsigned dc,unsigned hf,unsigned gf,unsigned low,unsigned high,unsigned a,unsigned b,unsigned c){
 unsigned r;fmcGroup++;memset(&fmcCtx,0,sizeof(fmcCtx));memcpy(fmcCtx.logical,fmcLogical,sizeof(fmcLogical));fmcCtx.range[0]=low;fmcCtx.range[1]=high;fmcCtx.range[2]=a;fmcCtx.range[3]=b;fmcCtx.range[4]=c;fmcContextReady=0;fmcContextOK=0;
 r=((FmcGlyphs)(base+0x181dfc))(s,d,dc,hf,gf,low,high,a,b,c);return r;
}
static void fmc_font_begin(void*s){wchar_t*name=*(wchar_t**)(*(unsigned*)s+8);memset(fmcLogical,0,sizeof(fmcLogical));if(name)wcsncpy(fmcLogical,name,47);}
static void fmc_end(void){FILE*f;wchar_t tmp[MAX_PATH];
 fmcActive=0;if(fmcMode==1&&!fmcDisabled&&fmcGroup<=FMC_GROUPS&&fmcHead.count){fmcHead.groups=fmcGroup;fmcHead.checksum=fmc_hash(fmcHead.ctx,sizeof(fmcHead.ctx),2166136261u);fmcHead.checksum=fmc_hash(fmcEntries,fmcHead.count*sizeof(FmcEntry),fmcHead.checksum);
  if(wcslen(fmcPath)<MAX_PATH-6){swprintf(tmp,L"%ls.tmp",fmcPath);f=_wfopen(tmp,L"wb");if(f){unsigned ok=fwrite(&fmcHead,sizeof(fmcHead),1,f)==1&&fwrite(fmcEntries,sizeof(FmcEntry),fmcHead.count,f)==fmcHead.count;if(fclose(f))ok=0;if(ok)fmcWritten=MoveFileExW(tmp,fmcPath,MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH);}}
 }
 if(fmcMode){f=_wfopen(trace,L"ab");if(f){fprintf(f,"{\"event\":\"FontCache\",\"mode\":%u,\"calls\":%u,\"hits\":%u,\"compared\":%u,\"mismatches\":%u,\"fallback\":%u,\"disabled\":%u,\"loaded\":%u,\"written\":%u,\"entries\":%u,\"consumed\":%u,\"groups\":%u}\n",fmcMode,fmcCalls,fmcHits,fmcCompared,fmcMismatch,fmcFallback,fmcDisabled,fmcLoaded,fmcWritten,fmcHead.count,fmcCursor,fmcGroup);fclose(f);}}
 if(fmcEntries){VirtualFree(fmcEntries,0,MEM_RELEASE);fmcEntries=0;}
}
