/* Software-test commands, excluded from the playable candidate DLL. */
static unsigned char FC qa_recon_cast(U self,U unused,U x,U y){typedef unsigned char(FC*Recon)(U,U,U,U);unsigned char result;U source=P(self,4);(void)unused;
 result=((Recon)(base+0x209a4e))(self,0,x,y);host->log("ui-scout-test","QA_RECON_EXECUTE source=%u target=%.2f,%.2f result=%u",source?P(source,0x14):0,*(float*)&x,*(float*)&y,(unsigned)result);return result;
}
X U __cdecl Test_Entry(U image,U fixtureHost,unsigned which){base=image;host=(Host*)fixtureHost;switch(which){case 1:return(U)allowed;case 2:return(U)air_orders;case 3:return(U)classify;case 4:return(U)inverse;case 5:return(U)project;case 6:return(U)map_draw;case 7:return(U)mini_update;case 8:return(U)air_update;case 9:return(U)wheel_zoom;case 10:return(U)quad_update;case 11:return(U)&zoom;case 12:return(U)far_region;case 13:return(U)day_minutes;case 14:return(U)remember_recon;case 15:return(U)clock_for;case 16:return(U)day_existing;case 17:return(U)day_clock_tick;default:return(U)cooldowns;}}
X void __cdecl Test_View(U widget,float scale,float x,float y){mapWidget=widget;zoom=scale;cx=x;cy=y;}
static void qa_run(const wchar_t*command){wchar_t*text=0;U console=P(P(base,0x13df08),0);if(!console)return;
 typedef void*(FC*StringFn)(void*,void*,const wchar_t*);typedef void(FC*RunFn)(void*,void*,void*,int);
 ((StringFn)(base+0x205de))(&text,0,command);
 host->log("ui-scout-test","QA_STRING text=%x header=%x first=%x",(unsigned)text,text?P((U)text-16,0):0,text?P(text,0):0);
 ((RunFn)(base+0x1f9963))((void*)console,0,&text,0);
 ((Void0)(base+0x21375))((U)text-16,0);
}
static void qa_recon(void){U sai=P(base,0x5f3fc8),i;if(!sai)return;
 for(i=0;i<P(sai,0x70)&&i<32;i++){U pl=P(P(sai,0x6c),i*4),node,steps=0;if(!pl)continue;
  for(node=P(pl,0x4c);node&&steps++<4096;node=P(node,4)){U actor=((Get1)(base+0x21117))(P(base,0x5ef72c),0,P(node,0)),denizen,group,j=0;
   if(!actor||P(actor,0)!=base+0x4e5c58)continue;if(P(actor,0x98)&&P(P(actor,0x98),0x14))actor=P(P(actor,0x98),0x14);
   if(P(actor,0)!=base+0x4e5c58||P(actor,0x14)>100||!(denizen=P(actor,0x88)))continue;
   for(group=P(denizen,0x18);group&&j++<32;group=P(group,0x10)){U def=P(group,4),active=P(group,0),unit=active?((Get1)(base+0x21117))(P(base,0x5ef72c),0,active):0;const wchar_t*name=def?(wchar_t*)P(def,8):L"?";
    if(!name||!wcsstr(name,L"scout"))continue;
    host->log("ui-scout-test","QA_RECON_UNIT kingdom=%u source=%u inventory=%x definition=%ls active=%u actor=%x vtable=%x position=%.2f,%.2f hp=%.1f",P(P(pl,8),0x194),P(actor,0x14),group,name,active,unit,unit?P(unit,0)-base:0,unit?F(unit,0x20):0,unit?F(unit,0x24):0,unit&&P(unit,0x60)?F(P(unit,0x60),0x10):0);
   }
  }
 }
}
static void qa_tick(void){static DWORD last;static unsigned serial,panFrame,panRemaining,panHome;wchar_t path[MAX_PATH];FILE*f;unsigned id;char cmd[500];U world=P(base,0x5f3fb8),session=P(base,0x5f3fe4),ve=mapWidget?P(mapWidget,0x74):0;
 if(panRemaining&&match()){wchar_t move[80];unsigned step=panFrame%120;swprintf(move,L"LookAt %u %u",panHome?900+(step<60?step:120-step)*2:300+(step<60?step:120-step)*6,panHome?560+step/2:350+step*2);qa_run(move);if(panFrame==30||panFrame==90||panFrame==150)qa_run(L"ScreenShot");panFrame++;panRemaining--;if(!panRemaining)host->log("ui-scout-test","QA_CONTINUOUS_PAN_COMPLETE frames=%u home=%u",panFrame,panHome);}
 if(GetTickCount()-last<250)return;last=GetTickCount();
 swprintf(path,L"%ls\\qa-state.json",host->modsDir);f=_wfopen(path,L"w");if(f){fprintf(f,"{\"pid\":%lu,\"base\":%u,\"phase\":%u,\"world\":%u,\"session\":%u,\"mode\":%u,\"seconds\":%.3f,\"match\":%u,\"zoom\":%.2f,\"cx\":%.4f,\"cy\":%.4f,\"mapWidget\":%u,\"ve\":%u,\"bounds\":[%.2f,%.2f,%.2f,%.2f],\"command\":%u}",GetCurrentProcessId(),base,P(base,0x5f92f4),world,session,session?P(session,0xf0):0,world?F(world,0xe8):0,match()?1:0,zoom,cx,cy,mapWidget,ve,ve?F(ve,0x20):0,ve?F(ve,0x24):0,ve?F(ve,0x28):0,ve?F(ve,0x2c):0,serial);fclose(f);}
 swprintf(path,L"%ls\\qa-command.txt",host->modsDir);f=_wfopen(path,L"r");if(!f)return;id=0;cmd[0]=0;fscanf(f,"%u %499[^\n]",&id,cmd);fclose(f);if(id<=serial)return;serial=id;
 if(!strcmp(cmd,"!recon"))qa_recon();
 else if(!strcmp(cmd,"!dynamic")&&world){U rule=day_rule(world,"Sun"),data=rule?P(rule,0):0,j;typedef void(FC*SetEnum)(U,U,U,U);if(data)for(j=0;j<P(data,0x38)&&j<128;j++)if(day_id(P(P(data,0x34),j*8),"paws_dynamic_sun")){((SetEnum)(base+0x296c07))(world+0xc,0,data,j);break;}}
 else if(!strcmp(cmd,"!clock")){U v=dayWidget?P(dayWidget,0x6c):0,r=world?day_rule(world,"PawsDayPhase"):0;host->log("ui-scout-test","DAY_CLOCK_STATE minutes=%d seconds=%.4f phase=%u widget=%x ve=%x text=%ls bounds=%.1f,%.1f,%.1f,%.1f",day_minutes(world),world?F(world,0xe8):0,r?P(r,8):0,dayWidget,v,v?(wchar_t*)P(v,0xc8):L"",v?F(v,0x20):0,v?F(v,0x24):0,v?F(v,0x28):0,v?F(v,0x2c):0);}
 else if(!strncmp(cmd,"!pan",4)){panFrame=0;panRemaining=180;panHome=strstr(cmd,"home")!=0;}
 else if(!strcmp(cmd,"!save")){U order[2];wchar_t*name=0;((Void1)(base+0x205de))((U)&name,0,(U)L"Save/TestSave.RSG");((Void1)(base+0x121bd0))((U)order,0,(U)&name);((Void1)(base+0x122822))((U)order,0,0);if(order[1])((Void0)(base+0x21375))(order[1]-16,0);((Void0)(base+0x21375))((U)name-16,0);}
 else if(!strncmp(cmd,"!wheel",6)&&ve){POINT point;int delta=cmd[6]=='-'?-120:120;point.x=(int)((F(ve,0x20)+F(ve,0x28))*.5f);point.y=(int)((F(ve,0x24)+F(ve,0x2c))*.5f);ClientToScreen(gameWindow,&point);window_proc(gameWindow,WM_MOUSEWHEEL,MAKEWPARAM(0,delta),MAKELPARAM(point.x,point.y));}
 else if(!strncmp(cmd,"!stats",6)&&world){U reg=P(base,0x5ef72c),i;for(i=0;i<65536;i++){U actor=P(reg,0x20004+i*4);if(actor&&P(actor,0)==base+0x4e5c58){U def=P(actor,4);const wchar_t*name=def?(wchar_t*)P(def,8):0;if(name&&(wcsstr(name,L"fort")||wcsstr(name,L"keep")))host->log("ui-scout-test","STAT_CLASS id=%u name=%ls native=%d patched=%d",P(actor,0x14),name,((int(__cdecl*)(U))(base+0x25e971))(actor),classify(actor));}}}
 else {wchar_t wide[500];mbstowcs(wide,cmd,499);wide[499]=0;qa_run(wide);}
 host->log("ui-scout-test","QA_COMMAND %u %s",id,cmd);
}
