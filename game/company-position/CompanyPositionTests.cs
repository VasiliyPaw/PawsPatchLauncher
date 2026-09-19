using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

internal static class CompanyPositionTests
{
    private sealed class Memory:IMemory
    {
        internal readonly Dictionary<uint,byte> Bytes=new Dictionary<uint,byte>();
        internal int Operations,FailAt=-1;internal bool Allocated,AlwaysFailCode;
        internal void Seed(uint a,byte[] b){for(int i=0;i<b.Length;i++)Bytes[a+(uint)i]=b[i];}
        private void Op(){if(++Operations==FailAt)throw new IOException("injected failure");}
        internal Memory(uint image)
        {
            Seed(image+CompanyPositionPatch.HookRva-2,CompanyPositionPatch.Guard);
            Seed(image+0x218885,CompanyPositionPatch.CallbackGuard);
            Seed(image+0x2925E6,CompanyPositionPatch.InsertGuard);
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
    internal static int Main(string[] args)
    {
        uint[] images={0x460000,0xE40000,0x12000000},caves={0x10000000,0x21000000,0x60000000};
        for(int n=0;n<images.Length;n++)
        {
            uint image=images[n];var success=new Memory(image);
            uint cave=CompanyPositionPatch.Install(success,image,delegate{});int operations=success.Operations;
            Check(success.Allocated,"successful allocation");
            Check(success.Read(image+CompanyPositionPatch.HookRva,5).SequenceEqual(CompanyPositionPatch.Jump(image,cave)),"hook verified");
            if(args.Length==1)File.WriteAllBytes(Path.Combine(args[0],"payload-"+image.ToString("X")+"-"+caves[n].ToString("X")+".bin"),CompanyPositionPayload.Build(image,caves[n]));
            for(int fault=1;fault<=operations;fault++)
            {
                var memory=new Memory(image){FailAt=fault};bool threw=false;
                try{CompanyPositionPatch.Install(memory,image,delegate{});}catch(IOException){threw=true;}
                Check(threw,"failure propagated");Check(!memory.Allocated,"allocation freed after rollback");
                Check(memory.Read(image+CompanyPositionPatch.HookRva,5).SequenceEqual(CompanyPositionPatch.Original),"partial transaction restored");
            }
            foreach(uint wrongAt in new uint[]{CompanyPositionPatch.HookRva-2,CompanyPositionPatch.HookRva,0x218885,0x2925E6})
            {
                var wrong=new Memory(image);wrong.Seed(image+wrongAt,new byte[]{0xCC});bool rejected=false;
                try{CompanyPositionPatch.Install(wrong,image,delegate{});}catch(InvalidOperationException){rejected=true;}
                Check(rejected&&!wrong.Allocated,"unknown executable rejected before allocation");
            }
            var persistent=new Memory(image){AlwaysFailCode=true};
            try{CompanyPositionPatch.Install(persistent,image,delegate{});}catch(IOException){}
            Check(persistent.Allocated,"stub retained if rollback cannot be proved");
        }
        Console.WriteLine("PASS "+checks+" company position transaction checks; no game launched.");return 0;
    }
}
