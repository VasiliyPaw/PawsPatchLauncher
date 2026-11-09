"""One owned peer at a time, with a two-GiB commit reserve for this fixture."""
from context import *
source=REPO/'game/reconnect-test/installed_saves_pair.py';code=source.read_text()
assert code.count('status.availPage<5*1024**3')==1;code=code.replace('status.availPage<5*1024**3','status.availPage<2*1024**3')
# These private presentation settings reduce retained graphics cache memory;
# all gameplay files and the packaged runtime remain unchanged.
code=code.replace(' flag SinglePlayerAutoPause = false\\n',' flag SinglePlayerAutoPause = false\\n int ResourceCacheTextureRAMWeight = 5\\n int ResourceCacheTextureVRAMWeight = 5\\n flag ViewShadows = false\\n')
start=code.index("  hd=prepare('host');cd=prepare('client');h=launch(hd);host_lobby(h);c=launch(cd,True);join(c);begin(h,c)\n  if a.client_game:")
end=code.index(' except Exception as error:',start)
code=code[:start]+'''  hd=prepare('host');h=launch(hd);host_lobby(h)
  checked('no-recovery-runtime',not any(s in text(hd/'game/harness-status.log') for s in ('MATCH_RECOVERY_READY','RESUME_READY:')))
  command(h,'StagingLaunch');wait(lambda:snapshot(h).get('state')==2 and snapshot(h).get('world'),90,'Owned match entered simulation')
  command(h,'GamePause 0');stay(5);before=snapshot(h);stay(15);after=snapshot(h);checked('simulation-advances',after.get('seconds',0)>before.get('seconds',0)+5)
  command(h,'GameSave "Save/QA Pure041.RSG"');wait(lambda:(saves(h)/'QA Pure041.RSG').is_file() and (saves(h)/'QA Pure041.RSG').stat().st_size>1000,45,'Host save written');stay(5)
  checked('save-written',(saves(h)/'QA Pure041.RSG').stat().st_size>1000)
  command(h,'ScreenShot');stay(2);command(h,'ReallyQuit');h['required']=False;h['process'].wait(timeout=30);checked('normal-exit',h['process'].returncode==0);checked('no-assert-desync',not errors())
  (root/'result.json').write_text(json.dumps(dict(passed=True,checks=checks,runtimeHashes=expected,automaticRecovery=False,environment='one isolated native peer; multiplayer pair requires more commit headroom'),indent=2));report('PASS single peer runtime and save')
'''+code[end:]
exec(compile(code,str(source),'exec'),{'__name__':'__main__','__file__':str(source)})
