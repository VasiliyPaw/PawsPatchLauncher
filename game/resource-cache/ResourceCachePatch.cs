using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;

internal static class ResourceCachePatch
{
    static uint state; static int pid; static Action<string> logger;
    static DateTime next; static byte[] previous;
    static uint U(IntPtr p) { return unchecked((uint)p.ToInt32()); }
    static uint U(byte[] b,int at) { return BitConverter.ToUInt32(b,at); }
    static uint Resolve(Process game,string name)
    {
        uint address=U(GetProcAddress(GetModuleHandle("kernel32.dll"),name));
        if(address==0) throw new IOException("Resource preparation system function is unavailable: "+name);
        using(var local=Process.GetCurrentProcess()) {
            var owner=local.Modules.Cast<ProcessModule>().Single(m=>address>=U(m.BaseAddress)&&address<U(m.BaseAddress)+(uint)m.ModuleMemorySize);
            game.Refresh();var remote=game.Modules.Cast<ProcessModule>().Single(m=>String.Equals(m.ModuleName,owner.ModuleName,StringComparison.OrdinalIgnoreCase));
            if(ReleaseStartup.Hash(owner.FileName)!=ReleaseStartup.Hash(remote.FileName)) throw new IOException("Resource preparation system module differs.");
            return U(remote.BaseAddress)+address-U(owner.BaseAddress);
        }
    }
    internal static void Install(Process game,IMemory m,uint image,Action<string> log)
    {
        uint clock=Resolve(game,"GetTickCount"),memory=Resolve(game,"GlobalMemoryStatusEx"),cave=0;
        var attempted=new List<int>();bool safe=true;
        for(int i=0;i<ResourceCachePayload.Sites.Length;i++)TerrainPatch.Expect(m,image+ResourceCachePayload.Sites[i],ResourceCachePayload.Original(i,image));
        try {
            cave=m.Allocate(ResourceCachePayload.Allocation);
            byte[] code=ResourceCachePayload.Build(image,cave);m.Write(cave,code);TerrainPatch.Expect(m,cave,code);
            var config=new byte[ResourceCachePayload.Allocation-ResourceCachePayload.CodeSize];
            Buffer.BlockCopy(BitConverter.GetBytes(image),0,config,0,4);
            Buffer.BlockCopy(BitConverter.GetBytes(clock),0,config,4,4);
            Buffer.BlockCopy(BitConverter.GetBytes(memory),0,config,8,4);
            Buffer.BlockCopy(BitConverter.GetBytes(3u),0,config,12,4);
            m.Write(cave+ResourceCachePayload.State,config);TerrainPatch.Expect(m,cave+ResourceCachePayload.State,config);
            m.MakeExecutable(cave,ResourceCachePayload.CodeSize);m.Flush(cave,code.Length);
            // Install the weight correction before the VIEW-thread callback.
            for(int k=ResourceCachePayload.Sites.Length-1;k>=0;k--) {
                uint site=image+ResourceCachePayload.Sites[k];byte[] original=ResourceCachePayload.Original(k,image),hook=new byte[original.Length];
                for(int j=0;j<hook.Length;j++)hook[j]=0x90;
                byte[] jump=TerrainPatch.Call(site,cave+ResourceCachePayload.Entries[k]);jump[0]=0xe9;Buffer.BlockCopy(jump,0,hook,0,jump.Length);
                attempted.Add(k);m.WriteCode(site,hook);TerrainPatch.Expect(m,site,hook);m.Flush(site,hook.Length);
            }
            pid=game.Id;state=cave+ResourceCachePayload.State;logger=log;previous=null;next=DateTime.MinValue;
            log("RESOURCE_CACHE r1; native per-class budgets repaired; bounded VIEW-thread model/effect preparation; state=0x"+state.ToString("X8"));
        } catch {
            for(int j=attempted.Count-1;j>=0;j--)try {
                int i=attempted[j];uint site=image+ResourceCachePayload.Sites[i];byte[] b=ResourceCachePayload.Original(i,image);
                m.WriteCode(site,b);TerrainPatch.Expect(m,site,b);m.Flush(site,b.Length);
            }catch {safe=false;}
            if(cave!=0&&safe)m.Free(cave);throw;
        }
    }
    internal static void Tick()
    {
        if(state==0||DateTime.UtcNow<next)return;next=DateTime.UtcNow.AddSeconds(5);
        try {
            byte[] b;using(var m=new NativeMemory(pid))b=m.Read(state,104);
            // Frame counts and scan cursors change without a material cache event.
            if(previous!=null&&U(previous,16)==U(b,16)&&U(previous,40)==U(b,40)&&U(previous,56)==U(b,56)&&U(previous,96)==U(b,96))return;
            previous=b;
            logger("RESOURCE_CACHE_COUNTERS weights="+U(b,16)+" prepared="+U(b,40)+" models="+U(b,44)+" animations="+U(b,48)+" failed="+U(b,52)+" pressureSkips="+U(b,56)+" workMs="+U(b,76)+" maxAssetMs="+U(b,68)+" complete="+U(b,96));
        }catch {next=DateTime.UtcNow.AddSeconds(20);}
    }
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode)]static extern IntPtr GetModuleHandle(string name);
    [DllImport("kernel32.dll",CharSet=CharSet.Ansi)]static extern IntPtr GetProcAddress(IntPtr module,string name);
}
