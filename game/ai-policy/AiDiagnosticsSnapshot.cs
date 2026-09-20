using System;
using System.Collections.Generic;
using System.Text;

// Read-only asynchronous context. Decisions themselves are captured on the
// simulation thread; these summaries explicitly carry start/end game times.
internal sealed class AiDiagnosticsSnapshot
{
    readonly IMemory memory; readonly uint image;
    readonly Dictionary<uint,string> names=new Dictionary<uint,string>();
    uint epoch;
    internal object Summary { get; private set; }
    internal AiDiagnosticsSnapshot(IMemory memory,uint image){this.memory=memory;this.image=image;}
    byte[] Read(uint p,int n){if(p<65536||n<0||n>1048576)throw new InvalidOperationException("Invalid diagnostic range");return memory.Read(p,n);}
    static uint U(byte[] b,int o){return BitConverter.ToUInt32(b,o);}
    static object F(byte[] b,int o){float f=BitConverter.ToSingle(b,o);return float.IsNaN(f)||float.IsInfinity(f)?(object)null:f;}
    uint P(uint p){return U(Read(p,4),0);}
    string Text(uint p){if(p==0)return "";var b=Read(p,256);int n=0;while(n+1<b.Length&&(b[n]!=0||b[n+1]!=0))n+=2;return Encoding.Unicode.GetString(b,0,n);}
    string Name(uint def){if(def==0)return "";string name;if(names.TryGetValue(def,out name))return name;name=Text(P(def+8));if(names.Count<8192)names[def]=name;return name;}
    string Type(uint vt){try{uint locator=P(vt-4),descriptor=P(locator+12);var b=Read(descriptor+8,128);int n=System.Array.IndexOf(b,(byte)0);return Encoding.ASCII.GetString(b,0,n<0?b.Length:n);}catch{return "unknown";}}
    uint[] Array(uint p,uint n,int limit){if(n>(uint)limit)throw new InvalidOperationException("Diagnostic list limit");if(n==0)return new uint[0];var b=Read(p,(int)n*4);var a=new uint[n];for(int i=0;i<a.Length;i++)a[i]=U(b,i*4);return a;}
    object[] Floats(uint p,uint n){if(n>16)throw new InvalidOperationException("Diagnostic resource limit");if(p==0)return null;var b=Read(p,(int)n*4);var a=new object[n];for(int i=0;i<a.Length;i++)a[i]=F(b,i*4);return a;}
    List<uint> Linked(uint head,int limit){var list=new List<uint>();var seen=new HashSet<uint>();while(head!=0&&seen.Add(head)&&list.Count<limit){var b=Read(head,8);list.Add(U(b,0));head=U(b,4);}return list;}
    object Goal(uint p,uint engine){if(p==0)return null;var b=Read(p,0x80);if(U(b,4)!=engine)return null;return new {address=p,type=Type(U(b,0)),state=U(b,8),priority=F(b,0x34),basePriority=F(b,0x38),tail=Convert.ToBase64String(Sub(b,0x3c,0x44))};}
    static byte[] Sub(byte[] b,int o,int n){var a=new byte[n];Buffer.BlockCopy(b,o,a,0,n);return a;}
    object Actor(uint p,uint id,uint kingdom){var b=Read(p,0x180);if(U(b,0x14)!=id||U(b,0xe8)!=kingdom)return null;
        object state=null,organization=null;
        uint cai=U(b,0x70),org=U(b,0x7c);
        if(cai!=0){var c=Read(cai,0x30);if(U(c,4)==p&&U(c,0x14)!=0){uint st=P(U(c,0x14));if(st!=0){var s=Read(st,0x80);state=new {type=Type(U(s,0)),raw=Convert.ToBase64String(s)};}}}
        if(org!=0){var o=Read(org,0xd0);if(U(o,4)==p)organization=new {formationX=F(o,0xbc),formationY=F(o,0xc0),members=Array(U(o,0x28),U(o,0x2c),128),raw=Convert.ToBase64String(o)};}
        return new {id=id,definition=Name(U(b,4)),x=F(b,0x20),y=F(b,0x24),flags=U(b,8),actorState=U(b,0x100),state=state,organization=organization};
    }
    object Building(uint p,uint kingdom,uint rc){var b=Read(p,0x110);if(U(b,0xe8)!=kingdom)return null;uint construction=U(b,0x9c),economy=U(b,0x84);object work=null,econ=null;
        if(construction!=0){var c=Read(construction,0x30);if(U(c,4)==p)work=new {upgrade=Name(U(c,0x28))};}
        if(economy!=0){var e=Read(economy,0x30);if(U(e,4)==p)econ=new {productionActive=e[0x10]!=0,upkeepActive=e[0x11]!=0,production=Floats(U(e,0x18),Math.Min(rc,U(e,0x1c))),upkeep=Floats(U(e,0x28),Math.Min(rc,U(e,0x2c)))};}
        return new {id=U(b,0x14),definition=Name(U(b,4)),x=F(b,0x20),y=F(b,0x24),state=U(b,0x100),work=work,economy=econ};
    }
    internal object Capture(){Summary=null;uint world=P(image+0x5f3fb8),phase=P(image+0x5f9218);if(phase!=2||world==0)return null;
        if(epoch!=world){names.Clear();epoch=world;}var w=Read(world,0x158);object start=F(w,0xe8);var kingdoms=Array(U(w,0x150),U(w,0x154),96);var valid=new HashSet<uint>(kingdoms);
        uint table=P(image+0x5f3fb4),rc=P(table+0x38);if(rc<1||rc>16)throw new InvalidOperationException("Unsupported resource table");var resourceDefs=Array(P(table+0x34),rc,16);var resources=new string[rc];for(int i=0;i<resources.Length;i++)resources[i]=Name(resourceDefs[i]);
        uint sai=P(image+0x5f3fc8),registry=P(image+0x5ef72c);if(sai==0||registry==0)return null;var slots=Read(registry+0x20004,0x40000);var sb=Read(sai,0x74);var bots=new List<object>();
        var compact=new List<object>();
        foreach(uint pl in Array(U(sb,0x6c),U(sb,0x70),96)){
            var pb=Read(pl,0x34);uint kp=U(pb,8),engine=U(pb,0xc);if(!valid.Contains(kp))continue;var k=Read(kp,0x2e4);var goals=new List<object>();var actors=new List<object>();var buildings=new List<object>();var eb=Read(engine,0x18);if(U(eb,4)!=pl)continue;
            foreach(uint gp in Linked(U(eb,0xc),4096))goals.Add(Goal(gp,engine));
            foreach(uint ap in Linked(U(pb,0x2c),1024)){var ab=Read(ap,0x14);if(U(ab,0xc)!=pl)continue;uint id=U(ab,8),p=U(slots,(int)(id&65535)*4);if(p!=0)actors.Add(new {actor=Actor(p,id,kp),assignedGoal=Goal(U(ab,0x10),engine)});}
            var seen=new HashSet<uint>();foreach(uint city in Array(U(k,0x2dc),U(k,0x2e0),256)){if(seen.Add(city))buildings.Add(Building(city,kp,rc));uint container=P(city+0x98);if(container==0)continue;var c=Read(container,0x20);uint center=U(c,0x14);if(center!=0&&seen.Add(center))buildings.Add(Building(center,kp,rc));foreach(uint child in Array(U(c,0x18),U(c,0x1c),256))if(child!=0&&seen.Add(child))buildings.Add(Building(child,kp,rc));}
            bots.Add(new {kingdom=kp,teamParent=U(k,0x1f8),name=Text(U(k,0x1a0)),profile=Name(U(pb,0x18)),ego=Name(U(pb,0x1c)),production=Floats(U(k,0x1a8),rc),upkeep=Floats(U(k,0x1c0),rc),stock=Floats(U(k,0x1cc),Math.Min(rc,U(k,0x1d0))),goals=goals,actors=actors,buildings=buildings});
            compact.Add(new {kingdom=kp,teamParent=U(k,0x1f8),name=Text(U(k,0x1a0)),profile=Name(U(pb,0x18)),ego=Name(U(pb,0x1c)),cities=U(k,0x2e0),production=Floats(U(k,0x1a8),rc),upkeep=Floats(U(k,0x1c0),rc),stock=Floats(U(k,0x1cc),Math.Min(rc,U(k,0x1d0))),actorCount=actors.Count});
        }
        if(P(image+0x5f3fb8)!=world||P(image+0x5f9218)!=phase)return null;
        Summary=new {world=world,gameTimeStart=start,gameTimeEnd=F(Read(world+0xe8,4),0),asynchronous=true,resources=resources,bots=compact};
        return new {world=world,gameTimeStart=start,gameTimeEnd=F(Read(world+0xe8,4),0),asynchronous=true,resources=resources,bots=bots};
    }
}
