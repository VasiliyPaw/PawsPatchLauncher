using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Web.Script.Serialization;

// Exercise the actually built helpers, without entering their launch code.
internal static class ReleaseLanguageTests
{
    static object Module(string version) { return new Dictionary<string,object> { {"version",version}, {"enabled",true}, {"files",new object[0]} }; }
    static int Main(string[] args)
    {
        int checks=0;
        foreach(string path in Directory.GetFiles(Path.GetFullPath(args[0]),"k2_paws*.exe"))
        {
            var type=Assembly.LoadFile(path).GetType("PawLobbyCompatibility",true);
            string version=(string)type.GetField("Version",BindingFlags.NonPublic|BindingFlags.Static).GetRawConstantValue();
            var method=type.GetMethod("Identity",BindingFlags.NonPublic|BindingFlags.Static);
            var modules=new Dictionary<string,object> { {"arcane-wars",Module("0.82.1.8")}, {"pawpatch-core",Module(version)} };
            var settings=new Dictionary<string,object> { {"mod","arcane-wars"}, {"pawPatchEnabled",true} };
            var state=new Dictionary<string,object> { {"modules",modules}, {"appliedSettings",settings} };
            var json=new JavaScriptSerializer();
            Func<string> token=()=> (string)method.Invoke(null,new object[] {json.Serialize(state),new string('A',64),Path.GetFileName(path),new string('B',64),false});
            string baseline=token();
            foreach(string language in new[]{"ru","uk","cs","de","fr"})
            {
                string id="localization-bot-ui-"+language;modules[id]=Module(version);
                if(token()!=baseline)throw new Exception("Language prevents joining: "+language);
                modules.Remove(id);checks++;
            }
            modules["ai-improvements"]=Module(version);
            if(token()==baseline)throw new Exception("Different AI settings accepted as equal");
            checks++;
        }
        if(checks!=48)throw new Exception("Expected eight helpers");
        Console.WriteLine("RELEASE_LANGUAGE_IDENTITY_PASS "+checks+"; no game launched");return 0;
    }
}
