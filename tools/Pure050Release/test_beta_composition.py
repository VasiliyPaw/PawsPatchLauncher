"""Exercise the exact generated Pure world/registry and existing native patches."""
import subprocess
from context import *
def main():
 out=OUT/'beta-helpers-r4';row=read(out/'build-report.json')['k2_paws_pure_fixes_1372.exe'];test=out/'PureBetaCompositionTests.exe';text=(REPO/'game/pure-fixes/PureBetaNativeTests.cs').read_text()
 anchor='                if(ai)AiPolicyRuntime.InstallNative(m,image,delegate{});';assert text.count(anchor)==1
 text=text.replace(anchor,anchor+'\n                LargeMapsPatch.Install(m,image,delegate{});\n                PureWorldOptionsPatch.Install(m,image,delegate{});\n                foreach(uint site in new uint[]{0xd5000,0xd5785,0x2a4570,0x2a47ee,0x2a43fa,0x2a4430,0x2a4466,0x2a449c,0x2b1ae6})if(m.Hooks.Any(h=>image+site<h.Item1+h.Item2&&h.Item1<image+site+5))throw new Exception("Pure UI code ownership conflict "+site.ToString("X"));')
 source=out/'PureBetaCompositionTests.cs';source.write_text(text)
 args=[('/target:exe'if x.startswith('/target:')else'/main:PawPureFixes.PureBetaNativeTests'if x.startswith('/main:')else'/out:'+str(test)if x.startswith('/out:')else x)for x in row['args']]+[str(source)]
 p=subprocess.run(args,capture_output=True,text=True);assert p.returncode==0,p.stdout+p.stderr
 p=subprocess.run([str(test),str(LEG/'k2_runtime_1372_20260904.bin')],capture_output=True,text=True);(out/'composition-tests.log').write_text(p.stdout+p.stderr);print(p.stdout+p.stderr);assert p.returncode==0
 write(out/'composition-test.json',dict(passed=True,bases=3,compositions=12,registryAndWorld=True,uiCodeSitesRemainNative=True))
if __name__=='__main__':main()
