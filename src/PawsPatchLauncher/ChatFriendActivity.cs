using System.Security.Cryptography;
using System.Text.Json;

namespace PawsPatchLauncher;

/// <summary>Remembers when this account first observes an accepted friendship.</summary>
public sealed class ChatFriendActivity(string root)
{
    private Guid? _owner;
    private Dictionary<Guid,DateTimeOffset?>? _friends;
    private string PathFor(Guid owner)=>Path.Combine(root,"account","chat-friends",owner.ToString("N")+".dat");

    // Call only for a successful, complete server list, never for a filtered view,
    // logout clearing or a failed request. Existing friends form the first baseline.
    public IReadOnlyDictionary<Guid,DateTimeOffset?> Update(Guid owner,IReadOnlyList<SocialPlayer> players,DateTimeOffset now)
    {
        if(owner==Guid.Empty)throw new ArgumentException("Missing chat owner.",nameof(owner));
        if(_owner!=owner) { _owner=owner;_friends=Read(owner); }
        var current=players.Where(p=>p.Relation=="friend"&&p.IsFriend).Select(p=>p.Id).Distinct().ToArray();
        if(_friends is not null && current.Length==_friends.Count && current.All(_friends.ContainsKey))return _friends;
        var next=new Dictionary<Guid,DateTimeOffset?>();
        foreach(var peer in current)
            next[peer]=_friends is null?null:_friends.TryGetValue(peer,out var added)?added:now;
        _friends=next;
        Save(owner,next);
        return next;
    }

    private Dictionary<Guid,DateTimeOffset?>? Read(Guid owner)
    {
        try
        {
            var path=PathFor(owner);
            if(!File.Exists(path)||new FileInfo(path).Length>1_000_000)return null;
            var plain=WindowsUserProtection.Transform(File.ReadAllBytes(path),false);
            try
            {
                var friends=JsonSerializer.Deserialize<Dictionary<Guid,DateTimeOffset?>>(plain);
                return friends is {Count:<=10000}&&!friends.ContainsKey(Guid.Empty)&&!friends.ContainsKey(owner)?friends:null;
            }
            finally { CryptographicOperations.ZeroMemory(plain); }
        }
        catch(Exception e) when(e is IOException or UnauthorizedAccessException or CryptographicException or JsonException or System.ComponentModel.Win32Exception) { return null; }
    }

    private void Save(Guid owner,Dictionary<Guid,DateTimeOffset?> friends)
    {
        var path=PathFor(owner);var temporary=path+"."+Guid.NewGuid().ToString("N")+".tmp";
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            var plain=JsonSerializer.SerializeToUtf8Bytes(friends);byte[] encrypted;
            try { encrypted=WindowsUserProtection.Transform(plain,true); }
            finally { CryptographicOperations.ZeroMemory(plain); }
            File.WriteAllBytes(temporary,encrypted);File.Move(temporary,path,true);
        }
        catch(Exception e) when(e is IOException or UnauthorizedAccessException or CryptographicException or System.ComponentModel.Win32Exception)
        {
            // Ordering still works for this session if local storage is unavailable.
        }
        finally { try { if(File.Exists(temporary))File.Delete(temporary); } catch(IOException){} catch(UnauthorizedAccessException){} }
    }
}
