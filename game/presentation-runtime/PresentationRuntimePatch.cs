using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Threading;

// Called only by the verified fresh-process helper, after its normal patches.
// Loader/thread notifications complete before original threads are suspended.
internal static class PresentationRuntimePatch
{
    static EventWaitHandle readiness;
    internal static void Ready() { if(readiness==null||!readiness.Set())throw new IOException("Cannot signal presentation startup readiness."); }
    static uint U(IntPtr p) { return unchecked((uint)p.ToInt32()); }
    static IntPtr P(uint p) { return new IntPtr(unchecked((int)p)); }
    static string Hash(byte[] b) { using(var h=SHA256.Create()) return BitConverter.ToString(h.ComputeHash(b)).Replace("-", ""); }
    internal static void Install(Process game,IntPtr image,string root,Action<string> log)
    {
        readiness=new EventWaitHandle(false,EventResetMode.ManualReset,"Local\\PawPresentationReady-"+game.Id+"-"+game.StartTime.ToUniversalTime().Ticks);
        byte[] payload;
        using(var s=Assembly.GetExecutingAssembly().GetManifestResourceStream("PawPresentationNative")) {
            if(s==null)throw new IOException("Missing presentation runtime.");
            using(var output=new MemoryStream()){s.CopyTo(output);payload=output.ToArray();}
        }
        if(Hash(payload)!=PresentationRuntimePayload.Sha256)throw new IOException("Presentation runtime integrity check failed.");
        if(ReleaseStartup.Hash(Path.Combine(root,"d3d9.dll"))!=PresentationRuntimePayload.GraphicsSha256)
            throw new IOException("Graphics runtime differs. Apply the patch in the launcher.");
        string folder=Path.Combine(root,".pawpatch","native",PresentationRuntimePayload.Sha256);
        Directory.CreateDirectory(folder);string dll=Path.Combine(folder,"PawsPresentation1372.dll");
        if(!File.Exists(dll)) {
            string temporary=Path.Combine(folder,Guid.NewGuid().ToString("N")+".tmp");
            try {File.WriteAllBytes(temporary,payload);try{File.Move(temporary,dll);}catch(IOException){if(!File.Exists(dll))throw;}}
            finally {if(File.Exists(temporary))File.Delete(temporary);}
        }
        if(ReleaseStartup.Hash(dll)!=PresentationRuntimePayload.Sha256)throw new IOException("Cached presentation runtime differs.");
        using(var installer=new Installer(game,image))installer.Install(dll,root);
        log("PRESENTATION_READY revision=1; minimapZoom=1..4; dayClock=true; reconRevision=26; localFind=true; animationCache=80/100/100; resourcePreparation=bounded; bufferReuse=disabled/native-allocation; gpuPreload=false");
    }
    sealed class Installer:IDisposable
    {
        IntPtr handle;readonly Process game;readonly uint image;readonly DateTime started;
        static readonly uint[] CodeSites={0x5cee6,0xd5000,0xd5785,0x2a4570,0x2a47ee,0x2a43fa,0x2a4430,0x2a4466,0x2a449c,0x206917,0x2069d2,0x22a8c1,0x22ebf0,0x25e75c,0x2b1ae6,0x18e3c8};
        internal Installer(Process p,IntPtr b){game=p;image=U(b);started=p.StartTime.ToUniversalTime();handle=OpenProcess(0x00100c3a,false,p.Id);if(handle==IntPtr.Zero)throw new IOException("Cannot open fresh game for presentation setup.");}
        byte[] Read(uint address,int n){var b=new byte[n];IntPtr done;if(!ReadProcessMemory(handle,P(address),b,n,out done)||done.ToInt32()!=n)throw new IOException("Presentation read failed.");return b;}
        uint Word(uint address){return BitConverter.ToUInt32(Read(address,4),0);}
        void Write(uint address,byte[] b){IntPtr done;if(!WriteProcessMemory(handle,P(address),b,b.Length,out done)||done.ToInt32()!=b.Length||!Read(address,b.Length).SequenceEqual(b))throw new IOException("Presentation write/readback failed.");}
        IntPtr Allocate(byte[] data){var p=VirtualAllocEx(handle,IntPtr.Zero,data.Length,0x3000,4);if(p==IntPtr.Zero)throw new IOException("Presentation allocation failed.");Write(U(p),data);return p;}
        uint Invoke(uint address,IntPtr arg){uint tid;IntPtr thread=CreateRemoteThread(handle,IntPtr.Zero,0,P(address),arg,0,out tid);if(thread==IntPtr.Zero)throw new IOException("Cannot start presentation loader.");try{if(WaitForSingleObject(thread,10000)!=0)throw new IOException("Presentation loader timed out.");uint value;if(!GetExitCodeThread(thread,out value))throw new IOException("Cannot read presentation loader status.");return value;}finally{CloseHandle(thread);}}
        uint Load(string dll)
        {
            uint load=U(GetProcAddress(GetModuleHandle("kernel32.dll"),"LoadLibraryW"));
            var owner=Process.GetCurrentProcess().Modules.Cast<ProcessModule>().Single(m=>load>=U(m.BaseAddress)&&load<U(m.BaseAddress)+(uint)m.ModuleMemorySize);
            game.Refresh();var remote=game.Modules.Cast<ProcessModule>().Single(m=>m.ModuleName.Equals(owner.ModuleName,StringComparison.OrdinalIgnoreCase));
            if(ReleaseStartup.Hash(owner.FileName)!=ReleaseStartup.Hash(remote.FileName))throw new IOException("Presentation system loader identity differs.");
            load=U(remote.BaseAddress)+load-U(owner.BaseAddress);
            IntPtr path=Allocate(Encoding.Unicode.GetBytes(dll+"\0"));
            uint module=Invoke(load,path);VirtualFreeEx(handle,path,0,0x8000);
            if(module==0)throw new IOException("Game could not load presentation runtime.");
            return module;
        }
        void Guard()
        {
            game.Refresh();if(game.HasExited||game.StartTime.ToUniversalTime()!=started||U(game.MainModule.BaseAddress)!=image||ResourceCachePatch.StateAddress==0)
                throw new IOException("Fresh presentation process identity changed.");
            uint cave=ResourceCachePatch.StateAddress-ResourceCachePayload.State;
            if(!Read(cave,ResourceCachePayload.CodeSize).SequenceEqual(ResourceCachePayload.Build(image,cave)))throw new IOException("Resource frame code differs.");
            for(int i=0;i<ResourceCachePayload.Sites.Length;i++) {
                uint site=image+ResourceCachePayload.Sites[i];byte[] b=Read(site,5);
                if(b[0]!=0xe9||unchecked(site+5+BitConverter.ToUInt32(b,1))!=cave+ResourceCachePayload.Entries[i])throw new IOException("Resource frame hook differs.");
            }
            if(Word(ResourceCachePatch.StateAddress+104)!=0)throw new IOException("Presentation runtime was already attached.");
        }
        void CheckThreads(uint worker)
        {
            game.Refresh();foreach(ProcessThread t in game.Threads) {
                if((uint)t.Id==worker)continue;IntPtr thread=OpenThread(0x48,false,(uint)t.Id);if(thread==IntPtr.Zero)throw new IOException("Cannot inspect a paused game thread.");
                IntPtr context=Marshal.AllocHGlobal(716);
                try {
                    Marshal.Copy(new byte[716],0,context,716);Marshal.WriteInt32(context,0x10001);
                    if(!GetThreadContext(thread,context))throw new IOException("Cannot read paused game instruction pointer.");
                    uint pc=unchecked((uint)Marshal.ReadInt32(context,184));
                    if(CodeSites.Any(rva=>pc>=image+rva&&pc<image+rva+5))throw new IOException("Presentation dispatch is currently executing. Retry launch.");
                }finally{Marshal.FreeHGlobal(context);CloseHandle(thread);}
            }
        }
        internal void Install(string dll,string root)
        {
            Guard();uint module=Load(dll);byte[] request=new byte[1068];
            uint manager=Word(image+0x5ef728);if(manager==0)throw new IOException("Game threads are not initialized.");
            uint view=Word(manager+0x48);if(view==0)throw new IOException("VIEW thread is not initialized.");
            foreach(string p in new[]{root,Path.Combine(root,"Mods")})if(p.Length>=260)throw new IOException("Presentation game path is too long.");
            BitConverter.GetBytes(1u).CopyTo(request,12);BitConverter.GetBytes(image).CopyTo(request,16);BitConverter.GetBytes(view).CopyTo(request,20);BitConverter.GetBytes(0x50574150u).CopyTo(request,24);
            Encoding.Unicode.GetBytes(root+"\0").CopyTo(request,28);Encoding.Unicode.GetBytes(Path.Combine(root,"Mods")+"\0").CopyTo(request,548);
            IntPtr arg=Allocate(request);uint tid;IntPtr worker=CreateRemoteThread(handle,IntPtr.Zero,0,P(module+PresentationRuntimePayload.QueuedRva),arg,0,out tid);
            if(worker==IntPtr.Zero)throw new IOException("Cannot queue presentation setup.");bool suspended=false;
            try {
                var timer=Stopwatch.StartNew();
                while(Word(U(arg)+4)!=1){if(game.HasExited||WaitForSingleObject(worker,0)==0||timer.ElapsedMilliseconds>10000)throw new IOException("Presentation worker did not initialize. Code="+Word(U(arg)+8));Thread.Sleep(10);}
                if(NtSuspendProcess(handle)!=0)throw new IOException("Cannot pause fresh game for presentation setup.");suspended=true;
                Guard();CheckThreads(tid);
                // DLL notifications and loader work already finished; only this worker runs.
                if(ResumeThread(worker)!=1)throw new IOException("Unexpected presentation worker suspend count.");
                Write(U(arg),BitConverter.GetBytes(1));timer.Restart();
                while(Word(U(arg)+4)!=2){if(WaitForSingleObject(worker,0)==0||timer.ElapsedMilliseconds>5000)throw new IOException("Presentation installation did not complete.");Thread.Sleep(1);}
                uint result=Word(U(arg)+8);if(result!=0)throw new IOException("Presentation installation declined. Code="+result);
                Write(ResourceCachePatch.StateAddress+104,BitConverter.GetBytes(module+PresentationRuntimePayload.FrameRva));
                VirtualFreeEx(handle,arg,0,0x8000);
            }finally {if(suspended&&NtResumeProcess(handle)!=0)throw new IOException("Cannot resume fresh game after presentation setup.");CloseHandle(worker);}
        }
        public void Dispose(){if(handle!=IntPtr.Zero){CloseHandle(handle);handle=IntPtr.Zero;}}
    }
    [DllImport("kernel32")]static extern IntPtr OpenProcess(uint access,bool inherit,int pid);
    [DllImport("kernel32")]static extern IntPtr OpenThread(uint access,bool inherit,uint tid);
    [DllImport("kernel32")]static extern bool GetThreadContext(IntPtr thread,IntPtr context);
    [DllImport("kernel32")]static extern bool CloseHandle(IntPtr h);
    [DllImport("kernel32")]static extern bool ReadProcessMemory(IntPtr h,IntPtr a,byte[] b,int n,out IntPtr read);
    [DllImport("kernel32")]static extern bool WriteProcessMemory(IntPtr h,IntPtr a,byte[] b,int n,out IntPtr written);
    [DllImport("kernel32")]static extern IntPtr VirtualAllocEx(IntPtr h,IntPtr a,int n,uint type,uint protect);
    [DllImport("kernel32")]static extern bool VirtualFreeEx(IntPtr h,IntPtr a,int n,uint type);
    [DllImport("kernel32")]static extern IntPtr CreateRemoteThread(IntPtr h,IntPtr attr,uint stack,IntPtr fn,IntPtr arg,uint flags,out uint id);
    [DllImport("kernel32")]static extern uint WaitForSingleObject(IntPtr h,uint ms);
    [DllImport("kernel32")]static extern uint ResumeThread(IntPtr h);
    [DllImport("kernel32")]static extern bool GetExitCodeThread(IntPtr h,out uint code);
    [DllImport("kernel32",CharSet=CharSet.Ansi)]static extern IntPtr GetProcAddress(IntPtr m,string name);
    [DllImport("kernel32",CharSet=CharSet.Unicode)]static extern IntPtr GetModuleHandle(string name);
    [DllImport("ntdll")]static extern int NtSuspendProcess(IntPtr h);
    [DllImport("ntdll")]static extern int NtResumeProcess(IntPtr h);
}
