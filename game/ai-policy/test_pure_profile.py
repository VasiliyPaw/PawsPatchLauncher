"""Pure native profile: AW-only gates must be absent, shared opening policy retained."""
from pathlib import Path

def fixtures(name):
    ns={'__file__':str(Path(__file__).with_name(name))}
    exec(compile(Path(ns['__file__']).read_text().split('\nfor image,cave in ')[0],name+':fixtures','exec'),ns)
    return ns

opening=fixtures('test_opening_lairs.py')
assert opening['meta']['profile']=='pure'
checks=0
for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
    for name in opening['LARGE']+['lair_dragon_lair','storm_drake_crag']:
        for cities in (0,1,2,3):
            f=opening['OpeningFixture'](image,cave,cities);opening['named'](f,name)
            assert f.score()==1000 and f.admission()==0 and opening['candidate'](f)==100,(name,cities)
            checks+=3
militia=fixtures('test_militia.py')
for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
    for name in militia['targets']:
        f=militia['EconomyFixture'](image,cave);militia['target'](f,name);f.f(f.target+0x38,2)
        f.invoke(0,f.target,[f.budget,0])
        assert militia['struct'].unpack('<f',f.u.mem_read(f.target+0x38,4))[0]==2
        assert not f.events(49)
        checks+=2
    for native in (0,1):
        f=militia['EconomyFixture'](image,cave);f.builder_alive();f.sovereign();f.f(f.stock,250)
        f.w(f.target+0x1c,f.recruit+0x400);f.w(f.target+0x20,9);f.f(f.recruit+0x400,100)
        assert f.invoke(30,f.target,[f.budget,0],native=native)==native,'No royal gold reserve'
        checks+=1
supply=fixtures('test_supply_notice.py')
for image,cave in [(0x460000,0x10000000),(0xf20000,0x22000000),(0x18000000,0x38000000)]:
    for name in supply['names']:
        for count in (0,1,2,4):
            for native in (0xc0ff00,0xc0ff01):
                f=supply['SupplyFixture'](image,cave)
                f.u.mem_write(f.df+0x800,(name+'\0').encode('utf-16le'))
                for n in range(count):f.company(n)
                assert f.run(next(h for h in supply['meta']['wrappers'] if h['mode']==4),native=native)[0]==native,'No AW supply cap'
                checks+=1
raw=opening['raw']
for marker in ('_center_sovereign','kingdom_points_consumed','human_company_supply','_militia','active_ice_dragon_lair'):
    assert marker.encode() not in raw,marker
    checks+=1
print('PURE_AI_PROFILE_PASS',checks)

