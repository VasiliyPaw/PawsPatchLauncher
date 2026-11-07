/* Native 1.3.72 WorldRules: GWorld+0x0c, records at +0x0c, count at
 * +0x10; each record is (WorldRuleData*, locked, value), 12 bytes.
 * Definitions/enum IDs are compared, never localized display strings. */
static int rule_id(W *value,const char *id){
 U i=0,a,b;if(!value)return 0;
 do{a=value[i];b=(unsigned char)id[i];if(a>='A'&&a<='Z')a+=32;if(b>='A'&&b<='Z')b+=32;
 if(a!=b)return 0;if(!a)return 1;i++;}while(i<160);return 0;
}
static U world_rule(U world,const char *id){
 U items,n,i,p,data;if(!world)return 0;items=R(world,0x18);n=R(world,0x1c);
 if(!items||n>256)return 0;
 for(i=0;i<n;i++){p=items+i*12;data=R(p,0);if(data&&rule_id((W*)R(data,8),id))return p;}
 return 0;
}
static int rule_enum(U world,const char *id,const char *value){
 U p=world_rule(world,id),data,index;if(!p)return 0;data=R(p,0);index=R(p,8);
 if(R(data,0x20)!=3||index>=R(data,0x38)||index>128)return 0;
 return rule_id((W*)R(R(data,0x34)+index*8,0),value);
}
