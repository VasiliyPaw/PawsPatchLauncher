/* Kohan II 1.3.72, presentation-only audio routing. Never changes actors,
   kingdom state, simulation RNG, orders, resources or network messages. */
typedef unsigned int U;
typedef unsigned short W;
#define P(p,o) (*(U*)((U)(p)+(o)))
typedef struct { U magic,image,language[6],calls,switched,last_faction,last_language,get_kingdom; } Data;
int __attribute__((stdcall)) _dllstart(void*m,U r,void*u){return 1;}
static U upper(U c){return c>='a'&&c<='z'?c-32:c;}
static int eq(W*w,char*a){U i;if(!w)return 0;for(i=0;i<80&&a[i];i++)if(upper(w[i])!=upper((unsigned char)a[i]))return 0;return i<80&&!a[i]&&!w[i];}
typedef U (*Owner)(U);
static U faction(Data*d,U k,U actor){
 U f,def,vt;
 if(!k&&actor){
  vt=P(actor,0);if(!vt||P(vt,0xb4)!=d->image+0x21250)return 5;
  k=((Owner)d->get_kingdom)(actor);
 }
 if(!k)return 5;
 f=P(k,0x23c);if(!f)return 5;def=P(f,4);if(!def)return 5;
 if(eq((W*)P(def,8),"royalist"))return 0;
 if(eq((W*)P(def,8),"council"))return 1;
 if(eq((W*)P(def,8),"nationalist"))return 2;
 if(eq((W*)P(def,8),"ceyah"))return 3;
 if(eq((W*)P(def,8),"fallen"))return 4;
 return 5;
}
/* Exact native DataCollection hash/lookup, collection dictionary at +0x30.
   Our generated IDs never use the engine's aliases or string ownership API. */
static U lookup(U image,W*id){
 U db=P(image,0x5f3fb4),table,n,hash=0,i,node,obj;W*s;
 if(!db)return 0;table=P(db,0x584);if(!table)return 0;
 n=P(table,0x34);table=P(table,0x30);if(!table||!n||n>65536)return 0;
 for(i=0;i<128&&id[i];i++)hash=hash*33+upper(id[i]);if(i==128)return 0;
 node=P(table,(hash%n)*4);
 for(i=0;node&&i<128;i++,node=P(node,4)){
  U j;obj=P(node,0);if(!obj)continue;s=(W*)P(obj,8);if(!s)continue;
  for(j=0;j<128&&s[j]&&id[j]&&upper(s[j])==upper(id[j]);j++);
  if(j<128&&!s[j]&&!id[j])return obj;
 }
 return 0;
}
__attribute__((dllexport)) U select_voice(Data*d,U audio,U kingdom,U actor){
 U f,lang,i,j,result;W key[128],*source;char*prefix="paws_voice_";char*codes="enrudefr";
 if(!d||d->magic!=0x56574346||!audio)return audio;
 d->calls++;f=faction(d,kingdom,actor);lang=d->language[f];d->last_faction=f;d->last_language=lang;
 if(lang>3||lang==d->language[5]||f==5)return audio;
 source=(W*)P(audio,8);if(!source)return audio;
 for(i=0;prefix[i];i++)key[i]=(unsigned char)prefix[i];
 key[i++]=(unsigned char)codes[lang*2];key[i++]=(unsigned char)codes[lang*2+1];key[i++]='_';
 for(j=0;j<80&&source[j];j++)key[i++]=source[j];if(j==80)return audio;key[i]=0;
 result=lookup(d->image,key);if(!result)return audio;
 d->switched++;return result;
}
