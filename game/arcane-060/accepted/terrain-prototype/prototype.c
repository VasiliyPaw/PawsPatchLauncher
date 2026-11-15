/* Local single-player feasibility probe. No builder UI or network command. */
typedef unsigned int U;
typedef unsigned short W;
int __attribute__((stdcall)) _dllstart(void *module,U reason,void *reserved) { return 1; }
#define R(p,o) (*(U *)((U)(p)+(o)))
#define B(p,o) (*(unsigned char *)((U)(p)+(o)))
typedef U (*NativeCall)(U fn,U self,U count,U *args);
typedef struct {
    U image, call, serial, completed, result, expected_world;
    U x0,y0,x1,y1,kind,world,map,width,height,tick,changed,before,after;
    U variant, requests, guard, padding;
} State;

static U invoke(State *s,U rva,U self,U n,U a,U b,U c) {
    U args[3]; args[0]=a; args[1]=b; args[2]=c;
    return ((NativeCall)s->call)(s->image+rva,self,n,args);
}
static int eq(W *wide,char *ascii) {
    int i; if(!wide)return 0;
    for(i=0;i<80 && ascii[i];i++)if(wide[i]!=(unsigned char)ascii[i])return 0;
    return !ascii[i] && !wide[i];
}
static U variation(State *s,U kind) {
    U manager=R(s->image,0x5f0030), i, count, array, p;
    char *name=kind==0?"temperate_grass01":kind==1?"temperate_river01":"temperate_road01";
    if(!manager)return 0;
    count=R(manager,0x28);array=R(manager,0x24);
    if(count>4096 || !array)return 0;
    for(i=0;i<count;i++) {
        p=R(array,i*4);
        if(p && R(p,0)==s->image+0x4741e8 && eq((W*)R(p,8),name))return p;
    }
    return 0;
}
__attribute__((dllexport)) void tick(State *s,U world) {
    U map,session,point[2],ctx[8],x,y,tile,variant,i,serial;
    s->world=world;s->tick++;
    if(!world)return;
    map=R(world,0x30);s->map=map;
    if(!map)return;
    s->width=R(map,0x1c);s->height=R(map,0x20);
    serial=s->serial;if(serial==s->completed)return;
    s->requests++;s->result=1;s->changed=0;
    session=R(s->image,0x5f3fe4);
    /* Refuse multiplayer, editor, stale world and unexpectedly large worlds. */
    if(!session || B(session,0x100) || R(session,0xf0)!=2 ||
       R(world,0xd8)==6 || s->expected_world!=world ||
       !s->width || !s->height || s->width>128 || s->height>128 ||
       s->x0>s->x1 || s->y0>s->y1 || s->x1>=s->width || s->y1>=s->height ||
       (s->x1-s->x0+1)*(s->y1-s->y0+1)>2048 || s->kind>2)goto done;
    variant=variation(s,s->kind);s->variant=variant;
    if(!variant){s->result=2;goto done;}
    tile=R(map,0x28)+(s->y0*s->width+s->x0)*0x30;
    s->before=R(tile,0x20);
    for(i=0;i<8;i++)ctx[i]=0;
    invoke(s,0x2517a3,(U)ctx,0,0,0,0);
    for(y=s->y0;y<=s->y1;y++)for(x=s->x0;x<=s->x1;x++){
        point[0]=x;point[1]=y;
        invoke(s,0x2517f9,(U)ctx,2,(U)point,variant,0);
    }
    /* Native transition rules, blocking bits, terrain-property notifications,
       renderer invalidation. No doodad spawning for this feasibility test. */
    invoke(s,0x25185b,(U)ctx,1,0,0,0);
    invoke(s,0x20d4b,(U)(ctx+3),0,0,0,0);
    invoke(s,0x20d4b,(U)(ctx+5),0,0,0,0);
    invoke(s,0x2424b2,world,1,0,0,0);
    for(y=s->y0;y<=s->y1;y++)for(x=s->x0;x<=s->x1;x++){
        tile=R(map,0x28)+(y*s->width+x)*0x30;
        if(R(tile,0)==variant)s->changed++;
    }
    tile=R(map,0x28)+(s->y0*s->width+s->x0)*0x30;
    s->after=R(tile,0x20);s->result=0;
done:s->completed=serial;
}
