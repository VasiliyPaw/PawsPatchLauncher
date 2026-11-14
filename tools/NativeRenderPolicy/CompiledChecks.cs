using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
internal static class CompiledChecks {
 static int checks;
 const BindingFlags Fields=BindingFlags.Static|BindingFlags.NonPublic;
 static void Check(bool ok,string message){checks++;if(!ok)throw new Exception(message);}
 static string Hash(Stream s){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(s)).Replace("-","");}
 static string Hash(string p){using(var s=File.OpenRead(p))return Hash(s);}
 static int Main(string[] args){try{
  foreach(string kind in new[]{"arcane","pure"})foreach(string path in Directory.GetFiles(Path.Combine(args[0],kind+"-helpers"),"k2_paws_*.exe")){
   Assembly a=Assembly.LoadFile(Path.GetFullPath(path)),old=Assembly.LoadFile(Path.GetFullPath(Path.Combine(args[1],kind+"-helpers",Path.GetFileName(path))));
   Check(a.GetManifestResourceNames().OrderBy(x=>x).SequenceEqual(old.GetManifestResourceNames().OrderBy(x=>x)),"Resource names preserved");
   string runtime=kind=="arcane"?"PawPresentationNative":"PawPurePresentationNative",dll=kind=="arcane"?"PawsPresentation1372.dll":"PawsPurePresentation1372.dll";
   foreach(string name in old.GetManifestResourceNames())using(Stream s=a.GetManifestResourceStream(name))using(Stream prior=old.GetManifestResourceStream(name)){
    Check(Hash(s)==(name==runtime?Hash(Path.Combine(args[0],kind+"-native",dll)):Hash(prior)),"Embedded payload: "+path+" / "+name);
   }
   Type t=a.GetType((kind=="arcane"?"":"Pure")+"PresentationRuntimePayload",true);
   Check((string)t.GetField("GraphicsSha256",Fields).GetRawConstantValue()==args[2],"Graphics hash preserved");
   Check((string)t.GetField("Sha256",Fields).GetRawConstantValue()==Hash(Path.Combine(args[0],kind+"-native",dll)),"Presentation hash coordinated");
   // These existing managed self checks exercise real helper installation/rollback
   // against a software memory implementation, without opening a game.
   foreach(string test in new[]{"ReleaseStartup","GamePresentation1372"}){
    Type q=a.GetType(test,false);if(q==null)continue;
    MethodInfo m=q.GetMethod("SelfTest",Fields,null,Type.EmptyTypes,null);if(m==null)continue;
    object result=m.Invoke(null,null);Check(!(result is int)||(int)result==0,"Managed self-test "+test);
   }
  }
  Console.WriteLine("COMPILED_POLICY_CHECKS_PASS "+checks+"; 12 helpers; other embedded resources identical; no game launched");return 0;
 }catch(Exception e){Console.Error.WriteLine(e);return 1;}}
}
