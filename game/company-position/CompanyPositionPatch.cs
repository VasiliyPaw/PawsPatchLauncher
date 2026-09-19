using System;

internal static class CompanyPositionPatch
{
    internal const uint HookRva=0x218666;
    internal static readonly byte[] Original=TerrainPatch.Hex("E868C2FFFF");
    internal static readonly byte[] Guard=TerrainPatch.Hex("8BCEE868C2FFFF84C0750AFF76408BCE");
    internal static readonly byte[] CallbackGuard=TerrainPatch.Hex("568BF1E87CF8FFFF84C0740C6A016A008D4E08E87E9A07005EC20400");
    internal static readonly byte[] InsertGuard=TerrainPatch.Hex("83C104568B7424088B01894E0C8D561085C075048902EB098B0189028B0189500C89315EC20400");
    internal static void Validate(IMemory memory,uint image)
    {
        TerrainPatch.Expect(memory,image+HookRva-2,Guard);
        TerrainPatch.Expect(memory,image+0x218885,CallbackGuard);
        TerrainPatch.Expect(memory,image+0x2925E6,InsertGuard);
    }
    internal static byte[] Jump(uint image,uint cave) {return TerrainPatch.Call(image+HookRva,cave);}
    internal static uint Install(IMemory memory,uint image,Action<string> log)
    {
        Validate(memory,image);
        uint cave=0;bool attempted=false,safeToFree=true;
        try
        {
            cave=memory.Allocate(8192);byte[] code=CompanyPositionPayload.Build(image,cave);
            memory.Write(cave,code);TerrainPatch.Expect(memory,cave,code);
            // Code stays RX; diagnostic counters occupy a separate RW page.
            memory.Write(cave+0x1000,new byte[12]);TerrainPatch.Expect(memory,cave+0x1000,new byte[12]);
            memory.MakeExecutable(cave,4096);memory.Flush(cave,code.Length);
            byte[] hook=Jump(image,cave);attempted=true;safeToFree=false;
            memory.WriteCode(image+HookRva,hook);TerrainPatch.Expect(memory,image+HookRva,hook);memory.Flush(image+HookRva,hook.Length);
            log("COMPANY_POSITION r1; native-position-event recovery; hero-independent; no position writes; image=0x"+image.ToString("X8")+" cave=0x"+cave.ToString("X8"));
            return cave;
        }
        catch
        {
            if(attempted)
            {
                try {memory.WriteCode(image+HookRva,Original);TerrainPatch.Expect(memory,image+HookRva,Original);memory.Flush(image+HookRva,Original.Length);safeToFree=true;}
                catch(Exception e){log("COMPANY_POSITION_ROLLBACK_UNCERTAIN: "+e.Message);}
            }
            if(cave!=0&&safeToFree){try{memory.Free(cave);}catch(Exception e){log("COMPANY_POSITION_FREE_FAILED: "+e.Message);}}
            throw;
        }
    }
}
