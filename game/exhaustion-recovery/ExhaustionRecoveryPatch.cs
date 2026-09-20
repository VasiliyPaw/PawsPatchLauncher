using System;

internal static class ExhaustionRecoveryPatch
{
    internal const uint HookRva=0x274A1A;
    internal static readonly byte[] Original=TerrainPatch.Hex("E8CDFDF9FF");
    internal static readonly byte[] Guard=TerrainPatch.Hex("8b487ce8cdfdf9ff8b4e045e83f8020f84fe2e000083c1348b01ff6010");
    internal static readonly byte[] DecisionGuard=TerrainPatch.Hex("8bd18b42048b487085c9740c83792800753883792c0075320f57c00f2f42607329f30f104a5c0f2f8ab8000000771b0f2ec89ff6c4447b0f8b01ff505c33c984c00f94c18bc1c333c0c36a0258c3");
    internal static void Validate(IMemory memory,uint image)
    {
        TerrainPatch.Expect(memory,image+HookRva-3,Guard);
        TerrainPatch.Expect(memory,image+0x2147EC,DecisionGuard);
    }
    internal static byte[] Jump(uint image,uint cave) {return TerrainPatch.Call(image+HookRva,cave);}
    internal static uint Install(IMemory memory,uint image,Action<string> log)
    {
        Validate(memory,image);
        uint cave=0;bool attempted=false,safeToFree=true;
        try
        {
            cave=memory.Allocate(8192);byte[] code=ExhaustionRecoveryPayload.Build(image,cave);
            memory.Write(cave,code);TerrainPatch.Expect(memory,cave,code);
            // Code stays RX; diagnostic counters occupy a separate RW page.
            memory.Write(cave+0x1000,new byte[8]);TerrainPatch.Expect(memory,cave+0x1000,new byte[8]);
            memory.MakeExecutable(cave,4096);memory.Flush(cave,code.Length);
            byte[] hook=Jump(image,cave);attempted=true;safeToFree=false;
            memory.WriteCode(image+HookRva,hook);TerrainPatch.Expect(memory,image+HookRva,hook);memory.Flush(image+HookRva,hook.Length);
            log("EXHAUSTION_RECOVERY r1; fully recovered lowered morale cap; Exhausted only; no morale writes; image=0x"+image.ToString("X8")+" cave=0x"+cave.ToString("X8"));
            return cave;
        }
        catch
        {
            if(attempted)
            {
                try {memory.WriteCode(image+HookRva,Original);TerrainPatch.Expect(memory,image+HookRva,Original);memory.Flush(image+HookRva,Original.Length);safeToFree=true;}
                catch(Exception e){log("EXHAUSTION_RECOVERY_ROLLBACK_UNCERTAIN: "+e.Message);}
            }
            if(cave!=0&&safeToFree){try{memory.Free(cave);}catch(Exception e){log("EXHAUSTION_RECOVERY_FREE_FAILED: "+e.Message);}}
            throw;
        }
    }
}
