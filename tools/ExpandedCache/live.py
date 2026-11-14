"""Observe/control only the existing owned G:/PawGraphicsQA game."""
import argparse,ctypes as C,json,struct,sys,time,os
from pathlib import Path
from build import OUT,WS,read,write
sys.path.insert(0,str(WS/'work/graphics-artifact-20261113'));import control
QA=control.QA;GAME=control.GAME;K=control.K
class MBI(C.Structure):
 _fields_=[('base',C.c_void_p),('allocation',C.c_void_p),('protection',C.c_ulong),('partition',C.c_ushort),('size',C.c_size_t),('state',C.c_ulong),('protect',C.c_ulong),('kind',C.c_ulong)]
K.VirtualQueryEx.argtypes=[C.c_void_p,C.c_void_p,C.POINTER(MBI),C.c_size_t];K.VirtualQueryEx.restype=C.c_size_t
def snapshot():
 snap=control.snapshot()
 if snap['world']:snap=control.snapshot(True)
 h=K.OpenProcess(0x1410,False,snap['pid']);assert h
 def data(at,n):
  b=C.create_string_buffer(n);got=C.c_size_t();assert K.ReadProcessMemory(h,at,b,n,C.byref(got))and got.value==n;return b.raw
 def u(at):return struct.unpack('<I',data(at,4))[0]
 try:
  image=snap['base'];entry=image+0x13c634;assert data(entry,1)==b'\xe9';frame=entry+5+struct.unpack('<i',data(entry+1,4))[0]
  session=u(image+0x5f3fe4);admin=u(image+0x5f3fec);node=u(session+0xc8);snap['players']=[]
  for _ in range(40):
   if not node:break
   p=u(node);name=data(u(p+8),100).decode('utf-16le',errors='replace').split('\0')[0]
   snap['players'].append(dict(name=name,ai=data(p+0xc,1)[0],local=u(p+4)==admin,kingdom=u(p+0x28)));node=u(node+4)
  assert data(frame+22,1)==b'\x68';state=u(frame+23);assert u(state)==image
  words=struct.unpack('<38I',data(state,152));snap['cacheState']=state
  snap['budget']=dict(zip(['calls','ram','vram','freeVaMiB','freePhysMiB','pressure','probeAt','refreshes','apiFailures','shrinks'],words[28:]));snap['prepared']=words[10]
  controller=u(image+0x5f3fe8);snap['paused']=data(controller+0x28,1)[0]if controller else None
  manager=u(image+0x5f3fd4)+0x9c;snap['nativeTotals']=[u(manager+0x34),u(manager+0x40)];snap['cachedEstimates']=[u(manager+0x30),u(manager+0x3c)]
  table=u(manager+0x20);count=u(manager+0x24);snap['classes']=[]
  assert count<4096
  for i in range(count):
   node=u(table+i*4)
   while node:
    p=u(node+4);snap['classes'].append(dict(type=u(p+4),ramLimit=u(p+8),ramUsed=u(p+12),ramWeight=u(p+20),vramLimit=u(p+24),vramUsed=u(p+28),vramWeight=u(p+36)));node=u(node+8)
  at=0;free=largest=0
  while at<0x100000000:
   region=MBI()
   if not K.VirtualQueryEx(h,at,C.byref(region),C.sizeof(region)):break
   end=(region.base or 0)+region.size
   if end<=at:break
   if region.state==0x10000:free+=region.size;largest=max(largest,region.size)
   at=end
  snap['addressSpace']=dict(free=free,largestFreeBlock=largest)
  return snap
 finally:K.CloseHandle(h)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['bind','snapshot','command','observe']);p.add_argument('value',nargs='?');a=p.parse_args()
 if a.action=='bind':
  text=Path(read(OUT/'live-helper.json')['log']).read_text();pid=int(text.split('OWNED_GAME ')[1].split()[0]);write(QA/'process.json',dict(pid=pid,helperPid=read(OUT/'live-helper.json')['helperPid'],mode='expanded-cache',created=time.time()));print(json.dumps(snapshot()))
 elif a.action=='snapshot':
  s=snapshot();write(OUT/(a.value or 'live-snapshot.json'),s);print(json.dumps({k:v for k,v in s.items()if k not in['companies','classes']}))
 elif a.action=='command':snapshot();control.command(a.value)
 else:
  rows=[];until=time.monotonic()+int(a.value or '60')
  while time.monotonic()<until:
   s=snapshot();rows.append({k:v for k,v in s.items()if k!='companies'});write(OUT/'live-observation.json',rows);print(s.get('seconds'),s['budget'],flush=True);time.sleep(2)
