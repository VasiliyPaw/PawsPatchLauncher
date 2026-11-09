"""Scoped adaptation: test saves while recovery is explicitly absent."""
from context import *
source=REPO/'game/reconnect-test/installed_saves_pair.py'
code=source.read_text();anchor="  for cycle in range(1,a.recovery_cycles+1):"
assert code.count(anchor)==1
replacement='''  prior=list(saves(h).glob('Paw Resume*.RSG'))
  stop(c);report('Client disconnected with automatic recovery disabled');stay(12)
  if snapshot(h).get('backup'):command(h,'CSDKickLaggingPlayers 0')
  command(h,'GamePause 0');stay(5);before=snapshot(h);stay(15);after=snapshot(h)
  checked('no-automatic-lobby-return',after.get('state')==2 and after.get('world')==before.get('world'))
  checked('no-recovery-save',list(saves(h).glob('Paw Resume*.RSG'))==prior and 'RESUME_READY:' not in log(h))
  checked('host-continues-after-client-loss',after.get('seconds',0)>before.get('seconds',0)+3)
  command(h,'ReallyQuit');h['required']=False;h['process'].wait(timeout=30)
  checked('normal-host-exit',h['process'].returncode==0);checked('no-assert-desync',not errors())
  (root/'result.json').write_text(json.dumps(dict(passed=True,checks=checks,runtimeHashes=expected,environment='two isolated local LAN processes',autosaveMinutes=5,automaticRecovery=False),indent=2));report('PASS saves retained and recovery disabled');return
'''+anchor
code=code.replace(anchor,replacement)
anchor="  for slot in 'AB'[:a.slots]:";assert code.count(anchor)==1
code=code.replace(anchor,"  command(h,'SpeedUp\\nSpeedUp\\nSpeedUp\\nSpeedUp')\n"+anchor)
# A supplied loader is hash-checked by the original runner. No production
# helper is changed; the existing reflection harness installs its exact bytes.
exec(compile(code,str(source),'exec'),{'__name__':'__main__','__file__':str(source)})
