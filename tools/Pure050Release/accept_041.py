"""Record the exact limited acceptance before public catalog promotion."""
import zipfile
from context import *
def main():
 for case in ['vanilla-single-r1','immortals-trace-r1']:assert read(Path('G:/PawPure041QA-20261109')/case/'result.json')['passed']
 report=read(OUT/'stable-helpers-r2/build-report.json');assert len(report)==4
 for name,row in report.items():
  assert sha(OUT/'stable-helpers-r2'/name)==row['sha256'];assert row['features']['matchRecoveryEnabled'] is False;assert row['features']['multiplayerSavesRevision']==2
 for p in read(OUT/'stable-stage/packages.json'):
  old=next(a for a in read(OUT/'baseline.json')['acceptedPackages']if a['id']==p['id']);a=OUT/'accepted-assets'/old['urls'][0].rsplit('/',1)[1];b=OUT/'stable-stage/assets'/p['urls'][0].rsplit('/',1)[1]
  with zipfile.ZipFile(a)as x,zipfile.ZipFile(b)as y:
   left={n:x.read(n)for n in x.namelist()if n.startswith('payload/')};right={n:y.read(n)for n in y.namelist()if n.startswith('payload/')};assert left.keys()==right.keys()
   changes=[n for n in left if left[n]!=right[n]];assert (len(changes)==4 and all(n.endswith('.exe')for n in changes))if p['id']=='pure-fixes-runtime'else not changes
 write(OUT/'stable-publication/acceptance.json',dict(passed=True,helpers=4,modeLivePasses=2,currentTwoPeerPass=False,live=['vanilla-single-r1','immortals-trace-r1'],staticPayloadParity=True,automaticRecovery=False,savesRetained=True));print('PURE_041_ACCEPTED limited live coverage recorded')
if __name__=='__main__':main()
