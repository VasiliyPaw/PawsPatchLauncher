using System;
using System.IO;
using System.Text;
using System.Reflection;
using System.Runtime.InteropServices;
using System.ComponentModel;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using System.Threading;

// Mandatory, UI-only part of Paw's Patch. No palette, family, sync or RNG code.
internal static class PawGamePresentation
{
    const int Size=4096;
    static readonly int[] Sites={0xBF99F,0xFA979};
    static readonly int[] Targets={0,0x400};
    static readonly byte[][] Expected={
        new byte[]{0xE8,0xFB,0xD3,0x1F,0},
        new byte[]{0xA1,0xC0,0x3F,0xA5,0}
    };
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool ReadProcessMemory(IntPtr p,IntPtr a,byte[] b,int n,out IntPtr done);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool WriteProcessMemory(IntPtr p,IntPtr a,byte[] b,int n,out IntPtr done);
    [DllImport("kernel32.dll",SetLastError=true)] static extern IntPtr VirtualAllocEx(IntPtr p,IntPtr a,int size,uint type,uint protect);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool VirtualFreeEx(IntPtr p,IntPtr a,int size,uint type);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool VirtualProtectEx(IntPtr p,IntPtr a,int n,uint protect,out uint old);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool FlushInstructionCache(IntPtr p,IntPtr a,int n);
    [DllImport("kernel32.dll",SetLastError=true)] static extern bool GetExitCodeProcess(IntPtr p,out uint code);
    static IntPtr Add(IntPtr p,int n){return new IntPtr(p.ToInt64()+n);}
    static byte[] Resource(string name)
    {
        using(var stream=Assembly.GetExecutingAssembly().GetManifestResourceStream(name))
        using(var output=new MemoryStream())
        {
            if(stream==null) throw new InvalidDataException("Missing common UI payload: "+name);
            stream.CopyTo(output); return output.ToArray();
        }
    }
    static bool Equal(byte[] a,byte[] b)
    {
        if(a.Length!=b.Length) return false;
        for(int i=0;i<a.Length;i++) if(a[i]!=b[i]) return false;
        return true;
    }
    static byte[] ExpectedAt(int site,uint image)
    {
        byte[] bytes=(byte[])Expected[site].Clone();
        // Main-menu MOV has an absolute operand relocated by the PE loader.
        // The relative formatter CALL has identical bytes at every image base.
        if(site==1) Buffer.BlockCopy(BitConverter.GetBytes(unchecked(image+0x5F3FC0)),0,bytes,1,4);
        return bytes;
    }
    internal static string VersionSuffix(string text)
    {
        var values=new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase);
        foreach(string raw in text.Split('\n'))
        {
            string line=raw.Trim();
            if(line.Length==0 || line.StartsWith(";") || line=="[Versions]") continue;
            int split=line.IndexOf('=');
            if(split<1) throw new InvalidDataException("Invalid version metadata line");
            string key=line.Substring(0,split).Trim(),value=line.Substring(split+1).Trim();
            if((key!="ArcaneWars" && key!="PawPatch") || values.ContainsKey(key) ||
                !Regex.IsMatch(value,@"\A[0-9A-Za-z.+_-]{1,64}\z"))
                throw new InvalidDataException("Invalid version metadata value");
            values.Add(key,value);
        }
        if(!values.ContainsKey("ArcaneWars") || !values.ContainsKey("PawPatch"))
            throw new InvalidDataException("Version metadata is incomplete");
        return "\nArcane Wars "+values["ArcaneWars"]+"\nPaw's Patch "+values["PawPatch"];
    }
    static byte[] Relocate(uint image,uint cave)
    {
        byte[] bytes=Resource("PawCommonUiPayload");
        if(bytes.Length!=Size) throw new InvalidDataException("Common UI payload size changed");
        using(var r=new BinaryReader(new MemoryStream(Resource("PawCommonUiFixups"))))
        {
            uint count=r.ReadUInt32();
            if(count>32 || r.BaseStream.Length!=4+12*count) throw new InvalidDataException("Invalid UI fixups");
            var seen=new HashSet<uint>();
            for(int i=0;i<count;i++)
            {
                uint kind=r.ReadUInt32(),off=r.ReadUInt32(),value=r.ReadUInt32();
                if(off>0x7fc || !seen.Add(off)) throw new InvalidDataException("Invalid UI relocation");
                uint result;
                if(kind==1) result=unchecked(image+value);
                else if(kind==2) result=unchecked(cave+value);
                else if(kind==3) result=unchecked(image+value-(cave+off+4));
                else throw new InvalidDataException("Unknown UI relocation");
                Buffer.BlockCopy(BitConverter.GetBytes(result),0,bytes,(int)off,4);
            }
        }
        return bytes;
    }
    public static int VerifyOffline()
    {
        if(!Equal(Resource("PawCommonUiPayload"),Relocate(0x460000,0x10000000)))
            throw new InvalidDataException("Common UI relocation self-test failed");
        foreach(uint image in new uint[]{0x460000,0x80000,0x6A0000})
        {
            byte[] menu=ExpectedAt(1,image);
            if(menu[0]!=0xA1 || BitConverter.ToUInt32(menu,1)!=image+0x5F3FC0 || !Equal(ExpectedAt(0,image),Expected[0]))
                throw new InvalidDataException("Common UI ASLR signature self-test failed");
        }
        if(!Equal(ExpectedAt(1,0x460000),Expected[1])) throw new InvalidDataException("Baseline UI signature changed");
        string expected="\nArcane Wars 0.82.1.8\nPaw's Patch 1.3.72-data.8-r2+ui.1";
        if(VersionSuffix("[Versions]\nArcaneWars=0.82.1.8\nPawPatch=1.3.72-data.8-r2+ui.1")!=expected)
            throw new InvalidDataException("UI version metadata self-test failed");
        foreach(string bad in new[]{"", "ArcaneWars=<color=red>\nPawPatch=1", "ArcaneWars=1\nArcaneWars=2\nPawPatch=3"})
        {
            bool rejected=false;
            try { VersionSuffix(bad); } catch(InvalidDataException) { rejected=true; }
            if(!rejected) throw new InvalidDataException("Unsafe UI version metadata accepted");
        }
        return 0;
    }
    static void Write(IntPtr process,IntPtr address,byte[] bytes)
    {
        IntPtr done;
        if(!WriteProcessMemory(process,address,bytes,bytes.Length,out done) || done.ToInt64()!=bytes.Length)
            throw new Win32Exception(Marshal.GetLastWin32Error(),"Write common UI patch");
    }
    static void Patch(IntPtr process,IntPtr address,byte[] bytes)
    {
        uint old,ignored;
        if(!VirtualProtectEx(process,address,bytes.Length,0x40,out old)) throw new Win32Exception();
        try { Write(process,address,bytes); }
        finally { VirtualProtectEx(process,address,bytes.Length,old,out ignored); }
        if(!FlushInstructionCache(process,address,bytes.Length)) throw new Win32Exception();
    }
    public static void Install(IntPtr process,IntPtr image,string logPath)
    {
        VerifyOffline();
        string root=AppDomain.CurrentDomain.BaseDirectory;
        string suffix=VersionSuffix(File.ReadAllText(Path.Combine(root,"paws_patch_versions.ini"),Encoding.UTF8));
        if(!File.Exists(Path.Combine(root,"data","UI","Menus","main.tgi")))
            throw new FileNotFoundException("Missing common UI main menu layout");
        // Steam decrypts code during boot. Validate BOTH sites before any writes.
        var timer=System.Diagnostics.Stopwatch.StartNew();
        for(int i=0;i<Sites.Length;i++)
        {
            while(true)
            {
                byte[] found=new byte[5]; IntPtr done; uint exitCode;
                if(ReadProcessMemory(process,Add(image,Sites[i]),found,5,out done) && done.ToInt64()==5 && Equal(found,ExpectedAt(i,(uint)image.ToInt64()))) break;
                if(timer.ElapsedMilliseconds>60000 || !GetExitCodeProcess(process,out exitCode) || exitCode!=259)
                    throw new InvalidOperationException("Common UI hook signature mismatch; no UI patch applied");
                Thread.Sleep(20);
            }
        }
        IntPtr cave=VirtualAllocEx(process,IntPtr.Zero,Size,0x3000,0x40);
        if(cave==IntPtr.Zero) throw new Win32Exception();
        int attempted=0;
        try
        {
            byte[] payload=Relocate((uint)image.ToInt64(),(uint)cave.ToInt64());
            byte[] label=Encoding.Unicode.GetBytes(suffix+"\0");
            if(label.Length>Size-0x800) throw new InvalidDataException("Version labels too long");
            Buffer.BlockCopy(label,0,payload,0x800,label.Length);
            Write(process,cave,payload);
            if(!FlushInstructionCache(process,cave,Size)) throw new Win32Exception();
            for(int i=0;i<Sites.Length;i++)
            {
                byte[] branch=new byte[5]; branch[0]=(byte)(i==0?0xe8:0xe9);
                int relative=unchecked((int)(cave.ToInt64()+Targets[i]-image.ToInt64()-Sites[i]-5));
                Buffer.BlockCopy(BitConverter.GetBytes(relative),0,branch,1,4);
                attempted=i+1; Patch(process,Add(image,Sites[i]),branch);
            }
            File.AppendAllText(logPath,DateTime.Now.ToString("O")+" COMMON_UI r1; versions="+suffix.Replace('\n',';')+
                "; negativeZero=display-only; allLaunchModes=true; simulationUntouched=true; cave=0x"+cave.ToInt64().ToString("X8")+Environment.NewLine);
        }
        catch
        {
            bool restored=true;
            for(int i=attempted-1;i>=0;i--) try { Patch(process,Add(image,Sites[i]),ExpectedAt(i,(uint)image.ToInt64())); } catch { restored=false; }
            if(restored) VirtualFreeEx(process,cave,0,0x8000);
            throw;
        }
    }
}
