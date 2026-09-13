using PawsPatchLauncher;

internal static class ChatMemoryCacheTests
{
    internal static int Run()
    {
        int checks = 0;
        void Check(bool ok, string why) { checks++; if (!ok) throw new Exception("Chat cache: " + why); }
        var cache = new ChatMemoryCache(); var owner = Guid.NewGuid(); var peer = Guid.NewGuid();
        var time = DateTimeOffset.UtcNow;
        SocialMessage Message(int i) => new(peer, new Guid(i, 0, 0, new byte[8]), owner, "message " + i, "text", time.AddSeconds(i), i);
        var messages = Enumerable.Range(1, 250).Select(Message).ToArray();
        SocialOffer Offer(SocialMessage m) => new(m.MessageId, peer, owner, "config", "config", null, null, null, "pending", time, time.AddDays(1), null, null);
        cache.SetOwner(owner);
        cache.Store(owner, peer, new(messages, [Offer(messages[0]), Offer(messages[^1])], 3, false, true));
        Check(cache.TryRead(owner, peer, out var snapshot), "stored conversation missing");
        Check(snapshot.Messages.Count == 200 && snapshot.Messages[0].Ordinal == 51 && snapshot.Messages[^1].Ordinal == 250, "bounded ordered tail");
        Check(snapshot.More && snapshot.Trimmed && snapshot.Revision == 3, "paging/retention flags lost");
        Check(snapshot.Offers.Count == 1 && snapshot.Offers[0].Id == messages[^1].MessageId, "offers outside retained history survived");
        messages[^1] = Message(9999);
        Check(snapshot.Messages[^1].Ordinal == 250, "snapshot shares mutable source array");
        var sent = Message(251) with { SenderId = owner, RecipientId = peer };
        cache.AppendSent(owner, peer, sent); cache.AppendSent(owner, peer, sent);
        cache.TryRead(owner, peer, out snapshot);
        Check(snapshot.Messages.Count == 200 && snapshot.Messages.Count(m => m.MessageId == sent.MessageId) == 1, "inactive send lost or duplicated");
        Check(!cache.TryRead(Guid.NewGuid(), peer, out _), "other owner read private history");
        cache.Store(Guid.NewGuid(), peer, new([], [], 9, false, false));
        cache.TryRead(owner, peer, out snapshot); Check(snapshot.Revision == 3, "stale owner overwrote history");
        var peers = Enumerable.Range(0, 19).Select(_ => Guid.NewGuid()).ToArray();
        foreach (var id in peers) cache.Store(owner, id, new([], [], 0, false, false));
        cache.TryRead(owner, peer, out _);
        var newest = Guid.NewGuid(); cache.Store(owner, newest, new([], [], 0, false, false));
        Check(cache.Count == 20 && cache.TryRead(owner, peer, out _) && !cache.TryRead(owner, peers[0], out _), "LRU eviction discards recently opened chat");
        cache.Prune([peer]); Check(cache.Count == 1, "removed/blocked contacts remain cached");
        cache.SetOwner(Guid.NewGuid()); Check(cache.Count == 0 && !cache.TryRead(owner, peer, out _), "account switch keeps previous history");
        cache.SetOwner(owner); cache.Store(owner, peer, new([], [], 0, false, false));
        Check(cache.TryRead(owner, peer, out snapshot) && snapshot.Messages.Count == 0, "empty conversations are not cached");
        cache.Clear(); Check(cache.Count == 0 && !cache.TryRead(owner, peer, out _), "logout retains memory");
        return checks;
    }
}
