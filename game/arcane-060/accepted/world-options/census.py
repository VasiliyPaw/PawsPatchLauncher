"""Read terrain IDs only from a path-verified, owned QA process."""
import argparse,collections,ctypes as C,json,re,struct
from pathlib import Path

def main():
 ap=argparse.ArgumentParser();ap.add_argument('peer',type=Path);a=ap.parse_args();root=a.peer.resolve()
 assert (root/'game/hotjoin-lab.marker').is_file()
 identity=json.loads((root/'process.json').read_text());k=C.WinDLL('kernel32',use_last_error=True)
 k.OpenProcess.restype=C.c_void_p;k.ReadProcessMemory.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_size_t,C.c_void_p]
 k.QueryFullProcessImageNameW.argtypes=[C.c_void_p,C.c_uint,C.c_wchar_p,C.c_void_p];k.CloseHandle.argtypes=[C.c_void_p]
 h=k.OpenProcess(0x1010,False,identity['pid']);assert h
 try:
  path=C.create_unicode_buffer(32768);size=C.c_ulong(len(path));assert k.QueryFullProcessImageNameW(h,0,path,C.byref(size))
  assert Path(path.value).resolve()==(root/'game/k2.exe').resolve()
  def read(p,n):
   b=C.create_string_buffer(n);done=C.c_size_t();assert k.ReadProcessMemory(h,p,b,n,C.byref(done)) and done.value==n,hex(p);return b.raw
  def u(p):return struct.unpack('<I',read(p,4))[0]
  base=int(re.search(r'k2.exe at ([0-9A-F]+)',(root/'game/Mods/plugins.log').read_text())[1],16)
  world=u(base+0x5f3fb8);terrain=u(world+0x30);w=u(terrain+0x1c);height=u(terrain+0x20);assert 32<=w<=1024 and 32<=height<=1024
  grid=read(u(terrain+0x28),w*height*48);variants=collections.Counter(struct.unpack_from('<I',grid,i*48)[0] for i in range(w*height));ids={}
  for v in variants:
   p=u(v+8);n=u(p-12);assert n<1024;ids[v]=read(p,n*2).decode('utf-16le')
  counts=collections.Counter()
  for v,n in variants.items():counts[ids[v].split('_')[0]]+=n
  assert set(counts)<={'temperate','arctic','desert','cursed'}
  result=dict(pid=identity['pid'],world=world,mapSide=w*2,cellCounts=dict(counts),biomeCount=len(counts),variationCounts={ids[v]:n for v,n in variants.items()})
  (root/'world-options-census.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='variationCounts'}))
 finally:k.CloseHandle(h)
if __name__=='__main__':main()
