using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;

namespace PawLairDiagnostics
{
    // Observer only: no write/allocate/protect/remote-thread API is exposed.
    internal interface IReadMemory { byte[] Read(uint address, int count); }

    internal sealed class ProcessMemory : IReadMemory, IDisposable
    {
        private IntPtr handle;
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern IntPtr OpenProcess(uint access, bool inherit, int pid);
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool ReadProcessMemory(IntPtr process, IntPtr address, byte[] buffer, IntPtr size, out IntPtr read);
        [DllImport("kernel32.dll")]
        private static extern bool CloseHandle(IntPtr handle);
        internal ProcessMemory(int pid)
        {
            handle = OpenProcess(0x410, false, pid); // QUERY_INFORMATION | VM_READ
            if (handle == IntPtr.Zero) throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
        }
        public byte[] Read(uint address, int count)
        {
            if (address < 0x10000 || count <= 0 || count > 0x60000 || (ulong)address + (uint)count > 0x100000000UL) return null;
            byte[] data = new byte[count]; IntPtr read;
            return ReadProcessMemory(handle, new IntPtr(unchecked((int)address)), data, new IntPtr(count), out read)
                && read.ToInt64() == count ? data : null;
        }
        public void Dispose() { if (handle != IntPtr.Zero) { CloseHandle(handle); handle = IntPtr.Zero; } }
    }

    internal sealed class ActorSample
    {
        public uint pointer, id, owner, state, flags, home;
        public string dataId;
        public float? x, y, health, maximumHealth;
    }
    internal sealed class GroupSample
    {
        public uint pointer, actorId, flags, dataFlags;
        public string dataId;
        public float? storedHealth, maximumHealth, baseResupplyRate, strengthWeight;
        public bool atHome, fullyRestoredAtHome, staleActorId;
        public ActorSample deployedActor;
    }
    internal sealed class DeploymentSample
    {
        public uint pointer, flags;
        public bool complete;
        public ActorSample organization;
        public List<ActorSample> members = new List<ActorSample>();
    }
    internal sealed class LairSample
    {
        public ActorSample actor;
        public uint component, flags, timerState, behaviorMask;
        public float? reportedStrength, maximumStrength, timer, delay;
        public int groupCount, atHomeCount, fullyRestoredAtHomeCount;
        public bool complete;
        public List<GroupSample> groups = new List<GroupSample>();
        public List<ActorSample> intruders = new List<ActorSample>();
        public List<DeploymentSample> deployed = new List<DeploymentSample>();
    }
    internal sealed class KingdomSample
    {
        public uint pointer, parent, majorIndex, minorIndex;
        public string dataId;
        public float? resupplyPenalty;
        public uint[] majorRelations, minorRelations;
        public float?[] production, consumption;
    }
    internal sealed class Frame
    {
        public uint world, registry, sessionKind;
        public float? gameTime;
        public int registeredObjects;
        public List<KingdomSample> kingdoms = new List<KingdomSample>();
        public List<LairSample> lairs = new List<LairSample>();
        public bool complete;
    }

    internal sealed class LairReader
    {
        internal const uint WorldRva = 0x5F3FB8, RegistryRva = 0x5EF72C, DenizenVtableRva = 0x4E0434;
        private readonly IReadMemory memory;
        private readonly uint image;
        private byte[] slots, generations;
        private uint registry;
        private uint previousWorld;
        private float? previousTime;
        private readonly Dictionary<uint,string> names = new Dictionary<uint,string>();

        internal LairReader(IReadMemory memory, uint image) { this.memory = memory; this.image = image; }
        internal static uint U(byte[] bytes, int offset)
        { return bytes != null && offset >= 0 && offset + 4 <= bytes.Length ? BitConverter.ToUInt32(bytes, offset) : 0; }
        internal static float? F(byte[] bytes, int offset)
        {
            if (bytes == null || offset < 0 || offset + 4 > bytes.Length) return null;
            float value = BitConverter.ToSingle(bytes, offset);
            return Single.IsNaN(value) || Single.IsInfinity(value) ? (float?)null : value;
        }
        private uint P(uint address) { return U(memory.Read(address,4),0); }
        internal bool VerifyLayout()
        {
            return Match(image + 0x21117, new byte[] {0x8b,0x44,0x24,0x04,0x0f,0xb7,0xd0,0xc1,0xe8,0x10})
                && Match(image + 0x20A28C, new byte[] {0x55,0x8b,0xec,0x53,0x56,0x8b,0x75,0x08,0x8b,0xd9})
                && Match(image + 0x20AED9, new byte[] {0xf3,0x0f,0x58,0x46,0x08,0xf3,0x0f,0x11,0x46,0x08});
        }
        internal object DescribeLayout()
        {
            var result=new Dictionary<string,string>();
            foreach(uint rva in new uint[]{0x21117,0x20A28C,0x20AED9})
            {
                byte[] actual=memory.Read(image+rva,10);
                result[rva.ToString("X8")]=actual==null ? "unreadable" : BitConverter.ToString(actual);
            }
            return result;
        }
        private bool Match(uint address, byte[] expected)
        {
            byte[] actual = memory.Read(address,expected.Length);
            if (actual == null) return false;
            for(int i=0;i<actual.Length;i++) if(actual[i]!=expected[i]) return false;
            return true;
        }
        private string Name(uint data)
        {
            if(data < 0x10000) return "";
            string value;
            if(names.TryGetValue(data,out value)) return value;
            uint text = P(data + 8); byte[] bytes = memory.Read(text,192);
            if(bytes == null) return "";
            int end=0; while(end+1<bytes.Length && (bytes[end]!=0 || bytes[end+1]!=0)) end+=2;
            value=Encoding.Unicode.GetString(bytes,0,end);
            if(names.Count>8192) names.Clear();
            names[data]=value; return value;
        }
        private uint Resolve(uint id)
        {
            if(id==0 || slots==null || generations==null) return 0;
            int index=(int)(id & 65535);
            if(BitConverter.ToUInt16(generations,index*2)!=(id>>16)) return 0;
            uint actor=U(slots,index*4);
            return P(actor+0x14)==id ? actor : 0;
        }
        private ActorSample Actor(uint ptr)
        {
            byte[] bytes=memory.Read(ptr,0x104);
            if(bytes==null) return null;
            uint id=U(bytes,0x14);
            if(Resolve(id)!=ptr) return null;
            byte[] body=memory.Read(U(bytes,0x60),0x18);
            return new ActorSample { pointer=ptr,id=id,dataId=Name(U(bytes,4)),owner=U(bytes,0xE8),
                flags=U(bytes,8),state=U(bytes,0x100),x=F(bytes,0x20),y=F(bytes,0x24),
                health=F(body,0x10),maximumHealth=F(body,0x14),home=U(bytes,0xBC) };
        }
        private static uint[] Vector(IReadMemory memory,uint address,int count)
        {
            if(count<0 || count>96) return null;
            if(count==0) return new uint[0];
            byte[] bytes=memory.Read(address,count*4); if(bytes==null) return null;
            uint[] result=new uint[count]; for(int i=0;i<count;i++) result[i]=U(bytes,i*4); return result;
        }
        private float?[] Floats(uint address,int count)
        {
            byte[] bytes=memory.Read(address,count*4); if(bytes==null) return null;
            var values=new float?[count]; for(int i=0;i<count;i++) values[i]=F(bytes,i*4); return values;
        }
        internal Frame Capture()
        {
            uint world=P(image+WorldRva);
            if(world<0x10000 || U(memory.Read(image+0x5F9218,4),0)!=2) {names.Clear();previousWorld=0;return null;}
            byte[] worldBytes=memory.Read(world,0x158); if(worldBytes==null) return null;
            float? time=F(worldBytes,0xE8);
            if(world!=previousWorld || time<previousTime) names.Clear();
            previousWorld=world;previousTime=time;
            registry=P(image+RegistryRva); if(registry<0x10000) return null;
            generations=memory.Read(registry+4,0x20000); slots=memory.Read(registry+0x20004,0x40000);
            if(slots==null || generations==null) return null;
            var frame=new Frame {world=world,registry=registry,gameTime=F(worldBytes,0xE8),complete=true,
                sessionKind=P(P(image+0x5F3FE4)+0x64)};
            uint count=U(worldBytes,0x154);
            if(count>96) return null;
            var kingdoms=Vector(memory,U(worldBytes,0x150),(int)count);
            if(kingdoms==null) return null;
            foreach(uint ptr in kingdoms)
            {
                byte[] k=memory.Read(ptr,0x244); if(k==null) {frame.complete=false;continue;}
                // Relation indices are native kingdom indices, preserved verbatim.
                frame.kingdoms.Add(new KingdomSample {pointer=ptr,dataId=Name(U(k,4)),parent=U(k,0x1F8),
                    minorIndex=U(k,0x38),majorIndex=U(k,0x190),resupplyPenalty=F(k,0x1FC),
                    majorRelations=Vector(memory,U(k,0x1D8),(int)U(k,0x1DC)),minorRelations=Vector(memory,U(k,0x1E4),(int)U(k,0x1E8)),
                    production=Floats(U(k,0x1A8),(int)Math.Min(U(k,0x1AC),16)),
                    consumption=Floats(U(k,0x1C0),(int)Math.Min(U(k,0x1C4),16))});
            }
            // Read native object table, then verify identity, component vtable,
            // back-reference and generation. No calls into game code are made.
            for(int index=0;index<65536;index++)
            {
                uint ptr=U(slots,index*4); if(ptr<0x10000) continue;
                frame.registeredObjects++;
                uint component=P(ptr+0x88);
                if(component<0x10000 || P(component)!=image+DenizenVtableRva || P(component+4)!=ptr) continue;
                ActorSample actor=Actor(ptr); if(actor==null || (actor.id&65535)!=(uint)index) continue;
                var lair=ReadComponent(actor,component);
                if(lair!=null) {frame.lairs.Add(lair);frame.complete &= lair.complete;} else frame.complete=false;
            }
            // Discard an observation spanning a world/registry transition.
            if(P(image+WorldRva)!=world || P(image+RegistryRva)!=registry) return null;
            return frame;
        }
        private LairSample ReadComponent(ActorSample actor,uint component)
        {
            byte[] c=memory.Read(component,0x4C); if(c==null) return null;
            var lair=new LairSample {actor=actor,component=component,complete=true,
                reportedStrength=F(c,0x10),maximumStrength=F(c,0x14),flags=U(c,0x20),
                timerState=U(c,0x0C),timer=F(c,0x30),delay=F(c,0x34),behaviorMask=U(c,0x38)};
            var seen=new HashSet<uint>(); uint node=U(c,0x18);
            while(node!=0)
            {
                if(seen.Count>=256 || !seen.Add(node)) {lair.complete=false;break;}
                byte[] g=memory.Read(node,0x14); if(g==null) {lair.complete=false;break;}
                uint data=U(g,4); byte[] d=memory.Read(data,0x2D0);
                if(d==null) {lair.complete=false;break;}
                uint actorId=U(g,0); uint deployed=Resolve(actorId);
                var item=new GroupSample {pointer=node,actorId=actorId,flags=U(g,0xC),dataFlags=U(d,0x174),
                    dataId=Name(data),storedHealth=F(g,8),maximumHealth=F(d,0x284),baseResupplyRate=F(d,0x2CC),
                    strengthWeight=F(d,0x1E4),atHome=actorId==0,staleActorId=actorId!=0 && deployed==0,
                    deployedActor=deployed==0 ? null : Actor(deployed)};
                item.fullyRestoredAtHome=item.atHome && item.maximumHealth>0 && item.storedHealth>=item.maximumHealth;
                lair.groups.Add(item); if(item.atHome) lair.atHomeCount++; if(item.fullyRestoredAtHome) lair.fullyRestoredAtHomeCount++;
                node=U(g,0x10);
            }
            lair.groupCount=lair.groups.Count;
            seen.Clear(); node=U(c,0x24);
            while(node!=0)
            {
                if(seen.Count>=128 || !seen.Add(node)) {lair.complete=false;break;}
                byte[] n=memory.Read(node,8); if(n==null) {lair.complete=false;break;}
                uint ptr=Resolve(U(n,0)); var intruder=Actor(ptr);
                if(intruder!=null) lair.intruders.Add(intruder);
                else lair.intruders.Add(new ActorSample {id=U(n,0),pointer=ptr,dataId="unresolved"});
                node=U(n,4);
            }
            seen.Clear();node=U(c,0x40);
            while(node!=0)
            {
                if(seen.Count>=128 || !seen.Add(node)) {lair.complete=false;break;}
                byte[] n=memory.Read(node,8); if(n==null) {lair.complete=false;break;}
                uint thing=U(n,0);byte[] t=memory.Read(thing,0x2C);
                if(t==null) {lair.complete=false;break;}
                var dep=new DeploymentSample {pointer=thing,flags=U(t,8),complete=true};
                // TGC_SmartPointer in +28 stores the actor directly (not an ID).
                dep.organization=Actor(U(t,0x28));
                if(dep.organization!=null)
                {
                    uint org=P(dep.organization.pointer+0x7C);
                    uint members=P(org+0x2C);
                    if(members<=64)
                    {
                        var list=Vector(memory,P(org+0x28),(int)members);
                        if(list!=null) foreach(uint member in list) {var a=Actor(member);if(a!=null) dep.members.Add(a);else dep.complete=false;}
                        else dep.complete=false;
                    }
                    else dep.complete=false;
                }
                lair.deployed.Add(dep);node=U(n,4);
            }
            if(P(actor.pointer+0x88)!=component || P(component+4)!=actor.pointer || Resolve(actor.id)!=actor.pointer) return null;
            return lair;
        }
    }
}
