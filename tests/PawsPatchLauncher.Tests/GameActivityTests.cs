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
        var probes=0;
        Check(KohanActivityReader.FirstAvailable(new[]{"helper","steam bootstrap","native game","later"},candidate=>
        {
            probes++;return candidate switch {"helper"=>null,"steam bootstrap"=>throw new IOException("exited"),"native game"=>new GameActivity("match"),_=>throw new Exception("must stop after first valid game")};
        })?.Phase=="match"&&probes==3,"helper and exited Steam process cannot hide the game; stop at first valid snapshot");
        foreach(var error in new Exception[]{new InvalidOperationException(),new System.ComponentModel.Win32Exception(),new IOException(),new UnauthorizedAccessException(),new OverflowException(),new ArgumentException()})
            Check(KohanActivityReader.FirstAvailable(new[]{0,1},i=>i==0?throw error:new GameActivity("lobby"))?.Phase=="lobby","continue after candidate failure "+error.GetType().Name);
        Check(KohanActivityReader.FirstAvailable(new[]{0,1},_=>null) is null,"all unavailable retain generic Playing state");
        var activity=new GameActivity("match",true,131,192,256,new string('A',64),"p1",[person,new("p2","Computer",true)]);
        GameActivity? Parse(object value,bool details=false)=>GameActivity.Read(JsonSerializer.SerializeToElement(value),details);
        Check(Parse(activity)?.Players?.Count==2,"valid Unicode roster");
        foreach(var team in new[]{1,16,64})foreach(var color in new[]{"#000000","#FFFFFF","#9a01Ff"})
            Check(Parse(activity with{Players=[person with{Team=team,Color=color}]})?.Players?[0] is {Team:not null,Color:not null},"team and RGB roundtrip");
        foreach(var phase in new[]{"menu","lobby","match","loading","editor"})Check(Parse(new GameActivity(phase))?.Phase==phase,"phase "+phase);
        foreach(var value in new object[]{activity with{Phase="bogus"},activity with{ElapsedSeconds=-1},activity with{ElapsedSeconds=604801},
            activity with{Width=0},activity with{Height=null},activity with{Room="steam://123"},activity with{Self="absent"},activity with{Multiplayer=false},
            activity with{Players=[person,person]},activity with{Players=[person with{Name=""}]},activity with{Players=[person with{Name="secret\nname"}]},
            activity with{Players=[person with{Key="not a key"}]},activity with{Phase="menu"},activity with{Players=[null!]},
            activity with{Players=Enumerable.Range(0,65).Select(i=>new GameParticipant("p"+i,"x",false)).ToArray()},
            activity with{Players=[person with{Name=new string('x',81)}]},
            activity with{Players=[person with{Team=0}]},activity with{Players=[person with{Team=65}]},
            activity with{Players=[person with{Color="red"}]},activity with{Players=[person with{Color="#12ggFF"}]},
            activity with{Players=[person with{Color="#FFFFFFFF"}]},
            new {phase="lobby",multiplayer=false,players=new[]{new{key="p1",name="x",bot=false,team=1.5}}},
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
            m.Appearance();read=KohanActivityReader.ReadSnapshot(image,m.Read);
            Check(read?.Players?[0] is {Team:2,Color:"#FF8000"},"lobby joins kingdom and team by ID, preserves native order and RGB");
            Check(read?.Players?[1] is {Team:null,Color:null},"unassigned participant has no invented team/color");
            m.PendingAppearance();Check(KohanActivityReader.ReadSnapshot(image,m.Read)?.Players?[0].Color=="#0040FF","Paw lobby choice overrides uncommitted template color");
            m.U32(0xf00600,1);Check(KohanActivityReader.ReadSnapshot(image,m.Read)?.Players?[0].Color is null,"random color stays unspecified in lobby");m.U32(0xf00600,0);
            m.U8(0xf20000,0);Check(KohanActivityReader.ReadSnapshot(image,m.Read)?.Players?[0].Color is null,"unknown palette detour never guessed");
            m.U8(image+0x295516,0);
            m.U32(m.Creator+0xc,65);Check(KohanActivityReader.ReadSnapshot(image,m.Read) is null,"team traversal bounded");m.U32(m.Creator+0xc,2);
            m.U32(m.Creator+0x18,257);Check(KohanActivityReader.ReadSnapshot(image,m.Read) is null,"kingdom traversal bounded");m.U32(m.Creator+0x18,1);
            for(uint kind=0;kind<=5;kind++)
            {
                m.U32(m.Session+0x64,kind);m.U32(m.Session+(kind switch{0=>0x80u,2=>0x7cu,5=>0x88u,_=>0x78u}),m.Creator);
                Check(KohanActivityReader.ReadSnapshot(image,m.Read)?.Width==192,"native WorldCreator variant "+kind);
            }
            m.U32(image+0x5f3fb8,m.World);m.U32(m.Session+0xf0,2);m.F32(m.World+0xe8,131.8f);
            Check(KohanActivityReader.ReadSnapshot(image,m.Read) is {Phase:"match",ElapsedSeconds:131},"native simulation time");
            Check(KohanActivityReader.ReadSnapshot(image,m.Read)?.Players?[0] is {Team:1,Color:"#0040FF"},"match uses actual team/color rather than template (save/random/diplomacy)");
            m.F32(0x1075318,float.NaN);Check(KohanActivityReader.ReadSnapshot(image,m.Read)?.Players?[0] is {Team:1,Color:null},"bad native RGB omitted");m.F32(0x1075318,0);
            var teamReads=0;
            byte[] TeamTransition(uint at,int size){if(at==0x10741f8&&++teamReads==2)return BitConverter.GetBytes(0u);return m.Read(at,size);}
            Check(KohanActivityReader.ReadSnapshot(image,TeamTransition) is null,"team change during sample discarded");
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
        var large=new Memory(0x400000);large.U32(large.Session+0xf0,1);
        for(var i=0;i<64;i++)large.Player(i,(uint)i,new string('界',80),false,i==0);
        Check(KohanActivityReader.ReadSnapshot(0x400000,large.Read) is {Phase:"lobby",Players:null,Self:null},"oversized Unicode roster preserves heartbeat summary");
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
        public void Appearance()
        {
            void Text(uint at,string value)=>Bytes(at,Encoding.Unicode.GetBytes(value+"\0"));
            U32(Creator+8,0x1071000);U32(Creator+0xc,2);U32(0x1071000,0x1072000);U32(0x107100c,0x1072100);
            Text(0x1072000,"alliance_a");Text(0x1072100,"alliance_b");Text(0x1072200,"kingdom_7");
            U32(Creator+0x14,0x1073000);U32(Creator+0x18,1);U32(0x1073000,0x1072200);
            U32(0x1073014,0x1072100);U32(0x1073020,0x1075000);U32(Person(0)+0x24,0x1072200);
            F32(0x1075018,1);F32(0x107501c,.5f);F32(0x1075020,0);
            U32(Person(0)+0x28,0x1074000);U32(0x10741f4,0x1075300);U32(0x10741f8,0x1075200);U32(0x1075218,0x1072000);
            F32(0x1075318,0);F32(0x107531c,.25f);F32(0x1075320,1);
        }
        public void PendingAppearance()
        {
            const uint cave=0xf00000;var site=image+0x295516;
            U8(site,0xe9);Bytes(site+1,BitConverter.GetBytes((int)(cave+0x20000-site-5)));
            Bytes(cave+0x20000,[0x9c,0x60,0x89,0xd9,0xe8,0xf7,0xef,0xff,0xff,0x61,0x9d,0x8b,0x43,0x20,0x89,0x45,0xf0,0xe9]);
            Bytes(cave+0x20012,BitConverter.GetBytes((int)(site+6-cave-0x20016)));
            Bytes(cave+0x1d000,[0x53,0x56,0x57,0x89,0xce,0x83,0x3d]);U32(cave+0x1d007,cave+0x120);
            Bytes(cave+0x1d00b,[1,0x75,0x5b,0x39,0x35]);U32(cave+0x1d010,cave+0x11c);Bytes(cave+0x1d014,[0x75,0x53]);
            U32(cave+0x100,1);U32(cave+0x120,1);U32(cave+0x11c,Session);U32(cave+0x140,1);
            U32(cave+0x300,0x1072200);U32(cave+0x200,0x1075300);
        }
        public void Player(int i,uint id,string name,bool bot,bool self)
        {
            U32(Session+0xc8,Node(0));if(i>0)U32(Node(i-1)+4,Node(i));U32(Node(i),Person(i));
            U32(Person(i),image+0x4bd914);U32(Person(i)+0x20,id);U8(Person(i)+0xc,bot?(byte)1:(byte)0);
            U32(Person(i)+8,0x1060000+(uint)i*256);Bytes(0x1060000+(uint)i*256,Encoding.Unicode.GetBytes(name+"\0"));
            if(self)U32(Person(i)+4,0x1070000);
        }
    }
}
