using System.IO.Compression;
using System.Text.Json;
using PawsPatchLauncher;

internal static class RebornTests
{
    internal static async Task<int> RunAsync(string root)
    {
        var checks=0;void Check(bool ok,string why){if(!ok)throw new Exception("Reborn: "+why);checks++;}
        var fixture=Path.Combine(root,"reborn");Directory.CreateDirectory(fixture);var install=Path.Combine(fixture,"installed");
        async Task<(RebornBuild Build,string Archive)> Package(string channel,params (string Path,string Content,int? Attributes)[] entries)
        {
            var path=Path.Combine(fixture,Guid.NewGuid()+".zip");
            using(var archive=ZipFile.Open(path,ZipArchiveMode.Create))foreach(var item in entries)
            {var entry=archive.CreateEntry(item.Path);if(item.Attributes is int value)entry.ExternalAttributes=value;using var writer=new StreamWriter(entry.Open());writer.Write(item.Content);}
            return (new(Guid.NewGuid(),channel,"0.1.0",new FileInfo(path).Length,await CryptoAndIO.Sha256Async(path),"KohanReborn.exe",DateTimeOffset.UtcNow,new()),path);
        }
        async Task Reject(Func<Task> work,string why)
        {try{await work();throw new Exception("Expected rejection: "+why);}catch(Exception e)when(e is IOException or InvalidDataException or JsonException or AccountException or OperationCanceledException){checks++;}}
        var stable=await Package("stable",("KohanReborn.exe","fixture executable; never run",null),("Assets/data.bin","release data",null));
        var beta=await Package("beta",("KohanReborn.exe","beta fixture; never run",null),("data.pck","beta data",null));
        var authorizations=0;Task Authorize(){authorizations++;return Task.CompletedTask;}
        Check(Path.GetDirectoryName(RebornInstall.ChannelPath(install,"stable"))==Path.GetFullPath(install)&&Path.GetFileName(RebornInstall.ChannelPath(install,"stable"))=="Release"&&Path.GetFileName(RebornInstall.ChannelPath(install,"beta"))=="Beta","channel folders must share a root and use stable Release/Beta names");
        Check(RebornInstall.Installed(install,"stable") is null,"empty installation invented a build");
        await RebornInstall.InstallAsync(install,stable.Build,stable.Archive,Authorize,CancellationToken.None);
        Check(RebornInstall.Installed(install,"stable")?.Id==stable.Build.Id&&RebornInstall.Installed(install,"beta") is null,"Release did not install independently");
        await RebornInstall.InstallAsync(install,beta.Build,beta.Archive,Authorize,CancellationToken.None);
        Check(RebornInstall.Installed(install,"stable")?.Id==stable.Build.Id&&RebornInstall.Installed(install,"beta")?.Id==beta.Build.Id,"Beta changed the Release install");
        await RebornInstall.InstallAsync(install,stable.Build,stable.Archive,Authorize,CancellationToken.None);
        Check(authorizations==3&&RebornInstall.Installed(install,"stable")?.Id==stable.Build.Id,"same verified build is not safely retryable");
        foreach(var path in new[]{"../escape.exe","/root.exe","C:/outside.exe","data/../../outside.exe","data/file:stream","CON.txt"})
        {
            var bad=await Package("stable",("KohanReborn.exe","fixture",null),(path,"bad",null));
            await Reject(()=>RebornInstall.InstallAsync(install,bad.Build,bad.Archive,Authorize,CancellationToken.None),"unsafe path "+path);
        }
        var collision=await Package("stable",("KohanReborn.exe","one",null),("kohanreborn.EXE","two",null));
        await Reject(()=>RebornInstall.InstallAsync(install,collision.Build,collision.Archive,Authorize,CancellationToken.None),"case-insensitive collision");
        var link=await Package("stable",("KohanReborn.exe","fixture",null),("link","outside",unchecked((int)0xA1FF0000)));
        await Reject(()=>RebornInstall.InstallAsync(install,link.Build,link.Archive,Authorize,CancellationToken.None),"archive symlink");
        var missing=await Package("stable",("only-data.bin","no exe",null));
        await Reject(()=>RebornInstall.InstallAsync(install,missing.Build,missing.Archive,Authorize,CancellationToken.None),"missing executable");
        await Reject(()=>RebornInstall.InstallAsync(install,stable.Build with{Sha256=new('0',64)},stable.Archive,Authorize,CancellationToken.None),"wrong archive hash");
        var revoked=await Package("stable",("KohanReborn.exe","unauthorized build",null));
        await Reject(()=>RebornInstall.InstallAsync(install,revoked.Build,revoked.Archive,()=>throw new AccountException("reborn_access_denied"),CancellationToken.None),"revoked role");
        await Reject(()=>RebornInstall.InstallAsync(install,revoked.Build,revoked.Archive,Authorize,new CancellationToken(true)),"cancelled install");
        Check(RebornInstall.Installed(install,"stable")?.Id==stable.Build.Id&&RebornInstall.Installed(install,"beta")?.Id==beta.Build.Id,"failed update changed an active build");
        Check(!Directory.EnumerateDirectories(install,".staging-*",SearchOption.AllDirectories).Any(),"owned staging directories left after failure");
        await File.WriteAllTextAsync(Path.Combine(Path.GetDirectoryName(RebornInstall.Executable(install,stable.Build))!,"keep.txt"),"user content");
        await Reject(()=>RebornInstall.InstallAsync(install,stable.Build,stable.Archive,Authorize,CancellationToken.None),"existing user files");
        Check(File.ReadAllText(Path.Combine(Path.GetDirectoryName(RebornInstall.Executable(install,stable.Build))!,"keep.txt"))=="user content","user files were overwritten");
        await Reject(()=>Task.Run(()=>RebornBuild.Validate(stable.Build with{Channel="../beta"})),"invalid channel");
        var foreignRoot=Path.Combine(fixture,"foreign");Directory.CreateDirectory(RebornInstall.ChannelPath(foreignRoot,"stable"));
        var foreignMarker=Path.Combine(RebornInstall.ChannelPath(foreignRoot,"stable"),"active.json");await File.WriteAllTextAsync(foreignMarker,"unrelated user file");
        await Reject(()=>RebornInstall.InstallAsync(foreignRoot,stable.Build,stable.Archive,Authorize,CancellationToken.None),"foreign marker");
        Check(File.ReadAllText(foreignMarker)=="unrelated user file"&&RebornInstall.Installed(foreignRoot,"stable") is null,"unrelated marker was overwritten or accepted");
        var translated=stable.Build with{Id=Guid.NewGuid(),Notes=new(){["ru"]=new('Ж',10000),["uk"]=new('І',10000)}};
        await RebornInstall.InstallAsync(install,translated,stable.Archive,Authorize,CancellationToken.None);
        Check(RebornInstall.Installed(install,"stable")?.Notes["uk"].Length==10000,"valid localized changelog exceeds installation-marker limit");
        Console.WriteLine($"REBORN INSTALL PASS {checks}: independent channels, verification, safe extraction, retry, revocation, cancellation and preserved installations; no EXE executed");return checks;
    }
}
