using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

internal static class MenuTests
{
    [DllImport("kernel32.dll")] static extern IntPtr VirtualAlloc(IntPtr at, int size, uint type, uint protection);
    [DllImport("kernel32.dll")] static extern bool VirtualFree(IntPtr at, int size, uint type);
    static int checks;
    static void Check(bool ok, string why) { checks++; if (!ok) throw new Exception(why); }
    static IntPtr Add(IntPtr p,int offset) { return new IntPtr(p.ToInt64()+offset); }
    static int Main(string[] args)
    {
        string root=Path.GetFullPath(args[0]); Directory.CreateDirectory(Path.Combine(root,"data/UI/Menus"));
        File.WriteAllText(Path.Combine(root,"data/UI/Menus/main.tgi"),"self-process test fixture");
        PawGamePresentation.VerifyOffline();
        foreach(string mod in new[]{"vanilla","immortals","arcane-wars"})
        foreach(bool patch in new[]{false,true})
        foreach(string branch in new[]{"stable","beta"})
        {
            if(mod=="vanilla" && !patch) continue;
            string patchVersion=mod=="arcane-wars"?"0.2.0":"0.1.0";
            string metadata="[Versions]\nMod="+mod+"\nModVersion=2.1\n"+(patch?"PawPatch="+patchVersion+"\nPatchChannel="+branch+"\n":"");
            string suffix=PawGamePresentation.VersionSuffix(metadata);
            Check(suffix.Contains("Paw's Patch")==patch,"Disabled patch claimed in menu");
            Check(suffix.Contains("Immortals")== (mod=="immortals"),"Wrong mod name");
            Check(suffix.Contains("Arcane Wars")== (mod=="arcane-wars"),"Wrong AW name");
            Check(!patch || suffix.Contains("Paw's Patch "+patchVersion),"Wrong public patch version");
            Check(!suffix.Contains("(Beta)") && !suffix.Contains("(Release)"),"Menu must show version without a channel suffix");
            File.WriteAllText(Path.Combine(root,"paws_launch_versions.ini"),metadata,Encoding.UTF8);
            IntPtr image=VirtualAlloc(IntPtr.Zero,0x610000,0x3000,0x40); Check(image!=IntPtr.Zero,"Test allocation");
            IntPtr cave=IntPtr.Zero;
            try
            {
                byte[] originalZero={0xE8,0xFB,0xD3,0x1F,0}; Marshal.Copy(originalZero,0,Add(image,0xBF99F),5);
                Marshal.WriteByte(Add(image,0xFA979),0xA1); Marshal.WriteInt32(Add(image,0xFA97A),unchecked(image.ToInt32()+0x5F3FC0));
                // Only this disposable test process is touched. No game is opened or attached.
                using(var current=Process.GetCurrentProcess())
                    PawGamePresentation.InstallMenuOnly(current.Handle,image,Path.Combine(root,"native-menu.log"),root);
                for(int i=0;i<5;i++) Check(Marshal.ReadByte(Add(image,0xBF99F+i))==originalZero[i],"Menu-only path modified negative-zero formatter");
                Check(Marshal.ReadByte(Add(image,0xFA979))==0xE9,"Missing menu jump");
                cave=Add(image,unchecked(0xFA979+5+Marshal.ReadInt32(Add(image,0xFA97A))-0x400));
                Check(Marshal.PtrToStringUni(Add(cave,0x800))==suffix,"Native payload has wrong version label");
            }
            finally { if(cave!=IntPtr.Zero)VirtualFree(cave,0,0x8000); VirtualFree(image,0,0x8000); }
        }
        foreach(string bad in new[]{"Mod=vanilla", "Mod=other\nModVersion=1", "Mod=immortals", "Mod=immortals\nModVersion=<red>", "Mod=vanilla\nPawPatch=1\nPatchChannel=other", "Mod=immortals\nMod=arcane-wars\nModVersion=1"})
        {
            bool rejected=false;try{PawGamePresentation.VersionSuffix(bad);}catch(InvalidDataException){rejected=true;}
            Check(rejected,"Invalid metadata accepted");
        }
        File.WriteAllText(Path.Combine(root,"menu-tests.json"),"{\"passed\":true,\"checks\":"+checks+",\"target\":\"disposable self-process allocations\",\"gameLaunched\":false}");
        Console.WriteLine("MENU NATIVE PASS "+checks+": modes, branches, disabled patch, version strings, actual single-hook installation; no game launch");
        return 0;
    }
}
