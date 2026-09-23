/* Native SAI actor/property counts include local workers and militia. They
 * must still describe the world for defense, construction and combat scoring.
 * Recruitment alone gets a separate mirror of native owned-field counts.
 * Registration/removal callbacks maintain it without per-candidate map scans,
 * temporary edits to engine tables, commands, allocations or race ID lists. */
static RecruitCounts* recruit_counts_record(U image,Data*d,U pl){
 FastData*f=(FastData*)d;U i,world=P(image,0x5f3fb8);
 if(!pl||!world||f->recruitWorld!=world)return 0;
 for(i=0;i<96;i++)if(f->recruitCounts[i].player==pl)return &f->recruitCounts[i];
 return 0;
}
static RecruitCountEntry* recruit_counts_entry(RecruitCounts*r,U key,int create){
 U i,start=(key>>2)*2654435761u;
 if(!key||(key&2))return 0;
 for(i=0;i<2048;i++){
  RecruitCountEntry*e=&r->entries[(start+i)&2047];
  if(e->key==key)return e;
  if(!e->key){if(create)e->key=key;return create?e:0;}
 }
 if(create)r->ready=0; /* Unsupported density: preserve native behavior. */
 return 0;
}
static void recruit_counts_change(RecruitCounts*r,U key,int add){
 RecruitCountEntry*e;
 if(!r->ready)return;
 e=recruit_counts_entry(r,key,add);if(!e){if(!add)r->ready=0;return;}
 if(add){if(e->count==0x7fffffffu)r->ready=0;else e->count++;}
 else if(e->count)e->count--;else r->ready=0;
}
static RecruitCountMember* recruit_counts_member(RecruitCounts*r,U id,int add){
 U i,start=id*2654435761u;RecruitCountMember*empty=0;
 for(i=0;i<4096;i++){
  RecruitCountMember*m=&r->members[(start+i)&4095];
  if(m->id==id)return m;
  if(!m->id)return add?(empty?empty:m):0;
  if(m->id==0xffffffffu&&!empty)empty=m;
 }
 return add?empty:0;
}
static void recruit_counts_actor(U image,Data*d,U pl,U def,U actor,int add){
 RecruitCounts*r=recruit_counts_record(image,d,pl);RecruitCountMember*m;U node,steps=0,alias,id;
 if(!r||!r->ready)return;
 /* Removal happens after an actor may have acquired its dead flag. Mirror
  * the engine's lifecycle notification, not a fresh alive/HP heuristic. */
 if(!actor||P(actor,0)!=image+0x4e5c58||!def||P(actor,4)!=def){r->ready=0;return;}
 id=P(actor,0x14);if(!id||id==0xffffffffu){r->ready=0;return;}
 m=recruit_counts_member(r,id,add);
 if(!m||(add&&m->id==id)){r->ready=0;return;}
 if(add){
  m->id=id;m->definition=(P(actor,0x144)==2||P(actor,0x144)==3||(P(actor,0x100)&4))?0:def;
  def=m->definition;
 }else{
  /* Use membership recorded at admission: allegiance/denizen flags can change
   * before removal during capture, disband or conversion to a field unit. */
  def=m->definition;m->id=0xffffffffu;m->definition=0;
 }
 if(!def)return;
 recruit_counts_change(r,def,add);
 alias=P(def,0x534);if(alias)recruit_counts_change(r,alias,add);
 alias=P(def,0x548);if(alias)recruit_counts_change(r,alias,add);
 for(node=P(def,0x1d4);node&&steps++<256;node=P(node,4)){
  U property=P(node,0),vt=property?P(property,0):0;
  if(!vt||!P(vt,0x18)){r->ready=0;return;}
  if(((EconomyM0)P(vt,0x18))(property,0)&255)recruit_counts_change(r,property|1,add);
 }
 if(node)r->ready=0;
}
static void recruit_counts_evaluate(U image,Data*d,U mode,U obj,U*args,float*result){
 FastData*f=(FastData*)d;RecruitCounts*r;U i,world=P(image,0x5f3fb8);
 if(mode==48){
  /* SAIPlayer constructor: reset by its native player index on new games and
   * save loads, including reused world/player addresses and elapsed times. */
  U pl=*(U*)result,index=args[0];
  if(!pl||!world||index>=96)return;
  if(f->recruitWorld!=world){
   f->recruitWorld=world;f->recruitScope=0;
   for(i=0;i<96;i++){f->recruitCounts[i].player=0;f->recruitCounts[i].ready=0;}
  }
  r=&f->recruitCounts[index];r->player=pl;r->ready=1;
  for(i=0;i<2048;i++){r->entries[i].key=0;r->entries[i].count=0;}
  for(i=0;i<4096;i++){r->members[i].id=0;r->members[i].definition=0;}
  return;
 }
 if(mode==46||mode==47){recruit_counts_actor(image,d,obj,args[0],args[1],mode==46);return;}
 if(mode==40){U old=f->recruitScope;f->recruitScope=args[1];f->recruitDefinition=args[0];*(U*)result=old;return;}
 if(mode==41){f->recruitScope=args[0];return;}
 if(!(d->mask&8)||!obj||!*(unsigned char*)(obj+4)||P(image,0x5f9218)!=2)return;
 if((mode==42||mode==43)&&f->recruitScope!=obj)return;
 r=recruit_counts_record(image,d,obj);if(!r||!r->ready)return;
 {U property=mode==43||mode==45,key=args[0],before=*(U*)result,after;RecruitCountEntry*e;
  if(!key||(key&3))return;
  e=recruit_counts_entry(r,key|property,0);after=e?e->count:0;
  /* The native settler rule has a one-company repeat penalty. Suppress that
   * penalty only while this builder type has unmatched settlement demand. */
  {U def=f->recruitScope==obj?f->recruitDefinition:(!property?key:0),target;
   if(def&&(!property||ids_equal(key,"role_settler"))&&(target=economy_center(def,0,0))&&builder_missing(image,d,obj,target)>0)after=0;
  }
  *(U*)result=after;
  if(before!=after)emit(image,d,55,obj,obj,property?0:key,property?2:1,(float)before,(float)after,0,0,0,0);
 }
}
