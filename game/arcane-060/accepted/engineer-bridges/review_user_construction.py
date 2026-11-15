"""Monitor a real mouse-accepted native build in the disposable user world."""
from pathlib import Path
driver=Path(__file__).with_name('review_user_bridges.py')
exec(compile(driver.read_text().split("send('GameSpeed")[0],str(driver),'exec'))
before=state()['completed'];send('GamePause 0');send('!peace-fixture')
try:
 result=wait(lambda s:s['completed']>before,'construction',90)
finally:send('GamePause 1')
target=r/'qa-evidence/final-mouse-construction-actors.json'
subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('observe.py')),'--out',str(r),'--save',str(target)],check=True,stdout=subprocess.DEVNULL)
actors=json.loads(target.read_text())['actors'];bridges=[v for v in actors if v['name'].startswith('paws_bridge_')]
assert len(bridges)==3
new=next(v for v in bridges if v['id'] not in [4882,4909])
assert new['health']==1000 and not new['construction'] and new['paidConstructionCost'][0]==75,new
send('GameSave Save/R6-fixed-bridges-check.RSG')
(r/'qa-evidence/final-mouse-construction.json').write_text(json.dumps(dict(passed=True,siteId=new['id'],mouseAccepted=True,health=new['health'],paid=new['paidConstructionCost'],time=result['time'],combatIsolated=True,snapshot=str(target),save='R6-fixed-bridges-check.RSG'),indent=2))
print('NATIVE_MOUSE_CONSTRUCTION_PASS',new['id'],result['time'],flush=True)
