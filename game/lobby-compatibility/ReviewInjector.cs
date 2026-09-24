// Local, explicit PID-only review tool. Does not modify game files or settings.
using System;
using System.IO;
using System.Linq;
using System.Diagnostics;
using System.Security.Cryptography;
using System.Runtime.InteropServices;
using System.Text;
class ReviewInjector {
    [DllImport("kernel32",SetLastError=true)]static extern IntPtr OpenProcess(uint access,bool inherit,int pid);
    [DllImport("kernel32",SetLastError=true)]static extern bool CloseHandle(IntPtr h);
    [DllImport("kernel32",SetLastError=true)]static extern bool ReadProcessMemory(IntPtr h,IntPtr a,byte[] b,int n,out IntPtr read);
    [DllImport("kernel32",SetLastError=true)]static extern bool WriteProcessMemory(IntPtr h,IntPtr a,byte[] b,int n,out IntPtr written);
    [DllImport("kernel32",SetLastError=true)]static extern IntPtr VirtualAllocEx(IntPtr h,IntPtr a,int n,uint type,uint protect);
    [DllImport("kernel32",SetLastError=true)]static extern bool VirtualFreeEx(IntPtr h,IntPtr a,int n,uint type);
    [DllImport("kernel32",SetLastError=true)]static extern IntPtr CreateRemoteThread(IntPtr h,IntPtr attr,uint stack,IntPtr fn,IntPtr arg,uint flags,out uint id);
    [DllImport("kernel32",SetLastError=true)]static extern uint WaitForSingleObject(IntPtr h,uint ms);
    [DllImport("kernel32",SetLastError=true)]static extern bool GetExitCodeThread(IntPtr h,out uint code);
    [DllImport("kernel32",CharSet=CharSet.Unicode,SetLastError=true)]static extern IntPtr LoadLibraryEx(string path,IntPtr file,uint flags);
    [DllImport("kernel32",CharSet=CharSet.Ansi,SetLastError=true)]static extern IntPtr GetProcAddress(IntPtr module,string name);
    [DllImport("kernel32")]static extern bool FreeLibrary(IntPtr module);
    [DllImport("kernel32",CharSet=CharSet.Unicode)]static extern IntPtr GetModuleHandle(string name);
    [DllImport("ntdll")]static extern int NtSuspendProcess(IntPtr h);
    [DllImport("ntdll")]static extern int NtResumeProcess(IntPtr h);
    static IntPtr handle;
    static uint U(IntPtr p){return unchecked((uint)p.ToInt32());}
    static IntPtr P(uint p){return new IntPtr(unchecked((int)p));}
    static byte[] Read(uint address,int n){var b=new byte[n];IntPtr done;if(!ReadProcessMemory(handle,P(address),b,n,out done)||done.ToInt32()!=n)throw new Exception("Read failed at "+address.ToString("X8"));return b;}
    static uint U32(uint a){return BitConverter.ToUInt32(Read(a,4),0);}
    static IntPtr Allocate(byte[] data){var p=VirtualAllocEx(handle,IntPtr.Zero,data.Length,0x3000,4);IntPtr n;if(p==IntPtr.Zero||!WriteProcessMemory(handle,p,data,data.Length,out n)||n.ToInt32()!=data.Length)throw new Exception("Remote data allocation failed.");return p;}
    static uint Invoke(uint address,IntPtr data,uint timeout){uint tid;var t=CreateRemoteThread(handle,IntPtr.Zero,0,P(address),data,0,out tid);if(t==IntPtr.Zero)throw new Exception("Thread creation failed.");try{if(WaitForSingleObject(t,timeout)!=0)throw new Exception("Review operation timed out. Close this game before retrying.");uint exit;if(!GetExitCodeThread(t,out exit))throw new Exception("Thread status unavailable.");return exit;}finally{CloseHandle(t);}}
    static string Sha(string path){using(var sha=SHA256.Create())using(var f=File.OpenRead(path))return BitConverter.ToString(sha.ComputeHash(f)).Replace("-","");}
    static ProcessModule Module(Process p,string name){p.Refresh();return p.Modules.Cast<ProcessModule>().Single(m=>m.ModuleName.Equals(name,StringComparison.OrdinalIgnoreCase));}
    static uint ExportRva(IntPtr local,string name){var a=GetProcAddress(local,name);if(a==IntPtr.Zero)a=GetProcAddress(local,"_"+name+"@4");if(a==IntPtr.Zero)throw new Exception("Missing export: "+name);return U(a)-U(local);}
    static readonly uint[] sites={0x151092,0x150e40,0x151c8a,0x1519ef,0x151bf3,0x7d3eb,0x77417};
    static readonly uint[] originals={0x7c92f,0x7c92f,0x149033,0x149046,0x23fb6,0x23ee7,0x77fdc};
    static void Guard(uint image){
        var session=U32(image+0x5f3fe4);if(session<0x10000||U32(session+0xf0)!=0)throw new Exception("Install only in the main menu, outside a lobby or match.");
        for(int i=0;i<sites.Length;i++){var b=Read(image+sites[i],5);var target=unchecked(image+sites[i]+5+BitConverter.ToUInt32(b,1));if(b[0]!=0xe8||target!=image+originals[i])throw new Exception("Native call guard failed: "+sites[i].ToString("X"));}
    }
    static int Main(string[] args){
        try{
            if(IntPtr.Size!=4)throw new Exception("Build this review helper for x86.");
            if(args.Length!=5)throw new Exception("Usage: ReviewInjector.exe inspect|install PID game-directory DLL identity.bin");
            var process=Process.GetProcessById(int.Parse(args[1]));var start=process.StartTime.ToUniversalTime();
            var root=Path.GetFullPath(args[2]).TrimEnd(Path.DirectorySeparatorChar);var exe=Path.Combine(root,"k2.exe");
            if(!process.MainModule.FileName.Equals(exe,StringComparison.OrdinalIgnoreCase))throw new Exception("PID is not the specified game.");
            if(Sha(exe)!="1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45")throw new Exception("Unsupported game executable.");
            var dll=Path.GetFullPath(args[3]);var config=File.ReadAllBytes(args[4]);
            if(config.Length!=264||BitConverter.ToUInt32(config,0)!=0x31434c50)throw new Exception("Invalid review identity.");
            var image=U(process.MainModule.BaseAddress);handle=OpenProcess(0x001F0FFF,false,process.Id);if(handle==IntPtr.Zero)throw new Exception("Cannot open this game.");
            var local=LoadLibraryEx(dll,IntPtr.Zero,1);if(local==IntPtr.Zero)throw new Exception("Cannot read review DLL exports.");
            try{
                Console.WriteLine("PID="+process.Id+" START="+start.ToString("o")+" IMAGE="+image.ToString("X8"));
                Console.WriteLine("IDENTITY="+Encoding.ASCII.GetString(config,8,256).TrimEnd('\0'));
                var loaded=process.Modules.Cast<ProcessModule>().FirstOrDefault(m=>m.FileName.Equals(dll,StringComparison.OrdinalIgnoreCase));
                if(args[0]=="inspect"){
                    var session=U32(image+0x5f3fe4);Console.WriteLine("SESSION="+session.ToString("X8")+" STATE="+(session>=0x10000?U32(session+0xf0).ToString():"none"));
                    if(loaded==null){Console.WriteLine("CHECK_NOT_INSTALLED");Guard(image);return 0;}
                    uint module=U(loaded.BaseAddress);
                    foreach(var name in new[]{"PawLobbyInstallStatus","PawLobbyVersionsSent","PawLobbyRequirementsSent","PawLobbyRequirementsRead","PawLobbyMismatchDialogs"})Console.WriteLine(name+"="+U32(module+ExportRva(local,name)));
                    for(int i=0;i<sites.Length;i++){var b=Read(image+sites[i],5);Console.WriteLine("CALL_"+sites[i].ToString("X")+"="+BitConverter.ToString(b));}return 0;
                }
                if(args[0]!="install"||loaded!=null)throw new Exception("Unknown mode, or check already loaded. Inspect or restart this game.");
                Guard(image);
                // Resolve the actual owner of LoadLibraryW (may be forwarded to KernelBase).
                uint load=U(GetProcAddress(GetModuleHandle("kernel32.dll"),"LoadLibraryW"));
                ProcessModule owner=Process.GetCurrentProcess().Modules.Cast<ProcessModule>().Single(m=>load>=U(m.BaseAddress)&&load<U(m.BaseAddress)+(uint)m.ModuleMemorySize);
                uint remoteLoad=U(Module(process,owner.ModuleName).BaseAddress)+load-U(owner.BaseAddress);
                if(Sha(owner.FileName)!=Sha(Module(process,owner.ModuleName).FileName))throw new Exception("System DLL mismatch.");
                var pathArg=Allocate(Encoding.Unicode.GetBytes(dll+"\0"));
                // Keep the path allocation on timeout; a still-running loader may need it.
                uint remoteModule=Invoke(remoteLoad,pathArg,10000);VirtualFreeEx(handle,pathArg,0,0x8000);
                if(remoteModule==0)throw new Exception("Game could not load the local review DLL.");
                if(process.StartTime.ToUniversalTime()!=start)throw new Exception("Game identity changed.");
                var arg=Allocate(config);bool suspended=false;
                try{
                    if(NtSuspendProcess(handle)!=0)throw new Exception("Cannot suspend game safely.");suspended=true;Guard(image);
                    uint result=Invoke(remoteModule+ExportRva(local,"PawInstall"),arg,5000);
                    Console.WriteLine("INSTALL_RESULT="+result);if(result!=0)throw new Exception("Hook installation refused or rolled back: "+result);
                    for(int i=0;i<sites.Length;i++){var b=Read(image+sites[i],5);if(b[0]!=0xe8)throw new Exception("Readback failed.");uint dest=unchecked(image+sites[i]+5+BitConverter.ToUInt32(b,1));if(dest==image+originals[i])throw new Exception("Call was not installed.");}
                    Console.WriteLine("VERIFIED_FIVE_NATIVE_CALLS");
                    VirtualFreeEx(handle,arg,0,0x8000);
                }finally{if(suspended&&NtResumeProcess(handle)!=0)Console.Error.WriteLine("Game resume failed; close this test game.");}
            }finally{FreeLibrary(local);}
            return 0;
        }catch(Exception ex){Console.Error.WriteLine(ex.Message);return 1;}
        finally{if(handle!=IntPtr.Zero)CloseHandle(handle);}
    }
}
