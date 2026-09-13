using PawsPatchLauncher;

internal static class ChatDividerTests
{
    internal static int Run()
    {
        var n=0;void Check(bool ok,string reason){if(!ok)throw new Exception(reason);n++;}
        var owner=Guid.NewGuid();var peer=Guid.NewGuid();var other=Guid.NewGuid();
        SocialMessage Message(long ordinal,bool own=false)=>new(own?owner:peer,Guid.NewGuid(),own?peer:owner,"text","text",DateTimeOffset.UtcNow.AddMinutes(ordinal),ordinal);
        var messages=new[]{Message(1),Message(2,true),Message(3),Message(4,true),Message(5)};
        var player=new SocialPlayer(peer,"friend","friend",Unread:2,LastMessageOrdinal:5);
        var divider=new ChatUnreadDivider();divider.Begin(owner,player);
        Check(divider.Boundary(messages)==messages[2].MessageId,"incoming boundary ignores own messages");
        divider.Begin(owner,player with {Unread=0});
        Check(divider.Boundary(messages)==messages[2].MessageId,"acknowledgement removed visit marker");
        var next=Message(6);messages=messages.Append(next).ToArray();
        Check(divider.Boundary(messages)==messages[2].MessageId,"live incoming moved existing boundary");
        divider.End();divider.Begin(owner,player with {Unread=3,LastMessageOrdinal=6});
        Check(divider.Boundary(messages) is null,"reentry redisplayed old unread after delayed acknowledgement");
        divider.End();var later=Message(7);messages=messages.Append(later).ToArray();
        divider.Begin(owner,player with {Unread=1,LastMessageOrdinal=7});
        Check(divider.Boundary(messages)==later.MessageId,"incoming while chat closed did not mark new");
        divider.Dismiss();Check(divider.Boundary(messages) is null,"reply did not dismiss new");
        divider.End();divider.Begin(owner,player with {Unread=0,LastMessageOrdinal=7});
        Check(divider.Boundary(messages.Append(Message(8))) is null,"incoming during open visit created divider");
        divider.End();divider.Begin(other,player with {Unread=2});
        Check(divider.Boundary(messages) is null,"other account messages leaked");
        var fresh=new ChatUnreadDivider();fresh.Begin(owner,player);
        Check(fresh.Boundary(messages.Skip(4))==messages[4].MessageId,"partial page lacks unread boundary");
        Check(fresh.Boundary(messages)==messages[2].MessageId,"loading earlier messages did not restore boundary");
        Console.WriteLine($"CHAT DIVIDERS PASS {n}: incoming-only, visit/reply, live arrivals, pagination, account isolation");return n;
    }
}
