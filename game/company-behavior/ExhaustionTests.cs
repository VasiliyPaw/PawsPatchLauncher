using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
internal static class ExhaustionTests
{
    sealed class Memory:IMemory
    {
        internal Dictionary<uint,byte> B=new Dictionary<uint,byte>();
        internal int Ops,Fail=-1,Freed;
        internal uint Image;internal bool FailDecisionFlush,FailDecisionRestore;
        internal void Seed(uint a,byte[] b){for(int i=0;i<b.Length;i++)B[a+(uint)i]=b[i];}
        void Op(){if(++Ops==Fail)throw new IOException("injected");}
        internal Memory(uint image){Image=image;Seed(image+CompanyExhaustionPatch.EntryRva,CompanyExhaustionPatch.EntryOriginal(image));Seed(image+CompanyExhaustionPatch.EntryRva+5,TerrainPatch.Hex("E80C9D160051568BF18B4E04"));Seed(image+ExhaustionRecoveryPatch.HookRva-3,ExhaustionRecoveryPatch.Guard);Seed(image+0x2147ec,ExhaustionRecoveryPatch.DecisionGuard);}
        public byte[] Read(uint a,int n){Op();return Enumerable.Range(0,n).Select(i=>B.ContainsKey(a+(uint)i)?B[a+(uint)i]:(byte)0).ToArray();}
        public void Write(uint a,byte[] b){Seed(a,b.Take(2).ToArray());Op();Seed(a,b);}
        public void WriteCode(uint a,byte[] b){if(FailDecisionRestore&&a==Image+CompanyExhaustionPatch.DecisionRva&&b.SequenceEqual(CompanyExhaustionPatch.DecisionOriginal))throw new IOException("restore blocked");Write(a,b);}
        public uint Allocate(int n){Op();if(n!=4096)throw new Exception("Unexpected allocation");return 0x60000000;}
        public void MakeExecutable(uint a,int n){Op();}
        public void Flush(uint a,int n){Op();if(FailDecisionFlush&&a==Image+CompanyExhaustionPatch.DecisionRva)throw new IOException("flush blocked");}
        public void Free(uint a){Op();Freed++;}
    }
    static int checks;
    static void Check(bool b){checks++;if(!b)throw new Exception("Check "+checks);}
    public static int Main(string[] args)
    {
        if(args.Length>0){uint image=args.Length==3?Convert.ToUInt32(args[1],16):0x460000,cave=args.Length==3?Convert.ToUInt32(args[2],16):0x60000000;File.WriteAllBytes(args[0]+".entry",CompanyExhaustionPatch.EntryDisabled);File.WriteAllBytes(args[0]+".update",CompanyExhaustionPatch.UpdateDisabled);File.WriteAllBytes(args[0]+".decision",CompanyExhaustionPatch.BuildDecision(image,cave));File.WriteAllBytes(args[0]+".decision-jump",CompanyExhaustionPatch.DecisionJump(image,cave));return 0;}
        foreach(uint image in new uint[]{0x460000,0xf20000,0x18000000})
        {
            var m=new Memory(image);CompanyExhaustionPatch.Install(m,image,delegate{});int ops=m.Ops;
            Check(m.Read(image+CompanyExhaustionPatch.EntryRva,5).SequenceEqual(CompanyExhaustionPatch.EntryDisabled));
            Check(m.Read(image+CompanyExhaustionPatch.UpdateRva,5).SequenceEqual(CompanyExhaustionPatch.UpdateDisabled));
            Check(m.Read(image+CompanyExhaustionPatch.DecisionRva,8).SequenceEqual(CompanyExhaustionPatch.DecisionJump(image,0x60000000)));
            Check(m.Read(0x60000000,CompanyExhaustionPatch.BuildDecision(image,0x60000000).Length).SequenceEqual(CompanyExhaustionPatch.BuildDecision(image,0x60000000)));
            for(int f=1;f<=ops;f++)
            {
                m=new Memory(image){Fail=f};bool failed=false;
                try{CompanyExhaustionPatch.Install(m,image,delegate{});}catch(IOException){failed=true;}
                Check(failed);Check(m.Read(image+CompanyExhaustionPatch.EntryRva,5).SequenceEqual(CompanyExhaustionPatch.EntryOriginal(image)));
                Check(m.Read(image+CompanyExhaustionPatch.UpdateRva,5).SequenceEqual(ExhaustionRecoveryPatch.Original));
                Check(m.Read(image+CompanyExhaustionPatch.DecisionRva,8).SequenceEqual(CompanyExhaustionPatch.DecisionOriginal));
            }
            m=new Memory(image);m.Seed(image+CompanyExhaustionPatch.EntryRva+1,new byte[]{0xcc});
            bool reject=false;try{CompanyExhaustionPatch.Install(m,image,delegate{});}catch(InvalidOperationException){reject=true;}Check(reject);
            m=new Memory(image);m.Seed(image+CompanyExhaustionPatch.DecisionRva+1,new byte[]{0xcc});
            reject=false;try{CompanyExhaustionPatch.Install(m,image,delegate{});}catch(InvalidOperationException){reject=true;}Check(reject);
            Check(m.Read(image+CompanyExhaustionPatch.EntryRva,5).SequenceEqual(CompanyExhaustionPatch.EntryOriginal(image)));
            m=new Memory(image){FailDecisionFlush=true,FailDecisionRestore=true};var logs=new List<string>();
            try{CompanyExhaustionPatch.Install(m,image,logs.Add);}catch(IOException){}
            Check(m.Freed==0);Check(logs.Any(s=>s.StartsWith("MORALE_DECISION_ROLLBACK_UNCERTAIN:")));
            Check(m.Read(image+CompanyExhaustionPatch.EntryRva,5).SequenceEqual(CompanyExhaustionPatch.EntryOriginal(image)));
            Check(m.Read(image+CompanyExhaustionPatch.UpdateRva,5).SequenceEqual(ExhaustionRecoveryPatch.Original));
        }
        foreach(bool enabled in new[]{false,true})foreach(string mod in new[]{"arcane-wars","vanilla","immortals"})foreach(bool core in new[]{false,true})foreach(bool data in new[]{false,true})foreach(string channel in new[]{"stable","beta","bad"})
        {
            var s=new Dictionary<string,object>{{"ignoreZeroMorale",enabled},{"mod",mod},{"pawPatchEnabled",core},{"dataOnly",data},{"channel",channel}};
            bool valid=!enabled || mod=="arcane-wars"&&core&&!data&&channel!="bad";
#if PAW_PURE_EXTENDED
            valid=!enabled;
#endif
            bool failed=false,result=false;try{result=PawCompanyOptions.Parse(s);}catch(InvalidDataException){failed=true;}
            Check(failed!=valid&&(!valid||result==enabled));
        }
        Check(!PawCompanyOptions.Parse(new Dictionary<string,object>()));
        bool invalid=false;try{PawCompanyOptions.Parse(new Dictionary<string,object>{{"ignoreZeroMorale","true"}});}catch(InvalidDataException){invalid=true;}Check(invalid);
        Console.WriteLine("EXHAUSTION_OPTION_TRANSACTION_PASS "+checks);return 0;
    }
}
