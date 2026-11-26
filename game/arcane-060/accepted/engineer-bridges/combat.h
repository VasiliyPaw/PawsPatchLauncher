/* Filter only automatic company/unit candidate scans. Direct native attack
 * commands, diplomacy, cursor targeting and damage retain their normal rules. */
/* Geometry deliberately excludes menu prototypes. Combat must also recognise
 * old, mistakenly spawned *_site actors, otherwise the automatic target
 * exclusion silently misses the exact actors that stock SAI built on land. */
static int bridge_combat_target(U a){U n,axis;return a&&(bridge_kind(P(a,4),&n,&axis)||bridge_menu_prototype(P(a,4)));}
static int bridge_explicit_attack(U mind,U id){U cmd=mind?P(mind,0x20):0,def=cmd?P(cmd,8):0;return def&&(P(def,0xc)==0||P(def,0xc)==1)&&(P(cmd,0xc)&1)&&P(cmd,0x10)==id;}
static int bridge_ordered_attack(U source,U target){U e,company;if(!source||!target)return 0;if(bridge_explicit_attack(P(source,0x70),P(target,0x14)))return 1;e=P(source,0x80);company=e?P(e,0x10):0;return company&&bridge_explicit_attack(P(company,0x70),P(target,0x14));}
static int bridge_automatic_target(Roads*d,U mind,U a){return d&&a&&allowed(d)&&bridge_combat_target(a)&&!bridge_explicit_attack(mind,P(a,0x14))&&!bridge_ordered_attack(mind?P(mind,4):0,a);}
EXPORT U FAST bridge_auto_organization(U org,U unused,U target,U visible,U members){Roads*d=current;U args[3];
 if(d&&allowed(d)&&bridge_combat_target(target)&&!bridge_ordered_attack(P(org,4),target))return 0;
 args[0]=target;args[1]=visible;args[2]=members;return ((NativeCall)d->call)(d->image+0x216535,org,3,args);
}
/* Rampaging neutral companies have their own attack activation path, outside
 * the ordinary candidate scans. Saved attacks need the same exclusion. */
EXPORT U FAST bridge_attack_activate(U self,U unused,U mode,U target){Roads*d=current;U args[2];
 if(bridge_automatic_target(d,P(self,4),target))return 0;
 args[0]=mode;args[1]=target;return ((NativeCall)d->call)(d->image+0x27031c,self,2,args);
}
EXPORT U bridge_attack_tick(Roads*d,U self){U a=actor(d,P(self,0x10));
 if(bridge_automatic_target(d,P(self,4),a)){m0(d,0x279072,self);P(self,0x10)=0;return 0;}
 return m0(d,0x270431,self);
}
EXPORT U FAST bridge_auto_candidate(U ai,U unused,U target){Roads*d=current;
 if(d&&allowed(d)&&bridge_combat_target(target)&&!bridge_ordered_attack(P(ai,4),target))return 0;
 return ((M1)P(P(ai,0),0xa4))(ai,0,target);
}
EXPORT U FAST bridge_auto_collision(U source,U unused,U target){Roads*d=current;
 if(d&&allowed(d)&&bridge_combat_target(target)&&!bridge_ordered_attack(source,target))return 0;
 return ((M1)P(P(source,0),0x16c))(source,0,target);
}

/* Individual UAI kill/bombard states have their own direct activation paths.
 * This also covers summoned actors without an OrganizationComponent. Do not
 * guess a summon flag: the same noncombat bridge policy applies to every unit.
 * Explicit unit or parent-company attack orders remain native; unrelated
 * targets, damage, area effects and ordinary retaliation are untouched. */
EXPORT U FAST bridge_unit_attack_activate(U self,U unused,U mode,U target){Roads*d=current;U args[2];
 if(bridge_automatic_target(d,P(self,4),target))return 0;
 args[0]=mode;args[1]=target;return d?((NativeCall)d->call)(d->image+0x281899,self,2,args):0;
}
EXPORT U FAST bridge_unit_bombard_activate(U self,U unused,U mode,U target){Roads*d=current;U args[2];
 if(bridge_automatic_target(d,P(self,4),target))return 0;
 args[0]=mode;args[1]=target;return d?((NativeCall)d->call)(d->image+0x281c95,self,2,args):0;
}
/* Saved automatic attacks may already be active before an acquisition hook
 * runs. Native deactivation releases the actual weapon/movement target; only
 * zeroing the state ID would leave that target active on the actor. */
EXPORT void FAST bridge_unit_attack_tick(U self,U unused){Roads*d=current;U a=d?actor(d,P(self,0x10)):0;
 if(bridge_automatic_target(d,P(self,4),a)){m0(d,0x281915,self);P(self,0x10)=0;return;}
 if(d)m0(d,0x281928,self);
}
EXPORT void FAST bridge_unit_bombard_tick(U self,U unused){Roads*d=current;U a=d?actor(d,P(self,0x10)):0;
 if(bridge_automatic_target(d,P(self,4),a)){m0(d,0x281e76,self);P(self,0x10)=0;return;}
 if(d)m0(d,0x281ec6,self);
}
EXPORT U bridge_combat_target_check(U a){return bridge_combat_target(a);}
