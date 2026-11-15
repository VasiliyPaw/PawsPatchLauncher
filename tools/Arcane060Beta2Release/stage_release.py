from publish import *
gate();commit=read(O/'source-publication.json')['commit'];assets=sorted((O/'assets').glob('*.zip'));assert len(assets)==9
args=[sys.executable,S/'tools/PublishLauncherRelease.py',VERSION,commit,O/'release-notes.md',*assets,'--tag',TAG,'--name','Paw’s Patch '+VERSION+' — Arcane Wars','--prerelease','--keep-draft']
with(O/'draft-upload.log').open('w',encoding='utf-8')as log:
 process=subprocess.Popen(list(map(str,args)),cwd=REPO,env=env(),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
 for line in process.stdout:log.write(line);log.flush();print(line,end='',flush=True)
 assert process.wait()==0,'Draft upload failed; see draft-upload.log'
print('DRAFT_ASSETS_STAGED',flush=True)
