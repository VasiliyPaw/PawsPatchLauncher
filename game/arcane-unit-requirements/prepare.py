"""Local Arcane Wars requirement overlay; preserve the installed unit verbatim."""
from pathlib import Path
import argparse, re, hashlib, json

def patch(raw):
    enc='utf-16' if raw[:2] in (b'\xff\xfe',b'\xfe\xff') else 'utf-8-sig' if raw[:3]==b'\xef\xbb\xbf' else 'utf-8'
    text=raw.decode(enc)
    assert re.search(r'IDS\s*=\s*maelstrom_destroyer\s',text)
    assert re.search(r'Kingdom_points_consumed\s*=\s*0\.75\s',text,re.I)
    assert text.count('[ElementComponent]')==1
    start=text.index('[ElementComponent]'); end=text.index('[MoverComponent]',start)
    block=text[start:end]
    if 'required_properties' in block:
        assert re.search(r'required_properties\s*=\s*gauri_kingdom\s',block)
        return raw
    newline='\r\n' if '\r\n' in text else '\n'
    at=start+len('[ElementComponent]')
    return (text[:at]+newline+'\trequired_properties = gauri_kingdom'+text[at:]).encode(enc)

def main():
    p=argparse.ArgumentParser();p.add_argument('--game',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    rel='data/Units/Gauri/AW_maelstrom_destroyer.tgi'
    raw=(a.game/rel).read_bytes();result=patch(raw);dest=a.out/'payload'/rel
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(result)
    (a.out/'arcane-requirement.json').write_text(json.dumps(dict(path=rel,before=hashlib.sha256(raw).hexdigest(),after=hashlib.sha256(result).hexdigest(),property='gauri_kingdom'),indent=2))
    print('GAURI_KINGDOM_REQUIREMENT_PREPARED')
if __name__=='__main__':main()
