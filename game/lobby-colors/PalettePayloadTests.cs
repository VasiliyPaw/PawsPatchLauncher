using System;
using System.IO;
using System.Reflection;
using System.Text;
using System.Collections.Generic;
using System.Web.Script.Serialization;

// Pure compiled-loader checks. Never calls Install or opens the game.
internal static class PalettePayloadTests
{
    static int checks;
    const BindingFlags PrivateStatic=BindingFlags.NonPublic|BindingFlags.Static;
    static void Check(bool ok,string reason){checks++;if(!ok)throw new Exception(reason);}
    static string StringAt(byte[] bytes,int offset){int end=offset;while(bytes[end]!=0||bytes[end+1]!=0)end+=2;return Encoding.Unicode.GetString(bytes,offset,end-offset);}
    static int Main(string[] args)
    {
        try {
            var expected=new JavaScriptSerializer().Deserialize<Dictionary<string,object>>(File.ReadAllText(args[1]));
            int required=args.Length>2?Int32.Parse(args[2]):8;
            var files=Directory.GetFiles(Path.GetFullPath(args[0]),required==2?"k2_paws_pure_colors*.exe":"k2_paws*.exe");Check(files.Length==required,"Unexpected assembly count");
            foreach(var file in files) {
                var assembly=Assembly.LoadFile(file);var colors=assembly.GetType("PawLobbyColorsNative",true);
                var text=assembly.GetType("PawGameText",true);
                var entries=(Dictionary<string,string>)text.GetField("entries",PrivateStatic).GetValue(null);
                foreach(var language in expected) {
                    var rows=(System.Collections.IList)language.Value;entries.Clear();
                    foreach(Dictionary<string,object> row in rows)entries.Add("color:"+(string)row["en"],(string)row["name"]);
                    var palette=colors.GetMethod("LoadPalette",PrivateStatic).Invoke(null,null);
                    foreach(uint cave in new uint[]{0x10000000,0x19000000}) {
                        var bytes=(byte[])colors.GetMethod("Relocate",PrivateStatic).Invoke(null,new object[]{(uint)0x460000,cave});
                        colors.GetMethod("ApplyPalette",PrivateStatic).Invoke(null,new object[]{bytes,new IntPtr(cave),palette});
                        Check(BitConverter.ToInt32(bytes,0x140)==39,"Managed palette count");
                        int visible=0;
                        foreach(Dictionary<string,object> row in rows) {
                            int nameOffset;
                            if((bool)row["visible"]) {
                                int entry=0x1400+visible++*20;
                                Check(StringAt(bytes,(int)(BitConverter.ToUInt32(bytes,entry)-cave))==(string)row["id"],"Stable ID/order");
                                var rgb=(System.Collections.IList)row["rgb"];
                                for(int channel=0;channel<3;channel++)Check(Math.Abs(BitConverter.ToSingle(bytes,entry+8+channel*4)-Convert.ToInt32(rgb[channel])/255.0f)<0.000001,"Stable RGB");
                                nameOffset=entry+4;
                            } else nameOffset=Convert.ToInt32(row["name_pointer"]);
                            Check(StringAt(bytes,(int)(BitConverter.ToUInt32(bytes,nameOffset)-cave))==(string)row["name"],"Localized visible/retired name: "+language.Key+" "+row["id"]);
                        }
                        Check(visible==39,"All visible entries checked");
                    }
                }
            }
            Console.WriteLine("PALETTE_PAYLOAD_PASS "+checks+" checks; "+required+" compiled loaders, 6 languages, 2 address layouts; no game launched");return 0;
        } catch(Exception e){Console.Error.WriteLine(e);return 1;}
    }
}
