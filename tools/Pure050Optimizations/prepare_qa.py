"""Freeze QA-only input/observation plus read-only compiled graphics counters."""
import shutil,subprocess
from context import *
def main():
 out=OUT/'qa-rig';shutil.copytree(PREVIOUS/'qa-rig-r3',out)
 loader=Path('G:/PawPure050QA-20261109/vanilla-pair-r5/host/game/avifil32.dll');assert sha(loader)=='449DA31A592CC53D48845EF980258F226FF389091E40D9A27373EE79FD8BA7E0';shutil.copy2(loader,out/'avifil32.dll')
 import pefile
 from capstone import Cs,CS_ARCH_X86,CS_MODE_32,CS_OP_MEM
 pe=pefile.PE(str(OUT/'native-r1/graphics/d3d9.dll'));base=pe.OPTIONAL_HEADER.ImageBase;entry=next(e.address for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name==b'PawBufferPoolStats');md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True;rvas=[]
 # Actual exported code copies these ten scalar globals to consecutive output
 # elements. Read them externally during QA; do not call a lock-taking API from
 # an arbitrary engine callback or retain resource pointers.
 for ins in md.disasm(pe.get_memory_mapped_image()[entry:entry+300],base+entry):
  if ins.mnemonic=='mov'and len(ins.operands)==2:
   m=ins.operands[1]
   if m.type==CS_OP_MEM and not m.mem.base and not m.mem.index and base<=m.mem.disp<base+pe.OPTIONAL_HEADER.SizeOfImage:rvas.append(m.mem.disp-base)
  if ins.mnemonic.startswith('ret'):break
 assert len(rvas)==10 and len(set(rvas))==10
 write(out/'graphics-counters.json',dict(dllSha256=sha(OUT/'native-r1/graphics/d3d9.dll'),functionRva=entry,names=['mode','hits','keeps','drops','held','bytes','privateDrops','busy','evictions','frame'],rvas=rvas,readOnly=True,atomicSnapshot=False))
 print('PURE_OPT_QA_FROZEN; no QA DLL or observer enters production')
if __name__=='__main__':main()
