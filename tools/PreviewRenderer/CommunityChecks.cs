using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Input;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class CommunityChecks
{
    private static IEnumerable<Button> FindButtons(DependencyObject parent)
    {
        for(var i=0;i<VisualTreeHelper.GetChildrenCount(parent);i++) { var child=VisualTreeHelper.GetChild(parent,i); if(child is Button b) yield return b; foreach(var nested in FindButtons(child)) yield return nested; }
    }
    internal static void Run(string language,string directory)
    {
        if(!ActivityStore.IsSmokeTest)throw new InvalidOperationException("Isolated fixture required");
        Directory.CreateDirectory(directory);
        new SettingsStore().Save(new UserSettings{Language=language,ModNoticeSeen=true});
        var window=new MainWindow(new LauncherConfiguration{FeedUrls=[],BetaFeedUrls=[]},null);
        const BindingFlags flags=BindingFlags.NonPublic|BindingFlags.Instance;
        T C<T>(string name)=>(T)window.FindName(name);
        T Field<T>(string name)=>(T)typeof(MainWindow).GetField(name,flags)!.GetValue(window)!;
        void Set(string name,object? value)=>typeof(MainWindow).GetField(name,flags)!.SetValue(window,value);
        object? Call(string name,params object?[] args)=>typeof(MainWindow).GetMethod(name,flags)!.Invoke(window,args);
        int checks=0;void Check(bool ok,string why){checks++;if(!ok)throw new Exception("Community UI: "+why);}
        var settings=Field<UserSettings>("_settings");
        var person=Guid.NewGuid();
        var ru=Enumerable.Range(1,30).Select(i=>new CommunityMessage(i,Guid.NewGuid(),person,"FixtureFriend","Игрок "+i,"Тестовое сообщение "+i+". Ищем компанию для матча в Kohan II.",DateTimeOffset.Now.AddMinutes(i-30),false,0)).ToArray();
        var en=new[]{new CommunityMessage(31,Guid.NewGuid(),person,"FixtureFriend","Player","Anyone up for a match?",DateTimeOffset.Now,false,0)};
        bool offline=false;
        Set("_communityReadOverride",new Func<string,CancellationToken,Task<IReadOnlyList<CommunityMessage>>>((channel,ct)=>offline?Task.FromException<IReadOnlyList<CommunityMessage>>(new AccountException("network")):Task.FromResult<IReadOnlyList<CommunityMessage>>(channel=="ru"?ru:en)));
        async Task Poll(){Set("_communityNextPoll",default(DateTimeOffset));await (Task)Call("PollCommunityAsync")!;window.UpdateLayout();await Task.Delay(50);}
        void Snap(string name)
        {
            window.UpdateLayout();var content=(FrameworkElement)window.Content;
            var bitmap=new RenderTargetBitmap((int)window.ActualWidth,(int)window.ActualHeight,96,96,PixelFormats.Pbgra32);bitmap.Render(content);
            var encoder=new PngBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(bitmap));using var output=File.Create(Path.Combine(directory,name+"-"+language+".png"));encoder.Save(output);
        }
        void DialogSnap(Window dialog,string name)
        {
            dialog.UpdateLayout();var content=(FrameworkElement)dialog.Content;
            var bitmap=new RenderTargetBitmap((int)dialog.ActualWidth,(int)dialog.ActualHeight,96,96,PixelFormats.Pbgra32);bitmap.Render(content);
            var encoder=new PngBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(bitmap));using var output=File.Create(Path.Combine(directory,name+"-"+language+".png"));encoder.Save(output);
        }
        async Task Scenario()
        {
            window.Width=1600;window.Height=1000;window.UpdateLayout();await Poll();
            Check(C<Border>("CommunityCard").IsVisible,"chat visible at startup");
            Set("_communityOnlineOverride",new Func<CancellationToken,Task<int>>(_=>Task.FromResult(12)));
            await (Task)Call("RefreshCommunityExtrasAsync")!;
            Check(C<TextBlock>("CommunityDescription").Text.Contains("12"),"guest sees launcher online count");
            Set("_communityOnlineOverride",new Func<CancellationToken,Task<int>>(_=>Task.FromException<int>(new AccountException("network"))));
            await (Task)Call("RefreshCommunityExtrasAsync")!;
            Check(C<TextBlock>("CommunityDescription").Text.Contains("—"),"offline count is unknown instead of stale zero");
            Set("_communityOnlineOverride",new Func<CancellationToken,Task<int>>(_=>Task.FromResult(12)));
            var publicMessage=en[0] with {AvatarRevision=DateTimeOffset.UtcNow};
            var bitmap=new RenderTargetBitmap(256,256,96,96,PixelFormats.Pbgra32);
            var encoder=new JpegBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(bitmap));
            using var jpeg=new MemoryStream();encoder.Save(jpeg);int avatarReads=0;
            Set("_communityAvatarOverride",new Func<Guid,DateTimeOffset,CancellationToken,Task<byte[]?>>((id,rev,ct)=>{avatarReads++;return Task.FromResult<byte[]?>(jpeg.ToArray());}));
            var publicAvatar=(ContentControl)Call("CommunityAvatar",publicMessage,64d)!;
            await (Task)Call("RefreshCommunityAvatarAsync",publicMessage)!;
            Check(((Grid)publicAvatar.Content).Children.OfType<System.Windows.Shapes.Ellipse>().Single().Fill is ImageBrush,"guest receives public avatar image");
            await (Task)Call("RefreshCommunityAvatarAsync",publicMessage)!;
            Check(avatarReads==1,"unchanged avatar uses memory cache");
            var guestProfileTimer=new DispatcherTimer{Interval=TimeSpan.FromMilliseconds(300)};
            guestProfileTimer.Tick+=(_,_)=>{guestProfileTimer.Stop();var profile=window.OwnedWindows.Cast<Window>().Single(w=>w.IsVisible);
                var action=FindButtons(profile).Single(b=>b.Name=="CommunityProfileAction");
                Check(action.Content?.ToString()==(language=="ru"?"Войти в аккаунт":"Sign in"),"guest profile action is sign in");
                DialogSnap(profile,"community-guest-profile");action.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));};
            guestProfileTimer.Start();await (Task)Call("OpenCommunityProfileAsync",publicMessage)!;
            Check(Field<string>("_activePage")=="account","guest profile sign in opens account form");Call("SetActivePage","home");

            Check(Field<string>("_communityChannel")=="en","fresh profile defaults to EN regardless of UI language");
            Check(settings.CommunityNotifications=="mentions","fresh profile only mentions notify");
            ContextMenu? notificationMenu=null;
            Set("_socialMenuOpenOverride",new Action<ContextMenu>(menu=>notificationMenu=menu));
            C<Button>("CommunityNotificationButton").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            Check(notificationMenu?.Items.Count==3&&notificationMenu.Items.OfType<MenuItem>().Single(i=>i.IsChecked).Tag?.ToString()=="mentions","notification choices show selected mentions mode");
            Check(notificationMenu!.Items.OfType<MenuItem>().Single(i=>i.IsChecked).Icon is LauncherIcon {Kind:IconKind.Check},"custom menu template displays selected check mark");
            notificationMenu!.Items.OfType<MenuItem>().Single(i=>i.Tag?.ToString()=="mute").RaiseEvent(new RoutedEventArgs(MenuItem.ClickEvent));
            Check(settings.CommunityNotifications=="mute"&&C<LauncherIcon>("CommunityNotificationIcon").Kind==IconKind.BellMuted,"mute selection changes bell and setting");
            Check(C<StackPanel>("CommunityGuest").IsVisible&&!C<Button>("CommunitySend").IsEnabled,"guest read-only composer");
            Check(!C<Border>("ChangelogCard").IsVisible,"history not in main pane");
            var initial=C<Grid>("PagesWorkspace").ActualWidth;
            var divider=C<GridSplitter>("CommunitySplitter");
            var beforeDrag=C<ColumnDefinition>("CommunityColumn").ActualWidth;
            divider.RaiseEvent(new DragStartedEventArgs(0,0));divider.RaiseEvent(new DragDeltaEventArgs(80,0));window.UpdateLayout();divider.RaiseEvent(new DragCompletedEventArgs(80,0,false));window.UpdateLayout();
            Check(Math.Abs(C<ColumnDefinition>("CommunityColumn").ActualWidth-(beforeDrag-80))<2,"native splitter drag resizes right pane");
            divider.Focus();window.UpdateLayout();
            var grip=(Border)divider.Template.FindName("Grip",divider);
            Check(divider.IsMouseOver||((SolidColorBrush)grip.Background).Color==Color.FromRgb(64,83,110),"keyboard focus after dragging does not leave grip gold");
            settings.CommunityWidth=300;Call("UpdateCommunityWidth");window.UpdateLayout();
            Check(C<Grid>("PagesWorkspace").ActualWidth>initial+100,"page expands when chat narrows");
            Call("CommunitySplitter_Completed",C<GridSplitter>("CommunitySplitter"),new DragCompletedEventArgs(0,0,false));
            await Task.Delay(1100);Check(Math.Abs(new SettingsStore().Load().CommunityWidth-300)<2,"width saved to disk");
            foreach(var page in new[]{"home","modules","friends","settings","account","about","mods"})
            {Call("SetActivePage",page);window.UpdateLayout();Check(C<Border>("CommunityCard").IsVisible,"chat survives "+page);Check(Math.Abs(C<ColumnDefinition>("CommunityColumn").ActualWidth-300)<2,"width survives "+page);}
            settings.CommunityWidth=0;Call("UpdateCommunityWidth");window.UpdateLayout();
            Call("SetActivePage","modules");await Task.Delay(250);Snap("components-wide");
            settings.CommunityWidth=300;Call("UpdateCommunityWidth");window.UpdateLayout();await Task.Delay(100);Snap("components-narrow");
            C<Button>("CommunityEn").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));window.UpdateLayout();
            Check(C<StackPanel>("CommunityRows").Children.Count==1,"EN is a separate history");
            C<ChatComposer>("CommunityInput").Text="English draft";
            C<Button>("CommunityRu").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));C<ChatComposer>("CommunityInput").Text="Русский черновик";
            C<Button>("CommunityEn").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));Check(C<ChatComposer>("CommunityInput").Text=="English draft","per-channel draft retained");
            C<Button>("CommunityRu").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));window.UpdateLayout();
            await Task.Delay(1100);
            Check(new SettingsStore().Load().CommunityChannel=="ru","channel choice saved to disk");
            var reopened=new MainWindow(new LauncherConfiguration{FeedUrls=[],BetaFeedUrls=[]},null);
            Check((string)typeof(MainWindow).GetField("_communityChannel",flags)!.GetValue(reopened)! == "ru","saved RU channel restored on next launch");
            Check(((UserSettings)typeof(MainWindow).GetField("_settings",flags)!.GetValue(reopened)!).CommunityNotifications=="mute","notification preference restored on next launch");
            reopened.Close();
            C<ScrollViewer>("CommunityScroll").ScrollToVerticalOffset(120);window.UpdateLayout();await Task.Delay(50);
            var position=C<ScrollViewer>("CommunityScroll").VerticalOffset;
            var firstRow=(Border)C<StackPanel>("CommunityRows").Children[0];
            var firstText=((StackPanel)firstRow.Child).Children.OfType<ChatMessageText>().Single();
            ContextMenuEventArgs OpenMessageMenu(ChatMessageText text)
            {
                var args=(ContextMenuEventArgs)Activator.CreateInstance(typeof(ContextMenuEventArgs),BindingFlags.Instance|BindingFlags.NonPublic,null,new object[]{text,true},null)!;
                text.RaiseEvent(args);return args;
            }
            Check(OpenMessageMenu(firstText).Handled&&firstText.ContextMenu.Items.Count==0,"guest message suppresses empty context menu without copy/select entries");
            firstText.Selection.Select(firstText.Document.ContentStart,firstText.Document.ContentEnd);
            var selected=firstText.SelectedText;
            var unchangedClock=System.Diagnostics.Stopwatch.StartNew();
            for(var n=0;n<20;n++){Set("_communityNextPoll",default(DateTimeOffset));await (Task)Call("PollCommunityAsync")!;}
            unchangedClock.Stop();
            Check(ReferenceEquals(firstRow,C<StackPanel>("CommunityRows").Children[0])&&firstText.SelectedText==selected,"unchanged polls preserve row and selected text");
            Console.WriteLine($"COMMUNITY unchanged x20: {unchangedClock.ElapsedMilliseconds} ms");
            ru=ru.Append(new CommunityMessage(32,Guid.NewGuid(),person,"FixtureFriend","Player","New message",DateTimeOffset.Now,false,0)).ToArray();
            await Poll();Check(Math.Abs(C<ScrollViewer>("CommunityScroll").VerticalOffset-position)<3,"poll keeps scroll while reading");
            Check(ReferenceEquals(firstRow,C<StackPanel>("CommunityRows").Children[0])&&firstText.SelectedText==selected,"new arrival preserves old controls and selection");
            var normalRead=Field<Func<string,CancellationToken,Task<IReadOnlyList<CommunityMessage>>>>("_communityReadOverride");
            var delayed=new TaskCompletionSource<IReadOnlyList<CommunityMessage>>(TaskCreationOptions.RunContinuationsAsynchronously);
            Set("_communityReadOverride",new Func<string,CancellationToken,Task<IReadOnlyList<CommunityMessage>>>((_,_)=>delayed.Task));
            Set("_communityNextPoll",default(DateTimeOffset));var pendingPoll=(Task)Call("PollCommunityAsync")!;
            Set("_communityMutationVersion",Field<int>("_communityMutationVersion")+1);delayed.SetResult([]);await pendingPoll;
            Check(C<StackPanel>("CommunityRows").Children.Count==31,"late read cannot overwrite a send or removal");Set("_communityReadOverride",normalRead);
            offline=true;await Poll();Check(C<Button>("CommunityRetry").IsVisible&&C<StackPanel>("CommunityRows").Children.Count==31,"offline keeps history and exposes retry");
            offline=false;await Poll();Check(!C<Button>("CommunityRetry").IsVisible,"retry recovers");
            Call("SetActivePage","friends");Set("_socialPeer",person);Call("RefreshCommunityPageLayout");
            window.Width=1050;window.Height=700;window.UpdateLayout();await Task.Delay(100);
            Check(C<Button>("CompactFriendsBack").IsVisible&&!C<Grid>("MainOptionsHost").IsVisible,"compact friends shows conversation with back");
            var launch=C<Button>("LaunchButton");var bounds=launch.TransformToAncestor(C<Grid>("PagesWorkspace")).TransformBounds(new Rect(launch.RenderSize));
            Check(bounds.Right<=C<Grid>("PagesWorkspace").ActualWidth+1,"launch action not clipped");
            C<Button>("CompactFriendsBack").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));window.UpdateLayout();
            Check(C<Grid>("MainOptionsHost").IsVisible&&!C<Grid>("FriendsConversationScroll").IsVisible,"compact back opens full-width friends list");
            Snap("friends-small");
            Call("SetActivePage","modules");window.UpdateLayout();await Task.Delay(200);
            foreach(var name in new[]{"GameLanguageCombo","GameVoiceCombo","GameSettingsButton","ArcaneWarsModRadio"})
            {var item=C<FrameworkElement>(name);var r=item.TransformToAncestor(C<Grid>("PagesWorkspace")).TransformBounds(new Rect(item.RenderSize));Check(r.Right<=C<Grid>("PagesWorkspace").ActualWidth+1,"small components control fits: "+name);}
            Snap("components-small");Call("SetActivePage","friends");
            window.Width=1600;window.Height=1000;settings.CommunityWidth=0;Call("UpdateCommunityWidth");window.UpdateLayout();await Task.Delay(100);Snap("friends-wide");
            Check(Math.Abs(C<ColumnDefinition>("CommunityColumn").ActualWidth-CommunityChat.Width(C<Grid>("CommunityWorkspace").ActualWidth-14,0))<2,"default restored after small window");
            var timer=new DispatcherTimer{Interval=TimeSpan.FromMilliseconds(350)};
            timer.Tick+=(_,_)=>{timer.Stop();var history=Field<Window>("_historyWindow");Check(history.IsVisible&&C<Border>("ChangelogCard").IsVisible,"history dialog opens from friends");Check(history.WindowStyle==WindowStyle.None&&System.Windows.Shell.WindowChrome.GetWindowChrome(history) is not null,"history uses custom caption with native resizing");DialogSnap(history,"history-dialog");history.Close();};
            timer.Start();C<Button>("HistoryButton").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            Check(!C<Border>("ChangelogCard").IsVisible&&C<Border>("CommunityCard").IsVisible,"history closes without losing chat");

            // Paginated history, no 10,000-element visual tree and no reset while reading.
            var data=Enumerable.Range(100,1000).Select(i=>new CommunityMessage(i,Guid.NewGuid(),person,"FixtureFriend","Player","Message "+i+" :ch_sword: 🙂",DateTimeOffset.Now,false,0)).ToArray();
            long revision=1;bool trimmed=false;var reads=0;
            Set("_communityPageReadOverride",new Func<string,long?,CancellationToken,Task<CommunityPage>>((channel,before,ct)=>
            {
                reads++;var source=(channel=="ru"?data:en).Where(m=>before is null||m.Ordinal<before).ToArray();
                return Task.FromResult(new CommunityPage(source.TakeLast(100).ToArray(),source.Length>100,revision,trimmed));
            }));
            await Poll();Check(C<StackPanel>("CommunityRows").Children.Count==100&&C<Button>("CommunityOlder").IsVisible,"latest history page is bounded");
            await (Task)Call("NavigateCommunityHistoryAsync",true)!;window.UpdateLayout();
            Check(C<StackPanel>("CommunityRows").Children.Count==200,"older page reaches bounded 200-row viewport");
            var retained=C<StackPanel>("CommunityRows").Children.OfType<Border>().Last();
            var anchorY=retained.TranslatePoint(new Point(),C<ScrollViewer>("CommunityScroll")).Y;
            await (Task)Call("NavigateCommunityHistoryAsync",true)!;window.UpdateLayout();
            Check(C<StackPanel>("CommunityRows").Children.Count==200&&C<Button>("CommunityNewer").IsVisible,"third page keeps bounded viewport with forward navigation");
            var readingRows=C<StackPanel>("CommunityRows").Children.OfType<Border>().ToArray();
            var readingOffset=C<ScrollViewer>("CommunityScroll").VerticalOffset;
            data=data.Append(new CommunityMessage(1100,Guid.NewGuid(),person,"FixtureFriend","Player","Incoming while reading",DateTimeOffset.Now,false,0)).ToArray();
            await Poll();
            Check(readingRows.SequenceEqual(C<StackPanel>("CommunityRows").Children.OfType<Border>())&&Math.Abs(readingOffset-C<ScrollViewer>("CommunityScroll").VerticalOffset)<3,"newest poll does not rebuild or jump an older page");
            for(var i=0;i<10;i++)await (Task)Call("NavigateCommunityHistoryAsync",true)!;
            Check(!C<Button>("CommunityOlder").IsVisible&&C<StackPanel>("CommunityRows").Children.Count==200,"oldest retained page reachable");
            var callsBefore=reads;C<Button>("CommunityJump").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));window.UpdateLayout();
            Check(reads==callsBefore&&C<StackPanel>("CommunityRows").Children.OfType<Border>().Last().Tag!.Equals(data.Last().Id),"jump to latest uses cached data without network");
            revision++;trimmed=true;data=data.TakeLast(50).ToArray();await Poll();
            Check(C<StackPanel>("CommunityRows").Children.Count==50&&C<TextBlock>("CommunityHistoryNotice").IsVisible,"trim clears older cached pages and explains retention");
            var rich=((StackPanel)((Border)C<StackPanel>("CommunityRows").Children[0]).Child).Children.OfType<ChatMessageText>().Single();
            Check(rich.Text.Contains(":ch_sword:")&&rich.Document.Blocks.OfType<System.Windows.Documents.Paragraph>().SelectMany(p=>p.Inlines.OfType<System.Windows.Documents.InlineUIContainer>()).Any(),"received glyph uses shared inline renderer");

            SocialChecks.Populate(window,"chat");Call("RefreshCommunityIdentity");Call("SetActivePage","modules");window.UpdateLayout();
            var composer=C<ChatComposer>("CommunityInput");var privateComposer=C<ChatComposer>("FriendsMessageInput");
            var account=Field<AccountService>("_account");
            data=data.Append(new CommunityMessage(1101,Guid.NewGuid(),person,"FixtureFriend","Player","Hello @"+account.Nickname+"!",DateTimeOffset.Now,false,0)).ToArray();await Poll();
            var mentionRow=(Border)C<StackPanel>("CommunityRows").Children[^1];
            Check(((SolidColorBrush)mentionRow.BorderBrush).Color==Color.FromRgb(211,175,89),"own mention has gold highlight");
            var messageHeader=(Grid)((StackPanel)mentionRow.Child).Children[0];
            var nicknameButton=messageHeader.Children.OfType<Button>().Single(b=>Grid.GetColumn(b)==1);
            Check(nicknameButton.ActualWidth+20<messageHeader.ColumnDefinitions[1].ActualWidth,"nickname hit area is limited to text instead of filling the row");
            var copyButton=messageHeader.Children.OfType<ClipboardButton>().Single();
            string? copied=null;Set("_clipboardWrite",new Action<string>(value=>copied=value));
            var rowHeight=mentionRow.ActualHeight;
            mentionRow.RaiseEvent(new MouseEventArgs(Mouse.PrimaryDevice,0){RoutedEvent=Mouse.MouseEnterEvent});await Task.Delay(160);
            Check(copyButton.Opacity>.95&&Math.Abs(rowHeight-mentionRow.ActualHeight)<1,"community copy appears without moving the message");
            copyButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));await Task.Delay(40);
            Check(copied==data.Last().Body&&ClipboardButton.GetIsCopySuccessful(copyButton),"community copy preserves the complete message and shows success");copyButton.ResetFeedback();
            mentionRow.RaiseEvent(new MouseEventArgs(Mouse.PrimaryDevice,0){RoutedEvent=Mouse.MouseLeaveEvent});await Task.Delay(160);
            Check(copyButton.Opacity<.05,"community copy hides after leaving the message");
            composer.Text="Draft";composer.CaretPosition=composer.Document.ContentEnd;
            messageHeader.Children.OfType<Button>().Single(b=>Grid.GetColumn(b)==1).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            Check(composer.Text=="Draft @FixtureFriend ","nickname inserts mention without discarding draft");
            var profileTimer=new DispatcherTimer{Interval=TimeSpan.FromMilliseconds(350)};
            profileTimer.Tick+=(_,_)=>{profileTimer.Stop();var profile=window.OwnedWindows.Cast<Window>().Single(w=>w.IsVisible);Check(profile.Title==(language=="ru"?"Профиль игрока":"Player profile"),"avatar opens public player profile");DialogSnap(profile,"community-profile");profile.Close();};
            profileTimer.Start();messageHeader.Children.OfType<Button>().Single(b=>Grid.GetColumn(b)==0).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            var stamp=messageHeader.Children.OfType<TextBlock>().Single();
            Check(Grid.GetColumn(stamp)==3&&stamp.Text.Count(c=>c==':')==2,"community time includes seconds at right edge");
            Snap("community-mentions");
            Call("SetActivePage","modules");
            C<Button>("AccountHeaderButton").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            Check(Field<string>("_activePage")=="account","profile header opens account");
            await Task.Delay(220);Snap("profile-header-selected");
            C<Button>("AccountHeaderButton").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            Check(Field<string>("_activePage")=="modules","second profile click returns to previous page");
            Call("SetActivePage","friends");Call("SetActivePage","account");
            C<Button>("AccountHeaderButton").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
            Check(Field<string>("_activePage")=="friends","profile return also remembers non-header entry");
            Call("SetActivePage","modules");
            privateComposer.Text="Private draft";composer.Text="Public draft ";composer.CaretPosition=composer.Document.ContentEnd;
            C<Button>("CommunityGlyphButton").RaiseEvent(new RoutedEventArgs(Button.ClickEvent));window.UpdateLayout();
            Check(Field<Grid?>("_chatPopup") is not null,"community opens shared glyph picker");
            Call("InsertPickerGlyph",ChatGlyphs.All[0],ModifierKeys.Shift);
            Call("InsertPickerGlyph",ChatGlyphs.All[1],ModifierKeys.Shift);
            Check(composer.Text=="Public draft "+ChatGlyphs.All[0].Token+ChatGlyphs.All[1].Token&&privateComposer.Text=="Private draft","shared picker inserts into community without touching private draft");
            Check(Field<Grid?>("_chatPopup") is not null,"Shift keeps community glyph picker open");
            Snap("community-glyphs");Call("RemoveChatPopup");
            window.Width=1050;window.UpdateLayout();
            foreach(var name in new[]{"CommunityInput","CommunityGlyphButton","CommunitySend"})
            {var control=C<FrameworkElement>(name);var r=control.TransformToAncestor(C<Border>("CommunityCard")).TransformBounds(new Rect(control.RenderSize));Check(r.Right<=C<Border>("CommunityCard").ActualWidth+1&&r.Left>=0,"narrow composer control fits: "+name);}
            Console.WriteLine($"COMMUNITY UI PASS {checks} {language}");
        }
        try
        {
            window.Show();var task=window.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();var frame=new DispatcherFrame();
            var deadline=new DispatcherTimer{Interval=TimeSpan.FromSeconds(60)};deadline.Tick+=(_,_)=>frame.Continue=false;
            task.ContinueWith(_=>window.Dispatcher.BeginInvoke(()=>frame.Continue=false),TaskScheduler.Default);deadline.Start();Dispatcher.PushFrame(frame);deadline.Stop();
            if(!task.IsCompleted)throw new TimeoutException("community UI");task.GetAwaiter().GetResult();
        }
        finally{window.Close();}
    }
}
