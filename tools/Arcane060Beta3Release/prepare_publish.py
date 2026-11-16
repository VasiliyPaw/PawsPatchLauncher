from context import *
s=(P.parent/'arcane060-beta2-release-20261115/publish.py').read_text();a=s.index('def gate():');b=s.index('\ndef commit_files',a)
s=s[:a]+'''def gate():
 unchanged();v=read(CAND/'verification.json');assert v['mismatches']==0 and v['commonCheckpoints']==133 and v['networkPeers']==3 and v['hiddenThirdKeepsOldOwner'];assert sha(CWORK/'build/PawsCaptureKnowledge.dll')==v['productionSha256']
 for n in ['native-rebuild.json','startup-contract.json']:assert read(O/n)['passed']
 assert read(O/'catalog-qa/result.json')['passed']
 for case in ['beta3-upgrade','beta3-off','beta3-reapply','beta3-network']:assert read(O/(case+'-result.json'))['passed']
 for q in read(O/'packages.json'):
  f=O/'assets'/(q['id']+'-'+VERSION+'.zip');assert sha(f)==q['sha256']and f.stat().st_size==q['size']
 assert sha(read(O/'bundle.json')['path'])==read(O/'bundle.json')['sha256'];print('BETA3_RELEASE_GATE_PASS',flush=True)
''' +s[b:]
s=s.replace('assert len(assets)==9','assert len(assets)==5').replace("assert len(read(O/'public-assets.json')['assets'])==9","assert len(read(O/'public-assets.json')['assets'])==5").replace('Pack Arcane terrain losslessly and validate beta.2 upgrade and archive compatibility','Fix capture ownership memory under fog and top group button picking for Arcane beta.3').replace('Publish Arcane Wars 0.6.0-beta.2 with lossless compact terrain resources','Publish Arcane Wars 0.6.0-beta.3 capture and HUD fixes')
(P/'publish.py').write_text(s)
