from context import *
from qa import project
Q=O/'reader-check';project(Q)
(Q/'Program.cs').write_text(r'''using System.Text.Json;using System.Security.Cryptography;using PawsPatchLauncher.Rwd;
var root=args[0];using var doc=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"resource-archives.json")));int count=0,blobs=0;
foreach(var part in doc.RootElement.EnumerateObject()){using var a=RwdArchive.Open(part.Value.GetProperty("path").GetString()!);var expected=part.Value.GetProperty("files");blobs+=a.Entries.Select(e=>(e.Offset,e.Size)).Distinct().Count();foreach(var e in a.Entries){var hash=Convert.ToHexString(SHA256.HashData(a.Read(e)));if(hash!=expected.GetProperty(e.Name).GetProperty("sha256").GetString())throw new Exception(e.Name);count++;}}
File.WriteAllText(Path.Combine(root,"reader-result.json"),JsonSerializer.Serialize(new{passed=true,entries=count,uniqueBlobs=blobs,reader="Published launcher RwdTool.dll"}));Console.WriteLine($"RWD_READER_PASS {count} entries, {blobs} unique blobs");
''');print(run([SDK,'run','--project',Q/'QA.csproj','-c','Release','--',O],O/'reader-check.log'),flush=True)
