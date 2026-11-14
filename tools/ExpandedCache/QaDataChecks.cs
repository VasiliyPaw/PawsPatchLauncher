using System;
using System.IO;
using System.Reflection;
internal static class QaDataChecks {
 static int Main(string[] args){try{
  Assembly a=Assembly.LoadFile(Path.GetFullPath(args[0]));string root=Path.GetFullPath(args[1]);
  var flags=BindingFlags.Static|BindingFlags.NonPublic;
  Type pure=a.GetType("PawPureFixes.PureBetaRuntime",false);
  if(pure!=null)pure.GetMethod("ValidateInstallation",flags).Invoke(null,new object[]{root});
  else a.GetType("ReleaseStartup",true).GetMethod("VerifyLocalLaunchData",flags).Invoke(null,new object[]{root});
  a.GetType("PawLobbyCompatibility",true).GetMethod("ValidateInstallation",flags).Invoke(null,new object[]{root});
  Console.WriteLine("EXISTING_QA_DATA_PREFLIGHT_PASS "+root+"; actual helper guards; no game launched");return 0;
 }catch(Exception e){Console.Error.WriteLine(e);return 1;}}
}
