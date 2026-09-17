using System.Diagnostics;
using System.Net.Http;
using System.Text.Json;
using System.Text.RegularExpressions;
using PawsPatchLauncher;

// Installs only into a fresh fixture; normal game/helper launch is never used.
internal static class ApparitionTextTests
{
    static void Check(bool value,string why){if(!value)throw new InvalidDataException(why);}
    public static async Task RunAsync(string repo,string stage,string sourceGame)
    {
        repo=Path.GetFullPath(repo);stage=Path.GetFullPath(stage);
        string root=Path.Combine(stage,"install-fixture");Check(!Directory.Exists(root),"Use a fresh fixture");
        Check(!root.Equals(Path.GetFullPath(sourceGame),StringComparison.OrdinalIgnoreCase),"Refusing the real game");
        Directory.CreateDirectory(root);File.Copy(Path.Combine(sourceGame,"k2.exe"),Path.Combine(root,"k2.exe"));
        var config=JsonSerializer.Deserialize(File.ReadAllText(Path.Combine(repo,"src/PawsPatchLauncher/launcher.config.json")),LauncherJsonContext.Default.LauncherConfiguration)!;
        ChannelManifest Feed(string folder,string channel){
            var e=JsonSerializer.Deserialize(File.ReadAllText(Path.Combine(stage,folder,channel+".json")),LauncherJsonContext.Default.SignedFeedEnvelope)!;
            byte[] raw=Convert.FromBase64String(e.Payload);Check(CryptoAndIO.VerifySignature(raw,e.Signature,config.PublicKeyPem),"Invalid catalog signature");
            return JsonSerializer.Deserialize(raw,LauncherJsonContext.Default.ChannelManifest)!;
        }
        var archives=Directory.EnumerateFiles(Path.GetFullPath(Path.Combine(repo,"../..","outputs")),"*.zip",SearchOption.AllDirectories)
            .Select(p=>new FileInfo(p)).GroupBy(f=>f.Length).ToDictionary(g=>g.Key,g=>g.Select(f=>f.FullName).ToArray());
        var installer=new ModuleInstaller(root);var modules=new Dictionary<string,InstalledModule>();
        using var http=new HttpClient();http.Timeout=TimeSpan.FromMinutes(3);
        async Task<InstalledModule> Prepare(PackageRelease p){
            if(modules.TryGetValue(p.Sha256,out var found)&&installer.IsPrepared(p))return found;
            string path=p.Urls[0];
            if(path.StartsWith("https://")){
                string? cached=null;
                if(archives.TryGetValue(p.Size,out var files))foreach(string f in files)if(await CryptoAndIO.Sha256Async(f)==p.Sha256){cached=f;break;}
                if(cached is null){cached=Path.Combine(stage,p.Sha256+".zip");await File.WriteAllBytesAsync(cached,await http.GetByteArrayAsync(path));}
                path=cached;
            }
            Check(await CryptoAndIO.Sha256Async(path)==p.Sha256,"Invalid archive: "+p.Id);
            var m=await installer.PrepareAsync(p,path);modules[p.Sha256]=m;return m;
        }
        string Term(string path){
            var m=Regex.Match(File.ReadAllText(path),"(?m)^\\s*awloc_apparations_ace6ef22\\s*=\\s*\"([^\"]+)\"");
            Check(m.Success,"Missing apparition name in "+path);return m.Groups[1].Value;
        }
        var expected=new Dictionary<string,string>{{"ru","Призраки"},{"de","Erscheinungen"},{"fr","Apparitions"},{"cs","Duchové"},{"uk","Привиди"}};
        int transitions=0,preflights=0,selectionChecks=0,updateChecks=0;
        foreach(string channel in new[]{"stable","beta"}){
            var before=Feed("previous",channel);var after=Feed("test-feeds",channel);
            Check(before.Launcher.Version==after.Launcher.Version,"Launcher version changed");
            Check(before.Packages.Select(p=>(p.Id,p.Version)).SequenceEqual(after.Packages.Select(p=>(p.Id,p.Version))),"Package version changed");
            foreach(string language in GameLanguages.Choices)for(int mode=0;mode<3;mode++){
                var raw=new UserSettings{Mod=GameMod.ArcaneWars,Channel=channel,PawPatchEnabled=mode!=2,DataOnly=mode==1,GameVoiceLanguage="en",RoamingSpawnMode="x4",AdditionalRoamingCompanies=true,SiegeBalance=true,DisablePowersAndShards=true,LargeMapSizes=true};
                GameLanguages.SetText(raw,language);var s=EffectiveSettings.ForFeed(raw,after);
                var selected=GamePackageSelector.Select(after,s,s.RussianLocalization,s.CustomPlayerColors);
                var old=GamePackageSelector.Select(before,s,s.RussianLocalization,s.CustomPlayerColors);
                Check(selected.Select(p=>p.Id).SequenceEqual(old.Select(p=>p.Id)),"Selection changed");selectionChecks++;
                var original=new Dictionary<string,InstalledModule>();foreach(var p in old)original[p.Id]=await Prepare(p);
                await installer.ReconcileAsync(original,settings:s);transitions++;
                bool updated=selected.Any(p=>old.Any(q=>p.Id==q.Id&&p.Sha256!=q.Sha256));
                Check(UpdateDetector.HasModuleChanges(installer.LoadState(),selected)==updated,"Same-version revision detection failed");updateChecks++;
                var desired=new Dictionary<string,InstalledModule>();foreach(var p in selected)desired[p.Id]=await Prepare(p);
                await installer.ReconcileAsync(desired,settings:s);transitions++;
                Check((await installer.VerifyAsync()).Count==0,"Installed fixture verification failed");
                Check(!UpdateDetector.HasModuleChanges(installer.LoadState(),selected),"Revision stays pending after installation");
                if(language!="en"){
                    string startup=File.ReadAllText(Path.Combine(root,"startup/autoexec_ru.txt"));
                    string? resolved=null;
                    foreach(Match depot in Regex.Matches(startup,@"(?m)^\s*addlocaledepot\s+(\S+)")){
                        string path=Path.Combine(root,depot.Groups[1].Value,"Localization/strings_data_K2.tgi");
                        if(File.Exists(path)&&File.ReadAllText(path).Contains("awloc_apparations_ace6ef22"))resolved=Term(path);
                    }
                    Check(resolved==expected[language],"Wrong winning translation: "+language+" "+mode+" "+resolved);
                    if(language=="ru"&&mode==0)Check(Term(Path.Combine(root,"Local_ru/Localization/strings_data_K2.tgi"))=="Приложения","Protected RU table changed");
                }
                if(mode==0){
                    // All released helper variants validate the unchanged guarded
                    // resources against the corrected mounted language layer.
                    foreach(string helper in Directory.EnumerateFiles(root,"k2_paws*.exe")){
                        var start=new ProcessStartInfo(helper){UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true,ArgumentList={"--preflight",root}};
                        using var process=Process.Start(start)!;string output=await process.StandardOutput.ReadToEndAsync(),error=await process.StandardError.ReadToEndAsync();await process.WaitForExitAsync();
                        Check(process.ExitCode==0&&output.Contains("PREFLIGHT_PASS"),"Preflight failed: "+helper+" "+error);preflights++;
                    }
                }
                Console.WriteLine($"TEXT PASS {channel} {language} mode={mode}");
            }
        }
        var report=new{passed=true,transitions,selectionChecks,updateChecks,preflights,gameLaunched=false,actualGameModified=false};
        await File.WriteAllTextAsync(Path.Combine(stage,"installation-verification.json"),JsonSerializer.Serialize(report));Console.WriteLine(JsonSerializer.Serialize(report));
    }
}
