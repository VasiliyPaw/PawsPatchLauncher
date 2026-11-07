"""Read-only x86 minidump exception/stack evidence. No memory mutation."""
import argparse,bisect,csv,json,struct
from pathlib import Path
def main():
 p=argparse.ArgumentParser();p.add_argument('dump',type=Path);p.add_argument('--out',type=Path);a=p.parse_args()
 b=a.dump.read_bytes();assert b[:4]==b'MDMP'
 u=lambda off:struct.unpack_from('<I',b,off)[0]
 q=lambda off:struct.unpack_from('<Q',b,off)[0]
 directories={}
 for i in range(u(8)):
  typ,size,off=struct.unpack_from('<III',b,u(12)+i*12);directories[typ]=(size,off)
 ranges=[]
 if 5 in directories:
  off=directories[5][1]
  for i in range(u(off)):
   at=off+4+i*16;ranges.append((q(at),u(at+8),u(at+12)))
 if 9 in directories:
  off=directories[9][1];pos=q(off+8)
  for i in range(q(off)):
   start,length=struct.unpack_from('<QQ',b,off+16+i*16);ranges.append((start,length,pos));pos+=length
 def read(address,n):
  for start,length,pos in ranges:
   if start<=address and address+n<=start+length:return b[pos+address-start:pos+address-start+n]
  raise ValueError(hex(address))
 modules=[]
 if 4 in directories:
  off=directories[4][1]
  for i in range(u(off)):
   at=off+4+i*108;name=u(at+20)
   modules.append(dict(base=q(at),size=u(at+8),name=b[name+4:name+4+u(name)].decode('utf-16le')))
 def resolve(address):
  for m in modules:
   if m['base']<=address<m['base']+m['size']:return dict(module=Path(m['name']).name,rva=hex(address-m['base']))
  return {}
 exc=directories[6][1];context=u(exc+164)
 registers={name:u(context+off) for name,off in [('edi',156),('esi',160),('ebx',164),('edx',168),('ecx',172),('eax',176),('ebp',180),('eip',184),('esp',196)]}
 stack=[];at=registers['ebp'];seen=set()
 while at not in seen and len(stack)<30:
  seen.add(at)
  try:
   saved,ret=struct.unpack('<II',read(at,8));args=struct.unpack('<8I',read(at+8,32))
   stack.append(dict(frame=hex(at),ret=hex(ret),**resolve(ret),args=[hex(x) for x in args]));at=saved
  except ValueError:break
 raw_stack=[]
 for offset in range(0,768,4):
  try:value=struct.unpack('<I',read(registers['esp']+offset,4))[0]
  except ValueError:break
  symbol=resolve(value)
  if symbol:raw_stack.append(dict(offset=hex(offset),value=hex(value),**symbol))
 result=dict(exception=hex(u(exc+8)),address=hex(q(exc+24)),where=resolve(q(exc+24)),registers={k:hex(v) for k,v in registers.items()},frames=stack,rawStackCodeCandidates=raw_stack)
 print(json.dumps(result,indent=2))
 if a.out:a.out.write_text(json.dumps(result,indent=2))
if __name__=='__main__':main()
