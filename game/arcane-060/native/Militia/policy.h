/* Per-attacker response; never changes a database guard/search radius. */
typedef struct {unsigned home,target,owner,enemy;float x,y,limit2,last;} Alert;
#define ALERT_COUNT 512
#define ALERT_LIFETIME 30.f
#define RETREAT_ALLOWANCE 6.f
#define MAX_EXTRA_RANGE 96.f
static float sq(float x){return x*x;}
static int number(float x){return x==x&&x>-100000.f&&x<100000.f;}
static int alert_position(Alert*a,float hx,float hy,float tx,float ty,float time){
 if(!number(time)||!number(tx)||!number(ty)||!number(hx)||!number(hy))return 0;
 if(time<a->last||time-a->last>ALERT_LIFETIME)return 0;
 return sq(tx-hx)+sq(ty-hy)<=a->limit2;
}
