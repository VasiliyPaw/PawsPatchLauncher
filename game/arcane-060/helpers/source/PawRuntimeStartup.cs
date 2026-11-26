using System;
using System.IO;
using System.Text;
using System.Linq;
using System.Diagnostics;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using System.Web.Script.Serialization;
using Microsoft.Win32;
internal static class PawRuntimeStartup {
 static string root,cache; static JavaScriptSerializer json=new JavaScriptSerializer { MaxJsonLength=20000000 };
 public class HashRow {public long Size;public long Modified;public long Created;public string Hash;}
 static string Digest(byte[] b){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(b)).Replace("-","").ToLowerInvariant();}
 static void Atomic(string path,string text){string tmp=path+".tmp";File.WriteAllText(tmp,text);if(File.Exists(path))File.Replace(tmp,path,null);else File.Move(tmp,path);}
 static string FontKey(string game) {
  var sw=Stopwatch.StartNew();var paths=new SortedSet<string>(StringComparer.OrdinalIgnoreCase);
  foreach(string p in Directory.EnumerateFiles(game).Concat(Directory.EnumerateDirectories(game).Where(d=>!String.Equals(Path.GetFileName(d),".pawpatch",StringComparison.OrdinalIgnoreCase)&&!String.Equals(Path.GetFileName(d),"Logs",StringComparison.OrdinalIgnoreCase)).SelectMany(d=>Directory.EnumerateFiles(d,"*",SearchOption.AllDirectories)))) {
   string ext=Path.GetExtension(p).ToLowerInvariant();if(new[]{".tgi",".ttf",".otf",".ttc",".rwd"}.Contains(ext))paths.Add(Path.GetFullPath(p));
  }
  foreach(string p in new[]{"k2.exe","GdiPlus.dll","Mods/PawsFontMetrics.dll","Mods/PawsStartupOptimizations.dll"})paths.Add(Path.Combine(game,p));
  paths.Add(typeof(PawRuntimeStartup).Assembly.Location);
  foreach(string dir in new[]{Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows),"Fonts"),Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Microsoft/Windows/Fonts")})
   if(Directory.Exists(dir))foreach(string p in Directory.EnumerateFiles(dir,"*",SearchOption.AllDirectories))paths.Add(p);
  foreach(string name in new[]{"gdi32.dll","gdi32full.dll","win32u.dll","usp10.dll"}) {string p=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows),"SysWOW64",name);if(File.Exists(p))paths.Add(p);}
  string index=Path.Combine(cache,"dependency-hashes.json");Dictionary<string,HashRow> old;
  try {old=json.Deserialize<Dictionary<string,HashRow>>(File.ReadAllText(index));}catch {old=new Dictionary<string,HashRow>();}
  var current=new Dictionary<string,HashRow>();var material=new StringBuilder("R24-FONT-1\n");long hashed=0;
  foreach(string p in paths) {
   var f=new FileInfo(p);HashRow prior;string hash;
   if(old.TryGetValue(p,out prior)&&prior.Size==f.Length&&prior.Modified==f.LastWriteTimeUtc.Ticks&&prior.Created==f.CreationTimeUtc.Ticks)hash=prior.Hash;
   else {using(var stream=File.OpenRead(p))using(var h=SHA256.Create())hash=BitConverter.ToString(h.ComputeHash(stream)).Replace("-","").ToLowerInvariant();hashed+=f.Length;}
   current[p]=new HashRow{Size=f.Length,Modified=f.LastWriteTimeUtc.Ticks,Created=f.CreationTimeUtc.Ticks,Hash=hash};material.Append(p).Append('=').Append(hash).Append('\n');
  }
  foreach(var hive in new[]{RegistryHive.LocalMachine,RegistryHive.CurrentUser})using(var baseKey=RegistryKey.OpenBaseKey(hive,RegistryView.Registry64))
   foreach(string sub in new[]{"Fonts","FontSubstitutes","FontLink\\SystemLink"})using(var key=baseKey.OpenSubKey("SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\"+sub))
    if(key!=null)foreach(string n in key.GetValueNames().OrderBy(x=>x,StringComparer.Ordinal)) {
     object v=key.GetValue(n);material.Append(hive).Append(sub).Append(n).Append('=').Append(json.Serialize(v)).Append('\n');
    }
  // Private display settings affect the native font atlases. Camera and sound
  // preferences do not invalidate otherwise compatible character measurements.
  string userSettings=Path.Combine(PawRuntimePaths.Documents,"Kohan2/data/User/UVars.tgi");
  var displaySettings=new SortedDictionary<string,string>(StringComparer.Ordinal);
  if(File.Exists(userSettings))foreach(string line in File.ReadAllLines(userSettings)) {
   var match=Regex.Match(line,@"^\s*\w+\s+(ResolutionX|ResolutionY|\w*Font\w*|\w*Language\w*|UIScale|TextScale)\s*=\s*([^;]+)",RegexOptions.IgnoreCase);
   if(match.Success)displaySettings[match.Groups[1].Value.ToLowerInvariant()]=match.Groups[2].Value.Trim();
  }
  foreach(var setting in displaySettings)material.Append(setting.Key).Append('=').Append(setting.Value).Append('\n');
  material.Append(Environment.OSVersion.VersionString);string result=Digest(Encoding.UTF8.GetBytes(material.ToString()));Atomic(index,json.Serialize(current));
  Atomic(Path.Combine(cache,"last-preparation.json"),json.Serialize(new{key=result,files=current.Count,hashedBytes=hashed,ms=sw.ElapsedMilliseconds}));return result;
 }

 internal static void Configure(ProcessStartInfo p,string game) {
  Validate(game);p.UseShellExecute=false;root=Path.GetFullPath(game);
  cache=Path.Combine(PawRuntimePaths.AppData,"PawsPatch","Startup",Digest(Encoding.UTF8.GetBytes(root.ToLowerInvariant())).Substring(0,16));
  foreach(string name in p.EnvironmentVariables.Keys.Cast<string>().ToArray())
   if(new[]{"PAWS_STARTUP_","PAWS_PROFILE_","PAWS_TGI_","PAWS_MAPGEN_","PAWS_FONT_"}.Any(prefix=>name.StartsWith(prefix,StringComparison.OrdinalIgnoreCase)))p.EnvironmentVariables.Remove(name);
  foreach(string k in new[]{"MEMORY_ESTIMATE","TRIM","TOKENS","FIELDS"})p.EnvironmentVariables["PAWS_STARTUP_"+k]="1";
  foreach(string k in new[]{"LOOKUP","TYPE_CACHE","LOOKUP_VALIDATE","LOOKUP_DIAG","LOOKUP_DIAGNOSTIC","TOKENS_VALIDATE","TOKEN_DIGEST","FIELDS_VALIDATE","TRIM_VALIDATE"})p.EnvironmentVariables["PAWS_STARTUP_"+k]="0";
  p.EnvironmentVariables["PAWS_PROFILE_REMAINING"]="0";p.EnvironmentVariables["PAWS_TGI_CACHE_MODE"]="off";p.EnvironmentVariables["PAWS_MAPGEN_INDEX"]="off";p.EnvironmentVariables["PAWS_FONT_CACHE_MODE"]="off";
  try {Directory.CreateDirectory(cache);p.EnvironmentVariables["PAWS_FONT_CACHE_KEY"]=FontKey(game);p.EnvironmentVariables["PAWS_FONT_CACHE_PATH"]=Path.Combine(cache,"font-metrics.bin");p.EnvironmentVariables["PAWS_FONT_CACHE_MODE"]="replay";}
  catch(Exception e){try{if(Directory.Exists(cache))File.WriteAllText(Path.Combine(cache,"font-preparation-error.txt"),e.ToString());}catch{}}
 }


 static void ValidateTextures(string game) {
  string[] names={"paws-biome-textures-01.rwd","paws-biome-textures-02.rwd","paws-biome-textures-03.rwd","paws-biome-textures-04.rwd"};long[] sizes={231258709L,231349614L,231234996L,208526886L};uint[] stamps={0x833671A8u,0x14FE7AFDu,0xCDA233C9u,0x9F8FD388u};
  string startup=Path.Combine(game,"startup","autoexec.txt");string mounted=File.Exists(startup)?File.ReadAllText(startup):"";
  for(int i=0;i<names.Length;i++){
   string path=Path.Combine(game,names[i]);if(!File.Exists(path)||new FileInfo(path).Length!=sizes[i])throw new InvalidDataException("Paw's Patch terrain textures are missing or incomplete. Apply the update in the launcher.");
   using(var input=new BinaryReader(File.OpenRead(path))){if(input.ReadUInt32()!=0x4B434754||input.ReadUInt32()!=2||input.ReadUInt32()!=3)throw new InvalidDataException("Paw's Patch terrain archive header differs. Apply the update in the launcher.");input.BaseStream.Position=26;if(input.ReadUInt32()!=stamps[i])throw new InvalidDataException("Paw's Patch terrain archive version differs. Apply the update in the launcher.");}
   bool found=mounted.Split(new[]{'\r','\n'},StringSplitOptions.RemoveEmptyEntries).Any(line=>String.Equals(line.Trim(),"adddepot "+names[i],StringComparison.OrdinalIgnoreCase));if(!found)throw new InvalidDataException("Paw's Patch terrain textures are not connected. Apply the update in the launcher.");
  }
 }
 static void Validate(string game) {
  ValidateTextures(game);
  if(!File.Exists(Path.Combine(game,"paws_runtime.marker")))throw new InvalidDataException("Paw's Patch 0.6.0 runtime data is missing. Apply the update in the launcher.");
  string[] names={"PawsBridges.dll","PawsMilitia.dll","PawsSiege.dll","PawsWideBiomes.dll","PawsWaterBiomes.dll","PawsCameraRange.dll","PawsMinimapBiomes.dll","PawsStartupOptimizations.dll","PawsFontMetrics.dll","PawsCaptureKnowledge.dll"};string[] hashes={"B3C13E79390327E698E75C0BF380B78AEA73A3C9C9945091BF058B1B4CAD38E5","D8FB006916B954A3C6A7AE0564FE375E89A1EA00FA83376FD09EC627757CD7ED","B710145DAE706F341A58DF44B8DB9F96EF81E3B1652E840DF6FE2F749F586365","6C9BE8F0F61EE0CBE9B914C4B7FC42FA594FA7B843E6188FFDB77141A93D86B7","45F24C74A262FF02646261265D12956E73A750F95565110A98B62E44C3C806FD","B3387EFF724E35FFC05EBFC95828BFBEE04597E4B989203F5EECF7FA60FC0B02","69738E50F613D3FB3899B72308085A3A24BA90F2493B2856CDF60D60FE10801B","7AF3C91CD5EA637EA94D238DF5E38B689D4884AADBF03FC79BDA2843E6D2613B","95BAB1F2BE7153606300BC2328F5A666205387E7F4BCD7A8007DFC754E6F25F9","D1944EA3B487E031064A0F274556CB4C0A1F9ED513B1DD3150E6C57C0CAB95A4"};
  for(int i=0;i<names.Length;i++){string path=Path.Combine(game,"Mods",names[i]);if(!File.Exists(path))throw new FileNotFoundException("Missing Paw's Patch runtime module: "+names[i]);using(var stream=File.OpenRead(path))using(var h=SHA256.Create())if(!String.Equals(BitConverter.ToString(h.ComputeHash(stream)).Replace("-",""),hashes[i],StringComparison.OrdinalIgnoreCase))throw new InvalidDataException("Paw's Patch runtime module differs: "+names[i]);}
  string loader=Path.Combine(game,"avifil32.dll");if(!File.Exists(loader))throw new FileNotFoundException("Paw's Patch module loader is missing.");
  using(var stream=File.OpenRead(loader))using(var h=SHA256.Create())if(!String.Equals(BitConverter.ToString(h.ComputeHash(stream)).Replace("-",""),"449DA31A592CC53D48845EF980258F226FF389091E40D9A27373EE79FD8BA7E0",StringComparison.OrdinalIgnoreCase))throw new InvalidDataException("Paw's Patch module loader differs.");
  string config=Path.Combine(game,"Mods/plugins.txt");if(!File.Exists(config))throw new FileNotFoundException("Paw's Patch module list is missing.");
  var active=File.ReadAllLines(config).Select(x=>x.Trim()).Where(x=>x.Length!=0&&!x.StartsWith("#")).ToArray();foreach(string name in names)if(!active.Contains(name,StringComparer.OrdinalIgnoreCase))throw new InvalidDataException("Required Paw's Patch module is disabled: "+name);
 }
}
