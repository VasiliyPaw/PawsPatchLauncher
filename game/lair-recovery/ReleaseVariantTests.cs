using System;
using System.IO;
using System.Linq;
using System.Reflection;

// Executes only pure payload/identity methods from each final release assembly.
internal static class ReleaseVariantTests
{
    static int checks;
    static void Check(bool ok,string why){checks++;if(!ok)throw new Exception(why);}
    static byte[] Build(Assembly assembly,uint image,uint cave,string type="LairRecoveryPayload")
    {
        return (byte[])assembly.GetType(type,true).GetMethod("Build",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,new object[]{image,cave});
    }
    static int Main(string[] args)
    {
        try {
            var release=Directory.GetFiles(Path.GetFullPath(args[0]),"k2_paws*.exe");Check(release.Length==8,"Eight release variants");
            var golden=Assembly.LoadFile(Path.GetFullPath(args[1]));string state=File.ReadAllText(args[2]);
            string expected=args.Length>3?args[3]:"0.3.0-beta.9";
            string negativeRoot=Path.Combine(Path.GetDirectoryName(Path.GetFullPath(args[2])),"unsupported-game-fixture");
            Directory.CreateDirectory(negativeRoot);string wrongExe=Path.Combine(negativeRoot,"k2.exe");
            File.WriteAllText(wrongExe,"Unsupported executable; never executed.");
            foreach(string path in release) {
                var a=Assembly.LoadFile(path);var startup=a.GetType("ReleaseStartup",true);var patch=a.GetType("LairRecoveryPatch",true);
                var install=patch.GetMethod("Install",BindingFlags.Static|BindingFlags.NonPublic);
                byte[] il=startup.GetMethod("InstallTerrainAndMap",BindingFlags.Static|BindingFlags.NonPublic).GetMethodBody().GetILAsByteArray();
                byte[] call=new byte[]{0x28}.Concat(BitConverter.GetBytes(install.MetadataToken)).ToArray();
                Check(Enumerable.Range(0,il.Length-call.Length+1).Any(i=>il.Skip(i).Take(call.Length).SequenceEqual(call)),"Native fix called by startup: "+path);
                Check(!a.GetTypes().Any(t=>t.Name.IndexOf("Minimap",StringComparison.OrdinalIgnoreCase)>=0),"No minimap runtime handling");
                Check(startup.GetField("GameDataDirectory",BindingFlags.Static|BindingFlags.NonPublic)==null,"Standalone-only path handling absent");
                foreach(uint image in new uint[]{0x460000,0xE40000,0x12000000})foreach(uint cave in new uint[]{0xD40000,0x60000000})
                    Check(Build(a,image,cave).SequenceEqual(Build(golden,image,cave)),"Accepted r3 native bytes preserved across relocation");
                if(golden.GetType("CameraZoomPayload")!=null) {
                    var camera=a.GetType("CameraZoomPatch",true).GetMethod("Install",BindingFlags.Static|BindingFlags.NonPublic);
                    byte[] cameraCall=new byte[]{0x28}.Concat(BitConverter.GetBytes(camera.MetadataToken)).ToArray();
                    Check(Enumerable.Range(0,il.Length-cameraCall.Length+1).Any(i=>il.Skip(i).Take(cameraCall.Length).SequenceEqual(cameraCall)),"Camera fix called by startup: "+path);
                    foreach(uint image in new uint[]{0x460000,0xE40000,0x12000000})foreach(uint cave in new uint[]{0xD40000,0x60000000})
                        Check(Build(a,image,cave,"CameraZoomPayload").SequenceEqual(Build(golden,image,cave,"CameraZoomPayload")),"Accepted camera payload preserved across relocation");
                }
                if(golden.GetType("CompanyPositionPayload")!=null) {
                    var company=a.GetType("CompanyPositionPatch",true).GetMethod("Install",BindingFlags.Static|BindingFlags.NonPublic);
                    byte[] companyCall=new byte[]{0x28}.Concat(BitConverter.GetBytes(company.MetadataToken)).ToArray();
                    Check(Enumerable.Range(0,il.Length-companyCall.Length+1).Any(i=>il.Skip(i).Take(companyCall.Length).SequenceEqual(companyCall)),"Company recovery called by startup: "+path);
                    foreach(uint image in new uint[]{0x460000,0xE40000,0x12000000})foreach(uint cave in new uint[]{0xD40000,0x60000000})
                        Check(Build(a,image,cave,"CompanyPositionPayload").SequenceEqual(Build(golden,image,cave,"CompanyPositionPayload")),"Accepted company payload preserved across relocation");
                }
                var lobby=a.GetType("PawLobbyCompatibility",true);
                Check((string)lobby.GetField("Version",BindingFlags.Static|BindingFlags.NonPublic).GetRawConstantValue()==expected,"Release identity");
                var identity=lobby.GetMethod("Identity",BindingFlags.Static|BindingFlags.NonPublic);
                var valid=new object[]{state,new string('A',64),Path.GetFileName(path),new string('B',64),false};
                Check(((string)identity.Invoke(null,valid)).Contains("|"+expected+"|"),"Matching installed state");
                bool rejected=false;valid[0]=state.Replace(expected,"0.2.1");
                try{identity.Invoke(null,valid);}catch(TargetInvocationException e){if(e.InnerException is InvalidDataException)rejected=true;else throw;}
                Check(rejected,"Old patch rejected before lobby");
                var verify=a.GetTypes().Select(t=>t.GetMethod("VerifyFiles",BindingFlags.Static|BindingFlags.NonPublic)).Single(m=>m!=null);
                bool wrongGameRejected=false;
                try{verify.Invoke(null,new object[]{negativeRoot,wrongExe});}
                catch(TargetInvocationException e){wrongGameRejected=e.InnerException is InvalidOperationException && e.InnerException.Message.Contains("k2.exe");}
                Check(wrongGameRejected,"Unsupported game executable rejected without launching");
            }
            Console.WriteLine("RELEASE_VARIANTS_PASS "+checks+"; 8 EXEs; accepted r3 bytes; guarded startup calls; version mismatch; no resolution handling; no game launched");return 0;
        }catch(Exception e){Console.Error.WriteLine(e);return 1;}
    }
}
