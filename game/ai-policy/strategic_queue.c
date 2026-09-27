/* Native ScheduleThink inserts by deadline, then repeatedly moves every later
 * deadline to maintain a global gap. Short-period players can consequently
 * push long-period players back forever. Preserve the insertion deadlines and
 * apply that same gap when the strategic scheduler peeks its next entry.
 * Native allocation, sorting, duplicate handling, player exclusion and yields
 * remain authoritative. No queue nodes or links are edited by the policy.
 */
static void strategic_queue(U image,Data*d,U mode,U obj,U*args,float*result){
 U sai=P(image,0x5f3fc8),world=P(image,0x5f3fb8),setting;
 float time,gap,due;StrategicClock*c=&((FastData*)d)->strategicClock;
 if(mode==52)*(U*)result=0;
 if(!(d->mask&8)||!sai||obj!=sai+0x58||!world||P(image,0x5f9218)!=2)return;
 time=F(world,0xe8);if(!finite(time))return;
 setting=P(image,0x5fcd78);
 /* Let the first native insertion initialize its cached SVar normally. */
 if(!setting)return;gap=F(setting,0);if(!finite(gap)||gap<0)return;
 if(mode==52){*(U*)result=1;return;}
 if(c->world!=world||c->sai!=sai||(c->valid&&time<c->last))c->valid=0;
 if(mode==54){if(*(U*)result&255){c->world=world;c->sai=sai;c->last=time;c->valid=1;}return;}
 /* Only adjust the scheduler's temporary peek result, never the stored due
  * time. An excluded/busy player or a future entry must not consume a turn. */
 if(!(*(U*)result&255)||!args[0]||!c->valid)return;
 due=c->last+gap;
 if(finite(due)&&finite(F(args[0],4))&&F(args[0],4)<due)F(args[0],4)=due;
}
