"""Execute the compiled byte/relocation guard at three game image bases."""
import argparse,json,struct
from pathlib import Path
from test_native import PE,PROJECT,Uc,UC_ARCH_X86,UC_MODE_32,Ks,KS_ARCH_X86,KS_MODE_32
from unicorn.x86_const import *
def main():
 p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();raw=(PROJECT/'work/kohan-ii-decompilation/inputs/k2_runtime_1372_20260904.bin').read_bytes();provenance=json.loads((a.build/'contract-provenance.json').read_text());pe=PE(a.build/'test-local.dll');exports=pe.exports();ks=Ks(KS_ARCH_X86,KS_MODE_32);checks=0
 for image in [0x400000,0x460000,0x1800000]:
  u=Uc(UC_ARCH_X86,UC_MODE_32);memory=bytearray(raw);delta=image-0x460000
  for addr in provenance['relocations']:
   if addr+4<=len(memory):struct.pack_into('<I',memory,addr,(struct.unpack_from('<I',memory,addr)[0]+delta)&0xffffffff)
  u.mem_map(image,(len(memory)+4095)&~4095);u.mem_write(image,bytes(memory));pe.load(u);stack=0x20000000;stop=0x40000000;stub=0x55000000
  for at in [stack,stop,stub]:u.mem_map(at,0x10000)
  # Imported CRT comparison is a deterministic byte comparator for this proof.
  code=bytes(ks.asm('push esi;push edi;mov esi,[esp+12];mov edi,[esp+16];mov ecx,[esp+20];cld;repe cmpsb;setz al;movzx eax,al;xor eax,1;pop edi;pop esi;ret',stub)[0]);u.mem_write(stub,code)
  imports=struct.unpack_from('<I',pe.b,pe.opt+104)[0]
  while imports:
   original,_,_,name,iat=struct.unpack_from('<5I',pe.b,pe.at(imports))
   if not name:break
   index=0
   while True:
    thunk=struct.unpack_from('<I',pe.b,pe.at(original or iat)+index*4)[0]
    if not thunk:break
    if not thunk&0x80000000:
     pos=pe.at(thunk)+2;symbol=pe.b[pos:pe.b.index(b'\0',pos)].decode()
     if symbol=='memcmp':u.mem_write(pe.base+iat+index*4,struct.pack('<I',stub))
    index+=1
   imports+=20
  def call(name,args=()):
   sp=stack+0x8000;u.mem_write(sp,struct.pack('<'+'I'*(len(args)+1),stop,*args));u.reg_write(UC_X86_REG_ESP,sp);u.emu_start(exports[name],stop,count=30000);assert u.reg_read(UC_X86_REG_EIP)==stop;return u.reg_read(UC_X86_REG_EAX)
  assert call('TestContractInit',(image,))==1;checks+=1
  for name,rva,size in provenance['ranges']:
   old=bytes(u.mem_read(image+rva,1));u.mem_write(image+rva,bytes([old[0]^1]));assert call('TestContractMatches')==0,(image,name);checks+=1;u.mem_write(image+rva,old);assert call('TestContractMatches')==1;checks+=1
 a.out.write_text(json.dumps(dict(accepted=True,checks=checks,imageBases=['0x400000','0x460000','0x1800000'],ranges=provenance['ranges'],contractRelocationCount=provenance['contractRelocationCount'],tamperedBodiesRefused=True),indent=2));print('LOCAL_FIND_CONTRACT_PASS',checks,'ASLR/corruption checks')
if __name__=='__main__':main()
