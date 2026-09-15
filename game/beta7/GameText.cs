using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Text;

// Installed with the selected text depot, independently of speech and Windows.
// No file reads occur in the game tick or while changing launcher selections.
internal static class PawGameText
{
    private static readonly Dictionary<string,string> entries=new Dictionary<string,string>(StringComparer.Ordinal);
    internal static readonly string Language=Load();
    private static string Load()
    {
        string root=Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
        string path=Path.Combine(root,"paws_game_text.ini");
        if(!File.Exists(path)) return "";
        string[] lines=File.ReadAllLines(path,Encoding.UTF8);
        if(lines.Length==0 || !lines[0].StartsWith("language=")) throw new InvalidDataException("Invalid game text catalog.");
        string code=lines[0].Substring(9);
        if(Array.IndexOf(new[]{"en","ru","de","fr","cs","uk"},code)<0) throw new InvalidDataException("Invalid game text language.");
        for(int i=1;i<lines.Length;i++)
        {
            if(lines[i].Length==0) continue;
            string[] pair=lines[i].Split('\t');
            if(pair.Length!=2) throw new InvalidDataException("Invalid game text entry.");
            string key=Encoding.UTF8.GetString(Convert.FromBase64String(pair[0]));
            string value=Encoding.UTF8.GetString(Convert.FromBase64String(pair[1]));
            entries.Add(key,value);
        }
        return code;
    }
    internal static string Text(string ru,string en,bool russianFallback)
    {
        string value;
        if(entries.TryGetValue(en,out value))return value;
        return Language=="ru" || Language=="" && russianFallback ? ru : en;
    }
    internal static string Color(string ru,string en)
    {
        string value;
        return entries.TryGetValue("color:"+en,out value)?value:Language=="ru"?ru:en;
    }
    internal static uint LanguageId
    {
        get { int i=Array.IndexOf(new[]{"en","ru","de","fr","cs","uk"},Language);return (uint)Math.Max(0,i); }
    }
}
