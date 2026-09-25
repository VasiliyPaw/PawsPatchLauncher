"""Compiled host/client differential regression, not a played multiplayer match.

Keep replicated world/session inputs equal while removing the client's local
strategic AI and varying host-only goals. Native service stubs are inherited
from the ABI/write-bound fixtures; the compiled policy and wrappers are real.
"""
from pathlib import Path
import json

def fixture(name):
    path=Path(__file__).with_name(name)
    ns={'__file__':str(path)}
    exec(compile(path.read_text().split('\nfor image,cave in ')[0],str(path),'exec'),ns)
    return ns

r=fixture('test_routing.py');s=fixture('test_supply_notice.py');b=fixture('test_builder_fleet.py')
checks=0
def check(ok,why):
    global checks
    assert ok,why
    checks+=1

layouts=[(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]
for image,cave in layouts:
    for bot in (False,True):
        for goal in (0,0x4da480,0x4d84d4):
            for hostile in (False,True):
                peers=[]
                for host in (True,False):
                    f=r['Fixture'](image,cave);f.w(f.slot+0xc,int(bot))
                    if not host:f.w(image+0x5f3fc8,0)
                    elif goal:
                        node=0x51012000;sa=node+0x100;g=sa+0x100;eng=g+0x100
                        f.w(f.player+0x2c,node);f.w(f.player+0xc,eng);f.w(node,sa);f.w(sa+8,1)
                        f.w(sa+0xc,f.player);f.w(sa+0x10,g);f.w(g,image+goal);f.w(g+4,eng);f.w(g+8,2)
                    if hostile:f.w(f.query+0x20,f.lair)
                    threats=f.begin();los=f.call(f.hook(13),[r['bits'](v) for v in (8,64,120,64)],native=0xcafe01)
                    node=f.actor+0x800;f.w(node,15);f.w(node+4,16)
                    cost=f.call(f.hook(15),[node,16,16],fp=5);f.end()
                    peers.append((threats,los,r['bits'](cost)))
                check(peers[0]==peers[1],('route peer parity',bot,goal,hostile,peers))
                check(peers[0][0]==int(bot and not hostile),'bot ownership and replicated attack bypass')
    for malformed in ('missing_session','missing_slot','wrong_type','duplicate','cycle','unassigned'):
        f=r['Fixture'](image,cave)
        if malformed=='missing_session':f.w(image+0x5f3fe4,0)
        if malformed=='missing_slot':f.w(f.slotnode,0)
        if malformed=='wrong_type':f.w(f.slot,0)
        if malformed=='duplicate':f.w(f.slotnode+4,f.slotnode+16);f.w(f.slotnode+16,f.slot)
        if malformed=='cycle':f.w(f.slotnode+4,f.slotnode)
        if malformed=='unassigned':f.w(f.slot+0x28,0)
        check(f.begin()==0,('invalid session preserves native path',malformed));f.end()
    for h in [h for h in s['meta']['wrappers'] if h['mode']==7]:
        for native in (0xcafe00,0xcafe01):
            for count in (0,2,4):
                values=[]
                for host in (True,False):
                    f=s['SupplyFixture'](image,cave)
                    for i in range(count):f.company(i)
                    if not host:f.w(image+0x5f3fc8,0)
                    values.append(f.run(h,native=native)[0])
                check(values==[native,native],('common recruit admission',count,hex(native),values))
    for race in ('human','haroun','undead'):
        for host in (True,False):
            f=b['FleetFixture'](image,cave);f.race(race)
            # No vacant marker: host planning refuses this builder. Applying
            # an already accepted native command still preserves its result.
            f.w(f.marker+8,1)
            if host:
                check(f.eligible()==0,('planning demand retained',race))
                before=f.r(f.stats)
                check(f.invoke(5,f.recruit,[f.prvec,f.upvec],native=0)==1,'final AI budget veto retained')
                check(f.r(f.stats)==before,'rejected builder does not reserve native budget')
            else:f.w(image+0x5f3fc8,0)
            for native in (0,1):
                check(f.invoke(7,f.city+0x900,[f.builder,0,0,0],native)==native,('builder execution parity',race,host,native))

report=dict(passed=True,checks=checks,routeAbiChecks=r['checks'],scope='compiled x86 peer fixtures; native services stubbed; no two-machine acceptance')
(r['a'].native/'peer-parity.json').write_text(json.dumps(report,indent=2)+'\n')
print('AI_PEER_PARITY_PASS',checks,'differential checks;',r['checks'],'route ABI checks')
