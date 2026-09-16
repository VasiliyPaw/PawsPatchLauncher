using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;

namespace PawLairDiagnostics
{
    internal sealed class Fixture : IReadMemory
    {
        internal readonly byte[] data=new byte[0x800000];
        internal const uint Base=0x10000000, World=Base+0x700000, Registry=Base+0x710000,
            Home=Base+0x780000, Component=Base+0x781000, Group=Base+0x782000,
            Definition=Base+0x783000, Kingdom=Base+0x786000, Unit=Base+0x787000;
        internal const uint HomeId=0x30001, UnitId=0x50002;
        public byte[] Read(uint address,int count)
        {
            long offset=(long)address-Base;
            if(offset<0 || count<0 || offset+count>data.Length) return null;
            byte[] result=new byte[count];Array.Copy(data,offset,result,0,count);return result;
        }
        internal void W(uint address,uint value){Array.Copy(BitConverter.GetBytes(value),0,data,address-Base,4);}
        internal void Float(uint address,float value){Array.Copy(BitConverter.GetBytes(value),0,data,address-Base,4);}
        internal void Bytes(uint address,params byte[] value){Array.Copy(value,0,data,address-Base,value.Length);}
        internal void Name(uint definition,string name){W(definition+8,definition+0x500);Bytes(definition+0x500,Encoding.Unicode.GetBytes(name+"\0"));}
        internal void Register(uint actor,uint id)
        {
            uint slot=id&65535;Bytes(Registry+4+slot*2,(byte)(id>>16),(byte)(id>>24));
            W(Registry+0x20004+slot*4,actor);W(actor+0x14,id);
        }
        internal Fixture()
        {
            W(Base+LairReader.WorldRva,World);W(Base+LairReader.RegistryRva,Registry);W(Base+0x5F9218,2);
            W(World+0x150,World+0x300);W(World+0x154,1);W(World+0x300,Kingdom);Float(World+0xE8,123);
            W(Kingdom+4,Kingdom+0x500);Name(Kingdom+0x500,"paws_war_fire_dragon");Float(Kingdom+0x1FC,0);
            Register(Home,HomeId);W(Home+0x88,Component);W(Home+4,Definition);W(Home+0xE8,Kingdom);
            W(Component,Base+LairReader.DenizenVtableRva);W(Component+4,Home);W(Component+0x18,Group);
            Float(Component+0x10,80);Float(Component+0x14,100);
            W(Group+4,Definition);Float(Group+8,6000);Name(Definition,"AW_dragon_fire");
            W(Definition+0x174,0x121);Float(Definition+0x284,6000);Float(Definition+0x2CC,0.01f);Float(Definition+0x1E4,100);
            Bytes(Base+0x21117,0x8b,0x44,0x24,0x04,0x0f,0xb7,0xd0,0xc1,0xe8,0x10);
            Bytes(Base+0x20A28C,0x55,0x8b,0xec,0x53,0x56,0x8b,0x75,0x08,0x8b,0xd9);
            Bytes(Base+0x20AED9,0xf3,0x0f,0x58,0x46,0x08,0xf3,0x0f,0x11,0x46,0x08);
        }
    }
    internal static class LairReaderTests
    {
        private static int checks;
        private static void Check(bool okay,string label){if(!okay)throw new Exception(label);checks++;}
        private static LairSample Read(Fixture f){return new LairReader(f,Fixture.Base).Capture().lairs.Single();}
        private static void Main()
        {
            long now=0;int disposed=0,scans=0;
            object bootstrap=new object(),actual=new object();
            object attached=GameAttachment.Wait(()=>{scans++;return scans==1?new[]{bootstrap}:new[]{actual};},
                candidate=>Object.ReferenceEquals(candidate,actual),candidate=>disposed++,()=>false,()=>now,ms=>now+=ms,2000);
            Check(Object.ReferenceEquals(attached,actual) && scans==2 && disposed==1,"Steam bootstrap replaced by verified final process");
            now=0;disposed=0;
            attached=GameAttachment.Wait(()=>new[]{bootstrap},candidate=>false,candidate=>disposed++,()=>false,()=>now,ms=>now+=ms,500);
            Check(attached==null && disposed==2,"unready or incompatible process is not attached; retries bounded");
            now=0;bool called=false;
            attached=GameAttachment.Wait(()=>{called=true;return new[]{actual};},candidate=>true,candidate=>{},()=>true,()=>now,ms=>now+=ms,500);
            Check(attached==null && !called,"cancelled attachment never starts enumeration");
            var f=new Fixture(); var reader=new LairReader(f,Fixture.Base);
            Check(reader.VerifyLayout(),"runtime signature accepted at relocated image base");
            f.Bytes(Fixture.Base+0x20AED9,0x90);Check(!reader.VerifyLayout(),"mismatched regeneration code rejected");
            f=new Fixture();var l=Read(f);Check(l.atHomeCount==1 && l.fullyRestoredAtHomeCount==1,"full defender at home");
            f.Float(Fixture.Group+8,4200);l=Read(f);
            Check(l.atHomeCount==1 && l.fullyRestoredAtHomeCount==0 && l.groups[0].storedHealth==4200,"returned wounded defender retained separately from fully healed count");
            Check(l.reportedStrength==80 && l.maximumStrength==100,"cached sword-bar strength captured separately");
            f.Float(Fixture.Kingdom+0x1FC,1);
            Check(new LairReader(f,Fixture.Base).Capture().kingdoms[0].resupplyPenalty==1,"zero resupply factor owner recorded");
            f.Register(Fixture.Unit,Fixture.UnitId);f.W(Fixture.Unit+4,Fixture.Definition);f.W(Fixture.Unit+0xE8,Fixture.Kingdom);
            f.W(Fixture.Unit+0x60,Fixture.Unit+0x200);f.Float(Fixture.Unit+0x210,2000);f.Float(Fixture.Unit+0x214,6000);
            f.W(Fixture.Group,Fixture.UnitId);l=Read(f);
            Check(l.atHomeCount==0 && l.groups[0].deployedActor.health==2000 && !l.groups[0].staleActorId,"deployed dragon ID resolved with its live HP");
            f.Bytes(Fixture.Registry+8,6,0);l=Read(f);
            Check(l.groups[0].staleActorId && l.groups[0].deployedActor==null,"recycled slot generation does not become the old dragon");
            f=new Fixture();f.W(Fixture.Group+0x10,Fixture.Group);l=Read(f);
            Check(!l.complete && l.groups.Count==1,"list cycle bounded and incomplete marked");
            Check(!new LairReader(f,Fixture.Base).Capture().complete,"incomplete component propagates to frame");
            f=new Fixture();f.W(Fixture.Component+4,Fixture.Unit);
            Check(new LairReader(f,Fixture.Base).Capture().lairs.Count==0,"component with wrong home rejected");
            f=new Fixture();f.Float(Fixture.Definition+0x284,Single.NaN);l=Read(f);
            Check(l.groups[0].maximumHealth==null && l.fullyRestoredAtHomeCount==0,"invalid floats are nullable and never count ready");
            f=new Fixture();reader=new LairReader(f,Fixture.Base);reader.Capture();
            f.Name(Fixture.Definition,"storm_drake");f.Float(Fixture.World+0xE8,1);
            Check(reader.Capture().lairs[0].groups[0].dataId=="storm_drake","save rewind invalidates definition names");
            f.W(Fixture.Base+0x5F9218,0);Check(reader.Capture()==null,"menu is not treated as match");
            f=new Fixture();f.W(Fixture.World+0x154,0xFFFFFFFF);
            Check(new LairReader(f,Fixture.Base).Capture()==null,"malformed kingdom count bounded");
            f=new Fixture();f.W(Fixture.Component+0x24,Fixture.Component+0x200);f.W(Fixture.Component+0x200,Fixture.HomeId);
            Check(Read(f).intruders.Single().id==Fixture.HomeId,"intruder list contains IDs resolved through current registry");
            var s=new Dictionary<string,object>{{"mod","arcane-wars"},{"pawPatchEnabled",true}};
            var selected=new HashSet<string>();
            for(int i=0;i<8;i++)
            {
                s["customPlayerColors"]=(i&1)!=0;s["independentHostility"]=(i&2)!=0;s["desyncMode"]=(i&4)!=0?"continue":"official";
                selected.Add(LaunchConfig.Select(s));
            }
            Check(selected.Count==8,"all eight current Arcane Wars option combinations remain distinct");
            s["dataOnly"]=true;bool rejected=false;try{LaunchConfig.Select(s);}catch(InvalidOperationException){rejected=true;}
            Check(rejected,"data-only launch does not receive incompatible observer start");
            string root=Path.Combine(Path.GetTempPath(),"PawsLairLogTest-"+Guid.NewGuid().ToString("N"));
            using(var log=new SessionLog(root))
            {
                log.Event("TEST",new {lair=Read(new Fixture())});string zip=log.Pack();
                Check(File.Exists(zip) && new FileInfo(zip).Length>0,"log serializes and archives fixture with nullable fields");
                // Exact test-owned paths, no recursive cleanup of external folders.
                foreach(string file in Directory.GetFiles(log.DirectoryPath))File.Delete(file);
                Directory.Delete(log.DirectoryPath);File.Delete(zip);
                Directory.Delete(Path.Combine(root,"Logs","PawsLairDiagnostics"));Directory.Delete(Path.Combine(root,"Logs"));Directory.Delete(root);
            }
            Console.WriteLine("PASS "+checks+" diagnostic observer checks; no game started or modified.");
        }
    }
}
