from context import *
import control as c,time,json,shutil
from network_run import hook

def command(s):c.command('host',s);time.sleep(.18)
def view():command('!capture-view');return read(c.folder('host')/'game/Mods/capture-view.json')
def main():
 c.start('host');c.wait(lambda:c.state('host').get('phase')==3,90,'Pure SP menu')
 for s in ['RequestSinglePlayer','RequestCustom','SelectLaunchType RANDOM_MAP','Commit','StagingLaunch']:command(s)
 c.wait(lambda:c.state('host').get('world')and c.state('host').get('mode')==2,100,'Pure SP world');command('UserReady');c.wait(lambda:c.state('host').get('phase')==4 and not c.state('host').get('frozen'),80,'Pure SP HUD');command('GamePause 1');before=view();write(O/(c.MODE+'-capture-before.json'),before)
 local=before['local'];cities=[a for a in before['actors']if '_center_'in a['name']and a['capturable']];own=next(a for a in cities if a['owner']==local);enemyCity=next(a for a in cities if a['owner']not in [0,local]);enemy=enemyCity['owner']
 # Retain a second settlement so the loss of the original cannot eliminate the tester.
 command(f"!sp-owner {enemyCity['id']} {local}")
 command(f"!sp-org company_bowman {enemy} {own['x']+3} {own['y']+3}")
 prepared=view();attacker=max((a for a in prepared['actors']if a['owner']==enemy and a['name']=='company_bowman'),key=lambda a:a['id'])
 command(f"!sp-capture {own['id']} {attacker['id']}");after=view();city=next(a for a in after['actors']if a['id']==own['id']);assert city['owner']==enemy and city['knownOwner']==enemy and city['color']!=own['color'],city
 result=dict(passed=True,mode=c.MODE,nativeCombatCapture=True,controlledSinglePlayerSetup=True,knownOwnerAndMinimapColorUpdated=True,beforeColor=own['color'],local=local,newOwner=enemy,city=city,hook=hook('host'),networkCaptureClaimed=False);write(O/(c.MODE+'-capture-after.json'),after);write(O/(c.MODE+'-capture-result.json'),result)
 command('Screenshot');time.sleep(.5)
 shots=c.folder('host')/'Documents/Kohan2/data/Screenshots'
 if shots.exists():
  pngs=list(shots.glob('*.png'))
  if pngs:shutil.copy2(max(pngs,key=lambda f:f.stat().st_mtime_ns),O/(c.MODE+'-capture.png'))
 command('ReallyQuit');c.wait(lambda:not c.own(),30,'Pure SP clean exit');print('PURE_NATIVE_CAPTURE_PASS',c.MODE,city['id'],city['owner'],city['knownOwner'],flush=True)
if __name__=='__main__':main()
