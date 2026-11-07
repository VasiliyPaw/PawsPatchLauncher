using System;
using System.IO;
namespace PawPureFixes {
    internal interface IPatchMemory {
        byte[] Read(uint address,int size);uint Allocate(int size);
        void Write(uint address,byte[] bytes);void WriteCode(uint address,byte[] bytes);
        void MakeExecutable(uint address,int size);void Flush(uint address,int size);void Free(uint address);
    }
    internal static class PurePatch {
        internal static byte[] Hex(string value) {
            var b=new byte[value.Length/2];for(int i=0;i<b.Length;i++)b[i]=Convert.ToByte(value.Substring(i*2,2),16);return b;
        }
        internal static void Expect(IPatchMemory m,uint address,byte[] expected) {
            var actual=m.Read(address,expected.Length);for(int i=0;i<expected.Length;i++)if(actual[i]!=expected[i])throw new InvalidDataException("guard");
        }
    }
}
internal static class R2PayloadExport {
    static void Main(string[] args) {
        Directory.CreateDirectory(args[0]);
        File.WriteAllBytes(Path.Combine(args[0],"base.bin"),PawFastTransfer.Payload(0x400000,0x10000000));
        File.WriteAllBytes(Path.Combine(args[0],"image-plus-one.bin"),PawFastTransfer.Payload(0x400001,0x10000000));
        File.WriteAllBytes(Path.Combine(args[0],"cave-plus-one.bin"),PawFastTransfer.Payload(0x400000,0x10000001));
        File.WriteAllBytes(Path.Combine(args[0],"aslr.bin"),PawFastTransfer.Payload(0x740000,0x19800000));
        foreach(uint image in new uint[]{0x400000,0x460000,0xaf0000})
            File.WriteAllBytes(Path.Combine(args[0],"payload-"+image.ToString("X")+".bin"),PawFastTransfer.Payload(image,0x10000000));
    }
}
