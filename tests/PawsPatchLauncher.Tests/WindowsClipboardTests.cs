using System.Runtime.InteropServices;
using PawsPatchLauncher;

internal static class WindowsClipboardTests
{
    internal static async Task<int> RunAsync()
    {
        int checks=0;
        void Check(bool ok,string why){if(!ok)throw new Exception("Background clipboard: "+why);checks++;}
        ExternalException Busy()=>new("simulated clipboard lock",unchecked((int)0x800401D0));
        int attempts=0;
        var writes=new List<string>();
        await WindowsClipboard.WriteTextAsync(1,"Юзер 🌙",default,(_,text,_)=>{
            Check(Thread.CurrentThread.IsThreadPoolThread&&SynchronizationContext.Current is null,"native writer ran on a UI context");
            if(Interlocked.Increment(ref attempts)<3)throw Busy();writes.Add(text);
        });
        Check(attempts==3&&writes.SequenceEqual(new[]{"Юзер 🌙"}),"retry / Unicode payload");
        attempts=0;
        try{await WindowsClipboard.WriteTextAsync(1,"busy",default,(_,_,_)=>{attempts++;throw Busy();});throw new Exception("Expected contention failure");}
        catch(ExternalException){Check(attempts==6,"bounded retry");}
        attempts=0;
        try{await WindowsClipboard.WriteTextAsync(1,"failure",default,(_,_,_)=>{attempts++;throw new InvalidOperationException("simulated failure");});throw new Exception("Expected other failure");}
        catch(InvalidOperationException){Check(attempts==1,"non-lock failure retried");}
        using var entered=new ManualResetEventSlim();using var release=new ManualResetEventSlim();
        using var old=new CancellationTokenSource();using var queued=new CancellationTokenSource();
        writes.Clear();
        var slow=WindowsClipboard.WriteTextAsync(1,"old",old.Token,(_,text,token)=>{
            entered.Set();if(!release.Wait(TimeSpan.FromSeconds(5)))throw new TimeoutException();
            token.ThrowIfCancellationRequested();writes.Add(text);
        });
        Check(entered.Wait(TimeSpan.FromSeconds(2))&&!slow.IsCompleted,"slow native operation did not leave caller responsive");
        var skipped=WindowsClipboard.WriteTextAsync(1,"skip",queued.Token,(_,text,_)=>writes.Add(text));
        queued.Cancel();old.Cancel();
        var latest=WindowsClipboard.WriteTextAsync(1,"latest",default,(_,text,_)=>writes.Add(text));
        Check(!latest.IsCompleted,"concurrent native writers");release.Set();
        foreach(var task in new[]{slow,skipped}){try{await task;throw new Exception("Expected cancellation");}catch(OperationCanceledException){checks++;}}
        Check(await latest&&writes.SequenceEqual(new[]{"latest"}),"cancelled / stale write reached clipboard");
        Console.WriteLine($"BACKGROUND CLIPBOARD PASS {checks}: simulated native delays, Unicode, contention, serialization, cancellation; no real clipboard access");
        return checks;
    }
}
