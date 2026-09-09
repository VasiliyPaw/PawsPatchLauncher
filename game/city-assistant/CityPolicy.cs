using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;

// Local preferences only. Neither simulation state nor the save format changes.
internal sealed class CityPolicy
{
    internal bool AllowNew = true, AllowUpgrade = true, AllowOther;
    internal float[] Floors = new float[5];
    internal readonly Dictionary<string,string> Branches = new Dictionary<string,string>(StringComparer.Ordinal);
    internal readonly HashSet<uint> Excluded = new HashSet<uint>();
    internal readonly Dictionary<uint,Dictionary<string,string>> CityBranches = new Dictionary<uint,Dictionary<string,string>>();
    // Definition +8 is a GameString pointer, NOT a persistent numeric ID.
    // Use its internal, language-independent text; never save a heap address.
    internal static string DefinitionKey(uint data, Func<uint,uint> pointer, Func<uint,string> text)
    {
        string name=text(pointer(checked(data+8)));
        if(string.IsNullOrEmpty(name) || name.Length>128 || name.Any(c=>c<' ' || c>'~'))
            throw new InvalidDataException("Building definition identifier is unavailable.");
        return "def:"+name;
    }
    // Gold is an optimization goal, never a configurable income target.
    // Preserve its zero-deficit safety guard and the separate cash reserve.
    internal float Floor(int resource) { return resource > 0 && resource < Floors.Length && CityPlanner.Finite(Floors[resource]) ? Math.Max(0,Floors[resource]) : 0; }
    internal string Rule(uint city, string family)
    {
        Dictionary<string,string> local; string rule;
        if (CityBranches.TryGetValue(city,out local) && local.TryGetValue(family,out rule)) return rule;
        return Branches.TryGetValue(family,out rule) ? rule : "auto";
    }
    internal bool Allows(CityPlanner.Candidate c)
    {
        if (Excluded.Contains(c.City) || (c.Kind == 13 && !AllowNew) || (c.Kind == 21 && !AllowUpgrade)) return false;
        if (c.Kind != 21) return true;
        if (c.Family=="unavailable" || c.Target=="unavailable" || string.IsNullOrEmpty(c.Family) || string.IsNullOrEmpty(c.Target)) return false;
        string rule = Rule(c.City,c.Family);
        if (rule == "auto") return true;
        if (rule == "manual") return c.BranchCount == 1;
        return c.Target == rule; // Never silently substitute a different branch.
    }
    internal CityPolicy Copy()
    {
        CityPolicy c = new CityPolicy { AllowNew=AllowNew, AllowUpgrade=AllowUpgrade, AllowOther=AllowOther, Floors=(float[])Floors.Clone() };
        foreach(var p in Branches) c.Branches.Add(p.Key,p.Value);
        foreach(uint city in Excluded) c.Excluded.Add(city);
        foreach(var p in CityBranches) c.CityBranches.Add(p.Key,new Dictionary<string,string>(p.Value));
        return c;
    }
    internal void ClearCities() { Excluded.Clear(); CityBranches.Clear(); }
    internal static CityPolicy LoadPreferred(string path, string legacyPath)
    {
        // Never overwrite production preferences with a later experimental run.
        return Load(File.Exists(path) ? path : legacyPath);
    }
    internal static CityPolicy Load(string path)
    {
        CityPolicy p = new CityPolicy();
        if (!File.Exists(path)) return p;
        foreach(string line in File.ReadAllLines(path,Encoding.UTF8).Take(4096))
        {
            string[] v=line.Split('\t'); float f; int i;
            if(v.Length != 2) continue;
            if(v[0]=="new") p.AllowNew=v[1]!="0";
            else if(v[0]=="upgrade") p.AllowUpgrade=v[1]!="0";
            else if(v[0]=="other") p.AllowOther=v[1]=="1";
            else if(v[0].StartsWith("floor:") && int.TryParse(v[0].Substring(6),out i) && i>0 && i<5
                && float.TryParse(v[1],NumberStyles.Float,CultureInfo.InvariantCulture,out f) && CityPlanner.Finite(f) && f>=0 && f<=9999) p.Floors[i]=f;
            else if(v[0].StartsWith("branch:") && v[0].Length<260 && v[1].Length<260) p.Branches[v[0].Substring(7)]=v[1];
        }
        return p;
    }
    internal void Save(string path)
    {
        List<string> lines=new List<string> {"new\t"+(AllowNew?1:0),"upgrade\t"+(AllowUpgrade?1:0),"other\t"+(AllowOther?1:0)};
        for(int i=1;i<5;i++) lines.Add("floor:"+i+"\t"+Floor(i).ToString(CultureInfo.InvariantCulture));
        foreach(var p in Branches.OrderBy(x=>x.Key)) lines.Add("branch:"+p.Key+"\t"+p.Value);
        // Unique sibling temp plus atomic replacement; a failed save keeps the previous preferences.
        Directory.CreateDirectory(Path.GetDirectoryName(path));
        string temp=path+"."+Guid.NewGuid().ToString("N")+".tmp";
        try { File.WriteAllLines(temp,lines,Encoding.UTF8); if(File.Exists(path)) File.Replace(temp,path,null); else File.Move(temp,path); }
        finally { if(File.Exists(temp)) File.Delete(temp); }
    }
}
