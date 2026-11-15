"""Read-only movement trace from the exact owned private bridge process."""
from pathlib import Path
import argparse,ctypes as C,json,re,struct,time
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--save',type=Path,required=True);p.add_argument('--seconds',type=float,default=20);p.add_argument('ids',nargs='+',type=int);a=p.parse_args()
r=a.out.resolve();identity=json.loads((r/'qa-process.json').read_text());log=(r/'sandbox/Mods/plugins.log').read_text();base=int(re.findall(r'k2.exe at ([0-9A-F]+)',log)[-1],16)
k=C.WinDLL('kernel32',use_last_error=True);k.OpenProcess.argtypes=[C.c_uint,C.c_int,C.c_uint];k.OpenProcess.restype=C.c_void_p;k.ReadProcessMemory.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_size_t,C.c_void_p];k.QueryFullProcessImageNameW.argtypes=[C.c_void_p,C.c_uint,C.c_wchar_p,C.c_void_p];k.CloseHandle.argtypes=[C.c_void_p]
h=k.OpenProcess(0x410,False,identity['pid']);assert h
buf=C.create_unicode_buffer(32768);size=C.c_uint(32768)
assert k.QueryFullProcessImageNameW(h,0,buf,C.byref(size)) and Path(buf.value).resolve()==(r/'sandbox/k2.exe').resolve()
def read(at,n=4):
 b=C.create_string_buffer(n);assert k.ReadProcessMemory(h,at,b,n,None),hex(at);return b.raw
def u(at):return struct.unpack('<I',read(at))[0]
def vec(at):return list(struct.unpack('<3f',read(at,12)))
try:
 reg=u(base+0x5ef72c);rows=[];until=time.monotonic()+a.seconds
 while True:
  world=u(base+0x5f3fb8);row={'time':struct.unpack('<f',read(world+0xe8))[0],'actors':{}}
  for ident in a.ids:
   actor=u(reg+0x20004+(ident&65535)*4)
   if not actor or u(actor+0x14)!=ident:continue
   mind=u(actor+0x70);org=u(actor+0x7c);body=u(actor+0x60)
   v={'position':vec(actor+32),'flags':hex(u(actor+8)),'health':struct.unpack('<f',read(body+16))[0] if body else None}
   if mind:
    node=u(mind+0x10);state=u(node) if node else 0;cmd=u(mind+32)
    v['state']=hex(u(state)-base) if state else None
    v['command']={'id':u(u(cmd+8)+12),'target':u(cmd+16),'point':vec(cmd+24)[:2]} if cmd else None
    if u(mind+0x68)==base+0x4f4df0:v['move']={'active':u(mind+0x74),'target':u(mind+0x78),'point':vec(mind+0x7c)[:2]};v['attackTarget']=u(mind+0xd0)
   if org:
    n=u(org+44);assert n<64;v['members']={}
    for i in range(n):
     member=u(u(org+40)+i*4)
     if member:v['members'][u(member+20)]={'position':vec(member+32),'flags':hex(u(member+8))}
   row['actors'][ident]=v
  rows.append(row)
  if time.monotonic()>=until:break
  time.sleep(.5)
 a.save.parent.mkdir(parents=True,exist_ok=True);a.save.write_text(json.dumps(rows,indent=2))
 print(json.dumps({'samples':len(rows),'start':rows[0],'finish':rows[-1]},ensure_ascii=False))
finally:k.CloseHandle(h)
