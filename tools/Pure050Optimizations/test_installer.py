"""Use the already isolated actual launcher installer; verify graphics ownership."""
from context import *
p=REPO/'tools/Pure050Release/install_beta.py';s=p.read_text()
s=once(s,"out=OUT/'beta-install-r7'","out=OUT/'installer-r5'")
s=once(s,"bin=REPO/'src/PawsPatchLauncher/bin/Release/net8.0-windows'","bin=PREVIOUS/'beta-install-r7/launcher'")
s=s.replace("OUT/'beta-stage-r4/packages.json'","OUT/'stage-r3/packages.json'")
s=once(s,"[OUT/'accepted-assets',OUT/'stable-stage/assets',OUT/'beta-stage-r4/assets',OUT/'optional-data-r1/inputs',WS/'outputs/release-pure-040-20261013/publication-final/packages']","[PREVIOUS/'accepted-assets',PREVIOUS/'stable-stage/assets',PREVIOUS/'beta-stage-r4/assets',OUT/'stage-r3/assets',PREVIOUS/'optional-data-r1/inputs',WS/'outputs/release-pure-040-20261013/publication-final/packages']")
s=s.replace('G:/PawPure050QA-20261109/installer','G:/PawPure050OptQA-20261109/installer')
# This runs after each completed transaction, including beta -> stable/off and
# file-only, so a newly managed graphics DLL cannot silently survive rollback.
anchor=" (out/'Program.cs').write_text(source)"
needle='Console.WriteLine("INSTALL_PASS '
assertion='''
                string graphics=Path.Combine(game,"d3d9.dll");
                bool optimized=packages.Any(p=>p.Id=="pure-fixes-runtime"&&p.Version=="1.3.72-pure.18-beta.2");
                string graphicsHash=File.Exists(graphics)?await CryptoAndIO.Sha256Async(graphics):"";
                if(optimized != string.Equals(graphicsHash,"112920FF0CB9A38158A12E9F8875B6B4FBBCE9ADA5C364EF55936EBBE4A83179",StringComparison.OrdinalIgnoreCase))
                    throw new InvalidDataException(item.Id+": graphics ownership/rollback mismatch");
'''
extra=' assert '+repr(needle)+' in source;source=source.replace('+repr(needle)+','+repr(assertion+needle)+')\n'
assert anchor in s;s=s.replace(anchor,extra+anchor)
exec(compile(s,str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
