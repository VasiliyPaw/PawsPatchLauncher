using System;

// Disable Exhausted. The depleted result uses the ordinary low-morale result.
// Native racial thresholds, low-morale retreat,
// explicit Run, Stun and actual morale values remain unchanged.
internal static class CompanyExhaustionPatch
{
    internal const uint EntryRva = 0x2778C6, UpdateRva = 0x274A1A;
    internal const uint DecisionRva = 0x2147EC;
    internal static readonly byte[] EntryDisabled = TerrainPatch.Hex("B000C39090");
    internal static readonly byte[] UpdateDisabled = TerrainPatch.Hex("B802000000");
    internal static readonly byte[] DecisionOriginal = TerrainPatch.Hex("8BD18B42048B4870");
    // Execute the original routine, preserving its registers/flags. Change only
    // depleted result 0 to low-morale result 1. Existing 1/2 results, thresholds
    // and query side effects stay native, including normal retreat.
    internal const string DecisionCodeHex = "e83b0000009c85c07505b8010000009dc390909090909090909090909090909090909090909090909090909090909090909090909090909090909090909090908bd18b42048b4870e9a74767a0";
    internal static byte[] BuildDecision(uint image,uint cave)
    {
        byte[] code=TerrainPatch.Hex(DecisionCodeHex);
        Array.Copy(BitConverter.GetBytes(unchecked(image+DecisionRva+8-(cave+(uint)code.Length))),0,code,code.Length-4,4);
        return code;
    }
    internal static byte[] DecisionJump(uint image,uint cave)
    {
        byte[] code=TerrainPatch.Hex("E900000000909090");
        Array.Copy(BitConverter.GetBytes(unchecked(cave-(image+DecisionRva+5))),0,code,1,4);
        return code;
    }
    internal static byte[] EntryOriginal(uint image)
    {
        byte[] bytes = new byte[] {0xB8,0,0,0,0};
        Array.Copy(BitConverter.GetBytes(image+0x441276),0,bytes,1,4);
        return bytes;
    }
    internal static void Validate(IMemory memory, uint image)
    {
        TerrainPatch.Expect(memory,image+EntryRva,EntryOriginal(image));
        TerrainPatch.Expect(memory,image+EntryRva+5,TerrainPatch.Hex("E80C9D160051568BF18B4E04"));
        ExhaustionRecoveryPatch.Validate(memory,image);
    }
    internal static void Install(IMemory memory,uint image,Action<string> log)
    {
        Validate(memory,image);
        bool entry=false, update=false, decision=false;
        uint cave=0;bool safeToFree=true;
        try
        {
            cave=memory.Allocate(4096);byte[] code=BuildDecision(image,cave);
            memory.Write(cave,code);TerrainPatch.Expect(memory,cave,code);
            memory.MakeExecutable(cave,4096);memory.Flush(cave,code.Length);
            entry=true; memory.WriteCode(image+EntryRva,EntryDisabled);
            TerrainPatch.Expect(memory,image+EntryRva,EntryDisabled); memory.Flush(image+EntryRva,5);
            update=true; memory.WriteCode(image+UpdateRva,UpdateDisabled);
            TerrainPatch.Expect(memory,image+UpdateRva,UpdateDisabled); memory.Flush(image+UpdateRva,5);
            byte[] jump=DecisionJump(image,cave);decision=true;safeToFree=false;
            memory.WriteCode(image+DecisionRva,jump);
            TerrainPatch.Expect(memory,image+DecisionRva,jump); memory.Flush(image+DecisionRva,jump.Length);
            log("COMPANY_EXHAUSTION r2; zero morale uses low-morale policy; Exhausted disabled; racial retreat thresholds, morale values, explicit Run and Stun preserved");
        }
        catch
        {
            // Attempt every restoration even when an earlier rollback fails.
            if(decision) try { memory.WriteCode(image+DecisionRva,DecisionOriginal); TerrainPatch.Expect(memory,image+DecisionRva,DecisionOriginal); memory.Flush(image+DecisionRva,DecisionOriginal.Length);safeToFree=true; }
                catch(Exception e) { log("MORALE_DECISION_ROLLBACK_UNCERTAIN: "+e.Message); }
            if(update) try { memory.WriteCode(image+UpdateRva,ExhaustionRecoveryPatch.Original); TerrainPatch.Expect(memory,image+UpdateRva,ExhaustionRecoveryPatch.Original); memory.Flush(image+UpdateRva,5); }
                catch(Exception e) { log("EXHAUSTION_UPDATE_ROLLBACK_UNCERTAIN: "+e.Message); }
            if(entry) try { memory.WriteCode(image+EntryRva,EntryOriginal(image)); TerrainPatch.Expect(memory,image+EntryRva,EntryOriginal(image)); memory.Flush(image+EntryRva,5); }
                catch(Exception e) { log("EXHAUSTION_ENTRY_ROLLBACK_UNCERTAIN: "+e.Message); }
            if(cave!=0&&safeToFree)try{memory.Free(cave);}catch(Exception e){log("MORALE_DECISION_FREE_FAILED: "+e.Message);}
            throw;
        }
    }
}
