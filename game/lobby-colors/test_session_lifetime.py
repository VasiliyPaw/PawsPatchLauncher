"""Recycled Session/player IDs with a genuine Reset-GUID lifetime boundary."""
import argparse,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--expect-fixed',type=int,choices=[0,1],required=True);p.add_argument('--palette',type=Path);a=p.parse_args()
sys.argv=[sys.argv[0],'--legacy',str(a.legacy),'--candidate',str(a.candidate)]
source=Path(__file__).with_name('test_participant_colors.py');scope={'__file__':str(source)}
exec(compile(source.read_text().split('\nfor game,cave in ')[0],str(source),'exec'),scope)
if a.palette:
 import configparser
 palette=configparser.ConfigParser();palette.read(a.palette,encoding='utf-8-sig')
 count=len(palette.sections());assert count in [39,48]
 scope['palette']=palette;scope['RANDOM']=scope['scope']['RANDOM']=count
 scope['env']['RANDOM']=scope['env']['PALETTE_COUNT']=count
Peer,RANDOM=scope['Peer'],scope['RANDOM'];checks=0
def check(value,label):
 global checks
 assert value,label;checks+=1
for game,cave in [(0x460000,0x10000000),(0x640000,0x19000000)]:
 for first,second in [(0,1),(1,7),(15,0)]:
  for pointer_reused in [False,True]:
   f=Peer(True,game,cave);guid=f.intern('0'*31+'1')
   f.write(f.session+0x170,guid);f.call('state_init',f.session);f.roster({first,second})
   f.choose(first,3);f.choose(second,9)
   original=(f.pref(first),f.pref(second));check(original==(3,9),'chosen participant preferences stored')
   f.call('state_init',f.session);check((f.pref(first),f.pref(second))==original,'same room lifetime preserves choices')
   # Real native Reset reuses the Session object, clears +F4 and creates a new
   # GUID. Host/client arrival order then recycles the same numeric player IDs.
   f.roster(set());f.write(f.session+0xf4,0)
   # Include a full-length GUID whose ONLY difference is the last WCHAR.
   other='0'*31+'2' if pointer_reused else 'F'*32
   if pointer_reused:f.u.mem_write(guid,other.encode('utf-16le')+b'\0\0')
   else:f.write(f.session+0x170,f.intern(other))
   f.roster({first,second});f.write(f.session+0xf4,2)
   f.write(f.player(first)+8,f.intern('former second player'));f.write(f.player(second)+8,f.intern('former first player'))
   f.call('state_init',f.session);f.move(first,first);f.move(second,second)
   observed=(f.choices()[first],f.choices()[second])
   if a.expect_fixed:
    check(observed==(RANDOM,RANDOM),'new people must not inherit colors from recycled IDs')
    check((f.pref(first),f.pref(second))==(RANDOM,RANDOM),'new lifetime clears ID preferences')
   else:check(observed==(3,9),'released payload reproduces cross-player color inheritance')
   # Repeated initialization in this same new room must not erase fresh choices.
   f.choose(first,12);f.call('state_init',f.session);check(f.choices()[first]==12,'new room choices remain stable after initialization')
   before=bytes(f.u.mem_read(f.params(0),16*0x6c))
   f.write(f.cave+0x128,1);f.call('state_init',f.session)
   check(f.choices()[first]==12,'allocation reset within a room preserves participant color')
   check(bytes(f.u.mem_read(f.params(0),16*0x6c))==before,'world/saved parameters unchanged')
 if a.expect_fixed:
  # Three friends enter a second room in another order, then a late client gets
  # the complete authoritative choices. Only the new room's choices may survive.
  h=Peer(True,game,cave);c=Peer(False,0xaf0000,0x12000000)
  for f in (h,c):
   f.write(f.session+0x170,f.intern('old room'));f.call('state_init',f.session);f.roster({0,1,2})
  h.choose(0,3,c);h.choose(1,9,c);h.choose(2,12,c)
  for f in (h,c):
   f.write(f.session+0x170,f.intern('new room'));f.call('state_init',f.session)
   check(all(v==RANDOM for v in f.choices()),'three participants do not inherit old colors')
   f.move(2,0);f.move(0,1);f.move(1,2)
  h.choose(2,17,c);h.snapshot(c)
  check(h.choices()==c.choices(),'new lobby host/client snapshot agrees')
  late=Peer(False,0x760000,0x15000000);late.roster({0,1,2})
  for actor,seat in [(2,0),(0,1),(1,2)]:late.move(actor,seat)
  h.snapshot(late);check(h.choices()==late.choices(),'late join gets only new room colors')
result=dict(passed=True,fixed=bool(a.expect_fixed),checks=checks,layouts=2,paletteCount=RANDOM,sessionAddressReused=True,guidBufferAddressAlsoReused=True,worldParametersUnchanged=True,liveGameTested=False)
(a.candidate/'session-lifetime-tests.json').write_text(json.dumps(result,indent=2));print('SESSION_LIFETIME_REGRESSION_PASS',checks,'fixed='+str(bool(a.expect_fixed)))
