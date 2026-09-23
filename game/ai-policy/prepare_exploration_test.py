"""Stage five opening CloseGoals per hard profile; never modifies an installation."""
import argparse,difflib,hashlib,json,re
from pathlib import Path
from prepare_data import blocks,owners,prop

def transform(text):
    edits=[];changes=[]
    for owner,(start,end,body) in owners(text).items():
        for a,b,group in blocks(body,r'^\s*\[CloseGoals\]'):
            if '_initial_' not in owner and '_rusher_need_settlements_' not in owner:continue
            old=prop(group,'num_goals');assert old in ('2','3'),(owner,old)
            new,n=re.subn(r'(?m)(^[ \t]*num_goals[ \t]*=[ \t]*)'+old+r'\b',r'\g<1>5',group)
            assert n==1
            edits.append((start+a,start+b,new))
            changes.append(dict(owner=owner,group='Exploration/CloseGoals',field='num_goals',before=int(old),after=5))
    assert len(edits)==1,changes
    a,b,new=edits[0];result=text[:a]+new+text[b:]
    # Exactly one value changes; all late-stage, deep, economic and goal weights survive.
    assert len(text)==len(result) and sum(x!=y for x,y in zip(text,result))==1
    return result,changes

def main():
    p=argparse.ArgumentParser();p.add_argument('--game',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    manifest=[];files=sorted((args.game/'data/SAI').glob('*hard*.tgi'));assert len(files)==12
    for file in files:
        raw=file.read_bytes();text=raw.decode('utf-8');new,changes=transform(text);blob=new.encode('utf-8')
        rel='data/SAI/'+file.name
        for sub,value in [('before',raw),('after',blob)]:
            path=args.out/sub/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value)
        (args.out/(file.stem+'.diff')).write_text(''.join(difflib.unified_diff(text.splitlines(True),new.splitlines(True),fromfile=rel+' before',tofile=rel+' after')),encoding='utf-8')
        manifest.append(dict(path=rel,before=hashlib.sha256(raw).hexdigest(),after=hashlib.sha256(blob).hexdigest(),changes=changes))
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('EXPLORATION_STAGED: 12 hard profiles; one opening CloseGoals value per file -> 5; other bytes unchanged')

if __name__=='__main__':main()
