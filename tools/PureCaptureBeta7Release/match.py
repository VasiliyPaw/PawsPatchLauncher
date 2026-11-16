from control import *
from context import O

def complete_file(path,data):
 try:return path.exists() and path.read_bytes()==data
 except OSError:return False

def fixture_name():
 return sys.argv[sys.argv.index('--fixture-name')+1]if '--fixture-name'in sys.argv else 'R17-bridge-fixture.RSG'
def native(r,c,pause=.7):command(r,c);time.sleep(pause)
def open_lan(r,name):
 wait(lambda:state(r).get('phase')==3,60,r+' menu')
 for c in ['RequestMultiplayer','RequestLobbyLAN','LobbySetLANNickname '+name,'MessageBoxButtonAction 1']:native(r,c)
def lobby():
 for r in ROLES:start(r)
 open_lan('host','CaptureHost');native('host','!port 6221');native('host','InternetGameCreate PureBeta7Private 3 2')
 if '--fixture'in sys.argv:native('host','!fixture Save/'+fixture_name(),2)
 else:native('host','SelectLaunchType RANDOM_MAP');native('host','Commit');native('host','TeamFormatDropdown 2v2')
 for r,name in [('client','CaptureClient'),('witness','CaptureWitness')]:
  open_lan(r,name);native(r,'LobbyJoinDirect');native(r,'JoinDirectJoin');wait(lambda:state(r).get('mode')==1,50,r+' join')
 (O/'lobby-three-humans.json').write_text(json.dumps({r:state(r)for r in ROLES},indent=2));print('THREE_HUMANS_JOINED',flush=True)
def launch():
 if state('host').get('mapType')==2:
  import hashlib
  name=fixture_name();source=folder('host')/'Documents/Kohan2/data/Save'/name
  if source.exists():
   data=source.read_bytes()
   for r in ['client','witness']:
    wait(lambda:complete_file(folder(r)/'Documents/Kohan2/data/Save'/name,data),90,r+' complete native fixture transfer')
 for r in ['client','witness']:native(r,'StagingReady 0')
 native('host','StagingLaunch');native('host','MessageBoxButtonAction 0')
 wait(lambda:all(state(r).get('mode')==2 and state(r).get('world')for r in ROLES),90,'three worlds')
 for r in ROLES:native(r,'UserReady',.2)
 wait(lambda:all(state(r).get('phase')==4 and not state(r).get('frozen')for r in ROLES),90,'three active worlds')
 if '--pause'in sys.argv:
  native('host','GamePause 1',.2);wait(lambda:all(state(r).get('paused')for r in ROLES),15,'common pause')
 (O/'match-three-humans-bot.json').write_text(json.dumps({r:state(r)for r in ROLES},indent=2));print('THREE_PEERS_IN_MATCH',flush=True)
if __name__=='__main__':
 if sys.argv[1]=='lobby':lobby()
 elif sys.argv[1]=='launch':launch()
