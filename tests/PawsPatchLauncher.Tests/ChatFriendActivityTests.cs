using PawsPatchLauncher;

internal static class ChatFriendActivityTests
{
    public static int Run()
    {
        var root=Path.Combine(Path.GetTempPath(),"PawsChatFriends-"+Guid.NewGuid().ToString("N"));
        var owner=Guid.NewGuid();var otherOwner=Guid.NewGuid();
        var now=new DateTimeOffset(2026,9,18,12,0,0,TimeSpan.Zero);
        var old=new SocialPlayer(Guid.NewGuid(),"alpha","friend",LastMessageAt:now.AddMinutes(-1));
        var added=new SocialPlayer(Guid.NewGuid(),"zulu","outgoing");
        var official=new SocialPlayer(Guid.NewGuid(),"official","friend",IsFriend:false);
        var store=new ChatFriendActivity(root);var order=new ChatActivityOrder();
        var checks=0;
        void Check(bool value,string why){checks++;if(!value)throw new Exception("Chat friendship: "+why);}
        Guid First(IReadOnlyList<SocialPlayer> players,IReadOnlyDictionary<Guid,DateTimeOffset?> times)
            =>order.Sort(owner.ToString(),players,[],[],[],times)[0].Id;
        try
        {
            var initial=store.Update(owner,[old,added,official],now);
            Check(initial.Count==1&&initial[old.Id] is null,"first snapshot must not promote all old friends or pending requests");
            added=added with {Relation="friend"};
            var joined=store.Update(owner,[old,added,official],now.AddSeconds(1));
            Check(First([old,added],joined)==added.Id,"accepted outgoing request without messages must become first");
            Check(joined[added.Id]==now.AddSeconds(1),"first observed friendship time");
            Check(store.Update(owner,[old,added,official],now.AddSeconds(30))[added.Id]==joined[added.Id],"poll must not renew promotion");
            var disk=new ChatFriendActivity(root);
            var restarted=disk.Update(owner,[old,added,official],now.AddMinutes(1));
            Check(restarted[added.Id]==joined[added.Id]&&First([old,added],restarted)==added.Id,"restart lost order");
            old=old with {LastMessageAt=now.AddMinutes(2),LastMessageOrdinal=2};
            Check(First([old,added],restarted)==old.Id,"later message must move above new friend");
            var pending=new PendingSocialMessage(owner,added.Id,Guid.NewGuid(),"draft","text"){CreatedAt=now.AddMinutes(3)};
            Check(order.Sort(owner.ToString(),[old,added],[],[pending],[],restarted)[0].Id==added.Id,"pending send promotion regressed");
            Check(First([old,added],restarted)==old.Id,"discarded pending send must not remain first");
            var second=new SocialPlayer(Guid.NewGuid(),"zzlast","incoming");
            disk.Update(owner,[old,added,second],now.AddMinutes(3));
            second=second with {Relation="friend"};
            var accepted=disk.Update(owner,[old,added,second],now.AddMinutes(4));
            Check(First([old,added,second],accepted)==second.Id,"accepted incoming request must become first");
            var removed=disk.Update(owner,[old,added with {Relation="blocked"},second],now.AddMinutes(5));
            Check(!removed.ContainsKey(added.Id),"blocked friendship must be forgotten");
            var readded=disk.Update(owner,[old,added,second],now.AddMinutes(6));
            Check(readded[added.Id]==now.AddMinutes(6)&&First([old,added,second],readded)==added.Id,"re-added friend must be first again");
            Check(disk.Update(otherOwner,[old,added],now.AddMinutes(7)).Values.All(v=>v is null),"other account inherited friendship timestamps");
            Check(disk.Update(owner,[old,added,second],now.AddMinutes(8))[added.Id]==now.AddMinutes(6),"account switch lost saved order");
            var offlineFriend=new SocialPlayer(Guid.NewGuid(),"zzzoffline","friend");
            var afterOffline=new ChatFriendActivity(root).Update(owner,[old,added,second,offlineFriend],now.AddMinutes(9));
            Check(First([old,added,second,offlineFriend],afterOffline)==offlineFriend.Id,"friend accepted while launcher was closed must be first");
            var emptyOwner=Guid.NewGuid();
            disk.Update(emptyOwner,[],now);
            Check(disk.Update(emptyOwner,[added],now.AddMinutes(1))[added.Id]==now.AddMinutes(1),"first friend after an empty baseline must be new");
            var file=Path.Combine(root,"account","chat-friends",owner.ToString("N")+".dat");
            Check(!System.Text.Encoding.UTF8.GetString(File.ReadAllBytes(file)).Contains(added.Id.ToString()),"friend identifiers stored unprotected");
            File.WriteAllText(file,"damaged fixture");
            Check(new ChatFriendActivity(root).Update(owner,[old,added],now.AddMinutes(10)).Values.All(v=>v is null),"damaged ordering cache must not break friend list");
            Console.WriteLine($"CHAT FRIEND ACTIVITY PASS {checks}: acceptance, restart, offline arrival, new messages, re-add and account isolation");
            return checks;
        }
        finally { if(Directory.Exists(root))Directory.Delete(root,true); }
    }
}
