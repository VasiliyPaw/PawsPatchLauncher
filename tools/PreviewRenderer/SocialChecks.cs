using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class SocialChecks
{
    private const BindingFlags Flags=BindingFlags.NonPublic|BindingFlags.Instance;
    private static object? Invoke(MainWindow w,string name,params object?[] args)=>typeof(MainWindow).GetMethod(name,Flags)!.Invoke(w,args);
    private static void Set(MainWindow w,string name,object? value)=>typeof(MainWindow).GetField(name,Flags)!.SetValue(w,value);
    internal static void Populate(MainWindow w,string mode)
    {
        var chat=mode is "chat" or "failed" or "details";
        if(!ActivityStore.IsSmokeTest)throw new InvalidOperationException("Social fixtures require smoke mode.");
        AccountChecks.Populate(w,"avatar");
        var service=(AccountService)typeof(MainWindow).GetField("_account",Flags)!.GetValue(w)!;
        var owner=Guid.Parse(service.UserId);var peer=Guid.NewGuid();var third=Guid.NewGuid();
        Set(w,"_socialPlayers",(IReadOnlyList<SocialPlayer>)(mode=="empty"?[]:new[]{new SocialPlayer(peer,"Huheru","friend",2,"playing",DateTimeOffset.UtcNow,DateTimeOffset.UtcNow.AddMinutes(-37),"beta","{\"core\":true,\"russian\":true,\"colors\":false,\"siege\":true,\"desync\":true,\"hostility\":false,\"roaming\":true,\"additional_roaming\":true,\"powers_shards\":false,\"large_maps\":true}",Configuration:"PAW-BETA-IW0-SP2-RM1-SG1-LM1-RU1-CL0-OOS1-PS0"),new SocialPlayer(third,"Союзник_7","incoming")}));
        if(mode=="outgoing")Set(w,"_socialPlayers",(IReadOnlyList<SocialPlayer>)new[]{new SocialPlayer(third,"Длинный_ник_12345678901234","outgoing")});
        Set(w,"_socialPeer",chat?peer:null);
        Set(w,"_socialListReceived",DateTimeOffset.UtcNow);
        Set(w,"_socialLoadedChat",chat?service.UserId+"|"+peer:null);
        Set(w,"_socialMessages",(IReadOnlyList<SocialMessage>)(chat?new[]{
            new SocialMessage(peer,Guid.NewGuid(),owner,"Привет! Сегодня играем?","text",DateTimeOffset.Now.AddMinutes(-2)),
            new SocialMessage(owner,Guid.NewGuid(),peer,"Да, после проверки настроек 🙂","text",DateTimeOffset.Now.AddMinutes(-1))}:[]));
        Set(w,"_socialPending",(IReadOnlyList<PendingSocialMessage>)(chat?new[]{new PendingSocialMessage(owner,peer,Guid.NewGuid(),"Сейчас подключусь","text",mode=="failed"?"delivery_timeout":"")}:[]));
        Invoke(w,"SetActivePage","friends");Invoke(w,"RenderSocialRows");Invoke(w,"RenderSocialMessages");Invoke(w,"RenderSocialIdentity");
        if(mode is "requests" or "outgoing")Invoke(w,"SwitchSocialSection","requests");
        if(mode=="outgoing")Invoke(w,"SwitchSocialRequests","outgoing");
        if(mode=="details")Invoke(w,"ShowSocialDetails",((IReadOnlyList<SocialPlayer>)typeof(MainWindow).GetField("_socialPlayers",Flags)!.GetValue(w)!).First(p=>p.Relation=="friend"));
    }
    internal static void Run(string language)
    {
        var w=new MainWindow();int checks=0;
        void Check(bool ok,string why){checks++;if(!ok)throw new Exception("Social UI: "+why);}
        T Control<T>(string name)=>(T)w.FindName(name);
        try {
            var text=(PawsPatchLauncher.Localization)typeof(MainWindow).GetField("_text",Flags)!.GetValue(w)!;text.SetLanguage(language);Invoke(w,"ApplyLanguage");
            Populate(w,"chat");
            Check(Control<Border>("FriendsChatCard").Visibility==Visibility.Visible,"chat hidden");
            Check(Control<StackPanel>("FriendsMessagesPanel").Children.Count==3,"confirmed and pending messages inline");
            Check(Control<StackPanel>("FriendsOutboxPanel").Children.Count==0,"separate queue UI remains");
            Check(Control<StackPanel>("FriendsRowsPanel").Children.Count==1,"chats must contain only friends");
            var row = Control<StackPanel>("FriendsRowsPanel").Children[0];
            Invoke(w,"RenderSocialRows");
            Check(ReferenceEquals(row,Control<StackPanel>("FriendsRowsPanel").Children[0]),"unchanged poll rebuilds focused row");
            Check(Control<Border>("FriendsAddPanel").Visibility==Visibility.Collapsed,"add form takes space by default");
            Check(Control<Button>("FriendsShowAddButton").Background.ToString()=="#FF216343","add friend is not green");
            Check(Control<TextBlock>("FriendsChatsBadgeText").Text=="2" && Control<TextBlock>("FriendsRequestsBadgeText").Text=="1","tab counts");
            Check(Control<Border>("FriendsNavBadge").Visibility==Visibility.Collapsed,"active Friends nav badge");
            Invoke(w,"SetActivePage","home");
            Check(Control<Border>("FriendsNavBadge").Visibility==Visibility.Visible && Control<TextBlock>("FriendsNavBadgeText").Text=="3","background notification count");
            Invoke(w,"SetActivePage","friends");
            Control<TextBox>("FriendsMessageInput").Text="draft across tabs";
            Invoke(w,"SwitchSocialSection","requests");
            Check(Control<StackPanel>("FriendsRowsPanel").Children.Count==1,"incoming request row isolated");
            Check(Control<WrapPanel>("FriendsRequestTabs").Visibility==Visibility.Visible,"request sub-tabs missing");
            Check(Control<StackPanel>("FriendsRowsPanel").Children[0] is Border,"request is not a compact card");
            Invoke(w,"SwitchSocialRequests","outgoing");
            Check(Control<StackPanel>("FriendsRowsPanel").Children.Count==0 && Control<TextBlock>("FriendsListEmptyText").Visibility==Visibility.Visible,"outgoing list leaks incoming requests");
            Invoke(w,"SwitchSocialRequests","incoming");
            Check(Control<Border>("FriendsChatCard").Visibility==Visibility.Collapsed,"requests shows private conversation");
            Invoke(w,"SwitchSocialSection","chats");
            Check(Control<TextBox>("FriendsMessageInput").Text=="draft across tabs","tabs cleared chat draft");
            Check(Control<Border>("FriendsChatCard").Visibility==Visibility.Visible,"return to selected chat");
            Invoke(w,"FriendsShowAdd_Click",Control<Button>("FriendsShowAddButton"),new RoutedEventArgs());
            Check(Control<Border>("FriendsAddPanel").Visibility==Visibility.Visible,"add form did not open");
            Check(Control<System.Windows.Documents.Run>("FriendsChatName").Text.Contains("Huheru"),"peer title");
            Check(Control<TextBox>("FriendsMessageInput").MaxLength==2000,"input bound");
            Check(w.FindName("AccountCancelButton") is null,"back-to-friends control remains");
            Check(Control<Button>("AccountDeleteButton").Background.ToString()=="#FF653A38","delete not red");
            var visibilityPolicy=typeof(MainWindow).GetMethod("SocialViewCanRead",BindingFlags.NonPublic|BindingFlags.Static)!;
            foreach(var state in new[]{
                (true,false,"friends","chats",true,0d,false,true),
                (true,false,"friends","chats",true,20d,false,true),
                (false,false,"friends","chats",true,0d,false,false),
                (true,true,"friends","chats",true,0d,false,false),
                (true,false,"home","chats",true,0d,false,false),
                (true,false,"account","chats",true,0d,false,false),
                (true,false,"friends","requests",true,0d,false,false),
                (true,false,"friends","chats",false,0d,false,false),
                (true,false,"friends","chats",true,21d,false,false),
                (true,false,"friends","chats",true,0d,true,false),
                (true,false,"friends","chats",true,double.NaN,false,false)})
                Check((bool)visibilityPolicy.Invoke(null,[state.Item1,state.Item2,state.Item3,state.Item4,state.Item5,state.Item6,state.Item7])! == state.Item8,"read visibility policy: "+state);
            var content=(FrameworkElement)w.Content;
            foreach(var size in new[]{new Size(1440,900),new Size(1050,680)}) {
                content.Measure(size);content.Arrange(new Rect(size));content.UpdateLayout();
                foreach(var name in new[]{"FriendsNicknameInput","FriendsAddButton","FriendsMessageInput","FriendsSendButton"}) {
                    var control=Control<FrameworkElement>(name);var bounds=control.TransformToAncestor(content).TransformBounds(new Rect(control.RenderSize));
                    Check(control.ActualWidth>=(name=="FriendsSendButton"?38:name=="FriendsAddButton"?32:45) && bounds.Left>=0 && bounds.Right<=size.Width,"horizontal clipping: "+name);
                }
            }
            // Leave a private draft, then switch identity to guest. All private view state must vanish.
            Control<TextBox>("FriendsMessageInput").Text="private draft";
            var old=(AccountService)typeof(MainWindow).GetField("_account",Flags)!.GetValue(w)!;
            Set(w,"_account",new AccountService(new AccountSessionStore(Path.Combine(ActivityStore.Root,"guest-fixture-"+Guid.NewGuid()))));old.Dispose();
            Invoke(w,"RenderAccount");
            Check(Control<Border>("FriendsChatCard").Visibility==Visibility.Collapsed,"guest chat visible");
            Check(Control<StackPanel>("FriendsMessagesPanel").Children.Count==0,"guest retained messages");
            Check(Control<StackPanel>("FriendsOutboxPanel").Children.Count==0,"guest retained queue");
            Check(Control<TextBox>("FriendsMessageInput").Text=="","guest retained draft");
            Invoke(w,"SetActivePage","home");
            Check(Control<Border>("FriendsNavBadge").Visibility==Visibility.Collapsed,"guest retained notification");
            Check(Control<Border>("FriendsChatsBadge").Visibility==Visibility.Collapsed && Control<Border>("FriendsRequestsBadge").Visibility==Visibility.Collapsed,"guest retained tab counts");
            Check(Control<StackPanel>("FriendsRowsPanel").Children.Count==0,"guest retained friends");
            Check(Control<Border>("FriendsChatEmptyCard").Visibility==Visibility.Collapsed,"empty list has redundant choose-friend card");
            Console.WriteLine($"SOCIAL UI PASS {checks} {language}: private mock fixtures, layout, account clearing and cosmetic regression");
        } finally {w.Close();}
    }
}
