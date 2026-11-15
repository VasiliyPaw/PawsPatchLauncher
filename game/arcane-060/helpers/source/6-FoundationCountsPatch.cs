using System;
internal static class FoundationCountsPatch
{
    internal const uint HookRva=0x25839b, GuardRva=0x258389;
    internal static readonly byte[] Original=TerrainPatch.Hex("894630660f6e4328");
    internal static readonly byte[] Guard=TerrainPatch.Hex("d84de88b5e08518b4e04d95de8f30f2c45e8894630660f6e43280f5bc0f30f1145e8f30f104320f30f110424e862daffffd84de8d95de8f30f2c7de8897e34");
    internal static readonly uint[] Sites={HookRva,0x255e09,0x247a27};
    internal static readonly byte[][] Originals={Original,TerrainPatch.Hex("8b4df48ac35f"),TerrainPatch.Hex("e8b579e2ff")};
    internal static void Validate(IMemory memory,uint image){
        TerrainPatch.Expect(memory,image+GuardRva,Guard);
        for(int i=1;i<Sites.Length;i++)TerrainPatch.Expect(memory,image+Sites[i],Originals[i]);
    }
    internal static byte[] Jump(uint image,uint cave){return Jump(image,cave,0);}
    internal static byte[] Jump(uint image,uint cave,int index){
        byte[] b=new byte[Originals[index].Length];for(int i=0;i<b.Length;i++)b[i]=0x90;
        b[0]=(byte)(index==2?0xE8:0xE9);
        Buffer.BlockCopy(BitConverter.GetBytes(unchecked(cave+FoundationCountsPayload.Entries[index]-image-Sites[index]-5)),0,b,1,4);return b;
    }
    internal static uint Install(IMemory memory,uint image,Action<string> log){
        Validate(memory,image);uint cave=0;int attempted=0;bool safeToFree=true;
        try{
            cave=memory.Allocate(FoundationCountsPayload.Allocation);byte[] code=FoundationCountsPayload.Build(image,cave);
            if(code.Length>FoundationCountsPayload.DataOffset)throw new InvalidOperationException("Foundation code overlaps writable state");
            memory.Write(cave,code);TerrainPatch.Expect(memory,cave,code);
            // The planner and selector update FinalPlan after generation. Keep its
            // page-aligned region RW; only the code and constants become RX.
            memory.Write(cave+FoundationCountsPayload.DataOffset,new byte[FoundationCountsPayload.Allocation-(int)FoundationCountsPayload.DataOffset]);
            memory.MakeExecutable(cave,(int)FoundationCountsPayload.DataOffset);memory.Flush(cave,code.Length);
            for(int i=0;i<Sites.Length;i++){
                byte[] hook=Jump(image,cave,i);attempted=i+1;safeToFree=false;
                memory.WriteCode(image+Sites[i],hook);TerrainPatch.Expect(memory,image+Sites[i],hook);memory.Flush(image+Sites[i],hook.Length);
            }
            log("FOUNDATION_COUNTS r2; writableState=true; settlement=80; foundation=20; actualPlacedPool=true; farthestPointSubset=true; rngCallsAdded=0; existingMaps=unchanged; cave=0x"+cave.ToString("X8"));return cave;
        }catch{
            if(attempted>0){safeToFree=true;for(int i=attempted-1;i>=0;i--){
                try{memory.WriteCode(image+Sites[i],Originals[i]);TerrainPatch.Expect(memory,image+Sites[i],Originals[i]);memory.Flush(image+Sites[i],Originals[i].Length);}
                catch(Exception e){safeToFree=false;log("FOUNDATION_COUNTS_ROLLBACK_UNCERTAIN: "+e.Message);}
            }}
            if(cave!=0&&safeToFree){try{memory.Free(cave);}catch(Exception e){log("FOUNDATION_COUNTS_FREE_FAILED: "+e.Message);}}
            throw;
        }
    }
}
