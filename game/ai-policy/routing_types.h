#define ROUTE_THREATS 512
typedef struct { float x,y,radius,weight,startDistance2,strength; U id; } RouteThreat;
typedef struct { U serial,world,actor,kingdom,builder,threats,changed; float strength,x,y,time; U commit; } RouteReport;
typedef struct { U image,world,thread,actor,kingdom,player,builder,count,changed,depth,frame;
 float sx,sy,tx,ty,strength; RouteThreat threats[ROUTE_THREATS]; RouteReport report; } Route;
