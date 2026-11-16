from context import *
s=(WS/'work/arcane060-beta3-release-20261116/publish.py').read_text();a=s.index('def gate():');b=s.index('\ndef commit_files',a)
s=s[:a]+'''def gate():
 unchanged();assert read(O/'callback-tests.json')['passed']and read(O/'callback-tests.json')['checks']==477;assert read(O/'clock-tests.json')['passed'];assert read(O/'native/build-report.json')['standaloneCompatibility'];assert sha(O/'native/PawsPurePresentation1372.dll')==read(O/'native/build-report.json')['sha256']
 for mode in ['vanilla','immortals']:
  for suffix in ['installer-result','network-result','capture-result']:assert read(O/(mode+'-'+suffix+'.json'))['passed']
  net=read(O/(mode+'-network-result.json'));assert net['peers']==3 and net['checksums']['commonSamples']>=65 and net['checksums']['mismatchCount']==0 and not net['checksums']['errors']
 assert read(O/'catalog-qa/result.json')['passed'];assert read(O/'cleanup.json')['passed']
 for p in read(O/'packages.json'):
  f=O/'assets'/(p['id']+'-'+p['version']+'.zip');assert sha(f)==p['sha256']and f.stat().st_size==p['size']
 for n,r in read(O/'helpers/build-report.json').items():assert sha(O/'helpers'/n)==r['sha256']and r['features']['captureKnowledgeRevision']==1
 assert sha(read(O/'bundle.json')['path'])==read(O/'bundle.json')['sha256'];print('PURE_BETA7_RELEASE_GATE_PASS',flush=True)
''' +s[b:]
s=s.replace('assert len(assets)==5','assert len(assets)==4').replace("assert len(read(O/'public-assets.json')['assets'])==5","assert len(read(O/'public-assets.json')['assets'])==4").replace('assert len(allowed)==4','assert len(allowed)==3').replace('Fix capture ownership memory under fog and top group button picking for Arcane beta.3','Port observed capture ownership and clock picking fixes to Vanilla and Immortals Pure beta.7').replace('Publish Arcane Wars 0.6.0-beta.3 capture and HUD fixes','Publish Pure 0.5.0-beta.7 capture and HUD fixes for Vanilla and Immortals').replace("' — Arcane Wars'","' — Vanilla / Immortals'")
s=s.replace("assert f['patchGuide']['version']==VERSION", "assert all(g['patchGuide']['version']==VERSION for g in f['modGuides']if g['id']in ['vanilla','immortals'])")
(P/'publish.py').write_text(s)
