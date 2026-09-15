"""Download a pinned public safetensors model with resumable verified ranges."""
import argparse, concurrent.futures, hashlib, json, os, time, urllib.request
from pathlib import Path

REV='fa184c675da0b5c9e1c8694fccd4e12e2d422094'
SIZE=11761587872
HASH='66ff5f8fcaf92291da486fdfbd4d5233cec90e1359348a56e3172c978b3a76d4'
BASE='https://huggingface.co/google/madlad400-3b-mt/resolve/'+REV+'/'
def main():
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    for name in ['config.json','generation_config.json','tokenizer.json','tokenizer_config.json','special_tokens_map.json','added_tokens.json','spiece.model','README.md']:
        dest=a.out/name
        if not dest.exists():dest.write_bytes(urllib.request.urlopen(BASE+name+'?t='+str(time.time()),timeout=60).read())
    dest=a.out/'model.safetensors';chunk=32*1024*1024;state=a.out/'ranges.json'
    done=set(json.loads(state.read_text()) if state.exists() else [])
    if not dest.exists():
        with dest.open('wb') as f:f.truncate(SIZE)
    def get(i):
        begin=i*chunk;end=min(SIZE,begin+chunk)-1
        for attempt in range(5):
            try:
                req=urllib.request.Request(BASE+'model.safetensors?t='+str(time.time()),headers={'Range':f'bytes={begin}-{end}'})
                with urllib.request.urlopen(req,timeout=90) as r:
                    assert r.status==206 and r.headers['Content-Range']==f'bytes {begin}-{end}/{SIZE}'
                    data=r.read();assert len(data)==end-begin+1
                with dest.open('r+b') as f:f.seek(begin);f.write(data)
                return i
            except Exception as e:
                if attempt==4:raise
                time.sleep(attempt+1)
    total=(SIZE+chunk-1)//chunk
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        jobs=[pool.submit(get,i) for i in range(total) if i not in done]
        for future in concurrent.futures.as_completed(jobs):
            done.add(future.result());state.write_text(json.dumps(sorted(done)))
            if len(done)%10==0:print('model download',len(done),'/',total,flush=True)
    with dest.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
    assert actual==HASH,(actual,HASH)
    (a.out/'verified.sha256').write_text(actual+'\n');print('Verified model',actual,flush=True)

if __name__=='__main__':main()
