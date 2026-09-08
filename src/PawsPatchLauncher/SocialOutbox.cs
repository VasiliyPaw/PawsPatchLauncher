using System.Security.Cryptography;
using System.Text.Json;

namespace PawsPatchLauncher;

public sealed record PendingSocialMessage(Guid Owner,Guid Target,Guid Id,string Body,string Kind,string Error="")
{
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? RetriedAt { get; init; }
    public DateTimeOffset Deadline => (RetriedAt ?? CreatedAt).AddMinutes(1);
    public bool TimedOut(DateTimeOffset now) => Error.Length == 0 && now >= Deadline;
}

// Per-account, DPAPI-protected, excluded with the account directory from diagnostics.
// Durable IDs are allocated before any HTTP request. Two processes may retry the same
// entry safely: the server deduplicates (owner,id), not message text or timestamps.
public sealed class SocialOutbox(string root)
{
    private readonly string directory=Path.Combine(root,"account","outbox");
    public async Task<IReadOnlyList<PendingSocialMessage>> ReadAsync(Guid owner,CancellationToken ct=default) =>
        await ChangeAsync(owner,items=>items.ToArray(),ct,write:false);
    public Task AddAsync(PendingSocialMessage item,CancellationToken ct=default) => ChangeAsync(item.Owner,items=> {
        Validate(item,item.Owner);
        var prior=items.FirstOrDefault(m=>m.Id==item.Id);
        if (prior is not null) { if(prior!=item) throw new InvalidDataException("Outbox identifier conflict."); return true; }
        if(items.Count>=100) throw new AccountException("outbox_full"); items.Add(item); return true;
    },ct);
    public Task RemoveAsync(Guid owner,Guid id,CancellationToken ct=default) => ChangeAsync(owner,items=> {items.RemoveAll(m=>m.Id==id);return true;},ct);
    public Task FailAsync(Guid owner,Guid id,string code,CancellationToken ct=default) => ChangeAsync(owner,items=> {
        var i=items.FindIndex(m=>m.Id==id); if(i>=0)items[i]=items[i] with {Error=code};return true;
    },ct);
    public Task RetryAsync(Guid owner,Guid id,CancellationToken ct=default) => ChangeAsync(owner,items=> {
        var i=items.FindIndex(m=>m.Id==id); if(i>=0)items[i]=items[i] with {Error="",RetriedAt=DateTimeOffset.UtcNow};return true;
    },ct);
    public Task FailAttemptAsync(PendingSocialMessage attempt,string code,CancellationToken ct=default) => ChangeAsync(attempt.Owner,items=> {
        var i=items.FindIndex(m=>m.Id==attempt.Id);
        if(i>=0 && items[i].CreatedAt==attempt.CreatedAt && items[i].RetriedAt==attempt.RetriedAt)
            items[i]=items[i] with {Error=code};return true;
    },ct);
    private async Task<T> ChangeAsync<T>(Guid owner,Func<List<PendingSocialMessage>,T> change,CancellationToken ct,bool write=true)
    {
        if(owner==Guid.Empty)throw new InvalidDataException("Missing outbox owner.");
        Directory.CreateDirectory(directory);
        var path=Path.Combine(directory,owner.ToString("N")+".dat");
        FileStream? gate=null;
        for(var attempt=0;gate is null;attempt++) {
            ct.ThrowIfCancellationRequested();
            try {gate=new FileStream(path+".lock",FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None);}
            catch(IOException) when(attempt<100){await Task.Delay(50,ct).ConfigureAwait(false);}
        }
        using(gate) {
            var items=new List<PendingSocialMessage>();
            if(File.Exists(path)) {
                if(new FileInfo(path).Length>1500000)throw new InvalidDataException("Outbox too large.");
                var data=WindowsUserProtection.Transform(File.ReadAllBytes(path),false);
                try {
                    items=JsonSerializer.Deserialize<List<PendingSocialMessage>>(data)??throw new InvalidDataException("Invalid outbox.");
                    using var legacy=JsonDocument.Parse(data);
                    for(var i=0;i<items.Count;i++)
                        if(!legacy.RootElement[i].TryGetProperty(nameof(PendingSocialMessage.CreatedAt),out _))
                            items[i]=items[i] with {CreatedAt=new DateTimeOffset(File.GetLastWriteTimeUtc(path))};
                    // Old builds had no timestamp. The file's stable write time prevents
                    // every poll/restart from resetting their one-minute attempt window.
                }
                finally {CryptographicOperations.ZeroMemory(data);}
                if(items.Count>100 || items.Select(m=>m.Id).Distinct().Count()!=items.Count)throw new InvalidDataException("Invalid outbox count.");
                foreach(var item in items)Validate(item,owner);
            }
            var result=change(items);
            if(!write)return result;
            foreach(var item in items)Validate(item,owner);
            var plain=JsonSerializer.SerializeToUtf8Bytes(items); byte[] encrypted;
            try {encrypted=WindowsUserProtection.Transform(plain,true);} finally {CryptographicOperations.ZeroMemory(plain);}
            var temp=path+"."+Guid.NewGuid().ToString("N")+".tmp";
            try {
                using(var stream=new FileStream(temp,FileMode.CreateNew,FileAccess.Write,FileShare.None)){stream.Write(encrypted);stream.Flush(true);}
                File.Move(temp,path,true);
            } finally {if(File.Exists(temp))File.Delete(temp);}
            return result;
        }
    }
    private static void Validate(PendingSocialMessage m,Guid owner)
    {
        if(m.Owner!=owner||m.Target==Guid.Empty||m.Target==owner||m.Id==Guid.Empty||m.Error.Length>64)throw new InvalidDataException("Invalid outbox owner.");
        AccountService.ValidateMessage(m.Body,m.Kind);
    }
}
