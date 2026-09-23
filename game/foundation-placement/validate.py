"""Data integration checks and native per-group dispatch/spacing probes.
The probes execute saved engine instructions; map construction is stubbed.
They do not claim end-to-end map generation or multiplayer testing.
"""
import argparse,hashlib,json,math,re,struct,sys
from pathlib import Path
from prepare import MAPS,TEMPLATE,section
p=argparse.ArgumentParser();p.add_argument('--game',type=Path,required=True);p.add_argument('--legacy',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
here=Path(__file__).resolve().parent;overlay=here/'data';repo=here.parents[1];checks=0
def check(ok,label):
    global checks
    checks+=1
    if not ok:raise AssertionError(label)
manifest=json.loads((overlay/'manifest.json').read_text())
for item in manifest:
    check(hashlib.sha256((overlay/item['path']).read_bytes()).hexdigest()==item['after'],item['path'])
    check(hashlib.sha256((a.game/item['path']).read_bytes()).hexdigest() in [item['before'],item['after']],'known installed baseline')
guards=(repo/'game/beta7/ReleaseStartup.cs').read_text()+(repo/'game/beta7/RandomMapBundle.cs').read_text()
for item in manifest:check(item['after'].upper() in guards,'new input guard '+item['path'])
text=(overlay/TEMPLATE).read_text();before=(a.game/TEMPLATE).read_text()
check(text[:section(text,'StartSettlement')[0]]==before[:section(before,'StartSettlement')[0]],'kingdoms/diplomacy unchanged')
for name in ['StartSettlement','RandomSettlementGroup']:
    check(section(text,name)[2]==section(before,name)[2],name+' unchanged')
settlement=section(text,'SettlementCamps')[2];foundation=section(text,'FoundationCamps')[2]
def group_range(group):return tuple(map(float,re.search(r'(?m)^\s*range = ([0-9.]+),([0-9.]+)',group).groups()))
sr=group_range(settlement);fr=group_range(foundation)
check(sr==(3.2,6.4) and fr==(0.8,1.6),'80 percent settlement / 20 percent foundation ranges')
check(all(abs(s/(s+f)-0.8)<1e-8 for s,f in zip(sr,fr)),'80/20 before native rounding')
check(all(abs(s+f-total)<1e-8 for s,f,total in zip(sr,fr,(4,8))),'combined requested density unchanged')
for group,target in [(settlement,'random_settlement_camps'),(foundation,'random_foundation_camps')]:
    check(re.findall(r'object_ids = (\w+)',group)==[target],'one category per group')
    check('balanced_placement = true' in group and 'area_factor = 1.4' in group,'balanced and scaled')
    check('kingdom_ids = kingdom_enemy' in group,'owner unchanged')
    check('group_ids = kingdom_start*' in group,'starting cities respected')
check('group_ids = random_settlementcamps' not in foundation and 'group_ids = random_enclavecamps' not in foundation,'no forward restrictions')
check('group_ids = random_foundationcamps' in settlement,'ordinary camps avoid foundations')
# Every existing later restriction also covers the newly separated category.
groups=re.split(r'(?m)(?=^\[Template )',text)
for g in groups:
    if 'group_ids = random_settlementcamps' not in g:continue
    pattern=r'group_ids = %s\s+proximity_min = ([0-9.]+)\s+proximity_desired = ([0-9.]+)'
    check(re.findall(pattern%'random_settlementcamps',g)==re.findall(pattern%'random_foundationcamps',g),'preserved later separation')
for biome,count in MAPS.items():
    t=(overlay/f'data/RandomMap/rmc_{biome}03.tgi').read_text()
    check(t.count('[ActorGroup Template=FoundationCamps]')==count,biome+' includes foundations')
    check(t.count('[ActorGroup Template=FoundationCamps]\n\n\t[ActorGroup Template=SettlementCamps]')==count,biome+' order')
    stripped=t.replace('\t[ActorGroup Template=FoundationCamps]\n\n','')
    original=(a.game/f'data/RandomMap/rmc_{biome}03.tgi').read_text().replace('\t[ActorGroup Template=FoundationCamps]\n\n','')
    check(stripped==original,biome+' unrelated settings unchanged')

sys.path[:0]=[str(a.legacy/'lobby_colors_1372/deps_r15')]
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
from keystone import Ks,KS_ARCH_X86,KS_MODE_32
raw=(a.legacy/'k2_runtime_1372_20260904.bin').read_bytes()
check(hashlib.sha256(raw).hexdigest()=='b865d8206990c4f055c51de857f0b09b88ab5ee3b6ae74ee5232134001aa591c','saved engine hash')
ks=Ks(KS_ARCH_X86,KS_MODE_32);base=0x460000;u=Uc(UC_ARCH_X86,UC_MODE_32)
u.mem_map(base,(len(raw)+4095)&~4095);u.mem_write(base,raw);u.mem_map(0x20000000,0x10000)
def w(p,v):u.mem_write(p,struct.pack('<I',v))
def f(p,v):u.mem_write(p,struct.pack('<f',v))
def asm(p,t):u.mem_write(p,bytes(ks.asm(t,p)[0]))
calls=[]
for address,code in [(0x2582e2,'ret 4'),(0x258308,'mov eax,1; ret 8'),(0x255824,'ret'),(0x2591c4,'mov eax,1; ret 8')]:asm(base+address,code)
def watch(u,address,size,data):
    if address==base+0x258308:calls.append(struct.unpack('<I',u.mem_read(u.reg_read(UC_X86_REG_ESP)+4,4))[0])
hook=u.hook_add(UC_HOOK_CODE,watch)
for ix,g in enumerate([foundation,settlement]):
    ptr=0x20001000+ix*0x100;w(ptr+0x58,1);w(0x20003000,0x20003100)
    u.reg_write(UC_X86_REG_ESP,0x2000e000);u.reg_write(UC_X86_REG_EBP,0x2000e400)
    u.reg_write(UC_X86_REG_ESI,ptr);u.reg_write(UC_X86_REG_EDI,0x20003000);u.reg_write(UC_X86_REG_EBX,123)
    u.emu_start(base+0x259098,base+0x2590db,count=500)
    check(u.reg_read(UC_X86_REG_ESP)==0x2000e000,'native dispatch stack')
check(calls==[0x20001000,0x20001100],'independent native balancer call per group');u.hook_del(hook)
# Native sqrt and spacing instructions, with the math library replaced only by
# the equivalent hardware sqrt. This probes actual native integer conversion.
asm(base+0x3ec8d0,'sqrtsd xmm0,xmm0; ret')
w(base+0x5f3fb8,0x20004000);w(0x20004030,0x20004100)
for width in [256,384,512,768,1024,1536]:
    f(0x2000410c,width)
    for count in [1,2,3,4,8,9,16,32,64,128]:
        w(0x20001230,count);w(0x2000e3f0,0x20001200)
        u.reg_write(UC_X86_REG_ESP,0x2000e000);u.reg_write(UC_X86_REG_EBP,0x2000e400)
        u.emu_start(base+0x2583c8,base+0x258407,count=100)
        actual=struct.unpack('<f',u.mem_read(0x2000122c,4))[0]
        check(abs(actual-width/(math.isqrt(count)+1))<0.001,'native spread scale')
result=dict(passed=True,checks=checks,files=5,mapVariants=5,nativeDispatch=True,nativeSpacing=True,gameMapGeneration=False)
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2));print(json.dumps(result))
