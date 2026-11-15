/* Native VFXModel detachment reparents the model with its local rotation.
 * Stock round construction particles hide that change; a bridge-length strip
 * visibly turns when its old parent carried the bridge's heading. Preserve
 * that world rotation through the ordinary native stop/fade lifecycle. */
static void bridge_effect_detach(U fx,U native){Roads*d=current;U def,model=0,root=0,parent=0,i,j,k;float rotation[9],relative[9];
 if(!d)return;
 def=P(fx,0x10);
 if(def&&(bridge_prefix((W*)P(def,8),"paws_bridge_haroun_growth_")||bridge_prefix((W*)P(def,8),"paws_bridge_haroun_finish_")||bridge_prefix((W*)P(def,8),"paws_bridge_build_"))&&(model=P(fx,0xac))&&(P(model,4)&2)&&(root=P(model,12))&&(parent=P(root,0x24))){
  for(i=0;i<9;i++){rotation[i]=F(root,0x6c+i*4);if(!finite(rotation[i])){root=0;break;}}
 }
 m0(d,native,fx);
 if(!root||P(fx,0xac)!=model||P(model,12)!=root||P(root,0x24)==parent)return;
 parent=P(root,0x24);
 for(i=0;i<3;i++)for(j=0;j<3;j++){
  float value=0;
  for(k=0;k<3;k++)value+=(parent?F(parent,0x6c+(k*3+i)*4):(k==i?1.0f:0.0f))*rotation[k*3+j];
  if(!finite(value))return;relative[i*3+j]=value;
 }
 for(i=0;i<9;i++){F(root,0x38+i*4)=relative[i];F(root,0x6c+i*4)=rotation[i];}
}
/* Run after the complete release operation: it detaches, updates the model,
 * and attaches it to the world scene again for the remaining particle fade. */
EXPORT void FAST bridge_growth_release(U fx,U unused){bridge_effect_detach(fx,0x2cedb4);}
