"""Stage the local mass-siege experiment; never launch or install the game."""
import argparse, hashlib, json, re, sys
from pathlib import Path
from prepare_data import blocks
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from GameplayPresentationData import decode

ELITE=('company_dragonfire_balistae','company_Maelstrom_engine',
       'company_vorpal_engine','company_crimson_catapult','company_plague_catapult')
MARKER=';; PAW_AI_MASS_SIEGE_R1'

def siege_requests(text):
    if MARKER in text:return text
    nl='\r\n' if '\r\n' in text else '\n'
    request=nl+'\t\t\t'+MARKER+nl
    for ids in ELITE:
        request+=nl.join(['\t\t\t[SpecificRecruitRequest]','\t\t\t{',
            '\t\t\t\trecruit_ids = '+ids,
            '\t\t\t\tnumber_to_request = 6',
            '\t\t\t\tbase_priority = 9000',
            '\t\t\t\teconomic_value_multiplier = 0.2',
            '\t\t\t\trepeat_penalty = -1250','\t\t\t}'])+nl
    matches=list(blocks(text,r'^\s*\[Recruiting\]'))
    assert matches,'No recruiting blocks'
    for a,b,s in reversed(matches):
        p=a+s.index('{')+1
        text=text[:p]+request+text[p:]
    return text

def no_kp(blob,ids):
    text,enc=decode(blob);nl='\r\n' if '\r\n' in text else '\n'
    # Scope to the actual unit definition; never clear an entire company's upkeep.
    matches=[(a,b,s) for a,b,s in blocks(text,r'^\[(?:Thing|Unit)[^\]]*\]')
             if re.search(r'^\s*IDS\s*=\s*'+re.escape(ids)+r'\s*$',s,re.M|re.I)]
    assert len(matches)==1
    a,b,s=matches[0]
    if re.search(r'Kingdom_points_consumed\s*=',s,re.I):
        s,n=re.subn(r'(Kingdom_points_consumed\s*=\s*)[^\r\n;]+',r'\g<1>0',s,flags=re.I);assert n==1
    elif '[Upkeep]' in s:
        s=s.replace('[Upkeep]','[Upkeep]'+nl+'\t\tKingdom_points_consumed = 0',1)
    else:
        assert '[EconomyComponent]' not in s
        s=s[:-1]+nl+'\t[EconomyComponent]'+nl+'\t{'+nl+'\t\t[Upkeep]'+nl+'\t\tKingdom_points_consumed = 0'+nl+'\t}'+nl+'}'
    return (text[:a]+s+text[b:]).encode(enc)

def main():
    p=argparse.ArgumentParser();p.add_argument('--game',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=False);manifest=[]
    edits=[]
    for f in sorted((args.game/'data/SAI').glob('*hard*.tgi')):
        raw=f.read_bytes();text,enc=decode(raw);new=siege_requests(text).encode(enc)
        assert siege_requests(new.decode(enc))==new.decode(enc)
        # A repeat must raise priority; do not alter generic siege, economy, or attack policy.
        assert new.decode(enc).count('repeat_penalty = -1250')==new.decode(enc).count(MARKER)*len(ELITE)
        edits.append((f,new))
    for name,ids in [('AW_bolt_master.tgi','bolt_master')]:
        f=args.game/'data/Units/Gauri'/name;new=no_kp(f.read_bytes(),ids)
        assert no_kp(new,ids)==new
        edits.append((f,new))
    for f,new in edits:
        rel=f.relative_to(args.game).as_posix();old=f.read_bytes()
        for sub,blob in [('before',old),('after',new)]:
            dest=args.out/sub/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(blob)
        manifest.append({'path':rel,'before':hashlib.sha256(old).hexdigest(),'after':hashlib.sha256(new).hexdigest()})
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('SIEGE_STAGED',len(manifest),'files; base 9000; bonus 1250 per existing elite company; no new KP cost')
if __name__=='__main__':main()
