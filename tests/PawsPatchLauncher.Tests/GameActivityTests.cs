using System.Text;
using System.Text.Json;
using PawsPatchLauncher;

internal static class GameActivityTests
{
    public static int Run()
    {
        var checks=0;
        void Check(bool ok,string message) { if(!ok)throw new Exception("Game activity: "+message);checks++; }
        var person=new GameParticipant("p1","Игрок",false);
        var activity=new GameActivity("match",true,131,192,256,new string('A',64),"p1",[person,new("p2","Computer",true)]);
        GameActivity? Parse(object value,bool details=false)=>GameActivity.Read(JsonSerializer.SerializeToElement(value),details);
        Check(Parse(activity)?.Players?.Count==2,"valid Unicode roster");
        foreach(var phase in new[]{"menu","lobby","match","loading","editor"})Check(Parse(new GameActivity(phase))?.Phase==phase,"phase "+phase);
        foreach(var value in new object[]{activity with{Phase="bogus"},activity with{ElapsedSeconds=-1},activity with{ElapsedSeconds=604801},
            activity with{Width=0},activity with{Height=null},activity with{Room="steam://123"},activity with{Self="absent"},activity with{Multiplayer=false},
            activity with{Players=[person,person]},activity with{Players=[person with{Name=""}]},activity with{Players=[person with{Name="secret\nname"}]},
            activity with{Players=[person with{Key="not a key"}]},activity with{Phase="menu"},activity with{Players=[null!]},
            activity with{Players=Enumerable.Range(0,65).Select(i=>new GameParticipant("p"+i,"x",false)).ToArray()},
            activity with{Players=[person with{Name=new string('x',81)}]},
            new {phase="match",multiplayer=true,elapsed=2.5},new {phase="match",multiplayer="true"},new {phase="menu",padding=new string('x',20000)}})
            Check(Parse(value) is null,"reject invalid payload "+JsonSerializer.Serialize(value)[..Math.Min(100,JsonSerializer.Serialize(value).Length)]);
        var profile=new GameParticipantProfile(Guid.NewGuid(),"fixture","Fixture");
        var enriched=activity with{Players=[person with{Profile=profile}]};
        Check(Parse(enriched) is null&&Parse(enriched,true)?.Players?[0].Profile?.Id==profile.Id,"only details accept server identity");
        Check(Parse(enriched with{Players=[person with{Profile=profile with{Nickname=null!}}]},true) is null,"null profile is bounded");
        Check(Parse(enriched with{Players=[person with{Bot=true,Profile=profile}],Self=null},true) is null,"bots cannot impersonate profiles");
        Check(activity.Summary().Players is null&&activity.Summary().Room is null&&activity.Summary().Self is null,"summary omits private join/matching metadata");
        foreach(var image in new uint[]{0x400000,0x460000,0x750000})
        {
            var m=new Memory(image);var read=KohanActivityReader.ReadSnapshot(image,m.Read);
            Check(read?.Phase=="menu","relocated menu");
            m.U32(m.Session+0xf0,1);m.U8(m.Session+0x100,1);m.Player(0,1,"Игрок",false,true);m.Player(1,2,"AI",true,false);
            m.Bytes(image+0x5f21e0,Encoding.ASCII.GetBytes("+connect_lobby 123456\0"));
            read=KohanActivityReader.ReadSnapshot(image,m.Read);
            Check(read is {Phase:"lobby",Multiplayer:true,Self:"p1",Width:192,Height:256}&&read.Players?.Count==2&&read.Players[1].Bot,"lobby and roster");
            Check(read?.Room?.Length==64&&!read.Room.Contains("123456")&&!JsonSerializer.Serialize(read).Contains("connect_lobby"),"room fingerprint never exposes join string");
            for(uint kind=0;kind<=5;kind++)
            {
                m.U32(m.Session+0x64,kind);m.U32(m.Session+(kind switch{0=>0x80u,2=>0x7cu,5=>0x88u,_=>0x78u}),m.Creator);
                Check(KohanActivityReader.ReadSnapshot(image,m.Read)?.Width==192,"native WorldCreator variant "+kind);
            }
            m.U32(image+0x5f3fb8,m.World);m.U32(m.Session+0xf0,2);m.F32(m.World+0xe8,131.8f);
            Check(KohanActivityReader.ReadSnapshot(image,m.Read) is {Phase:"match",ElapsedSeconds:131},"native simulation time");
            m.F32(m.World+0xe8,float.NaN);m.F32(m.Creator+0x3c,192.5f);
            Check(KohanActivityReader.ReadSnapshot(image,m.Read) is {ElapsedSeconds:null,Width:null,Height:null},"unknown values omitted");
            m.U32(image+0x5f3fb8,0);Check(KohanActivityReader.ReadSnapshot(image,m.Read)?.Phase=="loading","world loading");
            m.U32(image+0x5f92f4,13);Check(KohanActivityReader.ReadSnapshot(image,m.Read)?.Phase=="editor","editor");
            m.U32(image+0x5f92f4,0);m.U32(m.Session+0xf0,99);Check(KohanActivityReader.ReadSnapshot(image,m.Read) is null,"unknown native state");
            m.U32(m.Session+0xf0,1);m.U32(m.Node(1)+4,m.Node(0));
            Check(KohanActivityReader.ReadSnapshot(image,m.Read) is null,"cycle bounded");
            m.U32(m.Node(1)+4,0);m.U32(m.Person(1)+0x20,1);
            Check(KohanActivityReader.ReadSnapshot(image,m.Read) is null,"duplicate IDs discard snapshot");
            m.U32(m.Person(1)+0x20,2);var times=0;
            byte[] Transition(uint at,int size){if(at==m.Session+0xf0&&++times==2)return BitConverter.GetBytes(0u);return m.Read(at,size);}
            Check(KohanActivityReader.ReadSnapshot(image,Transition) is null,"transition during sample discarded");
            m.U8(image+0x1618a5,0);Check(KohanActivityReader.ReadSnapshot(image,m.Read) is null,"wrong binary signature rejected");
        }
        Check(KohanActivityReader.ReadSnapshot(0x400000,(_,_)=>throw new IOException()) is null,"access/exit failure preserves general Playing status");
        var modules=new InstallState{BaseGameSha256=KohanActivityReader.SupportedSha256,Modules=new(){["native"]=new(){Enabled=true,Files=[new(){Path="k2_paws_menu_1372.exe",Sha256=new string('F',64)},new(){Path="../k2_bad.exe",Sha256=new string('F',64)},new(){Path="k2_bad.exe",Sha256="bad"}]}}};
        Check(KohanActivityReader.SupportedExecutables(modules).Count==2,"stock and installed verified helpers allowed");
        modules.BaseGameSha256="unknown";Check(KohanActivityReader.SupportedExecutables(modules).Count==1,"future native layouts not guessed");
        Console.WriteLine($"GAME ACTIVITY PASS {checks}");return checks;
    }
    private sealed class Memory(uint image)
    {
        private readonly byte[] data=Make(image);
        public uint Session=>0x1000000;public uint World=>0x1020000;public uint Creator=>0x1030000;
        public uint Node(int i)=>0x1040000+(uint)i*16;public uint Person(int i)=>0x1050000+(uint)i*128;
        private static byte[] Make(uint image)
        {
            var b=new byte[0x1080000];
            void Put(uint at,byte[] value)=>value.CopyTo(b,(int)at);
            Put(image+0x1618a5,[0x8b,0x41,0x04,0x83,0xe8,0x00]);Put(image+0x15d1e7,[0x8b,0x41,0x04,0xc3]);
            Put(image+0x5f3fe4,BitConverter.GetBytes(0x1000000u));Put(image+0x5f3fec,BitConverter.GetBytes(0x1010000u));
            Put(0x101000c,BitConverter.GetBytes(0x1070000u));Put(0x1000080,BitConverter.GetBytes(0x1030000u));
            Put(0x103003c,BitConverter.GetBytes(192f));Put(0x1030040,BitConverter.GetBytes(256f));return b;
        }
        public byte[] Read(uint at,int size){if(at<0x10000||at+(long)size>data.Length)throw new IOException();return data.AsSpan((int)at,size).ToArray();}
        public void Bytes(uint at,byte[] value)=>value.CopyTo(data,(int)at);
        public void U32(uint at,uint value)=>Bytes(at,BitConverter.GetBytes(value));
        public void F32(uint at,float value)=>Bytes(at,BitConverter.GetBytes(value));
        public void U8(uint at,byte value)=>data[at]=value;
        public void Player(int i,uint id,string name,bool bot,bool self)
        {
            U32(Session+0xc8,Node(0));if(i>0)U32(Node(i-1)+4,Node(i));U32(Node(i),Person(i));
            U32(Person(i),image+0x4bd914);U32(Person(i)+0x20,id);U8(Person(i)+0xc,bot?(byte)1:(byte)0);
            U32(Person(i)+8,0x1060000+(uint)i*256);Bytes(0x1060000+(uint)i*256,Encoding.Unicode.GetBytes(name+"\0"));
            if(self)U32(Person(i)+4,0x1070000);
        }
    }
}
