using PawsPatchLauncher;
using System.Security.Cryptography;

internal static class CompatibilityModerationTests
{
    internal static async Task<int> RunAsync(string root)
    {
        int n=0;void Check(bool ok,string why){n++;if(!ok)throw new Exception("Compatibility/moderation: "+why);}
        var now=new DateTimeOffset(2026,9,8,12,30,1,TimeSpan.Zero);
        Check(ModerationDuration.TryDeadline(now,"0","0","1",out var minute)&&minute==now.AddMinutes(1),"one minute");
        Check(ModerationDuration.TryDeadline(now,"1","2","3",out var full)&&full==now.AddMinutes(1563),"all fields");
        Check(ModerationDuration.TryDeadline(now,"10000","0","0",out _),"long ban");
        foreach(var fields in new[]{new[]{"0","0","0"},new[]{"-1","0","1"},new[]{"0","24","0"},new[]{"0","0","60"},new[]{"0","0","1.5"},new[]{"x","0","1"},new[]{"2147483647","0","0"},new[]{"","0","1"}})
            Check(!ModerationDuration.TryDeadline(now,fields[0],fields[1],fields[2],out _),"invalid duration "+string.Join("/",fields));
        Check(!ModerationDuration.TryDeadline(DateTimeOffset.MaxValue.AddSeconds(-1),"0","0","1",out _),"date overflow");
        var path=Path.Combine(root,"compatibility-fixture.exe");
        var bytes=new byte[]{1,3,5,7};
        await File.WriteAllBytesAsync(path,bytes);
        var hash=Convert.ToHexString(SHA256.HashData(bytes));
        Check(await GameCompatibility.CheckAsync(path,new[]{hash})==GameCompatibilityState.Supported,"matching hash");
        Check(await GameCompatibility.CheckAsync(path,new[]{hash.ToLowerInvariant()})==GameCompatibilityState.Supported,"case insensitive hash");
        Check(await GameCompatibility.CheckAsync(path,new[]{new string('0',64),hash})==GameCompatibilityState.Supported,"multiple supported binaries");
        var before=GameFileStamp.Read(path);await File.WriteAllBytesAsync(path,new byte[]{1,2,3,4,5});
        Check(before!=GameFileStamp.Read(path),"replacement invalidates cache");
        Check(await GameCompatibility.CheckAsync(path,new[]{hash})==GameCompatibilityState.Unsupported,"updated binary rejected");
        Check(await GameCompatibility.CheckAsync(path+".missing",new[]{hash})==GameCompatibilityState.Unavailable,"missing not mislabeled unsupported");
        using(var locked=File.Open(path,FileMode.Open,FileAccess.ReadWrite,FileShare.None))
            Check(await GameCompatibility.CheckAsync(path,new[]{hash})==GameCompatibilityState.Unavailable,"locked not mislabeled unsupported");
        using(var cancel=new CancellationTokenSource())
        {
            cancel.Cancel();bool cancelled=false;
            try{await GameCompatibility.CheckAsync(path,new[]{hash},cancel.Token);}catch(OperationCanceledException){cancelled=true;}
            Check(cancelled,"cancelled read");
        }
        await File.WriteAllBytesAsync(path,bytes);
        Check(await GameCompatibility.CheckAsync(path,new[]{hash})==GameCompatibilityState.Supported,"restored game accepted");
        Console.WriteLine($"COMPATIBILITY/MODERATION PASS {n}: synthetic files only");
        return n;
    }
}
