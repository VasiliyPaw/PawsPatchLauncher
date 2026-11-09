// Owned QA only. Uses the public installer and speech startup API unchanged.
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using PawsPatchLauncher;
var json=new JsonSerializerOptions{PropertyNameCaseInsensitive=true};
string directory=Path.GetFullPath(args[1]);
if(!File.Exists(Path.Combine(directory,".paw-live-matrix.json")))throw new IOException("Owned matrix fixture required");
var installer=new ModuleInstaller(directory);var state=installer.LoadState();
var settings=JsonSerializer.Deserialize(JsonSerializer.Serialize(state.AppliedSettings??throw new IOException("Missing applied settings"),LauncherJsonContext.Default.UserSettings),LauncherJsonContext.Default.UserSettings)!;
Dictionary<string,string> Schema(string name)=>name=="B"
 ?new(){["royalist"]="de",["council"]="ru",["nationalist"]="fr",["ceyah"]="en",["fallen"]="fr",["other"]="en"}
 :new(){["royalist"]="fr",["council"]="en",["nationalist"]="de",["ceyah"]="ru",["fallen"]="en",["other"]="ru"};
if(args[0]=="prepare"){
 var source=Path.GetFullPath(args[2]);var original=new ModuleInstaller(source).LoadState();
 var envelope=JsonSerializer.Deserialize<SignedFeedEnvelope>(File.ReadAllBytes(args[3]),json)!;
 var config=SettingsStore.LoadConfiguration();var payload=Convert.FromBase64String(envelope.Payload);
 if(!CryptoAndIO.VerifySignature(payload,envelope.Signature,config.PublicKeyPem))throw new IOException("Signed catalog required");
 var channel=JsonSerializer.Deserialize<ChannelManifest>(payload,json)!;
 string before=FriendConfiguration.Create(settings);settings.GameVoiceLanguage="custom";
 settings.FactionVoiceLanguages=Schema(args.Contains("B")?"B":"A");
 var selected=GamePackageSelector.Select(channel,settings,settings.RussianLocalization,settings.CustomPlayerColors);
 var desired=new Dictionary<string,InstalledModule>();
 void CopyTree(string from,string to){
  if((File.GetAttributes(from)&FileAttributes.ReparsePoint)!=0)throw new IOException("Linked source rejected");
  Directory.CreateDirectory(to);
  foreach(var file in Directory.EnumerateFiles(from)){
   if((File.GetAttributes(file)&FileAttributes.ReparsePoint)!=0)throw new IOException("Linked file rejected");
   string target=Path.Combine(to,Path.GetFileName(file));
   if(File.Exists(target)){
    if(!SHA256.HashData(File.ReadAllBytes(file)).SequenceEqual(SHA256.HashData(File.ReadAllBytes(target))))throw new IOException("Different prepared file");
   }else File.Copy(file,target);
  }
  foreach(var child in Directory.EnumerateDirectories(from))CopyTree(child,Path.Combine(to,Path.GetFileName(child)));
 }
 foreach(var package in selected){
  if(!installer.IsPrepared(package)){
   if(!package.Id.StartsWith("game-voice-")||!original.Modules.TryGetValue(package.Id,out var voice)||voice.Version!=package.Version||!voice.ArchiveSha256.Equals(package.Sha256,StringComparison.OrdinalIgnoreCase))throw new IOException("Unverified missing dependency: "+package.Id);
   CopyTree(Path.Combine(source,".pawpatch/packages",package.Id,package.Version),Path.Combine(directory,".pawpatch/packages",package.Id,package.Version));
  }
  desired[package.Id]=await installer.PrepareAsync(package,"");
 }
 await installer.ReconcileAsync(desired,settings:settings,releaseId:state.ReleaseId,gameRequirement:state.GameRequirement,baseGameSha256:state.BaseGameSha256);
 if((await installer.VerifyAsync(allowCustomHotkeys:true)).Count!=0||FriendConfiguration.Create(settings)!=before)throw new Exception("Prepared voice fixture verification failed");
 if(await FactionVoiceRuntime.PrepareAsync(directory,settings)is null)throw new Exception("Runtime absent");
 Console.WriteLine("OWNED_PRODUCT_FACTION_PREPARED; gameplay unchanged; verified voice caches; no downloads");
}else if(args[0]=="launch"){
 if(Schema(args[3]).Any(p=>CustomVoices.Language(settings,p.Key)!=p.Value))throw new IOException("Prepare the real applied speech scheme before launching");
 var plan=await FactionVoiceRuntime.PrepareAsync(directory,settings)??throw new Exception("Missing voice plan");
 if(Path.GetFileName(args[2])!=args[2]||!args[2].StartsWith("k2_paws_"))throw new IOException("Owned helper filename required");
 var start=new ProcessStartInfo(Path.Combine(directory,args[2])){WorkingDirectory=directory,UseShellExecute=false,CreateNoWindow=true,WindowStyle=ProcessWindowStyle.Hidden,RedirectStandardOutput=true,RedirectStandardError=true};
 start.ArgumentList.Add("--game-dir");start.ArgumentList.Add(directory+Path.DirectorySeparatorChar);
 var started=DateTimeOffset.UtcNow;
 using var helper=Process.Start(start)??throw new Exception("Helper did not start");
 helper.OutputDataReceived+=(_,e)=>{if(e.Data is not null){Console.WriteLine(e.Data);Console.Out.Flush();}};
 helper.ErrorDataReceived+=(_,e)=>{if(e.Data is not null){Console.Error.WriteLine(e.Data);Console.Error.Flush();}};
 helper.BeginOutputReadLine();helper.BeginErrorReadLine();
 var install=FactionVoiceRuntime.InstallAsync(directory,plan,started,helper);
 await Task.WhenAny(install,helper.WaitForExitAsync());
 if(!install.IsCompleted){Environment.ExitCode=helper.ExitCode;return;}
 await install;
 Console.WriteLine("OWNED_PRODUCT_FACTION_READY "+args[3]);
 Console.Out.Flush();await helper.WaitForExitAsync();Environment.ExitCode=helper.ExitCode;
}else throw new ArgumentException("Unknown action");
