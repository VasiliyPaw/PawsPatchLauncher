"""Remove stdcall export decorations in our own diagnostic DLL only."""
import struct,json,hashlib,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class PE:
    def __init__(self,path):
        self.b=bytearray(Path(path).read_bytes());b=self.b
        self.pe=struct.unpack_from('<I',b,0x3c)[0];self.opt=self.pe+24
        assert self.u16(self.pe+4)==0x14c and self.u16(self.opt)==0x10b
        p=self.opt+self.u16(self.pe+20);self.sections=[]
        for i in range(self.u16(self.pe+6)):
            vsize,rva,size,off=struct.unpack_from('<IIII',b,p+40*i+8)
            self.sections.append((rva,max(vsize,size),off))
    def u16(self,p):return struct.unpack_from('<H',self.b,p)[0]
    def u32(self,p):return struct.unpack_from('<I',self.b,p)[0]
    def off(self,rva):
        for va,size,p in self.sections:
            if va<=rva<va+size:return p+rva-va
        raise ValueError(hex(rva))
    def string(self,p):return bytes(self.b[p:self.b.index(0,p)]).decode('ascii')
    def imports(self):
        p=self.off(self.u32(self.opt+104));result={}
        while self.u32(p+12):
            name=self.string(self.off(self.u32(p+12)));names=[]
            th=self.off(self.u32(p) or self.u32(p+16))
            while self.u32(th):
                entry=self.u32(th);names.append('#'+str(entry&65535) if entry&0x80000000 else self.string(self.off(entry)+2));th+=4
            result[name]=names;p+=20
        return result

parser=argparse.ArgumentParser()
parser.add_argument('dll',type=Path)
parser.add_argument('--game-exe',type=Path)
args=parser.parse_args()
path=args.dll;pe=PE(path)
ex=pe.off(pe.u32(pe.opt+96));n=pe.u32(ex+24)
names=pe.off(pe.u32(ex+32));ords=pe.off(pe.u32(ex+36));out=[]
for i in range(n):
    rva=pe.u32(names+4*i);off=pe.off(rva);old=pe.string(off)
    new=old.lstrip('_').split('@')[0]
    raw=new.encode()+b'\0';pe.b[off:off+len(old)+1]=raw+b'\0'*(len(old)+1-len(raw))
    out.append((new,rva,pe.u16(ords+2*i)))
for i,(name,rva,ordinal) in enumerate(sorted(out)):
    struct.pack_into('<I',pe.b,names+4*i,rva);struct.pack_into('<H',pe.b,ords+2*i,ordinal)
struct.pack_into('<I',pe.b,pe.opt+64,0) # optional checksum; our DLL is unsigned
path.write_bytes(pe.b)
required={'Direct3DCreate9'} # verified Kohan II 1.3.72 import
if args.game_exe:
    imports=PE(args.game_exe).imports()
    required={name for dll,names in imports.items() if dll.lower()=='d3d9.dll' for name in names}
exported={row[0] for row in out}
assert required<=exported,(required-exported)
report={'machine':'x86','d3d9Imports':sorted(required),'exports':sorted(exported),'sha256':hashlib.sha256(pe.b).hexdigest(),'bytes':len(pe.b)}
path.with_suffix('.build.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
