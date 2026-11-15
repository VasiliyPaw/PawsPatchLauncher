"""Read-only telemetry for the private terrain sandbox; never sends orders."""
import argparse,ctypes,json,struct,time,hashlib,collections
from ctypes import wintypes as W
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--pid',type=int,required=True);p.add_argument('--image',type=lambda s:int(s,0),required=True);p.add_argument('--state',type=lambda s:int(s,0));p.add_argument('--seconds',type=float,default=0);p.add_argument('--out',type=Path);p.add_argument('--terrain',action='store_true');a=p.parse_args()
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE
k.ReadProcessMemory.argtypes=[W.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)];k.ReadProcessMemory.restype=W.BOOL
k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,ctypes.POINTER(W.DWORD)]
k.CloseHandle.argtypes=[W.HANDLE]
h=k.OpenProcess(0x410,False,a.pid)
if not h:raise ctypes.WinError(ctypes.get_last_error())
path=ctypes.create_unicode_buffer(4096);size=W.DWORD(4096)
if not k.QueryFullProcessImageNameW(h,0,path,ctypes.byref(size)):raise ctypes.WinError(ctypes.get_last_error())
exe=Path(path.value)
if not (exe.parent/'terrain-prototype.marker').is_file():raise RuntimeError('Not the isolated test game')
def read(addr,n):
 b=ctypes.create_string_buffer(n);got=ctypes.c_size_t()
 if not k.ReadProcessMemory(h,addr,b,n,ctypes.byref(got)) or got.value!=n:raise OSError(hex(addr))
 return b.raw
def u(at):return struct.unpack('<I',read(at,4))[0]
def f(at):return struct.unpack('<f',read(at,4))[0]
def ids(at):
 try:return read(u(at+8),160).decode('utf-16-le',errors='replace').split('\0')[0]
 except OSError:return ''
def snapshot():
 world=u(a.image+0x5f3fb8);grid=u(world+0x30);reg=u(a.image+0x5ef72c)
 slots=struct.unpack('<65536I',read(reg+0x20004,65536*4));actors=[]
 for actor in slots:
  if not actor:continue
  try:
   if u(actor)!=a.image+0x4e5c58:continue
   flags=u(actor+8);org=u(actor+0x7c)
   if not org and not u(actor+0x80):continue
   move=u(actor+0x6c)
   actors.append(dict(ptr=hex(actor),id=u(actor+0x14),ids=ids(u(actor+4)),kingdom=hex(u(actor+0xe8)),flags=hex(flags),x=f(actor+0x20),y=f(actor+0x24),org=hex(org),company_speed=f(org+0xd8) if org else None,movement=[f(move+i) for i in (0x20,0x24,0x28)] if move else None))
  except OSError:continue
 result=dict(wall=time.time(),world=hex(world),seconds=f(world+0xec),tick=u(world+0xe4),map=dict(ptr=hex(grid),width=u(grid+0x1c),height=u(grid+0x20),cell=f(grid+8),worldsize=[f(grid+0xc),f(grid+0x10)]),actors=actors)
 if a.state:result['probe']=list(struct.unpack('<23I',read(a.state,92)))
 if a.terrain:
  raw=read(u(grid+0x28),u(grid+0x1c)*u(grid+0x20)*0x30);names={};terrain=[]
  for offset in range(0,len(raw),0x30):
   variant=struct.unpack_from('<I',raw,offset)[0]
   if variant not in names:names[variant]=ids(variant)
   terrain.append((names[variant],struct.unpack_from('<I',raw,offset+0x20)[0]&0x331))
  result['terrain']=dict(sha256=hashlib.sha256(json.dumps(terrain).encode()).hexdigest(),counts=dict(collections.Counter(t[0] for t in terrain)),cells=terrain)
 return result
try:
 end=time.monotonic()+a.seconds;rows=[]
 while True:
  rows.append(snapshot())
  if time.monotonic()>=end:break
  time.sleep(.1)
 if a.out:a.out.write_text(json.dumps(rows,indent=2),encoding='utf-8');print('Recorded',len(rows),'samples:',a.out)
 else:print(json.dumps(rows[-1],indent=2))
finally:k.CloseHandle(h)
