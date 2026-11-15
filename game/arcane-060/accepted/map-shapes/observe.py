"""Read-only telemetry for the private terrain sandbox; never sends orders."""
import argparse,ctypes,json,struct,time,hashlib,collections
from ctypes import wintypes as W
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--pid',type=int,required=True);p.add_argument('--image',type=lambda s:int(s,0),required=True);p.add_argument('--state',type=lambda s:int(s,0));p.add_argument('--roads',type=lambda s:int(s,0));p.add_argument('--seconds',type=float,default=0);p.add_argument('--out',type=Path);p.add_argument('--terrain',action='store_true');p.add_argument('--drag-roads',action='store_true');a=p.parse_args()
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
   # Include static actors to validate placement and access.
   move=u(actor+0x6c)
   actors.append(dict(ptr=hex(actor),id=u(actor+0x14),ids=ids(u(actor+4)),kingdom=hex(u(actor+0xe8)),flags=hex(flags),x=f(actor+0x20),y=f(actor+0x24),org=hex(org),company_speed=f(org+0xd8) if org else None,movement=[f(move+i) for i in (0x20,0x24,0x28)] if move else None))
  except OSError:continue
 result=dict(wall=time.time(),world=hex(world),seconds=f(world+0xec),tick=u(world+0xe4),map=dict(ptr=hex(grid),width=u(grid+0x1c),height=u(grid+0x20),cell=f(grid+8),worldsize=[f(grid+0xc),f(grid+0x10)]),actors=actors)
 if a.state:
  result['probe']=list(struct.unpack('<26I',read(a.state,104)))
  plan=u(a.state+88);size=u(a.state+92)
  if a.out and plan and size==u(grid+0x1c)*u(grid+0x20):
   target=a.out.with_suffix('.plan.bin');target.write_bytes(read(plan,size));result['riverPlan']=str(target)
 if a.roads:
  d=a.roads
  result['roads']=dict(header=list(struct.unpack('<46I',read(d,184))),lastTime=f(d+400),world_e8=f(world+0xe8),world_ec=f(world+0xec),jobs=[list(struct.unpack('<4I4f',read(d+404+i*32,32))) for i in range(0 if a.drag_roads else 64) if u(d+404+i*32)])
  if a.drag_roads:
   result['roads']['jobs']=[dict(id=u(d+404+i*2092),count=u(d+404+i*2092+32),index=u(d+404+i*2092+36),issued=u(d+404+i*2092+40),points=list(struct.unpack('<512I',read(d+404+i*2092+44,2048)))) for i in range(8) if u(d+404+i*2092)]
   result['roads']['plan']=list(struct.unpack('<9I',read(d+17140,36)))
  button=u(d+168)
  if button:
   result['roads']['tooltip_fields']={hex(off):read(u(button+off),128).decode('utf-16le',errors='replace').split('\0')[0] for off in (0x3c,0x40)}
 if a.terrain:
  hm=u(world+0x38); hw=u(hm+0xc); hh=u(hm+0x10); heights=read(u(hm+0x40),hw*hh*4)
  result['heights']=dict(width=hw,height=hh,shift=u(hm+0x14),pad=u(hm+0x1c),sha256=hashlib.sha256(heights).hexdigest(),minimum=min(struct.unpack('<%df'%(hw*hh),heights)),maximum=max(struct.unpack('<%df'%(hw*hh),heights)))
  basehm=u(world+0x34); baseheights=read(u(basehm+0x40),hw*hh*4)
  absolute=[b+d for (b,),(d,) in zip(struct.iter_unpack('<f',baseheights),struct.iter_unpack('<f',heights))]
  if a.out:a.out.with_suffix('.base-heights.bin').write_bytes(baseheights);a.out.with_suffix('.delta-heights.bin').write_bytes(heights)
  if a.out:a.out.with_suffix('.heights.bin').write_bytes(struct.pack('<%df'%len(absolute),*absolute))
  result['base_heights_sha256']=hashlib.sha256(baseheights).hexdigest()
  result['absolute_heights']=dict(minimum=min(absolute),maximum=max(absolute),below_water=sum(v<0 for v in absolute))
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
