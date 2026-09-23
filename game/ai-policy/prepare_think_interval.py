"""Opening strategy: 10s. Remaining hard-profile modes: 20s.

Keep the shared template and the separate tactical AI interval unchanged.
"""
from pathlib import Path
import json,re,hashlib
from prepare_data import owners,blocks,prop

def transform(text):
    edits=[];changes=[]
    for key,(a,b,owner) in owners(text).items():
        if not owner.startswith('[Ego '):continue
        interval=10 if ('_initial_' in key or '_rusher_need_settlements_' in key) else 20
        old=None
        engines=list(blocks(owner,r'^\s*\[GoalEngine\]'))
        assert len(engines)<=1,key
        if engines:
            ea,eb,engine=engines[0]
            settings=list(blocks(engine,r'^\s*\[GeneralSettings\]'))
            assert len(settings)<=1,key
            if settings:
                ga,gb,g=settings[0];old=prop(g,'think_frequency')
                if old==str(interval):continue
                if old is None:g=g[:g.index('{')+1]+f'\n\t\t\tthink_frequency = {interval}'+g[g.index('{')+1:]
                else:g,n=re.subn(r'(think_frequency\s*=\s*)[^\s;]+',lambda m:m[1]+str(interval),g);assert n==1
                engine=engine[:ga]+g+engine[gb:]
            else:engine=engine[:engine.index('{')+1]+f'\n\t\t[GeneralSettings]\n\t\t{{\n\t\t\tthink_frequency = {interval}\n\t\t}}'+engine[engine.index('{')+1:]
            owner=owner[:ea]+engine+owner[eb:]
        else:
            owner=owner[:-1]+f'\n\t[GoalEngine]\n\t{{\n\t\t[GeneralSettings]\n\t\t{{\n\t\t\tthink_frequency = {interval}\n\t\t}}\n\t}}\n'+owner[-1:]
        changes.append(dict(owner=key,field='strategic_think_frequency',before=old or 'inherit',after=interval))
        edits.append((a,b,owner))
    for a,b,new in reversed(edits):text=text[:a]+new+text[b:]
    return text,changes

if __name__=='__main__':
    folder=Path(__file__).with_name('data');manifest=json.loads((folder/'manifest.json').read_text())
    count=0
    for entry in manifest:
        if not entry['path'].startswith('data/SAI/'):continue
        file=folder/entry['path'];raw=file.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==entry['after'],file
        text,changes=transform(raw.decode('utf-8-sig'))
        if changes:
            file.write_bytes(text.encode('utf-8'));entry['after']=hashlib.sha256(file.read_bytes()).hexdigest()
            entry['changes']+=changes;count+=len(changes)
        assert transform(text)==(text,[]),'idempotency'
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('STRATEGIC_INTERVAL_10_20',count,'mode overrides')
