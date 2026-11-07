"""Export the existing lobby R2 core verbatim for the owned native hot-join lab."""
import argparse,hashlib,json,shutil,struct,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def u(b,i):return struct.unpack_from('<I',b,i)[0]
def arr(name,b,typ='unsigned char'):
    return 'static const '+typ+' '+name+'[]={\n'+''.join(' '+','.join('0x%02x'%x for x in b[i:i+16])+',\n' for i in range(0,len(b),16))+'};\n'
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--analysis-work',type=Path,required=True);a=p.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    source=HERE.parent/'fast-transfer/FastTransfer.cs';code=source.read_bytes();shutil.copy2(source,out/'FastTransfer.cs')
    csc=Path('C:/Windows/Microsoft.NET/Framework/v4.0.30319/csc.exe');exe=out/'R2PayloadExport.exe'
    subprocess.run([str(csc),'/nologo','/target:exe','/platform:x86','/define:PAW_PURE_FAST_TRANSFER','/out:'+str(exe),str(source),str(HERE/'R2PayloadExport.cs')],check=True)
    subprocess.run([str(exe),str(out)],check=True)
    b=(out/'base.bin').read_bytes();v=[(out/n).read_bytes() for n in ('image-plus-one.bin','cave-plus-one.bin')]
    assert len(b)==8192 and b[768:]==bytes(8192-768)
    fixes=[];i=0
    while i<768:
        if any(x[i]!=b[i] for x in v):
            delta=[(u(x,i)-u(b,i))&0xffffffff for x in v];assert delta[0] in (0,1) and delta[1] in (0,1,0xffffffff),(i,delta)
            fixes.append((i,delta[0],-1 if delta[1]==0xffffffff else delta[1]));i+=4
        else:i+=1
    reconstructed=bytearray(b)
    for i,image,cave in fixes:struct.pack_into('<I',reconstructed,i,(u(b,i)+image*(0x740000-0x400000)+cave*(0x19800000-0x10000000))&0xffffffff)
    assert reconstructed==(out/'aslr.bin').read_bytes(),'C relocation table differs from original managed R2 exporter'
    header='/* Generated from unchanged game/fast-transfer/FastTransfer.cs. */\n#define HJ_R2_SOURCE_SHA256 "'+sha(code)+'"\n'
    header+=arr('hj_r2_payload',b[:768])
    header+='static const struct {unsigned offset;int image,cave;} hj_r2_fixes[]={\n'+''.join(' {%d,%d,%d},\n'%x for x in fixes)+'};\n'
    (HERE/'r2_payload.h').write_text(header)
    subprocess.run([sys.executable,str(HERE.parent/'fast-transfer/prepare_guards.py'),'--work',str(a.analysis_work),'--out',str(out)],check=True)
    blob=(out/'FastTransferGuards.bin').read_bytes();magic,count=struct.unpack_from('<II',blob);assert magic==0x31544650
    at=8;header='/* Exact original R2 guards; expected image base 0x460000. */\n'
    for index in range(count):
        rva,n=struct.unpack_from('<II',blob,at);at+=8;data=blob[at:at+n];at+=n
        fix_count=u(blob,at);at+=4;fix=list(struct.unpack_from('<'+'I'*fix_count,blob,at));at+=fix_count*4
        header+=arr('hj_r2_guard_%d'%index,data)
        header+='static const unsigned hj_r2_guard_fix_%d[]={%s};\n'%(index,','.join(map(str,fix)) if fix else '0')
        header+='#define HJ_R2_GUARD_ROW_%d {%du,%du,hj_r2_guard_%d,%du,hj_r2_guard_fix_%d}\n'%(index,rva,n,index,fix_count,index)
    assert at==len(blob)
    header+='static const struct {unsigned rva,size;const unsigned char *bytes;unsigned count;const unsigned *fixes;} hj_r2_guards[]={\n'+''.join(' HJ_R2_GUARD_ROW_%d,\n'%i for i in range(count))+'};\n'
    (HERE/'r2_guards.h').write_text(header)
    shutil.copy2(source,HERE/'FastTransferR2Source.cs')
    (out/'export.json').write_text(json.dumps(dict(source=str(source),sourceSha256=sha(code),payloadSha256=sha(b),relocations=fixes,aslrByteIdentical=True,guardCount=count,guardsSha256=sha(blob)),indent=2))
    print('Exported unchanged lobby R2 payload; verified ASLR reconstruction; '+str(count)+' native guards')
if __name__=='__main__':main()
