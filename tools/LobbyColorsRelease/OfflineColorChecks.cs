using System;
using System.IO;
using System.Reflection;
using System.Security.Cryptography;
internal static class OfflineColorChecks {
 static int checks;
 static void Check(bool ok,string why){checks++;if(!ok)throw new Exception(why);}
 static int Main(string[] args){try{
  foreach(string folder in new[]{args[0],args[1]})foreach(string path in Directory.GetFiles(folder,"k2_paws_*.exe")){
   Assembly a=Assembly.LoadFile(Path.GetFullPath(path));Type t=a.GetType("PawLobbyColorsNative",true);
   BindingFlags flags=BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Static;
   Type startup=a.GetType("ReleaseStartup",true);
   startup.GetField("GameDataDirectory",flags).SetValue(null,Path.GetFullPath(folder));
   Check((int)t.GetMethod("VerifyOffline",flags).Invoke(null,null)==0,"Compiled offline loader");
   using(Stream s=a.GetManifestResourceStream("PawLobbyColorsPayload"))using(var sha=SHA256.Create()){
    Check(BitConverter.ToString(sha.ComputeHash(s)).Replace("-","")==args[2],"Exact accepted native payload");
   }
   object palette=t.GetMethod("LoadPalette",flags).Invoke(null,null);
   foreach(uint cave in new[]{0x10000000u,0x19000000u}){
    byte[] bytes=(byte[])t.GetMethod("Relocate",flags).Invoke(null,new object[]{0x460000u,cave});
    t.GetMethod("ApplyPalette",flags).Invoke(null,new object[]{bytes,new IntPtr(cave),palette});
    Check(BitConverter.ToInt32(bytes,0x140)==39,"Actual released selectable palette count");
    Check(bytes.Length==0x42000,"Payload size");
    for(int i=0;i<66;i++)Check(bytes[0x3df00+i]==0,"Lifetime buffer stays separate from localized palette data");
   }
  }
  Console.WriteLine("OFFLINE_COLORS_PASS "+checks+" checks; 12 compiled helpers; actual public palettes; two relocations; no games launched");return 0;
 }catch(Exception e){Console.Error.WriteLine(e);return 1;}}
}
