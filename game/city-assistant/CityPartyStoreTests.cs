using System;
using System.IO;
using System.Linq;
using System.Text;
internal static class CityPartyStoreTests
{
    private static int checks;
    private static void Check(bool value,string why) {if(!value)throw new Exception(why);checks++;}
    private static void Save(string path,string body) {File.WriteAllText(path,"TGCK"+new string(' ',16)+body,Encoding.ASCII);}
    internal static int Main()
    {
        string root=Path.Combine(Path.GetTempPath(),"PawPartyTests-"+Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        try
        {
            string a=Path.Combine(root,"a.rsg"),b=Path.Combine(root,"b.rsg"),copy=Path.Combine(root,"renamed.rsg");
            Save(a,"first party");Save(b,"second party");
            var store=new CityPartyStore(Path.Combine(root,"prefs"));
            string first=store.Open(a),second=store.Open(b);
            Check(first!=second,"different saves isolated");
            var s=store.Read(first);Check(s.Enabled && s.Reserve==2000 && s.Floors.All(x=>x==0),"old save starts with defaults");
            s.Enabled=false;s.Reserve=7654321;s.Floors=new float[]{0,12,3,9999,0};store.Write(first,s);
            Check(store.Read(second).Reserve==2000,"party B not changed");
            string later=Path.Combine(root,"later.rsg");Save(later,"later state of first party");store.Bind(first,later);
            store=new CityPartyStore(Path.Combine(root,"prefs"));
            Check(store.Open(later)==first && store.Open(a)==first,"different times in one party share preferences");
            s=store.Read(store.Open(later));Check(!s.Enabled && s.Reserve==7654321 && s.Floors[3]==9999,"settings survive helper restart");
            File.Copy(a,copy);Check(store.Open(copy)==first,"copy/rename retains identity");
            string fresh=store.Open(null);Check(fresh!=first && fresh!=second,"new match gets fresh identity");
            s=store.Read(fresh);Check(s.Enabled && s.Reserve==2000 && s.Floors.All(x=>x==0),"new match defaults");
            Save(a,"new unrelated party overwrites same filename");string overwritten=store.Open(a);
            Check(overwritten!=first && overwritten!=second && store.Read(overwritten).Reserve==2000,"filename reuse does not leak settings");
            Check(store.Open(copy)==first,"original copy still belongs to first party");
            byte[] bytes=File.ReadAllBytes(later);store.Bind(first,later);Check(bytes.SequenceEqual(File.ReadAllBytes(later)),"save bytes unchanged");
            using(var locked=new FileStream(later,FileMode.Open,FileAccess.Write,FileShare.Read))
            {
                bool denied=false;try{store.Bind(first,later);}catch(IOException){denied=true;}
                Check(denied,"partial active write is not fingerprinted");
            }
            foreach(string bad in new[]{"", "1\n2\n2000\n0\n0\n0\n0", "1\n1\n10000000\n0\n0\n0\n0", "1\n1\n2000\nNaN\n0\n0\n0", "1\n1\n2000\n-1\n0\n0\n0", "1\n1\n2000\n0.5\n0\n0\n0", "1\n1\n2000\n10000\n0\n0\n0"})
            {bool denied=false;try{CityPartySettings.Decode(bad);}catch(InvalidDataException){denied=true;}Check(denied,"invalid preference rejected");}
            foreach(uint reserve in new uint[]{0,2000,9999999})foreach(float floor in new[]{0f,1f,9999f})foreach(bool enabled in new[]{false,true})
            {
                s=new CityPartySettings {Enabled=enabled,Reserve=reserve,Floors=new[]{0,floor,floor,floor,floor}};
                store.Write(second,s);var read=store.Read(second);
                Check(read.Encode()==s.Encode(),"all boundary values roundtrip");
            }
            Check(Directory.GetFiles(root,"*.tmp",SearchOption.AllDirectories).Length==0,"no abandoned temporary files");
            Console.WriteLine("CITY_PARTY_STORE_PASS "+checks+" checks");return 0;
        }
        finally
        {
            // Explicit, unique test directory created above; never a user path.
            if(Path.GetFileName(root).StartsWith("PawPartyTests-",StringComparison.Ordinal))Directory.Delete(root,true);
        }
    }
}
