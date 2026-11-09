"""Fault-inject the actual generated registry/world installers."""
import re,subprocess
from context import *

def main():
 out=OUT/'beta-transactions-r4';out.mkdir(exist_ok=False);row=read(OUT/'beta-helpers-r4/build-report.json')['k2_paws_pure_fixes_1372.exe'];meta=read(OUT/'world-native-r2/native/payload.json')
 for name,path,main in [('registry',REPO/'game/large-maps/InstallerTests.cs','InstallerTests'),('world',REPO/'game/mixed-biomes/TransactionTests.cs','MixedTransactionTests')]:
  text=path.read_text()
  if name=='registry':text=re.sub(r'internal static class ReleaseStartup \{[^\n]+\}\n','',text)
  else:
   text=text.replace('MixedBiomesTestPatch','PureWorldOptionsPatch');text=re.sub(r'static readonly uint\[\] Sites=\{[^}]+\};','static readonly uint[] Sites={'+','.join('0x%x'%h['site']for h in meta['hooks'])+'};',text)
   start=text.index('    static byte[][] Originals(');end=text.index('    static MixedFakeMemory Memory',start)
   originals=[]
   for h in meta['hooks']:
    originals.append('(new byte[]{0xb8}).Concat(BitConverter.GetBytes(image+0x43ff0d)).ToArray()'if h['site']==0x2566b9 else'TerrainPatch.Hex("'+h['before']+'")')
   text=text[:start]+'    static byte[][] Originals(uint image){return new[]{'+','.join(originals)+'};}\n'+text[end:]
  source=out/(name+'.cs');source.write_text(text);exe=out/(name+'.exe');args=[('/main:'+main if a.startswith('/main:')else'/out:'+str(exe)if a.startswith('/out:')else a)for a in row['args']]+[str(source)]
  p=subprocess.run(args,capture_output=True,text=True);assert p.returncode==0,p.stdout+p.stderr
  p=subprocess.run([exe],capture_output=True,text=True);(out/(name+'.log')).write_text(p.stdout+p.stderr);print(p.stdout+p.stderr);assert p.returncode==0
 write(out/'result.json',dict(passed=True,registry=True,world=True,failureScope='every operation and mismatching native guards; registry partial writes and unsafe rollback retention'))
if __name__=='__main__':main()
