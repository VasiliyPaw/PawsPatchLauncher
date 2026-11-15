"""Read native lobby and world rules from the owned, marked QA copy only."""
import argparse,ctypes as C,json,struct
from pathlib import Path
import re
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--save',type=Path);a=p.parse_args();root=a.out.resolve()
identity=json.loads((root/'qa-process.json').read_text());log=(root/'sandbox/Mods/plugins.log').read_text();image=int(re.findall(r'k2.exe at ([0-9A-F]+)',log)[-1],16)
k=C.WinDLL('kernel32',use_last_error=True);k.OpenProcess.argtypes=[C.c_uint,C.c_int,C.c_uint];k.OpenProcess.restype=C.c_void_p;k.ReadProcessMemory.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_size_t,C.c_void_p];k.QueryFullProcessImageNameW.argtypes=[C.c_void_p,C.c_uint,C.c_wchar_p,C.c_void_p];k.CloseHandle.argtypes=[C.c_void_p]
h=k.OpenProcess(0x410,False,identity['pid']);assert h
name=C.create_unicode_buffer(32768);length=C.c_uint(32768);assert k.QueryFullProcessImageNameW(h,0,name,C.byref(length)) and Path(name.value).resolve()==root/'sandbox/k2.exe' and (root/'sandbox/terrain-prototype.marker').exists()
def read(at,n):
 b=C.create_string_buffer(n);got=C.c_size_t();assert k.ReadProcessMemory(h,at,b,n,C.byref(got)) and got.value==n,hex(at);return b.raw
def u(at):return struct.unpack('<I',read(at,4))[0]
def f(at):return struct.unpack('<f',read(at,4))[0]
def ids(at):return read(u(at+8),256).decode('utf-16le',errors='replace').split('\0')[0]
def rules(items,count):
 if not items or count>256:return {}
 return {ids(u(items+i*12)):{'value':u(items+i*12+8),'locked':read(items+i*12+4,1)[0]} for i in range(count) if u(items+i*12)}
try:
 session=u(image+0x5f3fe4);world=u(image+0x5f3fb8);prefs=u(image+0x5f9a0c);mode=u(session+0x64) if session else None
 info=u(session+0x80) if mode==0 else 0
 result={'pid':identity['pid'],'launchType':mode,'sessionType':u(session+0xf0) if session else None,'preferences':rules(u(prefs+0xb4),u(prefs+0xb8)) if prefs else {}}
 if info:result['lobby']={'ptr':hex(info),'size':[f(info+0x3c),f(info+0x40)],'profile':ids(u(info+0x50)) if u(info+0x50) else None,'rules':rules(u(info+0x2c),u(info+0x30))}
 if world:result['world']={'ptr':hex(world),'rules':rules(u(world+0x18),u(world+0x1c))}
 if a.save:a.save.write_text(json.dumps(result,indent=2))
 print(json.dumps(result,ensure_ascii=False))
finally:k.CloseHandle(h)
