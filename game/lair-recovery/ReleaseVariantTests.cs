using System;
using System.IO;
using System.Linq;
using System.Reflection;

// Executes only pure payload/identity methods from each final release assembly.
internal static class ReleaseVariantTests
{
    static int checks;
    static void Check(bool ok,string why){checks++;if(!ok)throw new Exception(why);}
    static byte[] Build(Assembly assembly,uint image,uint cave)
    {
        return (byte[])assembly.GetType("LairRecoveryPayload",true).GetMethod("Build",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,new object[]{image,cave});
    }
    static int Main(string[] args)
    {
        try {
            var release=Directory.GetFiles(Path.GetFullPath(args[0]),"k2_paws*.exe");Check(release.Length==8,"Eight release variants");
            var golden=Assembly.LoadFile(Path.GetFullPath(args[1]));string state=File.ReadAllText(args[2]);
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
                var lobby=a.GetType("PawLobbyCompatibility",true);
                Check((string)lobby.GetField("Version",BindingFlags.Static|BindingFlags.NonPublic).GetRawConstantValue()=="0.3.0-beta.9","Release identity");
                var identity=lobby.GetMethod("Identity",BindingFlags.Static|BindingFlags.NonPublic);
                var valid=new object[]{state,new string('A',64),Path.GetFileName(path),new string('B',64),false};
                Check(((string)identity.Invoke(null,valid)).Contains("|0.3.0-beta.9|"),"Matching installed state");
                bool rejected=false;valid[0]=state.Replace("0.3.0-beta.9","0.3.0-beta.8");
                try{identity.Invoke(null,valid);}catch(TargetInvocationException e){if(e.InnerException is InvalidDataException)rejected=true;else throw;}
                Check(rejected,"Old patch rejected before lobby");
            }
            Console.WriteLine("RELEASE_VARIANTS_PASS "+checks+"; 8 EXEs; accepted r3 bytes; guarded startup calls; version mismatch; no resolution handling; no game launched");return 0;
        }catch(Exception e){Console.Error.WriteLine(e);return 1;}
    }
}
