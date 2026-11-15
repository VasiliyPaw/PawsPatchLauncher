"""Read-only hashes and terrain invariants from the exact marked QA process."""
from pathlib import Path
import argparse,json,ctypes as C,struct,re,hashlib,collections
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--save',type=Path,required=True);p.add_argument('--dump-grid',action='store_true');a=p.parse_args()
r=a.out.resolve();identity=json.loads((r/'qa-process.json').read_text());base=int(re.findall(r'k2.exe at ([0-9A-F]+)',(r/'sandbox/Mods/plugins.log').read_text())[-1],16)
k=C.WinDLL('kernel32',use_last_error=True);k.OpenProcess.argtypes=[C.c_uint,C.c_int,C.c_uint];k.OpenProcess.restype=C.c_void_p;k.ReadProcessMemory.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_size_t,C.c_void_p];k.QueryFullProcessImageNameW.argtypes=[C.c_void_p,C.c_uint,C.c_wchar_p,C.c_void_p];k.CloseHandle.argtypes=[C.c_void_p]
h=k.OpenProcess(0x410,False,identity['pid']);assert h
buf=C.create_unicode_buffer(32768);size=C.c_uint(32768)
assert k.QueryFullProcessImageNameW(h,0,buf,C.byref(size)) and Path(buf.value).resolve()==(r/'sandbox/k2.exe').resolve()
def read(at,size):
 data=C.create_string_buffer(size);done=C.c_size_t();assert k.ReadProcessMemory(h,at,data,size,C.byref(done)) and done.value==size,hex(at);return data.raw
def u(at):return struct.unpack('<I',read(at,4))[0]
def ids(ptr):return read(u(ptr+8),160).decode('utf-16le',errors='replace').split('\0')[0]
try:
 world=u(base+0x5f3fb8);assert world and u(base+0x5f9218)==2
 result=dict(pid=identity['pid'],world=world,heights={})
 for key,offset in [('base',0x34),('deformation',0x38)]:
  hm=u(world+offset);width=u(hm+0xc);height=u(hm+0x10);assert 0<width<=4097 and 0<height<=4097
  data=read(u(hm+0x40),width*height*4)
  if a.dump_grid:a.save.with_suffix('.'+key+'.bin').write_bytes(data)
  result['heights'][key]=dict(width=width,height=height,shift=u(hm+0x14),pad=u(hm+0x1c),sha256=hashlib.sha256(data).hexdigest())
 grid=u(world+0x30);width=u(grid+0x1c);height=u(grid+0x20);assert width<=1024 and height<=1024
 data=read(u(grid+0x28),width*height*0x30);names={};cells=[]
 if a.dump_grid:a.save.with_suffix('.grid.bin').write_bytes(data)
 for index in range(width*height):
  offset=index*0x30;variant=struct.unpack_from('<I',data,offset)[0]
  if variant not in names:names[variant]=ids(variant)
  if names[variant]=='paws_engineer_bridge01':cells.append(dict(x=index%width,y=index//width,flags=struct.unpack_from('<I',data,offset+0x20)[0],waterBody=data[offset+0x2c]))
 result['bridgeCells']=cells
 if a.dump_grid:result['grid']={'width':width,'height':height,'variants':names}
 a.save.parent.mkdir(parents=True,exist_ok=True);a.save.write_text(json.dumps(result,indent=2))
 print('WORLD_SNAPSHOT',a.save,'bridgeCells',len(cells),'blocked',sum(bool(c['flags']&0x100) for c in cells),'waterBodies',sorted({c['waterBody'] for c in cells}),'heights',result['heights'])
finally:k.CloseHandle(h)
