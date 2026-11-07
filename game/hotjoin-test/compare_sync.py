"""Compare the stock engine's two sync traces without modifying them."""
import argparse, json, re
from pathlib import Path

def parse(path):
    rows={}
    for line in path.read_text(errors='replace').splitlines():
        m=re.fullmatch(r'(\d+):(-?\d+) (.*)',line)
        if m:rows[int(m[1])]=dict(crc=int(m[2])&0xffff,entry=m[3].rstrip())
    return rows

def main():
    ap=argparse.ArgumentParser();ap.add_argument('host',type=Path);ap.add_argument('client',type=Path)
    ap.add_argument('--start',type=int,default=0);ap.add_argument('--end',type=int,default=2**31)
    ap.add_argument('--out',type=Path);a=ap.parse_args()
    h,c=parse(a.host),parse(a.client)
    common=sorted(i for i in h.keys()&c.keys() if a.start<=i<=a.end)
    mismatch=next((i for i in common if h[i]['crc']!=c[i]['crc']),None)
    context=[dict(index=i,host=h.get(i),client=c.get(i)) for i in range(max(a.start,(mismatch or a.start)-3),(mismatch or a.start)+8)] if mismatch is not None else []
    values=[dict(index=i,host=h[i],client=c[i]) for i in common if h[i]['entry']!=c[i]['entry']]
    result=dict(firstCrcMismatch=mismatch,commonEntries=len(common),context=context,entryDifferences=values)
    if a.out:a.out.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(dict(firstCrcMismatch=mismatch,commonEntries=len(common),context=context,entryDifferences=values[:25]),indent=2,ensure_ascii=False))

if __name__=='__main__':main()
