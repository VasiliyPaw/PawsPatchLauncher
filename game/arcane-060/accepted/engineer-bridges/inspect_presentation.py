"""Read native bridge view and attached effects from the exact owned process."""
from pathlib import Path
import argparse,ctypes as C,json,re,struct
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('ids',nargs='+',type=int);a=p.parse_args();r=a.out.resolve()
ident=json.loads((r/'qa-process.json').read_text());base=int(re.findall(r'k2.exe at ([0-9A-F]+)',(r/'sandbox/Mods/plugins.log').read_text())[-1],16)
k=C.WinDLL('kernel32',use_last_error=True);k.OpenProcess.restype=C.c_void_p;k.ReadProcessMemory.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_size_t,C.c_void_p];k.QueryFullProcessImageNameW.argtypes=[C.c_void_p,C.c_uint,C.c_wchar_p,C.c_void_p];h=k.OpenProcess(0x410,False,ident['pid']);assert h
buf=C.create_unicode_buffer(32768);size=C.c_uint(32768);assert k.QueryFullProcessImageNameW(h,0,buf,C.byref(size)) and Path(buf.value).resolve()==(r/'sandbox/k2.exe').resolve()
def read(at,n=4):
 b=C.create_string_buffer(n);assert k.ReadProcessMemory(h,at,b,n,None),hex(at);return b.raw
def u(at):return struct.unpack('<I',read(at))[0]
def vec(at):return list(struct.unpack('<3f',read(at,12)))
def name(definition):return read(u(definition+8),160).decode('utf-16le',errors='replace').split('\0')[0] if definition else None
def scene_node(model):
 if not model:return None
 ptr=u(model+12)
 return {'pointer':hex(ptr),'flags':hex(struct.unpack('<H',read(ptr+0x20,2))[0]),'parent':hex(u(ptr+0x24)),'local':vec(ptr+0x5c),'world':vec(ptr+0x90),'localScale':struct.unpack('<f',read(ptr+0x68))[0],'worldScale':struct.unpack('<f',read(ptr+0x9c))[0]}
try:
 reg=u(base+0x5ef72c);rows=[]
 for actor_id in a.ids:
  actor=u(reg+0x20004+(actor_id&65535)*4);assert u(actor+20)==actor_id;view=u(actor+12);data=u(view+16);lst=u(view+0x9c);node=u(lst) if lst else 0;effects=[]
  while node and len(effects)<40:
   fx=u(node);definition=u(fx+16);effects.append({'pointer':hex(fx),'type':hex(u(fx)-base),'state':u(fx+0x18),'flags':hex(u(fx+0x54)),'modelFlags':hex(u(u(fx+0xac)+4)) if u(fx)-base==0x50aa5c and u(fx+0xac)>65536 else None,'name':name(definition),'local':vec(fx+0x38),'orientation':vec(fx+0x44),'owner':hex(u(fx+0x90)),'tag':hex(u(fx+0x78)),'scale':struct.unpack('<f',read(fx+0x98))[0],'model':hex(u(fx+0xac)),'transformB0':vec(fx+0xb0),'sceneNode':scene_node(u(fx+0xac)) if u(fx)-base==0x50aa5c else None});node=u(node+4)
  rows.append({'id':actor_id,'viewState':u(view+0x18),'view':hex(view),'flags':hex(u(view+0x54)),'position':vec(view+0x38),'selected':name(u(data+0x148)),'focused':name(u(data+0x14c)),'effects':effects})
 print(json.dumps(rows,indent=2))
finally:
 k.CloseHandle.argtypes=[C.c_void_p];k.CloseHandle(h)

