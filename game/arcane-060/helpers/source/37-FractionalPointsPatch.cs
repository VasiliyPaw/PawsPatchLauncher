using System;
using System.Collections.Generic;

internal static class FractionalPointsPatch
{
    internal static readonly uint[] Sites={0x2BCDF6,0x2BCE93,0x2BCD2B};
    internal static readonly uint[] Formats={0x483DDC,0x5075D4,0x5075AC};
    internal static byte[] Original(uint image,int i)
    {
        byte[] b=new byte[i==0?7:5];
        if(i==0){b[0]=0xC7;b[1]=4;b[2]=0x24;}else b[0]=0x68;
        Buffer.BlockCopy(BitConverter.GetBytes(image+Formats[i]),0,b,b.Length-4,4);return b;
    }
    internal static void Validate(IMemory m,uint image)
    {for(int i=0;i<Sites.Length;i++)TerrainPatch.Expect(m,image+Sites[i],Original(image,i));}
    internal static uint Install(IMemory m,uint image,Action<string> log)
    {
        Validate(m,image);uint cave=0;var attempted=new List<int>();bool safe=true;
        try
        {
            cave=m.Allocate(4096);byte[] code=FractionalPointsPayload.Build(image,cave);
            m.Write(cave,code);TerrainPatch.Expect(m,cave,code);m.MakeExecutable(cave,4096);m.Flush(cave,code.Length);
            for(int i=0;i<Sites.Length;i++)
            {
                byte[] b=Original(image,i);for(int k=0;k<b.Length;k++)b[k]=0x90;
                byte[] j=TerrainPatch.Call(image+Sites[i],cave+(uint)(i*0x200));j[0]=0xE9;Buffer.BlockCopy(j,0,b,0,5);
                attempted.Add(i);m.WriteCode(image+Sites[i],b);TerrainPatch.Expect(m,image+Sites[i],b);m.Flush(image+Sites[i],b.Length);
            }
            log("FRACTIONAL_KINGDOM_POINTS r1; top-bar and limited-resource tooltips; display only");return cave;
        }
        catch
        {
            foreach(int i in attempted)
                try{byte[] b=Original(image,i);m.WriteCode(image+Sites[i],b);TerrainPatch.Expect(m,image+Sites[i],b);m.Flush(image+Sites[i],b.Length);}
                catch(Exception e){safe=false;log("FRACTIONAL_POINTS_ROLLBACK_UNCERTAIN "+e.Message);}
            if(cave!=0&&safe)try{m.Free(cave);}catch(Exception e){log("FRACTIONAL_POINTS_FREE_FAILED "+e.Message);}
            throw;
        }
    }
}
