using System;
internal static class AllyEconomyPatch {
 internal static void Validate(IMemory m,uint image){
  for(int i=0;i<AllyEconomyPayload.Sites.Length;i++)TerrainPatch.Expect(m,image+AllyEconomyPayload.Sites[i],BitConverter.GetBytes(image+AllyEconomyPayload.Targets[i]));
 }
 internal static uint Install(IMemory m,uint image,Action<string> log){
  Validate(m,image);uint cave=0;int attempted=-1;bool free=true;
  try {
   cave=m.Allocate(AllyEconomyPayload.Allocation);byte[] code=AllyEconomyPayload.Build(image,cave);
   m.Write(cave,code);TerrainPatch.Expect(m,cave,code);
   m.Write(cave+(uint)AllyEconomyPayload.DataOffset,new byte[AllyEconomyPayload.Allocation-AllyEconomyPayload.DataOffset]);
   m.MakeExecutable(cave,AllyEconomyPayload.DataOffset);m.Flush(cave,code.Length);
   for(int i=0;i<AllyEconomyPayload.Sites.Length;i++){
    attempted=i;free=false;byte[] pointer=BitConverter.GetBytes(cave+AllyEconomyPayload.Offsets[i]);
    m.WriteCode(image+AllyEconomyPayload.Sites[i],pointer);TerrainPatch.Expect(m,image+AllyEconomyPayload.Sites[i],pointer);
   }
   log("ALLY_ECONOMY r2; native sliding panel; allied selection only; white numbers; hover forecast priority; UI only; cave=0x"+cave.ToString("X8"));return cave;
  }catch{
   free=true;
   for(int i=attempted;i>=0;i--)try{byte[] b=BitConverter.GetBytes(image+AllyEconomyPayload.Targets[i]);m.WriteCode(image+AllyEconomyPayload.Sites[i],b);TerrainPatch.Expect(m,image+AllyEconomyPayload.Sites[i],b);}catch(Exception e){free=false;log("ALLY_ECONOMY_ROLLBACK_UNCERTAIN "+e.Message);}
   if(cave!=0&&free)m.Free(cave);throw;
  }
 }
}
