using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

internal static class LairRecoveryTests
{
    private sealed class Memory:IMemory
    {
        internal readonly Dictionary<uint,byte> Bytes=new Dictionary<uint,byte>();
        internal int Operations,FailAt=-1;internal bool Allocated,AlwaysFailCode;
        internal void Seed(uint a,byte[] b){for(int i=0;i<b.Length;i++)Bytes[a+(uint)i]=b[i];}
        private void Op(){if(++Operations==FailAt)throw new IOException("injected failure");}
        internal Memory(uint image)
        {
            for(int i=0;i<LairRecoveryPatch.Sites.Length;i++)Seed(image+LairRecoveryPatch.Sites[i],LairRecoveryPatch.Originals[i]);
            LairRecoveryPayload.VisitGuards(image,Seed);
            Seed(image+0x212019,TerrainPatch.Hex("6A1958C3"));
            Seed(image+0x4E17AC+0x18,BitConverter.GetBytes(image+0x212019));
            Seed(image+0x22E158,TerrainPatch.Hex("89749F60"));
            Seed(image+0x22E16D+0x19*4,BitConverter.GetBytes(image+0x22E088));
        }
        public byte[] Read(uint a,int n){Op();return Enumerable.Range(0,n).Select(i=>Bytes.ContainsKey(a+(uint)i)?Bytes[a+(uint)i]:(byte)0).ToArray();}
        public void Write(uint a,byte[] b){Seed(a,b.Take(2).ToArray());Op();Seed(a,b);}
        public void WriteCode(uint a,byte[] b){Seed(a,b.Take(2).ToArray());Op();if(AlwaysFailCode)throw new IOException("persistent partial write");Seed(a,b);}
        public uint Allocate(int n){Op();Allocated=true;return 0x60000000;}
        public void MakeExecutable(uint a,int n){Op();}
        public void Flush(uint a,int n){Op();}
        public void Free(uint a){Allocated=false;}
    }
    private static int checks;
    private static void Check(bool ok,string why){checks++;if(!ok)throw new Exception(why);}
    internal static int Main()
    {
        foreach(uint image in new uint[]{0x460000,0xE40000,0x12000000})
        {
            var success=new Memory(image);
            uint cave=LairRecoveryPatch.Install(success,image,delegate{});
            int operations=success.Operations;
            Check(cave==0x60000000 && success.Allocated,"successful allocation");
            for(int i=0;i<LairRecoveryPatch.Sites.Length;i++)
                Check(success.Read(image+LairRecoveryPatch.Sites[i],LairRecoveryPatch.Originals[i].Length).SequenceEqual(
                    LairRecoveryPatch.Jump(image+LairRecoveryPatch.Sites[i],cave+LairRecoveryPatch.Offsets[i],LairRecoveryPatch.Originals[i].Length)),"all hooks verified");
            for(int fault=1;fault<=operations;fault++)
            {
                var memory=new Memory(image){FailAt=fault};bool threw=false;
                try{LairRecoveryPatch.Install(memory,image,delegate{});}catch(IOException){threw=true;}
                Check(threw,"failure propagated");Check(!memory.Allocated,"allocation freed after rollback");
                for(int i=0;i<LairRecoveryPatch.Sites.Length;i++)
                    Check(memory.Read(image+LairRecoveryPatch.Sites[i],LairRecoveryPatch.Originals[i].Length).SequenceEqual(LairRecoveryPatch.Originals[i]),"partial transaction restored all sites");
            }
            var wrong=new Memory(image);wrong.Seed(image+LairRecoveryPatch.Sites[0],new byte[]{0xCC});bool rejected=false;
            try{LairRecoveryPatch.Install(wrong,image,delegate{});}catch(InvalidOperationException){rejected=true;}
            Check(rejected&&!wrong.Allocated,"unknown executable rejected before allocation");
            var persistent=new Memory(image){AlwaysFailCode=true};
            try{LairRecoveryPatch.Install(persistent,image,delegate{});}catch(IOException){}
            Check(persistent.Allocated,"stub retained if rollback cannot be proved");
        }
        Console.WriteLine("PASS "+checks+" lair transaction checks; no game launched.");return 0;
    }
}
