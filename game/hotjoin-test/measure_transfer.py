"""Measure retained native CRC-ready times; no game or evidence mutation."""
import argparse,json,re
from pathlib import Path

def measure(root):
    rows=[]
    for peer in sorted(root.iterdir()):
        log=peer/'game/Mods/plugins.log'
        if not log.exists():continue
        pending=None
        for line in log.read_text(errors='replace').splitlines():
            m=re.match(r'\[(\d+):(\d+):(\d+)\.(\d+)\]',line)
            if not m:continue
            h,minute,sec,ms=map(int,m.groups());now=h*3600+minute*60+sec+ms/1000
            if 'CLIENT_SNAPSHOT_SESSION accepted' in line or 'EXISTING_PEER_CHECKPOINT_REQUESTED' in line:
                pending=(now,'incoming' if 'CLIENT_SNAPSHOT_SESSION' in line else 'existing')
            elif pending and 'CHECKPOINT_READY_REQUESTED after complete native file CRC verification' in line:
                elapsed=(now-pending[0])%86400
                rows.append(dict(peer=peer.name,role=pending[1],nativeTransferAndCrcSeconds=round(elapsed,3)))
                pending=None
    return rows

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args()
    print(json.dumps(measure(a.root),indent=2))
