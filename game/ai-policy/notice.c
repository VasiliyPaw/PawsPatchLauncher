/* Presentation only, after the unmodified native diagnostic logger.
 * No AI budget, worker synchronization, goal evaluation or simulation clock
 * is changed. The wrapper bypasses formatting/UI only, before allocation. */
static void goal_notice(U image,Data*d,float*result){
 FastData*f=(FastData*)d;U now,world=P(image,0x5f3fb8);
 *(U*)result=0;
 if(!(d->mask&8)||!world||P(image,0x5f9218)!=2)return;
 now=((EconomyM0)(image+0x29c19a))(image+0x5f9238,0);
 if(f->noticeWorld!=world||!f->noticeSeen||now-f->noticeTime>=300000){
  f->noticeWorld=world;f->noticeTime=now;f->noticeSeen=1;return;
 }
 *(U*)result=1;
}
