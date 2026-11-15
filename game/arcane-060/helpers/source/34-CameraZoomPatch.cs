using System;

internal static class CameraZoomPatch
{
    internal const uint HookRva = 0x175D2D;
    internal static readonly byte[] Original = TerrainPatch.Hex("F30F10870C020000");
    internal static readonly byte[] Guard = TerrainPatch.Hex("558bec51f30f104d0856578bf9f30f10870c0200000f2fc1f30f109710020000f30f118f08020000f30f114508760af30f118708020000eb170f2fcaf30f114d08760df30f119708020000f30f115508");
    internal static void Validate(IMemory memory,uint image)
    {
        TerrainPatch.Expect(memory,image+0x175D20,Guard);
        uint[] methods={0x176FBF,0x177451,0x380640,0x380C80};
        for(int i=0;i<methods.Length;i++)TerrainPatch.Expect(memory,image+0x4C385C+(uint)i*4,BitConverter.GetBytes(image+methods[i]));
    }
    internal static byte[] Jump(uint image,uint cave)
    {
        byte[] b=TerrainPatch.Hex("E900000000909090");
        Buffer.BlockCopy(BitConverter.GetBytes(unchecked(cave-image-HookRva-5)),0,b,1,4);return b;
    }
    internal static uint Install(IMemory memory,uint image,Action<string> log)
    {
        Validate(memory,image);
        uint cave=0;bool attempted=false,safeToFree=true;
        try
        {
            cave=memory.Allocate(4096);byte[] code=CameraZoomPayload.Build(image,cave);
            memory.Write(cave,code);TerrainPatch.Expect(memory,cave,code);
            memory.MakeExecutable(cave,4096);memory.Flush(cave,code.Length);
            byte[] hook=Jump(image,cave);attempted=true;safeToFree=false;
            memory.WriteCode(image+HookRva,hook);TerrainPatch.Expect(memory,image+HookRva,hook);memory.Flush(image+HookRva,hook.Length);
            log("CAMERA_ZOOM r1; gameplayMax=2; gameplayFar=1024; globalFar=unchanged; interfaceCameras=unchanged; polling=none; image=0x"+image.ToString("X8")+" cave=0x"+cave.ToString("X8"));
            return cave;
        }
        catch
        {
            if(attempted)
            {
                try {memory.WriteCode(image+HookRva,Original);TerrainPatch.Expect(memory,image+HookRva,Original);memory.Flush(image+HookRva,Original.Length);safeToFree=true;}
                catch(Exception e){log("CAMERA_ZOOM_ROLLBACK_UNCERTAIN: "+e.Message);}
            }
            if(cave!=0&&safeToFree){try{memory.Free(cave);}catch(Exception e){log("CAMERA_ZOOM_FREE_FAILED: "+e.Message);}}
            throw;
        }
    }
}
