from context import *
from qa import invoke,verify_game,ROOTS
from cryptography.hazmat.primitives import serialization
def prepare():
 feeds=O/'fullres-feeds';base=WS/'outputs/ui-fullres-release-20261117'
 for channel in['stable','beta']:
  f=verify(read(base/'signed'/f'feed/v3/{channel}.json'),key())
  if channel=='beta':
   for q in f['packages']:
    if not q['urls']:continue
    for folder in[base/'arcane/assets',base/'pure/assets',B2/'assets']:
     path=folder/Path(q['urls'][0]).name
     if path.exists()and sha(path)==q['sha256']:q['urls']=[str(path)];break
  write(feeds/(channel+'.json'),sign(f,serialization.load_pem_private_key(KEY.read_bytes(),None)))
 print('FULLRES_UPGRADE_FEEDS_READY')
def test(mod):
 root=Path(ROOTS[mod]);game=root/'game';pid='pawpatch-core'if mod=='arcane'else'pure-fixes-data';assert read(game/'.pawpatch/state.json')['modules'][pid]['version']==(ARC if mod=='arcane'else PURE)
 print(invoke(mod,O/'fullres-feeds','upgrade'),flush=True);state=read(game/'.pawpatch/state.json');old=state['modules'][pid]['version'];assert old==('0.6.0-beta.4'if mod=='arcane'else'0.5.0-beta.8');count=len([p for p in(game/'paws-hd-ui').rglob('*')if p.is_file()]);assert count>=645
 # A stale reserved HD archive outside the old loose module must also go away.
 (game/'paws-hd-ui.rwd').write_bytes(b'Owned QA stale HD archive sentinel\n')
 print(invoke(mod,O/'local-feeds','upgrade'),flush=True);images=verify_game(mod);assert read(game/'.pawpatch/state.json')['modules'][pid]['version']==(ARC if mod=='arcane'else PURE)
 write(O/(mod+'-fullres-upgrade.json'),dict(passed=True,fromVersion=old,toVersion=ARC if mod=='arcane'else PURE,oldLooseHdFiles=count,legacyImagesVerified=images,hdPathsAbsent=len(read(O/'hd-removals.json')),untrackedHdArchiveRemoved=True,nativeGameLaunched=False));print('FULLRES_TO_OLD_UI_PASS',mod,flush=True)
if __name__=='__main__':prepare()if sys.argv[1]=='prepare'else test(sys.argv[1])
