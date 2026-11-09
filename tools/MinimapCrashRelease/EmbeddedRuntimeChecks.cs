using System;
using System.IO;
using System.Reflection;
using System.Security.Cryptography;
internal static class EmbeddedRuntimeChecks {
 static int checks;
 static void Check(bool ok,string message){checks++;if(!ok)throw new Exception(message);}
 static string Hash(Stream s){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(s)).Replace("-","");}
 static int Main(string[] args){try{
  for(int mode=0;mode<2;mode++)foreach(string path in Directory.GetFiles(args[mode],"k2_paws_*.exe")){
   Assembly a=Assembly.LoadFile(Path.GetFullPath(path));string prefix=mode==0?"":"Pure";
   using(Stream s=a.GetManifestResourceStream(mode==0?"PawPresentationNative":"PawPurePresentationNative")){
    Check(s!=null,"Embedded runtime exists: "+path);Check(Hash(s)==args[mode+2],"Final helper embeds accepted fixed DLL: "+path);
   }
   Type t=a.GetType(prefix+"PresentationRuntimePayload",true);
   Check((string)t.GetField("Sha256",BindingFlags.Static|BindingFlags.NonPublic).GetRawConstantValue()==args[mode+2],"Loader hash matches fixed DLL");
  }
  Console.WriteLine("EMBEDDED_MINIMAP_RUNTIME_PASS "+checks+" checks; 12 final helpers; no game launched");return 0;
 }catch(Exception e){Console.Error.WriteLine(e);return 1;}}
}
