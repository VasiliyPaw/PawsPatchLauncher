using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using System.Windows.Media;
using System.Windows.Input;
using System.Text.Json;
using PawsPatchLauncher;
namespace PreviewRenderer;
internal static class AdminChecks
{
    private const BindingFlags F=BindingFlags.NonPublic|BindingFlags.Instance;
    private static object? Call(MainWindow w,string name,params object?[] args)=>typeof(MainWindow).GetMethod(name,F)!.Invoke(w,args);
    private static T Field<T>(MainWindow w,string name)=>(T)typeof(MainWindow).GetField(name,F)!.GetValue(w)!;
    private static void Set(MainWindow w,string name,object? v)=>typeof(MainWindow).GetField(name,F)!.SetValue(w,v);
    private static AccountSession Session(MainWindow w)=>(AccountSession)typeof(AccountService).GetField("_session",F)!.GetValue(Field<AccountService>(w,"_account"))!;
    private static IEnumerable<T> Descendants<T>(DependencyObject node) where T:DependencyObject
    {
        if(node is T value)yield return value;
        for(var i=0;i<VisualTreeHelper.GetChildrenCount(node);i++)foreach(var child in Descendants<T>(VisualTreeHelper.GetChild(node,i)))yield return child;
    }
    internal static void Populate(MainWindow w,string mode)
    {
        if(!ActivityStore.IsSmokeTest)throw new InvalidOperationException("Fixture only");
        var friends=SocialHubChecks.Populate(w);Call(w,"ResetBroadcast");
        var session=Session(w);session.AdminLevel=2;session.ProtectedAdmin=true;Call(w,"RenderAccount");
        var now=DateTimeOffset.UtcNow;
        var users=new[]{new AdminPlayer(friends[0].Id,"nightwatch","Лесной страж",now.AddMinutes(-38),0,false,null,null,"",null,false,true),
            new AdminPlayer(friends[1].Id,"support","Поддержка Paw’s Patch",now.AddHours(-4),1,false,null,null,"",null,false,true),
            new AdminPlayer(friends[2].Id,"old_friend","Старый друг",now.AddDays(-5),0,false,now.AddHours(-1),now.AddDays(1),"Нарушение правил общения",null,false,false),
            new AdminPlayer(Guid.Parse(session.UserId),"paw","Paw",now.AddDays(-10),2,true,null,null,"",null,false,false)};
        Set(w,"_adminSection",mode=="deleted"?"deleted":mode=="bans"?"bans":"users");
        Set(w,"_adminData",new AdminPage(mode=="deleted"?new[]{users[0] with{CreatedAt=now.AddDays(-15),DeletedAt=now.AddDays(-2),IsNew=false}}:mode=="bans"?Array.Empty<AdminPlayer>():users,
            mode=="bans"?new[]{new AdminBan(Guid.NewGuid(),"example@example.invalid",now.AddHours(-1),now.AddDays(1),"Нарушение правил общения")}:Array.Empty<AdminBan>(),false,now));
        Call(w,"BuildAdminLayout");Call(w,"SetActivePage","admin");
        if(mode=="status")
        {
            Set(w,"_adminSection","status");Set(w,"_adminData",null);Call(w,"BuildAdminLayout");
            using var state=JsonDocument.Parse(JsonSerializer.Serialize(new{checked_at=now,cleanup_at=now.AddMinutes(-2),cleanup_ok=true}));
            Call(w,"RenderAdminStatus",state.RootElement);
        }
        if(mode is "role" or "ban")_=(Task)Call(w,"ModerateAsync",users[0],mode)!;
        if(mode=="banned")
        {
            session.ProtectedAdmin=false;session.AdminLevel=0;session.BannedAt=now.AddHours(-1);session.BanUntil=now.AddDays(1);session.BanReason="Нарушение правил общения";
            Call(w,"RenderAccount");Call(w,"SetActivePage","friends");
        }
        if(mode is "chat" or "profile")
        {
            var players=friends.Select((p,i)=>i==0?p with{AdminLevel=1,DisplayName="Поддержка"}:i==1?p with{BannedAt=now,BanUntil=now.AddDays(1),BanReason="Нарушение правил"}:i==2?p with{DeletedAt=now,AvatarRevision=null}:p).ToArray();
            Set(w,"_socialPlayers",(IReadOnlyList<SocialPlayer>)players);Set(w,"_socialPeer",players[0].Id);
            Call(w,"SetActivePage","friends");Call(w,"RenderSocialRows");Call(w,"RenderSocialMessages");Call(w,"RenderSocialIdentity");
            if(mode=="profile")Call(w,"ShowSocialDetails",players[0]);
        }
    }
    internal static void Run(string language)
    {
        var w=new MainWindow{Left=-32000,Top=-32000,ShowActivated=false,ShowInTaskbar=false,WindowStartupLocation=WindowStartupLocation.Manual,Width=1050,Height=680};
        int n=0;void Check(bool ok,string why){n++;if(!ok)throw new Exception("Admin UI: "+why);}
        T C<T>(string name)=>(T)w.FindName(name);
        async Task Scenario()
        {
            Field<PawsPatchLauncher.Localization>(w,"_text").SetLanguage(language);Call(w,"ApplyLanguage");
            Populate(w,"users");w.UpdateLayout();
            Check(C<Button>("AdminNav").Visibility==Visibility.Visible&&C<StackPanel>("AdminPanel").Visibility==Visibility.Visible,"owner navigation");
            Check(Field<StackPanel>(w,"_adminRows").Children.Count==4,"paged cards");
            var bannedCard=Field<StackPanel>(w,"_adminRows").Children[2];
            Check(!Descendants<Button>(bannedCard).Single(b=>b.Content is TextBlock t&&t.Text==(language=="ru"?"Заблокировать почту":"Ban email")).IsEnabled,"already banned email button enabled");
            foreach(var status in new[]{"status","users","bans","deleted"})
            {
                Descendants<Button>(C<StackPanel>("AdminPanel")).Single(b=>Equals(b.Tag,status)).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));w.UpdateLayout();
                Check(Field<string>(w,"_adminSection")==status&&Field<StackPanel>(w,"_adminRows").RenderTransform is TranslateTransform,"tab selection / transition");
            }
            Populate(w,"status");w.UpdateLayout();
            Check(Field<StackPanel>(w,"_adminRows").Children.Count==5,"status service cards");
            Check(Descendants<TextBlock>(Field<StackPanel>(w,"_adminRows")).Count(t=>t.Text==(language=="ru"?"Не проверено":"Not checked"))==2,"unverified email/storage shown as healthy");
            using(var failed=JsonDocument.Parse(JsonSerializer.Serialize(new{checked_at=DateTimeOffset.UtcNow,cleanup_at=DateTimeOffset.UtcNow,cleanup_ok=false})))
                Call(w,"RenderAdminStatus",failed.RootElement);
            Check(Descendants<TextBlock>(Field<StackPanel>(w,"_adminRows")).Any(t=>t.Text==(language=="ru"?"Ошибка":"Error")&&t.Foreground.ToString()=="#FFFFB1A8"),"failed cleanup lacks red badge");
            Call(w,"RenderAdminStatusFailure");
            Check(Field<StackPanel>(w,"_adminRows").Children.Count==1,"failed refresh retains stale healthy cards");
            Populate(w,"users");w.UpdateLayout();
            Check(C<ContentControl>("AccountAdminBadge").Content is Border,"own trusted badge");
            var profile=(AccountService)Field<AccountService>(w,"_account");Check(profile.AdminLevel==2&&profile.ProtectedAdmin,"owner trusted state");
            var user=Field<AdminPage>(w,"_adminData").Users[0];
            var pending=(Task)Call(w,"ModerateAsync",user,"ban")!;await Task.Delay(30);
            Check(C<Border>("ConfirmationOverlay").Visibility==Visibility.Visible,"ban confirmation absent");
            w.UpdateLayout();var inputs=Descendants<TextBox>(C<StackPanel>("ConfirmationChangesPanel")).ToArray();
            Check(inputs.Length==4&&!C<Button>("ConfirmationDeleteButton").IsEnabled,"reason mandatory / three duration fields");
            inputs[0].Text="Rule violation";Check(C<Button>("ConfirmationDeleteButton").IsEnabled,"valid temporary ban not accepted");
            inputs[1].Text="0";Check(!C<Button>("ConfirmationDeleteButton").IsEnabled,"zero ban accepted");
            inputs[3].Text="1";Check(C<Button>("ConfirmationDeleteButton").IsEnabled,"one-minute ban rejected");
            inputs[2].Text="24";Check(!C<Button>("ConfirmationDeleteButton").IsEnabled,"invalid hours accepted");
            C<StackPanel>("ConfirmationChangesPanel").Children.OfType<CheckBox>().Single().IsChecked=true;
            Check(C<Button>("ConfirmationDeleteButton").IsEnabled&&!inputs[1].IsEnabled,"permanent switch");
            await (Task)Call(w,"CompleteConfirmationAsync",false)!;await pending;
            var calls=0;int? selectedRole=null;DateTimeOffset? deadline=null;
            Set(w,"_adminActionOverride",(Func<string,Guid,string,DateTimeOffset?,int?,Task>)((action,id,reason,until,level)=>{calls++;selectedRole=level;deadline=until;return Task.CompletedTask;}));
            // Prevent fixture refresh from changing the preloaded mock social list.
            Set(w,"_socialBusy",true);
            pending=(Task)Call(w,"ModerateAsync",user,"role")!;w.UpdateLayout();
            var choices=Descendants<Button>(C<StackPanel>("ConfirmationChangesPanel")).Where(b=>b.Tag is int).ToArray();
            Check(choices.Length==3&&!C<Button>("ConfirmationDeleteButton").IsEnabled,"role choices / unchanged selection");
            choices[1].RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            Check(C<Border>("ConfirmationOverlay").Visibility==Visibility.Visible&&C<Button>("ConfirmationDeleteButton").IsEnabled,"select role dismissed dialog");
            Check(choices[0].Foreground.ToString()=="#FFF1F5FC","unprivileged role unreadable");
            // Owned popup hit testing must still work for other/future dropdowns.
            var combo=new ComboBox{ItemsSource=new[]{"one","two"}};C<StackPanel>("ConfirmationChangesPanel").Children.Add(combo);w.UpdateLayout();combo.IsDropDownOpen=true;await Task.Delay(60);w.UpdateLayout();
            var item=(ComboBoxItem)combo.ItemContainerGenerator.ContainerFromIndex(0);
            Check(item is not null,"popup item not realized");
            var inside=typeof(MainWindow).GetMethod("InsideCard",BindingFlags.Static|BindingFlags.NonPublic)!;
            Check((bool)inside.Invoke(null,new object[]{item!,C<Border>("ConfirmationCard")})!,"owned popup considered outside");
            combo.IsDropDownOpen=false;
            await (Task)Call(w,"CompleteConfirmationAsync",true)!;await pending;
            Check(calls==1&&selectedRole==1,"confirmed role not dispatched exactly once");
            Check(C<TextBlock>("ToastText").Text==(language=="ru"?"Изменения сохранены.":"Changes saved."),"role success toast absent");
            Set(w,"_adminActionOverride",(Func<string,Guid,string,DateTimeOffset?,int?,Task>)((_,_,_,_,_)=>throw new AccountException("higher_role_required")));
            pending=(Task)Call(w,"ModerateAsync",user,"role")!;w.UpdateLayout();
            Descendants<Button>(C<StackPanel>("ConfirmationChangesPanel")).Single(b=>Equals(b.Tag,2)).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            await (Task)Call(w,"CompleteConfirmationAsync",true)!;await pending;
            Check(C<TextBlock>("ToastText").Text==(string)Call(w,"AccountMessage","higher_role_required")!,"role failure hidden");
            Check(!Field<bool>(w,"_adminBusy")&&C<Grid>("MainBody").IsEnabled,"failure left form locked");
            Set(w,"_adminActionOverride",(Func<string,Guid,string,DateTimeOffset?,int?,Task>)((action,id,reason,until,level)=>{calls++;selectedRole=level;deadline=until;return Task.CompletedTask;}));
            pending=(Task)Call(w,"ModerateAsync",user,"ban")!;w.UpdateLayout();inputs=Descendants<TextBox>(C<StackPanel>("ConfirmationChangesPanel")).ToArray();
            inputs[0].Text="One minute test";inputs[1].Text="0";inputs[2].Text="0";inputs[3].Text="1";
            var before=DateTimeOffset.UtcNow;await (Task)Call(w,"CompleteConfirmationAsync",true)!;await pending;
            Check(calls==2&&deadline>=before.AddMinutes(1)&&deadline<=DateTimeOffset.UtcNow.AddMinutes(1),"minute duration not sent correctly");
            Set(w,"_socialBusy",false);
            Populate(w,"chat");profile=Field<AccountService>(w,"_account");var friends=Field<IReadOnlyList<SocialPlayer>>(w,"_socialPlayers");
            var identity=(StackPanel)Call(w,"SocialNameLabel",friends[0])!;
            foreach(var width in new[]{110d,210d})
            {
                identity.Measure(new Size(width,double.PositiveInfinity));identity.Arrange(new Rect(0,0,width,identity.DesiredSize.Height));
                var row=(SocialIdentityLine)identity.Children[1];var badge=(Border)row.Children[1];
                Check(badge.TranslatePoint(new Point(badge.ActualWidth,0),identity).X<=width+.1,"badge escapes narrow row");
                if(width==210)Check(Math.Abs(row.Children[0].TranslatePoint(new Point(0,9.5),row).Y-badge.TranslatePoint(new Point(0,badge.ActualHeight/2),row).Y)<1,"username and badge not centered");
            }
            var menu=(ContextMenu)Call(w,"CreateSocialMenu",new Button(),friends[0])!;
            Call(w,"ShowSocialDetails",friends[0]);w.UpdateLayout();
            var profileBadge=(Border)C<ContentControl>("SocialDetailsAdminBadge").Content;
            Check(profileBadge.ActualWidth>60&&profileBadge.ActualWidth<160&&profileBadge.HorizontalAlignment==HorizontalAlignment.Left,"profile badge stretches across card");
            Check(Math.Abs(profileBadge.TranslatePoint(new Point(0,0),C<Border>("SocialDetailsCard")).X-C<TextBlock>("SocialDetailsName").TranslatePoint(new Point(0,0),C<Border>("SocialDetailsCard")).X)<.1,"profile badge left edge misaligned");
            var componentRows=C<StackPanel>("SocialDetailsComponents").Children.OfType<Grid>().ToArray();
            Check(componentRows.Length==9,"profile component row count");
            Check(componentRows.All(row=>row.Children[0] is Border surface&&surface.Background is not null&&surface.CornerRadius.TopLeft==5&&Grid.GetColumnSpan(surface)==2&&!surface.IsHitTestVisible),"component lacks a continuous non-interactive surface");
            Check(componentRows.All(row=>Math.Abs(((Border)row.Children[0]).ActualWidth-row.ActualWidth)<.1),"component surface does not span label and value");
            Check(componentRows.All(row=>row.Children.OfType<TextBlock>().Single().ActualWidth>100&&row.Children.OfType<Border>().Single(b=>b.Child is TextBlock).ActualWidth>=48),"component label or value squeezed");
            Check(componentRows.All(row=>row.ActualHeight>15&&row.ActualHeight<30),"component surface added unnecessary height");
            Check(componentRows.All(row=>Math.Abs(row.Children.OfType<Border>().Single(b=>b.Child is TextBlock).TranslatePoint(new Point(0,0),row).X+row.Children.OfType<Border>().Single(b=>b.Child is TextBlock).ActualWidth-row.ActualWidth)<.1),"component values no longer align at right edge");
            Call(w,"CloseSocialDetails");
            Check(!menu.Items.OfType<MenuItem>().Any(i=>Equals(i.Tag,"block")),"block administrator offered");
            menu=(ContextMenu)Call(w,"CreateSocialMenu",new Button(),friends[2])!;
            Check(menu.Items.Count==1&&Equals(((MenuItem)menu.Items[0]).Tag,"hide_chat"),"deleted user context actions");
            Set(w,"_socialPeer",friends[1].Id);Call(w,"RenderSocialMessages");Call(w,"RenderSocialIdentity");
            Check(!C<Button>("FriendsSendButton").IsEnabled&&!C<Button>("FriendsComposerMoreButton").IsEnabled,"banned peer send enabled");
            Call(w,"ShowSocialDetails",friends[1]);Check(C<TextBlock>("SocialDetailsModerationText").Text.Length>20,"ban detail absent");
            Check(!C<Button>("SocialDetailsCopyButton").IsEnabled&&C<Button>("SocialDetailsRemoveButton").IsEnabled,"banned profile allowed actions");
            for(var tick=0;tick<5;tick++){Call(w,"RefreshGameLaunchState");Call(w,"RenderSocialDetails",friends[1]);Call(w,"RefreshSocialCopyAvailability");}
            Check(C<TextBlock>("SocialDetailsCopyHint").Visibility==Visibility.Collapsed&&C<TextBlock>("SocialDetailsCopyHint").Text=="","banned profile hint flickers");
            Call(w,"CloseSocialDetails");
            var session=Session(w);session.ProtectedAdmin=false;session.AdminLevel=1;Call(w,"RenderAccount");Check(profile.AdminLevel==1,"ordinary admin level");
            session.AdminLevel=0;Call(w,"RenderAccount");Check(C<Button>("AdminNav").Visibility==Visibility.Collapsed&&Field<AdminPage?>(w,"_adminData")==null,"revoked role retains privileged view");
            session.BannedAt=DateTimeOffset.UtcNow;session.BanUntil=DateTimeOffset.UtcNow.AddDays(1);session.BanReason="Test";Call(w,"RenderAccount");
            Check(!C<StackPanel>("FriendsSignedInPanel").IsEnabled&&C<ContentControl>("FriendsModerationNotice").Content is Border,"own friends ban state");
            Check(C<Border>("FriendsNavBadge").Visibility==Visibility.Visible&&C<TextBlock>("FriendsNavBadgeText").Text=="!","ban nav indicator");
            Check(!C<Button>("AccountAvatarEditButton").IsEnabled&&!C<Button>("AccountEditNicknameButton").IsEnabled,"banned profile editable");
            Check(C<Button>("AccountDeleteButton").IsEnabled&&C<Button>("AccountLogoutButton").IsEnabled,"banned logout/delete unavailable");
            Check(C<Grid>("MainBody").IsEnabled&&C<Button>("SettingsNav").IsEnabled,"ban blocked local launcher");
            session.BanUntil=DateTimeOffset.UtcNow.AddSeconds(-1);Call(w,"RenderAccount");Check(!profile.Banned&&C<StackPanel>("FriendsSignedInPanel").IsEnabled,"expired temporary ban did not unlock");
            Call(w,"FriendsSearch_Click",C<Button>("FriendsSearchButton"),new RoutedEventArgs());Call(w,"FriendsClearSearch_Click",C<Button>("FriendsClearSearchButton"),new RoutedEventArgs());
            await Task.Delay(300);Check(C<Border>("FriendsSearchPanel").Visibility==Visibility.Collapsed,"search X did not close");
            Call(w,"FriendsBlocked_Click",C<Button>("FriendsBlockedTab"),new RoutedEventArgs());Check(Field<string>(w,"_socialSection")=="blocked","separate blocked section");
        }
        try{w.Show();var task=w.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();var frame=new DispatcherFrame();var timeout=new DispatcherTimer{Interval=TimeSpan.FromSeconds(30)};
            timeout.Tick+=(_,_)=>frame.Continue=false;task.ContinueWith(_=>w.Dispatcher.BeginInvoke(()=>frame.Continue=false),TaskScheduler.Default);timeout.Start();Dispatcher.PushFrame(frame);timeout.Stop();if(!task.IsCompleted)throw new TimeoutException();task.GetAwaiter().GetResult();Console.WriteLine($"ADMIN UI PASS {n} {language}: roles, forms, sanctions, tombstones, search close; mock data only");}
        finally{w.Close();}
    }
}
