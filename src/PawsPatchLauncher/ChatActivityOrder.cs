namespace PawsPatchLauncher;

/// <summary>Account-scoped conversation order. Older polls/read pages cannot undo known activity.</summary>
public sealed class ChatActivityOrder
{
    private readonly Dictionary<Guid,(DateTimeOffset At,long Ordinal)> _confirmed = [];
    private string? _owner;
    public void SetOwner(string owner)
    {
        if(_owner==owner)return;
        _owner=owner; _confirmed.Clear();
    }
    public void Observe(Guid peer,DateTimeOffset? at,long ordinal=0)
    {
        if(at is null)return;
        var stamp=(at.Value,ordinal);
        if(!_confirmed.TryGetValue(peer,out var previous)||stamp.CompareTo(previous)>0)_confirmed[peer]=stamp;
    }
    public IReadOnlyList<SocialPlayer> Sort(string owner,IReadOnlyList<SocialPlayer> players,
        IEnumerable<SocialMessage> messages,IEnumerable<PendingSocialMessage> pending,IEnumerable<SocialOffer> offers)
    {
        SetOwner(owner);
        var peers=players.Where(p=>p.Relation=="friend").Select(p=>p.Id).ToHashSet();
        foreach(var id in _confirmed.Keys.Where(id=>!peers.Contains(id)).ToArray())_confirmed.Remove(id);
        foreach(var player in players.Where(p=>peers.Contains(p.Id)))Observe(player.Id,player.LastMessageAt,player.LastMessageOrdinal);
        if(Guid.TryParse(owner,out var actor))
            foreach(var message in messages)
            {
                var peer=message.SenderId==actor?message.RecipientId:message.RecipientId==actor?message.SenderId:Guid.Empty;
                if(peers.Contains(peer))Observe(peer,message.CreatedAt,message.Ordinal);
            }
        var effective=new Dictionary<Guid,(DateTimeOffset At,long Ordinal)>(_confirmed);
        void Local(Guid peer,DateTimeOffset at)
        {
            if(peers.Contains(peer)&&(!effective.TryGetValue(peer,out var prior)||at>prior.At))effective[peer]=(at,long.MaxValue);
        }
        foreach(var item in pending.Where(m=>m.Owner.ToString()==owner))Local(item.Target,item.CreatedAt);
        foreach(var offer in offers.Where(o=>o.Sender.ToString()==owner))Local(offer.Recipient,offer.CreatedAt);
        return players.Where(p=>p.Relation=="friend").DistinctBy(p=>p.Id)
            .OrderByDescending(p=>effective.GetValueOrDefault(p.Id).At)
            .ThenByDescending(p=>effective.GetValueOrDefault(p.Id).Ordinal)
            .ThenBy(p=>p.Name,StringComparer.CurrentCultureIgnoreCase).ThenBy(p=>p.Id).ToArray();
    }
}
