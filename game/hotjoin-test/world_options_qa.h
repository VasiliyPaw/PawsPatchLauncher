/* Observer-only fixture actions. Not compiled into the shipped runtime. */
#ifdef PAWS_HOTJOIN_MONITOR
static unsigned testWorldVisited[8192],testWorldVisitCount;
static int test_world_widget(uintptr_t widget,uintptr_t data,unsigned index,unsigned depth){
 unsigned i;uintptr_t name,rules,node;int changed=0;
 if(depth>20||testWorldVisitCount>=8192||!readable(widget,0x30))return 0;
 for(i=0;i<testWorldVisitCount;i++)if(testWorldVisited[i]==widget)return 0;
 testWorldVisited[testWorldVisitCount++]=(unsigned)widget;name=word(widget+4);
 if(readable(name,32)&&!wcscmp((wchar_t*)name,L"WorldRulesPanel")&&readable(widget,0xbc)&&byte(widget+0xb8)){
  rules=word(widget+0x8c);
  if(readable(rules,0x1c)&&word(rules+0x10)<=256){
   ((DisconnectFn)(base+0x296c07))((void*)rules,0,(int)data,(int)index);changed++;
  }
 }
 node=word(widget+0x28);
 for(i=0;node&&i<1024&&readable(node,12);i++){
  changed+=test_world_widget(word(node),data,index,depth+1);node=word(node+8);
 }
 return changed;
}
static int test_world_option(const wchar_t *args){
 wchar_t id[80],choice[80];uintptr_t db=word(base+0x5f3fb4),data=0,items;unsigned i,j,n,order[3];
 if(swscanf(args,L"%79ls %79ls",id,choice)!=2||!db)return 0;
 items=word(db+0x118);n=word(db+0x11c);if(n>256)return 0;
 for(i=0;i<n;i++){uintptr_t p=word(items+i*4);if(readable(p,0x44)&&!_wcsicmp((wchar_t*)word(p+8),id)){data=p;break;}}
 if(!data||word(data+0x20)!=3||word(data+0x38)>128)return 0;
 for(j=0;j<word(data+0x38);j++)if(!_wcsicmp((wchar_t*)word(word(data+0x34)+j*8),choice)){
  /* Random-map dialogs edit a private WorldRules clone; Commit subsequently
   * sends it through the normal host request. Use that exact SetEnum branch,
   * 0052ee0d..0052ee15, rather than an editor-world decree in a lobby. */
  uintptr_t ui=word(base+0x5f3fc0),buckets=word(ui+0x7c),node;unsigned count=word(ui+0x80),k;int changed=0;
  (void)order;if(count>65536)return 0;testWorldVisitCount=0;
  for(i=0;i<count;i++)for(node=word(buckets+i*4),k=0;node&&k<1024&&readable(node,8);node=word(node+4),k++)changed+=test_world_widget(word(node),data,j,0);
  host->log("world-options-qa","NATIVE_UI_ENUM_CLONE rule=%ls value=%ls index=%u panels=%d",id,choice,j,changed);return changed>0;
 }
 return 0;
}
static void test_world_sample(void){
 wchar_t path[MAX_PATH];uintptr_t w=word(base+0x5f3fb8),items,data,entry;unsigned i,n;FILE *f;
 if(!w||!readable(w,0x100))return;
 swprintf(path,L"%ls\\lab-world-options.jsonl",host->modsDir);f=_wfopen(path,L"a");if(!f)return;
 fprintf(f,"{\"tick\":%u,\"seconds\":%.4f,\"colors\":[",word(w+0xe4),*(float*)(w+0xe8));
 for(i=0;i<9;i++)fprintf(f,"%s%.7f",i?",":"",*(float*)(w+0x84+i*4));
 fprintf(f,"],\"rules\":{");items=word(w+0x18);n=word(w+0x1c);if(n>256)n=0;
 for(i=0;i<n;i++){entry=items+i*12;data=word(entry);if(!data)continue;
  if(!_wcsicmp((wchar_t*)word(data+8),L"PawsDayPhase"))fprintf(f,"\"phase\":%u,",word(entry+8));
  if(!_wcsicmp((wchar_t*)word(data+8),L"Sun"))fprintf(f,"\"sun\":%u,",word(entry+8));
  if(!_wcsicmp((wchar_t*)word(data+8),L"PawsBiomes"))fprintf(f,"\"biomes\":%u,",word(entry+8));
 }
 fprintf(f,"\"sample\":1}}\n");fclose(f);
}
#endif
