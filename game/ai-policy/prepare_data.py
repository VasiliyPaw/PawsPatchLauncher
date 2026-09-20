"""Prepare a reversible local AI data experiment, preserving unrelated values."""
import argparse, re, json, hashlib, difflib
from pathlib import Path

def blocks(text, pattern):
    for m in re.finditer(pattern, text, re.M):
        start=m.start(); brace=text.find('{',m.end()); next_header=text.find('[',m.end())
        assert brace>=0 and (next_header<0 or brace<next_header),m.group()
        depth=1; end=brace+1
        while depth:
            if text[end]=='{': depth+=1
            elif text[end]=='}': depth-=1
            end+=1
        yield start,end,text[start:end]

def owners(text):
    out={}
    for a,b,s in blocks(text,r'^\[(?:template [^\]]+|Ego [^\]]+)\]'):
        if s.startswith('[template '): key=s.split()[1]
        else: key=re.search(r'^\s*IDS\s*=\s*(\S+)',s,re.M).group(1)
        assert key not in out
        out[key]=(a,b,s)
    return out

def prop(s,key):
    m=re.search(r'^\s*'+re.escape(key)+r'\s*=\s*([^;\r\n]+)',s,re.M)
    return m.group(1).strip() if m else None

def transform(current,vanilla):
    changes=[]; edits=[]; old=owners(vanilla)
    for key,(a,b,s) in owners(current).items():
        assert key in old,key
        orig=old[key][2]
        matches=list(blocks(s,r'^\s*\[Recruiting\]'))
        orig_matches=list(blocks(orig,r'^\s*\[Recruiting\]'))
        assert len(matches)<=1 and len(orig_matches)<=1
        if not matches: continue
        ca,cb,recruit=matches[0]; vr=orig_matches[0][2] if orig_matches else ''
        expected=prop(vr,'insufficient_income_level')
        actual=prop(recruit,'insufficient_income_level')
        if actual!=expected:
            assert actual=='0',(key,actual,expected)
            pattern=r'(?m)^[ \t]*insufficient_income_level[ \t]*=[ \t]*0[^\r\n]*(?:\r?\n)?'
            if expected is None: recruit,n=re.subn(pattern,'',recruit)
            else: recruit,n=re.subn(r'(?m)(^[ \t]*insufficient_income_level[ \t]*=[ \t]*)0\b',lambda m:m.group(1)+expected,recruit)
            assert n==1
            changes.append(dict(owner=key,field='insufficient_income_level',before=actual,after=expected or 'inherit vanilla'))
        vanilla_requests={prop(x[2],'property_ids') for x in blocks(vr,r'^\s*\[SpecificRecruitRequest\]')}
        req_edits=[]
        for ra,rb,request in blocks(recruit,r'^\s*\[SpecificRecruitRequest\]'):
            ids=prop(request,'property_ids')
            if ids in vanilla_requests or 'settler' in ids or prop(request,'economic_value_multiplier')!='0': continue
            new,n=re.subn(r'(economic_value_multiplier\s*=\s*)0\b',r'\g<1>0.2',request);assert n==1
            req_edits.append((ra,rb,new))
            changes.append(dict(owner=key,field='economic_value_multiplier',property_ids=ids,before=0,after=0.2))
        for ra,rb,new in reversed(req_edits):recruit=recruit[:ra]+new+recruit[rb:]
        edits.append((a,b,s[:ca]+recruit+s[cb:]))
    for a,b,s in reversed(edits):current=current[:a]+s+current[b:]
    return current,changes

def main():
    p=argparse.ArgumentParser();p.add_argument('--game',type=Path,required=True);p.add_argument('--audit',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);manifest=[]
    for file in sorted((a.game/'data/SAI').glob('*hard*.tgi')):
        raw=file.read_bytes(); text=raw.decode('utf-8-sig'); vanilla=(a.audit/'vanilla/SAI'/file.name).read_text(encoding='utf-8-sig')
        archived=(a.audit/'installed/SAI'/file.name).read_text(encoding='utf-8-sig')
        normalize=lambda s:'\n'.join(x.strip() for x in s.splitlines() if x.strip())
        assert normalize(text)==normalize(archived),'Profile changed since comparison: '+str(file)
        new,changes=transform(text,vanilla)
        if not changes:continue
        rel='data/SAI/'+file.name
        for directory,payload in [('before',raw),('after',new.encode('utf-8'))]:
            dst=a.out/directory/rel;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(payload)
        (a.out/(file.stem+'.diff')).write_text(''.join(difflib.unified_diff(text.splitlines(True),new.splitlines(True),fromfile=rel+' before',tofile=rel+' after')),encoding='utf-8')
        manifest.append(dict(path=rel,before=hashlib.sha256(raw).hexdigest(),after=hashlib.sha256(new.encode('utf-8')).hexdigest(),changes=changes))
    rel='data/Game/SVars.tgi';raw=(a.game/rel).read_bytes();text=raw.decode('utf-8-sig')
    new,n=re.subn(r'(?m)(^[ \t]*(?:fixed[ \t]+)?settlement_cv_range_fudge_factor[ \t]*=[ \t]*)0\.1\b',r'\g<1>1.7',text);assert n==1
    for directory,payload in [('before',raw),('after',new.encode('utf-8'))]:
        dst=a.out/directory/rel;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(payload)
    manifest.append(dict(path=rel,before=hashlib.sha256(raw).hexdigest(),after=hashlib.sha256(new.encode('utf-8')).hexdigest(),changes=[dict(field='settlement_cv_range_fudge_factor',before=0.1,after=1.7)]))
    (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'files':len(manifest),'changes':sum(len(x['changes']) for x in manifest),'output':str(a.out)}))
if __name__=='__main__':main()
