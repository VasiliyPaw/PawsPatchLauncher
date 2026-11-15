using System;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;

// Local preferences. Save files and network packets are never modified.
// Content-addressed bindings survive renamed/copied saves and never confuse
// two different parties which reuse the same save filename.
internal sealed class CityPartySettings
{
    internal bool Enabled = true;
    internal uint Reserve = 2000;
    internal float[] Floors = new float[5];
    internal string Encode()
    {
        return "1\n"+(Enabled?"1":"0")+"\n"+Reserve+"\n"+
            string.Join("\n",Floors.Skip(1).Select(v=>v.ToString(CultureInfo.InvariantCulture)).ToArray())+"\n";
    }
    internal static CityPartySettings Decode(string text)
    {
        string[] lines=text.Replace("\r","").TrimEnd('\n').Split('\n');
        uint reserve;
        if(lines.Length!=7 || lines[0]!="1" || (lines[1]!="0" && lines[1]!="1") ||
            !uint.TryParse(lines[2],out reserve) || reserve>9999999)
            throw new InvalidDataException("Invalid city party preferences.");
        var result=new CityPartySettings {Enabled=lines[1]=="1",Reserve=reserve};
        for(int i=1;i<5;i++)
        {
            float value;
            if(!float.TryParse(lines[i+2],NumberStyles.Float,CultureInfo.InvariantCulture,out value) ||
                float.IsNaN(value) || float.IsInfinity(value) || value<0 || value>9999 || value!=Math.Floor(value))
                throw new InvalidDataException("Invalid city party resource target.");
            result.Floors[i]=value;
        }
        return result;
    }
}

internal sealed class CityPartyStore
{
    private readonly string root;
    internal CityPartyStore(string directory) {root=Path.GetFullPath(directory);}
    private static string ValidId(string id)
    {
        Guid guid;
        if(!Guid.TryParseExact(id,"N",out guid))throw new InvalidDataException("Invalid party identifier.");
        return guid.ToString("N");
    }
    private string Profile(string id) {return Path.Combine(root,"parties",ValidId(id)+".ini");}
    private string Binding(string hash) {return Path.Combine(root,"saves",hash+".txt");}
    internal static string Fingerprint(string path)
    {
        // Open without write sharing: a partial save must not be bound.
        using(var file=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read))
        using(var sha=SHA256.Create())
        {
            if(file.Length<16 || file.Length>512L*1024*1024)throw new InvalidDataException("Invalid save size.");
            byte[] magic=new byte[4];if(file.Read(magic,0,4)!=4 || Encoding.ASCII.GetString(magic)!="TGCK")
                throw new InvalidDataException("Not a Kohan save.");
            file.Position=0;return BitConverter.ToString(sha.ComputeHash(file)).Replace("-","").ToLowerInvariant();
        }
    }
    internal string Open(string savePath)
    {
        string hash=savePath==null?null:Fingerprint(savePath);
        if(hash!=null && File.Exists(Binding(hash)))
        {
            string found=ValidId(File.ReadAllText(Binding(hash),Encoding.UTF8).Trim());
            // Validate before returning; callers can report corruption and
            // retain automation paused instead of overwriting a valid profile.
            Read(found);return found;
        }
        string id=Guid.NewGuid().ToString("N");Write(id,new CityPartySettings());
        if(hash!=null)Atomic(Binding(hash),id+"\n");
        return id;
    }
    internal CityPartySettings Read(string id)
    {
        string path=Profile(id);
        if(new FileInfo(path).Length>4096)throw new InvalidDataException("Oversized city party preferences.");
        return CityPartySettings.Decode(File.ReadAllText(path,Encoding.UTF8));
    }
    internal void Write(string id,CityPartySettings settings) {Atomic(Profile(id),settings.Encode());}
    internal void Bind(string id,string savePath) {Atomic(Binding(Fingerprint(savePath)),ValidId(id)+"\n");}
    private static void Atomic(string path,string text)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path));
        string temp=path+"."+Guid.NewGuid().ToString("N")+".tmp";
        try {File.WriteAllText(temp,text,new UTF8Encoding(false));if(File.Exists(path))File.Replace(temp,path,null);else File.Move(temp,path);}
        finally {if(File.Exists(temp))File.Delete(temp);}
    }
}
