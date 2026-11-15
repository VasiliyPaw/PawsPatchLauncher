"""Refresh manifests only inside the explicitly marked private composition."""
import argparse,json,hashlib
from pathlib import Path
def refresh(fixture,report,version):
 game=fixture/'game';assert (game/'reconnect-test.marker').read_text()=='Private world-options test only\n'
 p=game/'.pawpatch/state.json';state=json.loads(p.read_text(encoding='utf-8-sig'));prep=json.loads((fixture/'preparation.json').read_text(encoding='utf-8'))
 changed={x.replace('\\','/').lower() for x in prep['changed']}|{x.lower() for x in report}
 found=set()
 def descriptor(rel):
  f=game/rel;return dict(path=rel,sha256=hashlib.sha256(f.read_bytes()).hexdigest().upper(),size=f.stat().st_size)
 for mid,module in state['modules'].items():
  if mid in ('pawpatch-core','common-ui','player-colors','desync-continue') or mid.startswith('pawpatch-data'):module['version']=version
  for entry in module.get('files',[]):
   rel=entry['path'];key=rel.replace('\\','/').lower();found.add(key)
   if key in changed:entry.update(descriptor(rel))
 for rel in prep['changed']:
  if rel.lower() not in found:state['modules']['pawpatch-core']['files'].append(descriptor(rel))
 state['releaseId']=version;p.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
 print('OWNED_MANIFEST_READY',version)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('fixture',type=Path);ap.add_argument('report',type=Path);a=ap.parse_args()
 refresh(a.fixture,json.loads(a.report.read_text()),'0.5.0-local-world.1')
