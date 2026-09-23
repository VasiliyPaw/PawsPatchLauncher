using System;
using System.Diagnostics;
using System.Runtime.InteropServices;

// Use the production allocator/protection code in this isolated x86 process.
// No game process is opened. The empty world takes the real planner's reset path.
internal static class FoundationNativeMemoryTests
{
    [StructLayout(LayoutKind.Sequential)]
    private struct Mbi { internal uint Base, AllocationBase, AllocationProtect, Size, State, Protect, Type; }
    [DllImport("kernel32.dll",SetLastError=true)]
    private static extern UIntPtr VirtualQuery(IntPtr address,out Mbi info,UIntPtr size);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    private delegate void Planner(uint image,uint data,uint success);
    internal static int Main(string[] args)
    {
        if(IntPtr.Size!=4||args.Length!=1)throw new Exception("Requires x86 and generated plan_map offset");
        int checks=0;uint image=0,cave=0;
        using(var m=new NativeMemory(Process.GetCurrentProcess().Id))
        try{
            image=m.Allocate(0x600000);
            m.Write(image+FoundationCountsPatch.GuardRva,FoundationCountsPatch.Guard);
            for(int i=1;i<FoundationCountsPatch.Sites.Length;i++)m.Write(image+FoundationCountsPatch.Sites[i],FoundationCountsPatch.Originals[i]);
            m.MakeExecutable(image,0x260000);
            cave=FoundationCountsPatch.Install(m,image,delegate{});
            for(uint off=0;off<FoundationCountsPayload.Allocation;off+=4096){
                Mbi info;
                if(VirtualQuery(new IntPtr(unchecked((int)(cave+off))),out info,new UIntPtr(28)).ToUInt32()!=28)throw new Exception("VirtualQuery failed");
                if(info.Protect!=(off<FoundationCountsPayload.DataOffset?0x20u:0x04u))throw new Exception("Incorrect real Windows protection");
                checks++;
            }
            var run=(Planner)Marshal.GetDelegateForFunctionPointer(new IntPtr(unchecked((int)(cave+uint.Parse(args[0])))),typeof(Planner));
            foreach(uint success in new uint[]{0,1}){
                m.Write(cave+FoundationCountsPayload.DataOffset+4,BitConverter.GetBytes(123));
                run(image,cave+FoundationCountsPayload.DataOffset,success);
                if(BitConverter.ToUInt32(m.Read(cave+FoundationCountsPayload.DataOffset+4,4),0)!=0)throw new Exception("Planner did not reset readiness");
                checks++;
                if(BitConverter.ToUInt32(m.Read(cave+FoundationCountsPayload.DataOffset+24,4),0)!=2)throw new Exception("Planner did not execute revision write");
                checks++;
            }
        }finally{if(cave!=0)m.Free(cave);if(image!=0)m.Free(image);}
        Console.WriteLine("PASS "+checks+" real Windows memory/procedure checks; only this isolated test process.");return 0;
    }
}
