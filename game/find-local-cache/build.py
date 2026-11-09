"""Build only a fresh private module and freeze its exact native contract."""
import argparse,csv,hashlib,json,shutil,struct,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3];TCC=PROJECT/'work/crash-20260914-continue/tools/tinycc/tcc/tcc.exe'
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 raw=(PROJECT/'work/kohan-ii-decompilation/inputs/k2_runtime_1372_20260904.bin').read_bytes();base=0x460000
 # Relocation-bearing bodies are checked after rebasing to the observed image.
 # Predicates contain absolute RTTI/jump-table references: encode those entries
 # relative to the captured base and compare with an explicit relocation mask.
 ranges=[('find',0x18e3c8,0xe4),('match',0x18de67,0x36),('predicate',0x18de9d,0x2c8),('shader',0x18e184,0x71),('texture',0x18e1f5,0x22)]
 functions={int(r['rva'],16):int(r['body_bytes'])for r in csv.DictReader((PROJECT/'work/kohan-ii-decompilation/exports/functions.tsv').open(encoding='utf-8'),delimiter='\t')}
 ranges.extend((name,rva,functions[rva])for name,rva in [('rtti',0x142c27),('property',0x384190)])
 contract='/* Exact native spans, with explicit PE HIGHLOW rebasing. */\n'
 # Absolute operands in matcher dispatch/RTTI are omitted from byte arrays by
 # generating a runtime expected copy with loader rebasing applied below.
 entries=[]
 for name,rva,n in ranges:
  data=raw[rva:rva+n];contract+=f'static BYTE lc_{name}_contract[{n}]={{'+','.join(hex(v)for v in data)+'};\n';entries.append((name,rva,n))
 # Actual rebasing sites come from the untouched installed PE relocation table.
 stock=(Path('D:/SteamLibrary/steamapps/common/Kohan II/k2.exe')).read_bytes();nt=struct.unpack_from('<I',stock,60)[0];count=struct.unpack_from('<H',stock,nt+6)[0];opt=nt+24;section=opt+struct.unpack_from('<H',stock,nt+20)[0];rr,rs=struct.unpack_from('<II',stock,opt+96+5*8);sections=[]
 assert hashlib.sha256(stock).hexdigest()=='1eb79bbb678668be5a05f8c98103cd9988048490ce7c53c74c9a1d0813e9cd45'
 assert hashlib.sha256(raw).hexdigest()=='b865d8206990c4f055c51de857f0b09b88ab5ee3b6ae74ee5232134001aa591c'
 for i in range(count):
  vs,va,size,offset=struct.unpack_from('<IIII',stock,section+i*40+8);sections.append((va,max(vs,size),offset))
 def off(r):return next(offset+r-va for va,size,offset in sections if va<=r<va+size)
 relocs=[];at=off(rr);end=at+rs
 while at<end:
  page,size=struct.unpack_from('<II',stock,at)
  if size<8:break
  for entry in struct.unpack_from('<'+'H'*((size-8)//2),stock,at+8):
   if entry>>12==3:relocs.append(page+(entry&4095))
  at+=size
 fix=[]
 for name,rva,n in entries:
  for addr in relocs:
   if rva<=addr and addr+4<=rva+n:fix.append(f'*(UINT*)(lc_{name}_contract+{addr-rva})+=(UINT)(base-0x460000);')
 assert len(fix)>=8,'Native relocation contract unexpectedly empty'
 contract+='static void lc_rebase_contract(void){'+''.join(fix)+'}\n'
 contract+='static int lc_contract_matches(void){return '+'&&'.join(f'!memcmp((void*)(base+{rva}),lc_{name}_contract,sizeof(lc_{name}_contract))'for name,rva,n in entries)+';}\n';(a.out/'native_contract.h').write_text(contract)
 (a.out/'contract-provenance.json').write_text(json.dumps(dict(captureBase=base,ranges=ranges,relocations=relocs,contractRelocationCount=len(fix),runtimeSha256=hashlib.sha256(raw).hexdigest(),stockSha256=hashlib.sha256(stock).hexdigest()),indent=2))
 for name in ['local_find.h','plugin.c','test_exports.c']:shutil.copy2(HERE/name,a.out/name)
 for source,target in [('plugin.c','PawFindLocalCache.dll'),('test_exports.c','test-local.dll')]:subprocess.run([str(TCC),'-shared','-Wall','-Werror',str(a.out/source),'-o',str(a.out/target),'-lkernel32'],check=True)
 (a.out/'build-manifest.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in a.out.iterdir()if p.is_file()},indent=2));print('PRIVATE_LOCAL_FIND_BUILT',a.out)
if __name__=='__main__':main()
