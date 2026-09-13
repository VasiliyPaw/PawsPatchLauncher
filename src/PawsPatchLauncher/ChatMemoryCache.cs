namespace PawsPatchLauncher;

// Session-only message data. Never keeps controls, media, credentials or another account's history.
internal sealed class ChatMemoryCache
{
    internal const int ConversationLimit = 20;
    internal const int MessageLimit = 200;
    internal sealed record Snapshot(IReadOnlyList<SocialMessage> Messages, IReadOnlyList<SocialOffer> Offers,
        long Revision, bool More, bool Trimmed);
    private Guid? _owner;
    private readonly Dictionary<Guid, Snapshot> _entries = new();
    private readonly LinkedList<Guid> _recent = new();
    internal int Count => _entries.Count;

    internal void SetOwner(Guid owner)
    {
        if (_owner == owner) return;
        Clear(); _owner = owner;
    }
    internal void Clear() { _entries.Clear(); _recent.Clear(); _owner = null; }
    internal void Remove(Guid peer) { _entries.Remove(peer); _recent.Remove(peer); }
    internal void Prune(IEnumerable<Guid> peers)
    {
        var available = peers.ToHashSet();
        foreach (var peer in _entries.Keys.Where(p => !available.Contains(p)).ToArray()) Remove(peer);
    }
    internal bool TryRead(Guid owner, Guid peer, out Snapshot snapshot)
    {
        snapshot = null!;
        if (_owner != owner || !_entries.TryGetValue(peer, out var entry)) return false;
        _recent.Remove(peer); _recent.AddLast(peer); snapshot = entry; return true;
    }
    internal void Store(Guid owner, Guid peer, Snapshot snapshot)
    {
        if (_owner != owner) return;
        var all = snapshot.Messages.Where(m => m.SenderId == owner && m.RecipientId == peer
            || m.SenderId == peer && m.RecipientId == owner)
            .GroupBy(m => (m.SenderId, m.MessageId)).Select(g => g.Last())
            .OrderBy(m => m.CreatedAt).ThenBy(m => m.Ordinal).ToArray();
        var messages = all.TakeLast(MessageLimit).ToArray();
        var ids = messages.Select(m => (m.SenderId, m.MessageId)).ToHashSet();
        _entries[peer] = snapshot with { Messages = messages,
            Offers = snapshot.Offers.Where(o => ids.Contains((o.Sender, o.Id))).ToArray(),
            More = snapshot.More || all.Length > messages.Length };
        _recent.Remove(peer); _recent.AddLast(peer);
        while (_entries.Count > ConversationLimit) Remove(_recent.First!.Value);
    }
    internal void AppendSent(Guid owner, Guid peer, SocialMessage message)
    {
        if (_owner != owner || !_entries.TryGetValue(peer, out var snapshot)) return;
        Store(owner, peer, snapshot with { Messages = snapshot.Messages.Append(message).ToArray() });
    }
}
