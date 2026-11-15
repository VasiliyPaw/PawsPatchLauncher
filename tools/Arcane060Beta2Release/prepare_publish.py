from context import *
s=(PREV/'publish.py').read_text().replace('from release_context import *','from context import *')
start=s.index('def gate():');end=s.index('\ndef commit_files',start)
s=s[:start]+'''def gate():
 unchanged();assert read(O/'verification.json')['passed'];assert read(O/'network-cleanup.json')['ownedProcessesStopped'];assert read(O/'product-smoke.json')['normalNineModules'];assert read(LOSS/'RESULT.json')['pixelAlphaDimensionsFormatMetadataUnchanged']
 for q in read(O/'packages.json'):
  f=O/'assets'/(q['id']+'-'+VERSION+'.zip');assert sha(f)==q['sha256']and f.stat().st_size==q['size']
 assert sha(read(O/'bundle.json')['path'])==read(O/'bundle.json')['sha256'];print('BETA2_RELEASE_GATE_PASS',flush=True)
''' +s[end:]
s=s.replace("b=read(P/'public-baseline.json')","b=read(P/'baseline.json')")
s=s.replace(" for p in paths:assert not git('ls-tree',parent,'--',p),'Existing remote source path requires merge: '+p",''' for p in paths:
  current=subprocess.run(['git','show',parent+':'+p],cwd=REPO,capture_output=True)
  if (S/p).exists():assert current.returncode==0 and normalize(current.stdout)==normalize((S/p).read_bytes()),'Remote source changed; merge first: '+p
  else:assert current.returncode!=0,'New source path already exists: '+p''')
s=s.replace('Add Arcane Wars 0.6.0 roads, bridges, world features and release verification','Pack Arcane terrain losslessly and validate beta.2 upgrade and archive compatibility').replace('Publish Arcane Wars 0.6.0 beta with roads, racial bridges and 24-minute days','Publish Arcane Wars 0.6.0-beta.2 with lossless compact terrain resources')
s=s.replace('assert len(assets)==15','assert len(assets)==9').replace("assert len(read(O/'public-assets.json')['assets'])==15","assert len(read(O/'public-assets.json')['assets'])==9").replace('catalogs.baseline();catalogs.catalogs()','catalogs.snapshot();catalogs.catalogs()')
(P/'publish.py').write_text(s)
