"""Execute candidate x86 with the accepted real native setter/list lookup fixture.

Native rendering and connection scheduling are separate live acceptance checks.
"""
import argparse, json, os, struct, configparser
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--legacy', type=Path, required=True)
p.add_argument('--candidate', type=Path, required=True)
a=p.parse_args()
os.environ['PAW_COLOR_CANDIDATE']=str(a.candidate.resolve())
source=a.legacy/'test_rejoin_r19.py'
scope={'__file__':str(source)}
exec(compile(source.read_text().split('\nfor game,cave in ')[0],str(source),'exec'),scope)
NativePeer,env,check=scope['NativePeer'],scope['env'],scope['check']
palette=configparser.ConfigParser()
palette.read(Path(__file__).resolve().parents[1]/'beta7/paws_player_colors.ini',encoding='utf-8-sig')
RANDOM=len(palette.sections())
assert RANDOM==39
old=configparser.ConfigParser();old.read(Path(__file__).with_name('palette-48.ini'),encoding='utf-8-sig')
assert len(old.sections())==48
assert palette.sections()==[k for i,k in enumerate(old.sections(),1) if i not in {6,18,20,22,24,29,30,35,37}]
assert all(dict(palette[k])==dict(old[k]) for k in palette.sections()), 'Remaining RGBs/names/IDs unchanged'
env['PALETTE_COUNT']=env['RANDOM']=scope['RANDOM']=RANDOM
MAN=env['MAN']

class Peer(NativePeer):
    def __init__(self,host=True,game=0x460000,cave=0x10000000):
        super().__init__(host,game,cave)
        # Use the real release palette, not the older fixture's generated colors.
        for i,k in enumerate(palette.sections()):
            entry=self.cave+0x1400+i*20
            self.write(entry,self.intern(k));self.write(entry+4,self.intern(palette[k]['name_en']))
            self.u.mem_write(entry+8,struct.pack('<fff',*(int(v)/255 for v in palette[k]['rgb'].split(','))))
        self.write(self.cave+0x100,0);self.call('ensure')
        for k in range(16): self.write(self.player(k)+0x20,k+1)
        self.call('bind_snapshot')

    def move(self,actor,seat):
        ref=self.cave+0x300+seat*4 if seat is not None else 0x200ed100
        if seat is None:self.write(ref,self.intern(''))
        MAN['functions']['native_assign_test']=self.addr(0x5bd6d5)-self.cave
        result=self.call('native_assign_test',self.player(actor),arg=ref)
        check(result==self.player(actor)+0x24,'native setter return preserved')
        check(self.read(self.player(actor)+0x24)==self.read(ref),'native kingdom assignment preserved')

    def pref(self,actor):
        ptr=self.call('preference',self.read(self.player(actor)+0x20))
        return self.read(ptr+4)

for game,cave in [(0x460000,0x10000000),(0x640000,0x19000000)]:
    # Every shade, both directions, all host-authoritative peers and late joins.
    for color in range(RANDOM+1):
        h=Peer(True,game,cave);c=Peer(False,0xaf0000,0x12000000)
        for f in (h,c):f.roster({0,1,7})
        h.choose(1,color,c)
        for f in (h,c):
            f.move(1,5)
            check(f.choices()[5]==color and f.choices()[1]==RANDOM,'color follows participant into empty seat')
            check(f.pref(1)==color,'participant preference retained')
            f.move(1,None)
            check(f.choices()[5]==RANDOM,'spectating releases prior seat')
            f.move(1,6)
            check(f.choices()[6]==color,'return from spectator keeps preference')
            f.move(1,1)
            # A new ID at the exact same object address is a different player.
            f.roster({0,7})
            f.write(f.player(1)+0x20,99)
            f.move(1,1)
            f.roster({0,1,7})
            check(f.choices()[1]==RANDOM,'new participant never inherits previous occupant color')
        check(h.choices()==c.choices(),'host and client converge without a UI tick')
        late=Peer(False,0x760000,0x15000000)
        # Snapshot serialization recreates the native roster before our extension.
        late.write(late.player(1)+0x20,99);late.roster({0,1,7})
        h.snapshot(late)
        check(late.choices()==h.choices(),'late join gets authoritative choices')

    # Two non-random players swapping in either event order retain both colors.
    for first,second in [(1,7),(7,1)]:
        f=Peer(True,game,cave);f.roster({0,1,7})
        f.choose(1,3);f.choose(7,9)
        f.move(first,second);f.move(second,first)
        check(f.choices()[7]==3 and f.choices()[1]==9,'two-step seat swap preserves both preferences')
        f.move(1,None);f.choose(1,3);f.move(1,5)
        check(f.choices()[5]==RANDOM and f.choices()[1]==3,'occupied former shade becomes Random, incumbent preserved')

    f=Peer(True,game,cave);f.roster({0,1,7});f.choose(1,12)
    f.write(f.player(1)+8,f.intern('same display name'))
    f.write(f.player(7)+8,f.intern('same display name'))
    f.move(7,5);check(f.choices()[5]==RANDOM,'same nickname cannot steal another preference')
    f.move(1,6);check(f.choices()[6]==12,'renaming does not lose color')
    f.write(f.session+0x64,2)
    before=f.choices();f.move(1,4)
    check(f.choices()==before,'saved-world seat changes do not alter kingdom colors')
    f.write(f.session+0x64,0);f.write(f.session+0x100,0)
    f.move(1,3);check(f.choices()[3]==12,'single-player seat changes use same participant rule')

    # Native object recreation with the SAME replicated ID retains the preference.
    f=Peer(True,game,cave);f.roster({0,1});f.choose(1,7)
    f.roster({0});f.move(1,None);f.roster({0,1});f.move(1,5)
    check(f.choices()[5]==7,'same native participant returning retains preference')
    f.write(f.cave+0x120,0);f.call('state_init',f.session)
    check(all(v==RANDOM for v in f.choices()),'new session resets all seat choices')
    check(f.pref(1)==RANDOM,'new session resets participant preferences')

    # 300 departures cannot overwrite any of the 16 active participants.
    f=Peer(True,game,cave);f.roster(range(16))
    f.choose(1,17)
    for ident in range(1000,1300):
        check(f.call('preference',ident)!=0,'bounded table safely reclaims inactive IDs')
    check(f.pref(1)==17,'table reclamation preserves active choice')

    f=Peer(True,game,cave)
    # Fixture call has one stack argument; dedicated wrapper supplies two.
    from unicorn.x86_const import UC_X86_REG_ESP
    original_call=f.call
    def codec(name,stream,ref):
        # x86 adapter: push ref, push stream, call routine, add esp,8, ret.
        va=f.cave+(0x40e00 if name=='color_wire_write' else 0x40f00);target=f.cave+MAN['functions'][name]
        code=b'\x68'+struct.pack('<I',ref)+b'\x68'+struct.pack('<I',stream)
        code+=b'\xe8'+struct.pack('<i',target-(va+15))+b'\x83\xc4\x08\xc3'
        f.u.mem_write(va,code);MAN['functions']['codec_adapter']=va-f.cave
        return f.call('codec_adapter')
    all_colors=list(MAN['retired_colors'])+[
        dict(id=k,rgb=[int(v) for v in palette[k]['rgb'].split(',')],
             descriptor=0xa00+i*0x24,wire_id=0x50440000+i)
        for i,k in enumerate(palette.sections())]
    for color in all_colors:
        key=f.intern(color['id'])
        desc=f.call('saved_color_lookup',f.manager+0x3cc,arg=key)
        check(desc==f.cave+color['descriptor'],'save color resolves by unchanged ID: '+color['id'])
        rgb=struct.unpack('<fff',f.u.mem_read(desc+0x18,12))
        check(all(abs(x-y/255)<1e-6 for x,y in zip(rgb,color['rgb'])),'save RGB retained')
        visible=[f.read(f.cave+0x200+4*k) for k in range(RANDOM)]
        check((desc in visible)==(color['id'] in palette),'retired colors excluded from picker/RNG')
        f.write(0x200ed200,desc);f.streams[f.decree_stream]=[]
        codec('color_wire_write',f.decree_stream,0x200ed200)
        words=f.streams[f.decree_stream]
        check(words==[color['wire_id']],'dedicated bounded wire ID')
        f.feed(f.decree_stream,words);f.write(0x200ed200,0)
        codec('color_wire_read',f.decree_stream,0x200ed200)
        check(f.read(0x200ed200)==desc,'color survives multiplayer save transfer')
    check(f.call('saved_color_lookup',f.manager+0x3cc,arg=f.intern('paws_unknown'))==0,'Unknown IDs retain failure behavior')
    for invalid in [0x50440000+RANDOM,0x5044fff4,0x5044ffff]:
        f.feed(f.decree_stream,[invalid]);codec('color_wire_read',f.decree_stream,0x200ed200)
        check(f.read(0x200ed200)==0,'Invalid tagged color is rejected')
    f.roster(set(range(16)))
    for iteration in range(20):
        for k in range(16):f.write(f.cave+0x600+k*4,RANDOM)
        f.write(f.cave+0x128,0);f.write(f.cave+0x12c,0)
        f.call('allocate')
        check(all(0<=v<RANDOM for v in f.assigned()),'Random allocation uses visible palette only')

result={'passed':True,'assertions':env['COUNT'],'palette_count':RANDOM,
        'payload_sha256':MAN['payload_sha256'],'layouts':2,
        'native_setter_and_linked_list':True,'game_launched':False,'retired_colors':len(MAN['retired_colors'])}
(a.candidate/'participant-tests.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
