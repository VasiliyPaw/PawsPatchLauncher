"""Sign owned, local-only fixtures; do not change any public catalog."""
import argparse,copy,json,sys
from pathlib import Path
from cryptography.hazmat.primitives import serialization
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];sys.path.insert(0,str(REPO/'tools'))
from PrepareRelease070 import verify,encode,validate_package
from PrepareRelease081 import key,sign
KEY=Path('G:/CodexData/projects/Codex/2026-08-11/kohan-ii-d-steamlibrary-steamapps-common/work/PawsPatchLauncher/.local/signing/pawpatch-signing-private.pem')
def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);a=p.parse_args();stage=a.stage.resolve();proof=json.loads((stage/'preparation.json').read_text());private=serialization.load_pem_private_key(KEY.read_bytes(),None);assert private.public_key().public_numbers()==key().public_numbers()
 resolved={x['id']:x['path'] for x in proof['assets']}
 for channel in ['stable','beta']:
  raw=(REPO/'feed/v3'/f'{channel}.json').read_bytes();before=stage/'before/feed/v3'/f'{channel}.json';before.parent.mkdir(parents=True,exist_ok=True);before.write_bytes(raw);feed=verify(json.loads(raw),key())
  if channel=='beta':
   assert next(p for p in feed['packages'] if p['id']=='pawpatch-core')['version']=='0.5.0-beta.4'
   feed=copy.deepcopy(feed);feed['packages']=[copy.deepcopy(proof['replacements'].get(x['id'],x)) if x.get('mods')==['arcane-wars'] else x for x in feed['packages']]
   feed['patchGuide']['version']=proof['version'];feed['changelog']=[proof['note']]+feed['changelog'];feed['newsTitle']=proof['note']['title'];feed['newsBody']=proof['note']['body']
   for package in feed['packages']:
    if package['id'] in resolved and package.get('mods')==['arcane-wars']:package['urls']=[resolved[package['id']]]
    elif package.get('mods')==['arcane-wars']:
     cached=REPO/'outputs/arcane-051-release-20261109/stable/accepted-assets'/(package['id']+'-'+package['version']+'.zip')
     if cached.exists():validate_package(cached,package);package['urls']=[str(cached)]
  target=stage/'local-feeds'/f'{channel}.json';target.parent.mkdir(exist_ok=True);target.write_bytes(encode(sign(feed,private)))
 (stage/'public.pem').write_text(json.loads((REPO/'src/PawsPatchLauncher/launcher.config.json').read_text())['publicKeyPem'])
 print('LOCAL_BETA_FEEDS_SIGNED',proof['version'],'no public changes',flush=True)
if __name__=='__main__':main()
