using System;
using System.Diagnostics;
using System.Linq;

// Reuse the accepted constructor/save-owner and personal herd-relation code.
// This entry never runs the Arcane startup, user-file migration or city assistant.
internal static partial class K2PawFamilyPostgen1372
{
    internal static void InstallPure(Process game, IntPtr image, string log)
    {
        IntPtr process=game.Handle;
        int[] sites={InitialKingdomStoreRva,MaterializedKingdomStoreRva};
        byte[][] signatures={new byte[]{0x89,0x87,0xe8,0,0,0,0x85,0xc0,0x75,0x1d},new byte[]{0x89,0x87,0xe8,0,0,0,0xeb,9}};
        for(int i=0;i<sites.Length;i++)
            if(!ReadBytes(process,Add(image,sites[i]),signatures[i].Length).SequenceEqual(signatures[i]))
                throw new InvalidOperationException("Pure family constructor signature differs.");
        if(!ReadBytes(process,Add(image,KingdomGetRelationRva),6).SequenceEqual(new byte[]{0x8b,0xc1,0x8b,0x4c,0x24,4}))
            throw new InvalidOperationException("Pure personal diplomacy signature differs.");
        IntPtr counters=VirtualAllocEx(process,IntPtr.Zero,CounterCount*4,MemCommit|MemReserve,PageReadWrite);
        if(counters==IntPtr.Zero)ThrowWin32("Pure relation counters");
        WriteBytes(process,counters,new byte[CounterCount*4]);
        InstallPersonalKingdomRelationHook(process,image,counters,IntPtr.Zero,IntPtr.Zero,log);
        for(int i=0;i<sites.Length;i++)
        {
            IntPtr target=Add(image,sites[i]);
            IntPtr stub=VirtualAllocEx(process,IntPtr.Zero,32768,MemCommit|MemReserve,PageExecuteReadWrite);
            if(stub==IntPtr.Zero)ThrowWin32("Pure relation stub");
            byte[] code=BuildFamilyOwnerStub(image,target,signatures[i].Take(6).ToArray(),counters,stub,
                i==0?CounterInitialConstructor:CounterMaterializedConstructor,IntPtr.Zero);
            WriteBytes(process,stub,code);
            if(!FlushInstructionCache(process,stub,code.Length))ThrowWin32("Pure relation cache");
            byte[] detour=new byte[5];detour[0]=0xe9;
            Buffer.BlockCopy(BitConverter.GetBytes(RelativeBranch(target,stub)),0,detour,1,4);
            WriteCodePatch(process,target,detour,"Pure family constructor");
        }
        AppendLog(log,"PURE_FAMILY_RELATIONS savedOwners=preserved; no-user-file-migration; mode-native-families");
    }
}
