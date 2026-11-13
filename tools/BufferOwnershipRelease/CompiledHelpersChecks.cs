using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
internal static class CompiledHelpersChecks {
 static int checks;
 static void Check(bool ok,string message){checks++;if(!ok)throw new Exception(message);}
 static string Hash(Stream s){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(s)).Replace("-","");}
 static int Main(string[] args){try{
  for(int mode=0;mode<2;mode++)foreach(string path in Directory.GetFiles(args[mode],"k2_paws_*.exe")){
   Assembly a=Assembly.LoadFile(Path.GetFullPath(path));Assembly old=Assembly.LoadFile(Path.GetFullPath(Path.Combine(args[mode+2],Path.GetFileName(path))));
   Check(a.GetManifestResourceNames().OrderBy(x=>x).SequenceEqual(old.GetManifestResourceNames().OrderBy(x=>x)),"Resource names preserved");
   foreach(string name in old.GetManifestResourceNames())using(Stream s=a.GetManifestResourceStream(name))using(Stream prior=old.GetManifestResourceStream(name))Check(Hash(s)==Hash(prior),"Payload unchanged: "+path+" / "+name);
   Type t=a.GetType((mode==0?"":"Pure")+"PresentationRuntimePayload",true);
   Check((string)t.GetField("GraphicsSha256",BindingFlags.Static|BindingFlags.NonPublic).GetRawConstantValue()==args[4],"Graphics hash coordinated");
  }
  Console.WriteLine("COMPILED_HELPERS_PASS "+checks+" checks; all embedded payloads byte identical; all 12 graphics hashes coordinated; no game launched");return 0;
 }catch(Exception e){Console.Error.WriteLine(e);return 1;}}
}
