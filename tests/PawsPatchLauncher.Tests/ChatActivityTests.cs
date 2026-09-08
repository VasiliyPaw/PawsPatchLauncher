using System.Text.Json;
using PawsPatchLauncher;

internal static class ChatActivityTests
{
    public static int Run()
    {
        int n=0;void Check(bool ok,string message){n++;if(!ok)throw new Exception("Chat activity: "+message);}
        var owner=Guid.NewGuid();var a=Guid.NewGuid();var b=Guid.NewGuid();var c=Guid.NewGuid();
        var time=new DateTimeOffset(2026,9,9,0,0,0,TimeSpan.Zero);
        var order=new ChatActivityOrder();
        var players=new[]{new SocialPlayer(a,"alpha","friend"),new SocialPlayer(b,"beta","friend"),new SocialPlayer(c,"charlie","friend")};
        Guid[] Sorted(IEnumerable<SocialMessage>? messages=null,IEnumerable<PendingSocialMessage>? pending=null,IEnumerable<SocialOffer>? offers=null)
            =>order.Sort(owner.ToString(),players,messages??[],pending??[],offers??[]).Select(p=>p.Id).ToArray();
        Check(Sorted().SequenceEqual(new[]{a,b,c}),"empty alphabetical fallback");
        players[1]=players[1] with {LastMessageAt=time,LastMessageOrdinal=4};
        Check(Sorted()[0]==b,"server metadata ignored");
        players[2]=players[2] with {LastMessageAt=time,LastMessageOrdinal=5};
        Check(Sorted()[0]==c,"same-time ordinal tie");
        var incoming=new SocialMessage(a,Guid.NewGuid(),owner,"in","text",time.AddMinutes(1),6);
        Check(Sorted([incoming])[0]==a,"incoming message ignored");
        Check(Sorted()[0]==a,"older server poll undid observed activity");
        var outgoing=new SocialMessage(owner,Guid.NewGuid(),b,"out","text",time.AddMinutes(2),7);
        Check(Sorted([outgoing])[0]==b,"outgoing message ignored");
        var pending=new PendingSocialMessage(owner,c,Guid.NewGuid(),"pending","text"){CreatedAt=time.AddMinutes(3)};
        Check(Sorted(pending:[pending])[0]==c,"optimistic message ignored");
        Check(Sorted()[0]==b,"deleted optimistic message left phantom activity");
        Check(Sorted(pending:[pending with {Owner=Guid.NewGuid()}])[0]==b,"other account outbox leaked");
        Check(Sorted([incoming with {SenderId=c,RecipientId=Guid.NewGuid(),CreatedAt=time.AddYears(1)}])[0]==b,"unrelated message leaked");
        for(var i=0;i<150;i++)
        {
            var index=i%3;players[index]=players[index] with {LastMessageAt=time.AddMinutes(4+i),LastMessageOrdinal=8+i};
            var actual=Sorted();
            Check(actual[0]==players[index].Id&&actual.Distinct().Count()==3,"burst duplicates/incorrect latest");
        }
        var fresh=new ChatActivityOrder();
        Check(fresh.Sort(owner.ToString(),players,[],[],[]).Select(p=>p.Id).SequenceEqual(Sorted()),"restart order changed");
        order.SetOwner(Guid.NewGuid().ToString());
        players=players.Select(p=>p with{LastMessageAt=null,LastMessageOrdinal=0}).ToArray();
        Check(Sorted().SequenceEqual(new[]{a,b,c}),"account activity retained");
        using var modern=JsonDocument.Parse(JsonSerializer.Serialize(new{id=a,nickname="alpha",relation="friend",last_message_at=time,last_message_ordinal=999}));
        var parsed=AccountService.ReadSocialPlayer(modern.RootElement);
        Check(parsed.LastMessageAt==time&&parsed.LastMessageOrdinal==999,"metadata parser");
        using var legacy=JsonDocument.Parse(JsonSerializer.Serialize(new{id=a,nickname="alpha",relation="friend"}));
        Check(AccountService.ReadSocialPlayer(legacy.RootElement).LastMessageAt is null,"legacy response failed");
        Console.WriteLine($"CHAT ACTIVITY POLICY PASS {n}: server/restart, both directions, pending, ties, stale polls, account isolation, bursts and metadata");
        return n;
    }
}
