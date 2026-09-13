namespace PawsPatchLauncher;

// A divider belongs to one visit. Server unread counts may already be cleared by
// acknowledgement; that must not remove the marker until leaving or replying.
public sealed class ChatUnreadDivider
{
    private readonly Dictionary<(Guid Owner, Guid Peer), long> _dismissedThrough = [];
    private (Guid Owner, Guid Peer)? _visit;
    private int _unread;
    private long _ceiling, _observed;
    public long Revision { get; private set; }

    public void Begin(Guid owner, SocialPlayer peer)
    {
        if (_visit == (owner, peer.Id)) return;
        End();
        _visit = (owner, peer.Id); _unread = Math.Max(0, peer.Unread);
        _ceiling = peer.LastMessageOrdinal; _observed = 0; Revision++;
    }

    public Guid? Boundary(IEnumerable<SocialMessage> messages)
    {
        if (_visit is not { } visit) return null;
        var incoming = messages.Where(m => m.SenderId == visit.Peer && m.RecipientId == visit.Owner)
            .OrderBy(m => m.Ordinal).ThenBy(m => m.CreatedAt).ToArray();
        _observed = Math.Max(_observed, incoming.Select(m => m.Ordinal).DefaultIfEmpty().Max());
        if (_unread == 0) return null;
        if (_ceiling == 0 && incoming.Length > 0) _ceiling = _observed;
        var dismissed = _dismissedThrough.GetValueOrDefault(visit);
        return incoming.Where(m => m.Ordinal <= _ceiling).TakeLast(_unread)
            .FirstOrDefault(m => m.Ordinal > dismissed)?.MessageId;
    }

    public void Dismiss()
    {
        if (_visit is not { } visit) return;
        _dismissedThrough[visit] = Math.Max(_dismissedThrough.GetValueOrDefault(visit), Math.Max(_ceiling, _observed));
        _unread = 0; Revision++;
    }

    public void End()
    {
        if (_visit is null) return;
        Dismiss(); _visit = null; _observed = _ceiling = 0;
    }
}
