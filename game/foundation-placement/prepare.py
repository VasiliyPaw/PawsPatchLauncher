"""Prepare a narrow data-only AW map-generation overlay; never edits the game.

The native balancer spreads positions per ActorGroup, before weighted object
types are resolved. A mixed group balances their union, not either category.
"""
import argparse,hashlib,json,re
from pathlib import Path

MAPS={'arctic':1,'cursed':1,'desert':1,'temperate':2}
TEMPLATE='data/Templates/template_rmc_k2.tgi'

def section(text,name):
    m=re.search(r'(?im)^\[Template '+re.escape(name)+r'\s+Template=RMCActorGroup\]\s*\n\{',text)
    if not m:raise ValueError('Missing group '+name)
    end=text.index('\n}',m.end())+2
    return m.start(),end,text[m.start():end]

def once(text,old,new):
    if text.count(old)!=1:raise ValueError('Unexpected input: '+old)
    return text.replace(old,new)

def restriction(group,distance):
    return '\t[GroupRestriction]\n\tgroup_ids = '+group+'\n\tproximity_min = '+str(distance)+'\n\tproximity_desired = 0'

def patch_template(text):
    # Disable no other feature: all changes are confined to RMC actor groups.
    lo,hi,foundation=section(text,'FoundationCamps')
    foundation=once(foundation,'range = 0,0','range = 0.8,1.6')
    foundation=once(foundation,restriction('random_settlements',96),restriction('random_settlements',128))
    for group,distance in [('random_settlementcamps',96),('random_enclavecamps',128)]:
        foundation=once(foundation,'\n\n'+restriction(group,distance),'')
    text=text[:lo]+foundation+text[hi:]
    # Every later group previously avoided both categories through the mixed
    # group ID. Preserve those existing cross-group distances after splitting.
    pattern=r'\t\[GroupRestriction\]\n\tgroup_ids = random_settlementcamps\n\tproximity_min = [0-9.]+\n\tproximity_desired = [0-9.]+'
    text,n=re.subn(pattern,lambda m:m[0]+'\n\n'+m[0].replace('random_settlementcamps','random_foundationcamps'),text)
    if n!=16:raise ValueError(f'Expected 16 later group restrictions, got {n}')
    lo,hi,settlement=section(text,'SettlementCamps')
    settlement=once(settlement,'range = 4,8','range = 3.2,6.4')
    settlement=once(settlement,'\n\t[Object]\n\tobject_ids = random_foundation_camps\n\tweight = 1\n','')
    settlement=settlement[:-2]+'\n\n'+restriction('random_foundationcamps',128)+'\n}'
    text=text[:lo]+settlement+text[hi:]
    return text

def prepare(game,out):
    if out.exists():raise ValueError('Output must be a new directory')
    files={TEMPLATE:patch_template}
    for biome,count in MAPS.items():
        def transform(t,count=count):
            needle='\t[ActorGroup Template=SettlementCamps]'
            if t.count(needle)!=count or 'Template=FoundationCamps]' in t:raise ValueError('Unexpected map groups')
            return t.replace(needle,'\t[ActorGroup Template=FoundationCamps]\n\n'+needle)
        files['data/RandomMap/rmc_'+biome+'03.tgi']=transform
    prepared=[]
    for rel,transform in files.items():
        raw=(game/rel).read_bytes();text=raw.decode('utf-8');newline='\r\n' if '\r\n' in text else '\n'
        changed=transform(text.replace('\r\n','\n')).replace('\n',newline).encode('utf-8')
        prepared.append((rel,raw,changed))
    out.mkdir(parents=True)
    manifest=[]
    for rel,raw,changed in prepared:
        dst=out/rel;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(changed)
        manifest.append(dict(path=rel,before=hashlib.sha256(raw).hexdigest(),after=hashlib.sha256(changed).hexdigest()))
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('FOUNDATION_OVERLAY_PREPARED',len(manifest),'files; 5 map variants')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--game',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    prepare(a.game,a.out)
