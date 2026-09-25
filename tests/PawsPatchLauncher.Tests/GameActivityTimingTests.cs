using System.Text.Json;
using PawsPatchLauncher;

internal static class GameActivityTimingTests
{
    public static int Run()
    {
        var checks=0;
        void Check(bool ok,string why){checks++;if(!ok)throw new Exception("Activity timing: "+why);}
        GameActivity? Parse(object value)=>GameActivity.Read(JsonSerializer.SerializeToElement(value));
        var activity=new GameActivity("match",ElapsedSeconds:100,Paused:true,Speed:1.5);
        Check(Parse(activity) is {Paused:true,Speed:1.5},"explicit timing roundtrip");
        Check(Parse(activity.Summary()) is {Paused:true,Speed:1.5},"summary retains timing");
        Check(Parse(new GameActivity("match")) is {Paused:null,Speed:null},"legacy source stays unknown");
        Check(!JsonSerializer.Serialize(new GameActivity("lobby")).Contains("paused")&&!JsonSerializer.Serialize(new GameActivity("lobby")).Contains("speed"),"unknown fields omitted");
        foreach(var phase in new[]{"menu","loading","editor","lobby"})
        {
            Check(Parse(new GameActivity(phase,Paused:false)) is null,"pause restricted to match");
            Check(Parse(new GameActivity(phase,Speed:1)) is null,"speed restricted to match");
        }
        foreach(var paused in new object[]{"true",1,new{value=true}})
            Check(Parse(new{phase="match",multiplayer=false,paused}) is null,"invalid pause rejected");
        foreach(var speed in new object[]{"1.5",true,0,-1,0.0001,1025})
            Check(Parse(new{phase="match",multiplayer=false,speed}) is null,"invalid speed rejected");
        foreach(var speed in new[]{0.001,0.25,0.5,1,1.5,2,4,1024})
            Check(Parse(activity with{Speed=speed})?.Speed==speed,"valid speed accepted");
        foreach(var image in new uint[]{0x400000,0x460000,0x750000})
        {
            var m=new GameActivityTests.Memory(image);const uint controller=0x1076000,options=0x1077000,option=0x1077800;
            m.U32(image+0x5f3fb8,m.World);m.U32(m.Session+0xf0,2);m.F32(m.World+0xe8,100.5f);
            m.U32(image+0x5f3fe8,controller);m.U32(image+0x5f921c,2);
            m.Bytes(image+0x1612a2,[0x8a,0x44,0x24,0x04,0x88,0x41,0x28,0xc2,0x04,0x00]);
            m.Bytes(image+0x1613aa,[0x80,0x79,0x28,0x00,0x75,0x09,0x80,0x79,0x29,0x00,0x75,0x03,0xb0,0x01,0xc3,0x32,0xc0,0xc3]);
            m.Bytes(image+0x16107b,[0xf3,0x0f,0x5c,0xca,0xf3,0x0f,0x11,0x57,0x20]);
            GameActivity? Read()=>KohanActivityReader.ReadSnapshot(image,m.Read);
            foreach(var exponent in new[]{-2f,-1f,0f,0.5f,1f,2f})
            {
                m.F32(controller+0x20,exponent);
                Check(Read() is {Paused:false,Speed:double s}&&Math.Abs(s-Math.Pow(2,exponent))<1e-9,"live logarithmic speed including hotkeys");
            }
            m.U8(controller+0x28,1);Check(Read() is {Paused:true,Speed:4,ElapsedSeconds:100},"explicit native pause retains selected speed");
            m.U8(controller+0x28,0);m.U8(controller+0x29,1);Check(Read()?.Paused==true,"native secondary pause");m.U8(controller+0x29,0);
            m.U32(image+0x5f921c,0);m.U32(image+0x5f9480,options);m.U32(options+0x37c,option);m.U8(option,1);
            Check(Read()?.Paused==true,"single-player background auto-pause");
            m.U8(m.Session+0x100,1);Check(Read()?.Paused==false,"multiplayer is not paused by losing focus");m.U8(m.Session+0x100,0);
            m.U8(option,0);Check(Read()?.Paused==false,"disabled background auto-pause");m.U8(option,7);
            Check(Read()?.Paused is null,"corrupt native boolean stays unknown");m.U32(image+0x5f921c,2);
            m.U8(controller+0x28,7);Check(Read()?.Paused is null,"invalid explicit pause is unknown");m.U8(controller+0x28,0);
            m.F32(controller+0x20,float.NaN);Check(Read() is {Speed:null,ElapsedSeconds:100},"invalid speed cannot poison activity");m.F32(controller+0x20,0);
            var reads=0;
            byte[] ChangeSpeed(uint at,int count)=>at==controller+0x20&&++reads==2?BitConverter.GetBytes(1f):m.Read(at,count);
            Check(KohanActivityReader.ReadSnapshot(image,ChangeSpeed) is null,"speed changed mid-sample discarded");
            reads=0;
            byte[] ChangePause(uint at,int count)=>at==controller+0x28&&++reads==2?[1,0]:m.Read(at,count);
            Check(KohanActivityReader.ReadSnapshot(image,ChangePause) is null,"pause changed mid-sample discarded");
            m.U8(image+0x1612a2,0);Check(Read() is {Paused:null,Speed:null,ElapsedSeconds:100},"unknown timing code preserves other activity");
        }
        var now=DateTimeOffset.UtcNow;
        foreach(var speed in new[]{0.25,0.5,1,1.5,2,4})
        {
            var clock=new GameActivityClock();var sample=new GameActivityDetails(activity with{Paused=false,Speed=speed},now);
            clock.Observe(sample,1000,now.AddSeconds(2));
            Check(clock.Seconds(9000)==100+(int)(10*speed),"sample age and local seconds scale by speed");
            Check(clock.Seconds(100000)==100+(int)(40*speed),"stale cap remains forty wall seconds");
            var paused=sample with{ObservedAt=now.AddSeconds(10),Activity=sample.Activity with{ElapsedSeconds=120,Paused=true}};
            clock.Observe(paused,10000,now.AddSeconds(12));
            Check(clock.Seconds(10000)==120&&clock.Seconds(999999)==120,"pause freezes including network sample age");
            clock.Observe(sample,10001,now);Check(clock.Seconds(15000)==120,"out-of-order running sample cannot unpause");
            clock.Observe(paused,20000,now.AddSeconds(30));Check(clock.Seconds(21000)==120,"repeat sample cannot reset frozen clock");
            clock.Observe(new(activity with{Paused=false,ElapsedSeconds=120,Speed=speed},now.AddSeconds(30)),30000,now.AddSeconds(30));
            Check(clock.Seconds(40000)==120+(int)(10*speed),"resume at new anchor excludes paused duration");
        }
        Console.WriteLine($"GAME ACTIVITY TIMING PASS {checks}");return checks;
    }
}
