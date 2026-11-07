"""Read-only census of an owned test process. Refuses other executable paths."""
import ctypes as C,json,re,struct,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve(); identity=json.loads((root/'process.json').read_text())
k=C.WinDLL('kernel32',use_last_error=True);k.OpenProcess.restype=C.c_void_p
k.ReadProcessMemory.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_size_t,C.c_void_p]
k.QueryFullProcessImageNameW.argtypes=[C.c_void_p,C.c_uint,C.c_wchar_p,C.c_void_p]
k.CloseHandle.argtypes=[C.c_void_p]
h=k.OpenProcess(0x1010,False,identity['pid']);assert h
try:
 p=C.create_unicode_buffer(32768);n=C.c_ulong(len(p));assert k.QueryFullProcessImageNameW(h,0,p,C.byref(n))
 assert Path(p.value).resolve()==(root/'game/k2.exe').resolve()
 def read(p,n):
  b=C.create_string_buffer(n);done=C.c_size_t();assert k.ReadProcessMemory(h,p,b,n,C.byref(done)) and done.value==n,hex(p);return b.raw
 def u(p):return struct.unpack('<I',read(p,4))[0]
 base=int(re.search(r'k2.exe at ([0-9A-F]+)',(root/'game/Mods/plugins.log').read_text())[1],16)
 session=u(base+0x5f3fe4);admin=u(base+0x5f3fec);sim=u(base+0x5f3fe8)
 def string_at(p):
  if not p:return ''
  length=u(p-12);return read(p,min(length,160)*2).decode('utf-16le',errors='replace')
 result=dict(pid=identity['pid'],mode=u(session+0xf0),desired=u(session+0x60),world=hex(u(base+0x5f3fb8)),frozen=read(sim+0x29,1).hex(),netSync=[u(u(base+0x5f3ff0)+i*4) for i in range(6)],worldSync=[u(u(base+0x5f3ff4)+i*4) for i in range(6)],players=[])
 result.update(filename=string_at(u(session+0x68)),mapIndex=u(session+0x164),hostState=u(admin+0x300),nativeHost=hex(u(admin+0x2e4)),nativeServer=hex(u(admin+0x2e8)))
 node=u(session+0xc8)
 for _ in range(40):
  if not node:break
  player=u(node);conn=u(player+4);row=dict(player=hex(player),conn=hex(conn),id=u(player+0x20))
  if conn!=admin:
   row['flags']={hex(off):read(conn+off,1)[0] for off in [0x34,0x4d,0x4e,0x4f,0x59,0x98,0x99,0xb6]}
   row['connection']={hex(off):u(conn+off) for off in [0x3c,0x40,0x44,0x48,0x430]}
   row['sender']={hex(off):u(conn+0x3b4+off) for off in [0x2c,0x30,0x48]}
   row['receiver']={hex(off):u(conn+0x400+off) for off in [0x10,0x14,0x24]}
  result['players'].append(row);node=u(node+4)
 result['ownFlags']={hex(off):read(admin+off,1)[0] for off in [0x34,0x4d,0x4e,0x4f,0x59,0x2e0]}
 if '--sources' in sys.argv:
  result['sourceChain']=[];res=u(u(base+0x5f3fb8)+0x28);seen=set()
  for _ in range(20):
   if not res or res in seen:break
   seen.add(res)
   row=dict(resource=hex(res),flags=hex(u(res+8)),creator=hex(u(res+0x88)),settings=hex(u(res+0x90)),filename=string_at(u(res+0x38)))
   try:
    creator=u(res+0x88);vtable=u(creator)
    row.update(creatorVtableRva=hex(vtable-base),getClassFunctionRva=hex(u(vtable+4)-base),nextResource=hex(u(creator+0x50)))
    result['sourceChain'].append(row);res=u(creator+0x50)
   except AssertionError:result['sourceChain'].append(row);break
  result['sourceChainTerminal']=hex(res)
 print(json.dumps(result,indent=2))
finally:k.CloseHandle(h)
