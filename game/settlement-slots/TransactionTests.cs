using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
internal static class SettlementSlotsTests
{
    sealed class Memory : IMemory
    {
        internal Dictionary<uint, byte> Bytes = new Dictionary<uint, byte>();
        internal int Operations, FailAt = -1, Writes;
        internal bool Allocated, Persistent;
        internal void Seed(uint a, byte[] b) { for(int i=0;i<b.Length;i++)Bytes[a+(uint)i]=b[i]; }
        internal Memory(uint image)
        {
            for(int i=0;i<2;i++)Seed(image+SettlementSlotsPatch.Sites[i],SettlementSlotsPatch.Original[i]);
            Seed(image+0xE2361,TerrainPatch.Hex("8B750C8D4F746A0133DB"));
            Seed(image+0xE243B,TerrainPatch.Hex("3B9F8C0000007C95"));
            Seed(image+SettlementSlotsPatch.LayoutSite,SettlementSlotsPatch.LayoutOriginal);
        }
        void Op() { if(++Operations==FailAt)throw new IOException("injected failure"); }
        public byte[] Read(uint a,int n) { Op();return Enumerable.Range(0,n).Select(i=>Bytes.ContainsKey(a+(uint)i)?Bytes[a+(uint)i]:(byte)0).ToArray(); }
        public void Write(uint a,byte[] b) { Seed(a,b.Take(2).ToArray());Op();Seed(a,b); }
        // Fail AFTER modifying memory, exercising restoration of a partial transaction.
        public void WriteCode(uint a,byte[] b) { Writes++;Seed(a,b.Take(2).ToArray());Op();if(Persistent&&b.Length>1)throw new IOException("persistent write failure");Seed(a,b); }
        public uint Allocate(int n) { Op();Allocated=true;return 0x60000000; }
        public void MakeExecutable(uint a,int n) { Op(); }
        public void Flush(uint a,int n) { Op(); }
        public void Free(uint a) { Allocated=false; }
    }
    static int checks;
    static void Check(bool ok) { checks++;if(!ok)throw new Exception("Settlement slots transaction #"+checks); }
    internal static int Main()
    {
        foreach(uint image in new uint[]{0x460000,0xE40000,0x12000000})
        {
            var good=new Memory(image);var before=new Dictionary<uint,byte>(good.Bytes);
            SettlementSlotsPatch.Install(good,image,delegate{});int count=good.Operations;
            Check(good.Writes==3&&good.Allocated);
            foreach(var p in before)
                if(p.Key<image+SettlementSlotsPatch.LayoutSite||p.Key>=image+SettlementSlotsPatch.LayoutSite+8)
                    Check(good.Bytes[p.Key]==p.Value+(p.Key==image+0xE1C7E||p.Key==image+0xBB4C9?1:0));
            for(int at=1;at<=count;at++)
            {
                var m=new Memory(image){FailAt=at};bool threw=false;
                try{SettlementSlotsPatch.Install(m,image,delegate{});}catch(IOException){threw=true;}
                Check(threw&&!m.Allocated);Check(before.All(p=>m.Bytes[p.Key]==p.Value));
            }
            foreach(uint site in new uint[]{0xE1C7D,0xBB4C8,0xE2361,0xE243B,SettlementSlotsPatch.LayoutSite})
            {
                var m=new Memory(image);m.Seed(image+site,new byte[]{0xCC});bool rejected=false;
                try{SettlementSlotsPatch.Install(m,image,delegate{});}catch(InvalidOperationException){rejected=true;}
                Check(rejected&&m.Writes==0&&!m.Allocated);
            }
            var persistent=new Memory(image){Persistent=true};bool uncertain=false;
            try{SettlementSlotsPatch.Install(persistent,image,s=>{if(s.Contains("ROLLBACK_UNCERTAIN"))uncertain=true;});}catch(IOException){}
            Check(uncertain&&persistent.Allocated);
        }
        Console.WriteLine("SETTLEMENT_SLOTS_TRANSACTIONS_PASS "+checks+" checks");return 0;
    }
}
