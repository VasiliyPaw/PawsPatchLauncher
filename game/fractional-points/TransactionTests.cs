using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
internal static class FractionalPointsTests
{
    sealed class Memory:IMemory
    {
        internal Dictionary<uint,byte> Bytes=new Dictionary<uint,byte>();
        internal int Operations,FailAt=-1;internal bool Allocated,Persistent;
        internal void Seed(uint a,byte[] b){for(int i=0;i<b.Length;i++)Bytes[a+(uint)i]=b[i];}
        internal Memory(uint image){for(int i=0;i<3;i++)Seed(image+FractionalPointsPatch.Sites[i],FractionalPointsPatch.Original(image,i));}
        void Op(){if(++Operations==FailAt)throw new IOException("injected failure");}
        public byte[] Read(uint a,int n){Op();return Enumerable.Range(0,n).Select(i=>Bytes.ContainsKey(a+(uint)i)?Bytes[a+(uint)i]:(byte)0).ToArray();}
        public void Write(uint a,byte[] b){Seed(a,b.Take(2).ToArray());Op();Seed(a,b);}
        public void WriteCode(uint a,byte[] b){Seed(a,b.Take(2).ToArray());Op();if(Persistent)throw new IOException("persistent write failure");Seed(a,b);}
        public uint Allocate(int n){Op();Allocated=true;return 0x60000000;}
        public void MakeExecutable(uint a,int n){Op();}
        public void Flush(uint a,int n){Op();}
        public void Free(uint a){Allocated=false;}
    }
    static int checks;
    static void Check(bool b){checks++;if(!b)throw new Exception("Fractional points transaction #"+checks);}
    internal static int Main()
    {
        foreach(uint image in new uint[]{0x460000,0xE40000,0x12000000})
        {
            var good=new Memory(image);FractionalPointsPatch.Install(good,image,delegate{});int count=good.Operations;
            Check(good.Allocated);
            for(int at=1;at<=count;at++)
            {
                var m=new Memory(image){FailAt=at};bool threw=false;
                try{FractionalPointsPatch.Install(m,image,delegate{});}catch(IOException){threw=true;}
                Check(threw&&!m.Allocated);
                for(int i=0;i<3;i++)Check(m.Read(image+FractionalPointsPatch.Sites[i],FractionalPointsPatch.Original(image,i).Length).SequenceEqual(FractionalPointsPatch.Original(image,i)));
            }
            for(int i=0;i<3;i++)
            {
                var m=new Memory(image);m.Seed(image+FractionalPointsPatch.Sites[i],new byte[]{0xCC});bool rejected=false;
                try{FractionalPointsPatch.Install(m,image,delegate{});}catch(InvalidOperationException){rejected=true;}
                Check(rejected&&!m.Allocated);
            }
            var bad=new Memory(image){Persistent=true};try{FractionalPointsPatch.Install(bad,image,delegate{});}catch(IOException){}
            Check(bad.Allocated);
        }
        Console.WriteLine("FRACTIONAL_TRANSACTIONS_PASS "+checks+" checks");return 0;
    }
}
