using System;
using System.Collections.Generic;
using System.Linq;

internal sealed class MixedFakeMemory : IMemory
{
    internal readonly Dictionary<uint,byte> Bytes=new Dictionary<uint,byte>();
    internal int Calls,Fail=-1; internal bool Freed; internal uint Image;
    void Step(){if(++Calls==Fail)throw new InvalidOperationException("fixture fault");}
    internal void Seed(uint p,byte[] b){for(int i=0;i<b.Length;i++)Bytes[p+(uint)i]=b[i];}
    public byte[] Read(uint p,int n){Step();byte[] b=new byte[n];for(int i=0;i<n;i++){byte v;Bytes.TryGetValue(p+(uint)i,out v);b[i]=v;}return b;}
    public void Write(uint p,byte[] b){Step();Seed(p,b);}
    public void WriteCode(uint p,byte[] b){Step();Seed(p,b);}
    public uint Allocate(int n){Step();return 0x16000000;}
    public void MakeExecutable(uint p,int n){Step();}
    public void Flush(uint p,int n){Step();}
    public void Free(uint p){Step();Freed=true;}
}
internal static class MixedTransactionTests
{
    static int checks;
    static void Check(bool b){if(!b)throw new Exception("transaction check failed");checks++;}
    static readonly uint[] Sites={0x25697a,0x2566b9,0x235c4c,0x5c138,0xbf32d,0x1251a8};
    static byte[][] Originals(uint image){return new[]{TerrainPatch.Hex("e89a050000"),(new byte[]{0xb8}).Concat(BitConverter.GetBytes(image+0x43ff0d)).ToArray(),TerrainPatch.Hex("8b80b4010000"),TerrainPatch.Hex("8b80b4010000"),TerrainPatch.Hex("8b80b4010000"),TerrainPatch.Hex("e804001800")};}
    static MixedFakeMemory Memory(uint image){var m=new MixedFakeMemory{Image=image};var old=Originals(image);for(int i=0;i<Sites.Length;i++)m.Seed(image+Sites[i],old[i]);return m;}
    public static void Main()
    {
        foreach(uint image in new uint[]{0x460000,0x620000,0xd00000})
        {
            var good=Memory(image);MixedBiomesTestPatch.Install(good,image,delegate{});int total=good.Calls;Check(!good.Freed);
            for(int fault=1;fault<=total;fault++)
            {
                var m=Memory(image);m.Fail=fault;bool failed=false;
                try{MixedBiomesTestPatch.Install(m,image,delegate{});}catch{failed=true;}
                Check(failed);var old=Originals(image);m.Fail=-1;
                for(int i=0;i<Sites.Length;i++)Check(m.Read(image+Sites[i],old[i].Length).SequenceEqual(old[i]));
            }
            for(int bad=0;bad<Sites.Length;bad++)
            {
                var m=Memory(image);m.Seed(image+Sites[bad],new byte[]{0xcc});bool failed=false;
                try{MixedBiomesTestPatch.Install(m,image,delegate{});}catch{failed=true;}
                Check(failed);Check(!m.Bytes.ContainsKey(0x16000000));
            }
        }
        Console.WriteLine("MIXED_TRANSACTION_PASS "+checks+"; every operation fault and guard mismatch; three image bases");
    }
}
