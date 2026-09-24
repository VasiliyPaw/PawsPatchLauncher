using System;
using System.IO;

internal static class BotLobbyPatch {
    internal static void Validate(IMemory m,uint image){
        for(int i=0;i<BotLobbyPayload.Sites.Length;i++)TerrainPatch.Expect(m,image+BotLobbyPayload.Sites[i]-3,TerrainPatch.Hex(BotLobbyPayload.Guards[i]));
    }
    internal static uint Install(IMemory m,uint image,uint language,Action<string> log){
        return Install(m,image,language,false,log);
    }
    internal static uint Install(IMemory m,uint image,uint language,bool nightmareDefault,Action<string> log){
        Validate(m,image);uint cave=0;int attempted=-1;bool free=true;
        try {
            cave=m.Allocate(BotLobbyPayload.Allocation);var code=BotLobbyPayload.Build(image,cave);
            m.Write(cave,code);TerrainPatch.Expect(m,cave,code);
            var data=new byte[BotLobbyPayload.Allocation-BotLobbyPayload.DataOffset];
            Buffer.BlockCopy(BitConverter.GetBytes(language),0,data,4,4);
            Buffer.BlockCopy(BitConverter.GetBytes(nightmareDefault?1u:0u),0,data,32+3*36+3*4+64*24,4);
            m.Write(cave+(uint)BotLobbyPayload.DataOffset,data);m.MakeExecutable(cave,BotLobbyPayload.DataOffset);m.Flush(cave,code.Length);
            for(int i=0;i<BotLobbyPayload.Sites.Length;i++){
                attempted=i;free=false;var call=TerrainPatch.Call(image+BotLobbyPayload.Sites[i],cave+BotLobbyPayload.Offsets[i]);
                m.WriteCode(image+BotLobbyPayload.Sites[i],call);TerrainPatch.Expect(m,image+BotLobbyPayload.Sites[i],call);m.Flush(image+BotLobbyPayload.Sites[i],5);
            }
            log("BOT_LOBBY r2; participant difficulty persistence; nightmareDefault="+nightmareDefault+"; saved games excluded; cave=0x"+cave.ToString("X8"));return cave;
        }catch{
            free=true;
            for(int i=attempted;i>=0;i--)try{var bytes=TerrainPatch.Hex(BotLobbyPayload.Originals[i]);m.WriteCode(image+BotLobbyPayload.Sites[i],bytes);TerrainPatch.Expect(m,image+BotLobbyPayload.Sites[i],bytes);m.Flush(image+BotLobbyPayload.Sites[i],5);}catch(Exception e){free=false;log("BOT_LOBBY_ROLLBACK_UNCERTAIN: "+e.Message);}
            if(cave!=0&&free)m.Free(cave);throw;
        }
    }
}
