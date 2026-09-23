using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

internal static class FoundationCountsTests
{
    private sealed class Memory:IMemory
    {
        internal readonly Dictionary<uint,byte> Bytes=new Dictionary<uint,byte>();
        internal int Operations,FailAt=-1;internal bool Allocated,AlwaysFailCode;
        internal uint ExecutableStart,ExecutableEnd;
        internal void Seed(uint a,byte[] b){for(int i=0;i<b.Length;i++)Bytes[a+(uint)i]=b[i];}
        private void Op(){if(++Operations==FailAt)throw new IOException("injected failure");}
        internal Memory(uint image)
        {
            Seed(image+FoundationCountsPatch.GuardRva,FoundationCountsPatch.Guard);
            for(int i=1;i<FoundationCountsPatch.Sites.Length;i++)Seed(image+FoundationCountsPatch.Sites[i],FoundationCountsPatch.Originals[i]);
        }
        public byte[] Read(uint a,int n){Op();return Enumerable.Range(0,n).Select(i=>Bytes.ContainsKey(a+(uint)i)?Bytes[a+(uint)i]:(byte)0).ToArray();}
        public void Write(uint a,byte[] b){if(a<ExecutableEnd&&a+(uint)b.Length>ExecutableStart)throw new IOException("write to RX page");Seed(a,b.Take(2).ToArray());Op();Seed(a,b);}
        public void WriteCode(uint a,byte[] b){Seed(a,b.Take(2).ToArray());Op();if(AlwaysFailCode)throw new IOException("persistent partial write");Seed(a,b);}
        public uint Allocate(int n){Op();Allocated=true;return 0x60000000;}
        public void MakeExecutable(uint a,int n){Op();ExecutableStart=a;ExecutableEnd=(a+(uint)n+4095)&~4095u;}
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
            uint cave=FoundationCountsPatch.Install(success,image,delegate{});int operations=success.Operations;
            Check(success.Allocated,"successful allocation");
            Check(success.ExecutableStart==cave&&success.ExecutableEnd==cave+FoundationCountsPayload.DataOffset,"RX code stops before writable state");
            success.Write(cave+FoundationCountsPayload.DataOffset+4,BitConverter.GetBytes(1));
            Check(BitConverter.ToInt32(success.Read(cave+FoundationCountsPayload.DataOffset+4,4),0)==1,"planner first state write permitted");
            success.Write(cave+(uint)FoundationCountsPayload.Allocation-4,BitConverter.GetBytes(1));
            Check(BitConverter.ToInt32(success.Read(cave+(uint)FoundationCountsPayload.Allocation-4,4),0)==1,"last data page writable");
            bool codeWriteRejected=false;try{success.Write(cave,new byte[]{0});}catch(IOException){codeWriteRejected=true;}
            Check(codeWriteRejected,"code remains nonwritable");
            Check(success.Read(image+FoundationCountsPatch.HookRva,8).SequenceEqual(FoundationCountsPatch.Jump(image,cave)),"hook verified");
            for(int i=1;i<FoundationCountsPatch.Sites.Length;i++)Check(success.Read(image+FoundationCountsPatch.Sites[i],FoundationCountsPatch.Originals[i].Length).SequenceEqual(FoundationCountsPatch.Jump(image,cave,i)),"extra hook verified");
            if(args.Length==1)File.WriteAllBytes(Path.Combine(args[0],"payload-"+image.ToString("X")+"-"+caves[n].ToString("X")+".bin"),FoundationCountsPayload.Build(image,caves[n]));
            for(int fault=1;fault<=operations;fault++)
            {
                var memory=new Memory(image){FailAt=fault};bool threw=false;
                try{FoundationCountsPatch.Install(memory,image,delegate{});}catch(IOException){threw=true;}
                Check(threw,"failure propagated");Check(!memory.Allocated,"allocation freed after rollback");
                Check(memory.Read(image+FoundationCountsPatch.HookRva,8).SequenceEqual(FoundationCountsPatch.Original),"partial transaction restored");
                for(int i=1;i<FoundationCountsPatch.Sites.Length;i++)Check(memory.Read(image+FoundationCountsPatch.Sites[i],FoundationCountsPatch.Originals[i].Length).SequenceEqual(FoundationCountsPatch.Originals[i]),"all hooks rolled back");
            }
            foreach(uint wrongAt in new uint[]{FoundationCountsPatch.GuardRva,FoundationCountsPatch.HookRva,FoundationCountsPatch.GuardRva+50,0x255e09,0x247a27})
            {
                var wrong=new Memory(image);wrong.Seed(image+wrongAt,new byte[]{0xCC});bool rejected=false;
                try{FoundationCountsPatch.Install(wrong,image,delegate{});}catch(InvalidOperationException){rejected=true;}
                Check(rejected&&!wrong.Allocated,"unknown executable rejected before allocation");
            }
            var persistent=new Memory(image){AlwaysFailCode=true};
            try{FoundationCountsPatch.Install(persistent,image,delegate{});}catch(IOException){}
            Check(persistent.Allocated,"stub retained if rollback cannot be proved");
        }
        Console.WriteLine("PASS "+checks+" foundation distribution transaction checks; no game launched.");return 0;
    }
}
