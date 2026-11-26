/* Restrict the dry-river correction to generated blocked water. Existing
 * lakes keep native depth; passable bog/ice/quicksand keep native shallow beds. */
static int water_depth_generated(unsigned shape,unsigned nativeBlocked,unsigned river,unsigned flags){
 return (flags&0x170)==0x120 && (river || (shape&&!nativeBlocked));
}
static float water_bed_target(unsigned bankDistance){
 if(bankDistance>5)bankDistance=5;
 return -.25f-(float)bankDistance*.25f;
}
