using System;

internal static class LairRecoveryPatch
{
    internal static readonly uint[] Sites=LairRecoveryPayload.Sites;
    internal static readonly uint[] Offsets=LairRecoveryPayload.Offsets;
    internal static readonly byte[][] Originals=LairRecoveryPayload.Originals;
    internal static byte[] Jump(uint site,uint target,int length)
    {
        byte[] result=new byte[length];for(int i=0;i<length;i++)result[i]=0x90;
        result[0]=0xE9;Buffer.BlockCopy(BitConverter.GetBytes(unchecked(target-site-5)),0,result,1,4);return result;
    }
    internal static void Validate(IMemory memory,uint image)
    {
        for(int i=0;i<Sites.Length;i++)TerrainPatch.Expect(memory,image+Sites[i],Originals[i]);
        LairRecoveryPayload.ValidateOriginalFunctions(memory,image);
        TerrainPatch.Expect(memory,image+0x212019,TerrainPatch.Hex("6A1958C3"));
        TerrainPatch.Expect(memory,image+0x4E17AC+0x18,BitConverter.GetBytes(image+0x212019));
        TerrainPatch.Expect(memory,image+0x22E158,TerrainPatch.Hex("89749F60"));
        TerrainPatch.Expect(memory,image+0x22E16D+0x19*4,BitConverter.GetBytes(image+0x22E088));
    }
    internal static uint Install(IMemory memory,uint image,Action<string> log)
    {
        Validate(memory,image);
        uint cave=0;int attempted=-1;bool safeToFree=true;
        try
        {
            cave=memory.Allocate(4096);
            byte[] code=LairRecoveryPayload.Build(image,cave);
            memory.Write(cave,code);TerrainPatch.Expect(memory,cave,code);
            memory.MakeExecutable(cave,4096);memory.Flush(cave,code.Length);
            for(int i=0;i<Sites.Length;i++)
            {
                byte[] hook=Jump(image+Sites[i],cave+Offsets[i],Originals[i].Length);
                attempted=i;safeToFree=false;
                memory.WriteCode(image+Sites[i],hook);TerrainPatch.Expect(memory,image+Sites[i],hook);
                memory.Flush(image+Sites[i],hook.Length);
            }
            log("LAIR_WOUNDED r3; scope=KKC_LairComponent; ready=fullHP_or_returnedAlive; dead=waitFullHP; loadUnknown=waitFullHP; deploymentHP=storedFraction; nativeHealing=unchanged; saveFormat=unchanged; savedOwners=unchanged; image=0x"+image.ToString("X8")+" cave=0x"+cave.ToString("X8"));
            return cave;
        }
        catch
        {
            if(attempted>=0)
            {
                safeToFree=true;
                for(int i=attempted;i>=0;i--)
                {
                    try
                    {
                        memory.WriteCode(image+Sites[i],Originals[i]);TerrainPatch.Expect(memory,image+Sites[i],Originals[i]);
                        memory.Flush(image+Sites[i],Originals[i].Length);
                    }
                    catch(Exception error){safeToFree=false;log("LAIR_WOUNDED_ROLLBACK_UNCERTAIN: "+error.Message);}
                }
                if(safeToFree)log("LAIR_WOUNDED_ROLLBACK_VERIFIED");
            }
            if(cave!=0 && safeToFree){try{memory.Free(cave);}catch(Exception error){log("LAIR_RECOVERY_FREE_FAILED: "+error.Message);}}
            throw;
        }
    }
}
