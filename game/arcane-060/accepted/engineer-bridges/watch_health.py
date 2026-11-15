"""Read exact owned native actors without changing the running simulation."""
from pathlib import Path
import argparse,ctypes as C,json,re,struct,time
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--save',type=Path);p.add_argument('--samples',type=int,default=2);p.add_argument('--interval',type=float,default=2);p.add_argument('--cell',nargs=2,type=int);p.add_argument('ids',nargs='+',type=int);a=p.parse_args();r=a.out.resolve()
assert 1<=a.samples<=30 and 0<a.interval<=10
ident=json.loads((r/'qa-process.json').read_text());base=int(re.findall(r'k2.exe at ([0-9A-F]+)',(r/'sandbox/Mods/plugins.log').read_text())[-1],16)
k=C.WinDLL('kernel32',use_last_error=True);k.OpenProcess.restype=C.c_void_p;k.ReadProcessMemory.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_size_t,C.c_void_p];k.QueryFullProcessImageNameW.argtypes=[C.c_void_p,C.c_uint,C.c_wchar_p,C.c_void_p];k.CloseHandle.argtypes=[C.c_void_p];h=k.OpenProcess(0x410,False,ident['pid']);assert h
buf=C.create_unicode_buffer(32768);n=C.c_uint(32768);assert k.QueryFullProcessImageNameW(h,0,buf,C.byref(n)) and Path(buf.value).resolve()==(r/'sandbox/k2.exe').resolve()
def read(at,n=4):
 b=C.create_string_buffer(n);assert k.ReadProcessMemory(h,at,b,n,None),hex(at);return b.raw
def u(at):return struct.unpack('<I',read(at))[0]
def f(at):return struct.unpack('<f',read(at))[0]
rows=[]
try:
 for sample in range(a.samples):
  world=u(base+0x5f3fb8);assert world;reg=u(base+0x5ef72c);actors={}
  for i in a.ids:
   act=u(reg+0x20004+(i&65535)*4)
   if not act or u(act+20)!=i:actors[str(i)]=None;continue
   body=u(act+0x60);actors[str(i)]={'position':list(struct.unpack('<3f',read(act+32,12))),'health':f(body+16) if body else None,'maxHealth':f(body+20) if body else None,'states':hex(u(act+0x100)),'flags':hex(u(act+8)),'commands':hex(u(act+0xf0))}
  row={'time':f(world+0xe8),'actors':actors}
  if a.cell:
   grid=u(world+0x30);x,y=a.cell;assert 0<=x<u(grid+0x1c) and 0<=y<u(grid+0x20)
   tile=u(grid+0x28)+(y*u(grid+0x1c)+x)*48;definition=u(tile)
   row['cell']={'xy':a.cell,'variant':read(u(definition+8),160).decode('utf-16le',errors='replace').split('\0')[0],'flags':hex(u(tile+32))}
  rows.append(row)
  if sample+1<a.samples:time.sleep(a.interval)
finally:k.CloseHandle(h)
if a.save:a.save.write_text(json.dumps(rows,indent=2))
print(json.dumps(rows))
