using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;

namespace PawsPatchLauncher;
public partial class MainWindow
{
    private readonly Dictionary<Guid,(GameActivityDetails details,DateTimeOffset received)> _gameActivityCache = new();
    private Guid? _gameActivityPeer;
    private CancellationTokenSource? _gameActivityLifetime;
    private DispatcherTimer? _gameActivityTimer;
    private bool _gameActivityBusy;
    private int _gameActivityGeneration;
    private string? _gameActivityRenderKey;
    private GameActivityDetails? _gameActivityShown;
    private Func<Guid,CancellationToken,Task<GameActivityDetails?>>? _gameActivityReadOverride = null;

    private string GameActivityPhaseName(string phase) => phase switch
    {
        "menu" => T("В меню игры", "In game menus"),
        "lobby" => T("В лобби", "In a lobby"),
        "match" => T("В матче", "In a match"),
        "loading" => T("Загружает игру", "Loading a game"),
        "editor" => T("В редакторе карт", "In the map editor"),
        _ => T("Играет", "Playing")
    };
    private void ApplyGameActivityLanguage()
    {
        ShareGameActivityToggle.Content=T("Показывать подробный статус игры", "Share detailed game activity");
        ShareGameActivityToggle.ToolTip=T("Показывает в профиле меню, лобби или матч, время и участников. Общий статус «Играет» останется и при отключении.",
            "Shows menus, lobby or match, time and participants on your profile. The general Playing status remains when disabled.");
        ShareGameActivityToggle.IsChecked=_settings.ShareGameActivity;
        if(GameActivityOverlay.Visibility==Visibility.Visible)
        {
            GameActivityTitle.Text=T("Сейчас в игре", "Current game activity");
            if(_gameActivityShown is { } details)RenderGameActivity(details);
        }
    }
    private void ShareGameActivityToggle_Click(object sender,RoutedEventArgs e)
    {
        _settings.ShareGameActivity=ShareGameActivityToggle.IsChecked==true;
        _settingsStore.Save(_settings);_socialPresenceNext=default;
        ActionJournal.Record("game_activity.sharing",_settings.ShareGameActivity?"enabled":"disabled");
    }
    private async void SocialDetailsGameActivity_Click(object sender,RoutedEventArgs e)
    {
        if(_socialDetailsPeer is not Guid peer||AccountConnectionBlocked||ConfirmationActive)return;
        await ShowGameActivityAsync(peer);
    }
    private async Task ShowGameActivityAsync(Guid peer)
    {
        CloseGameActivity();
        _gameActivityPeer=peer;_gameActivityLifetime=CancellationTokenSource.CreateLinkedTokenSource(_accountLifetime.Token);
        GameActivityTitle.Text=T("Сейчас в игре", "Current game activity");
        GameActivityPlayerName.Text=SocialDetailsPlayer()?.Name??"";
        GameActivityClose.ToolTip=T("Закрыть", "Close");
        GameActivityCard.IsHitTestVisible=true;
        GameActivityOverlay.Visibility=Visibility.Visible;GameActivityOverlay.UpdateLayout();
        Motion.Reveal(GameActivityOverlay);RevealDialogCard(GameActivityCard);GameActivityClose.Focus();
        if(_gameActivityTimer is null)
        {
            _gameActivityTimer=new DispatcherTimer{Interval=TimeSpan.FromSeconds(15)};
            _gameActivityTimer.Tick+=async(_,_)=>await RefreshGameActivityAsync();
        }
        _gameActivityTimer.Start();
        if(_gameActivityCache.TryGetValue(peer,out var cached)&&DateTimeOffset.UtcNow-cached.received<TimeSpan.FromSeconds(15))
        { RenderGameActivity(cached.details);await RefreshGameParticipantAvatarsAsync(cached.details,_gameActivityGeneration);return; }
        await RefreshGameActivityAsync();
    }
    private async Task RefreshGameActivityAsync()
    {
        if(_gameActivityPeer is not Guid peer||_gameActivityBusy||_gameActivityLifetime is null||GameActivityOverlay.Visibility!=Visibility.Visible)return;
        if(AccountConnectionBlocked){GameActivityStatus.Text=T("Нет подключения. Показаны последние полученные сведения.", "No connection. Showing the last received details.");return;}
        var generation=_gameActivityGeneration;
        _gameActivityBusy=true;
        if(_gameActivityShown is null)GameActivityStatus.Text=T("Загружаю сведения…", "Loading details…");
        using var timeout=CancellationTokenSource.CreateLinkedTokenSource(_gameActivityLifetime.Token);timeout.CancelAfter(TimeSpan.FromSeconds(8));
        try
        {
            var details=await (_gameActivityReadOverride?.Invoke(peer,timeout.Token)??_account.GetGameActivityAsync(peer,timeout.Token));
            if(generation!=_gameActivityGeneration||peer!=_gameActivityPeer)return;
            if(details is null)
            {
                _gameActivityCache.Remove(peer);_gameActivityShown=null;_gameActivityRenderKey=null;GameActivityBody.Children.Clear();
                GameActivityStatus.Text=T("Сведения пока недоступны: игрок мог выйти из игры или отключить подробный статус.", "Details are unavailable. The player may have left the game or disabled detailed activity.");
                return;
            }
            if(_gameActivityCache.Count>=16&&!_gameActivityCache.ContainsKey(peer))_gameActivityCache.Remove(_gameActivityCache.MinBy(x=>x.Value.received).Key);
            _gameActivityCache[peer]=(details,DateTimeOffset.UtcNow);RenderGameActivity(details);
            await RefreshGameParticipantAvatarsAsync(details,generation);
        }
        catch(Exception error) when(error is AccountException or System.Net.Http.HttpRequestException or OperationCanceledException or System.IO.IOException)
        {
            if(generation==_gameActivityGeneration)GameActivityStatus.Text=T("Не удалось обновить сведения. Попробуем ещё раз.", "Could not refresh details. We will try again.");
        }
        finally { if(generation==_gameActivityGeneration)_gameActivityBusy=false; }
    }
    private void RenderGameActivity(GameActivityDetails details)
    {
        _gameActivityShown=details;
        GameActivityStatus.Text=T("Обновлено: ", "Updated: ")+details.ObservedAt.ToLocalTime().ToString("HH:mm:ss");
        var activity=details.Activity;
        var key=_text.Language+"|"+JsonSerializer.Serialize(activity);
        if(key==_gameActivityRenderKey)return;
        _gameActivityRenderKey=key;GameActivityBody.Children.Clear();_gameActivityAvatarViews.Clear();
        GameActivityBody.Children.Add(new TextBlock{Text=GameActivityPhaseName(activity.Phase),FontSize=19,FontWeight=FontWeights.SemiBold,Foreground=SocialBrush("#72DDAA"),Margin=new Thickness(0,0,0,14)});
        void Information(string label,string value)
        {
            var grid=new Grid{Margin=new Thickness(0,0,0,9)};grid.ColumnDefinitions.Add(new ColumnDefinition());grid.ColumnDefinitions.Add(new ColumnDefinition{Width=GridLength.Auto});
            grid.Children.Add(new TextBlock{Text=label,Foreground=SocialBrush("#A8BBD2")});
            var text=new TextBlock{Text=value,FontWeight=FontWeights.SemiBold,Margin=new Thickness(16,0,0,0)};Grid.SetColumn(text,1);grid.Children.Add(text);GameActivityBody.Children.Add(grid);
        }
        if(activity.Phase is "lobby" or "match")Information(T("Режим", "Mode"),activity.Multiplayer?T("Сетевая игра", "Multiplayer"):T("Одиночная игра", "Single player"));
        if(activity.ElapsedSeconds is int elapsed)
        {
            var time=TimeSpan.FromSeconds(elapsed);Information(T("Время матча", "Match time"),time.TotalHours>=1?$"{(int)time.TotalHours}:{time.Minutes:00}:{time.Seconds:00}":$"{time.Minutes:00}:{time.Seconds:00}");
        }
        if(activity.Width is int width&&activity.Height is int height)Information(T("Размер карты", "Map size"),$"{width} × {height}");
        var people=activity.Players??[];
        if(people.Count==0)return;
        GameActivityBody.Children.Add(new TextBlock{Text=T("УЧАСТНИКИ", "PARTICIPANTS")+$" · {people.Count}",FontSize=12,Foreground=SocialBrush("#A8BBD2"),Margin=new Thickness(0,13,0,10)});
        foreach(var team in people.GroupBy(p=>p.Team).OrderBy(g=>g.Key??int.MaxValue))
        {
            var group=new StackPanel{Margin=new Thickness(0,0,0,14),Tag=team.Key};
            var heading=new Grid{Margin=new Thickness(0,0,0,8)};
            heading.ColumnDefinitions.Add(new ColumnDefinition());heading.ColumnDefinitions.Add(new ColumnDefinition{Width=GridLength.Auto});
            heading.Children.Add(new TextBlock{Text=team.Key is int number?T("Команда ","Team ")+number:T("Без указанной команды","Team not specified"),FontSize=14,FontWeight=FontWeights.SemiBold,Foreground=SocialBrush("#ECD08A")});
            var count=new TextBlock{Text=team.Count().ToString(),FontSize=12,Foreground=SocialBrush("#A8BBD2"),VerticalAlignment=VerticalAlignment.Center};Grid.SetColumn(count,1);heading.Children.Add(count);
            group.Children.Add(heading);
            foreach(var player in team)
            {
            var grid=new Grid();grid.ColumnDefinitions.Add(new ColumnDefinition{Width=new GridLength(42)});grid.ColumnDefinitions.Add(new ColumnDefinition());grid.ColumnDefinitions.Add(new ColumnDefinition{Width=GridLength.Auto});
            var marker=new Grid{Width=34,Height=34,HorizontalAlignment=HorizontalAlignment.Left,VerticalAlignment=VerticalAlignment.Center};
            if(player.Profile is { } identity)
            {
                var avatar=new ContentControl{Content=SocialAvatar(identity.Id,34,false,openProfile:false),IsHitTestVisible=false};
                marker.Children.Add(avatar);
                if(!_gameActivityAvatarViews.TryGetValue(identity.Id,out var views))_gameActivityAvatarViews[identity.Id]=views=[];
                views.Add(avatar);
            }
            else marker.Children.Add(new LauncherIcon{Kind=player.Bot?IconKind.Bot:IconKind.Person,Width=22,Height=22,Foreground=SocialBrush("#CBD9EB")});
            marker.Children.Add(new Border{Width=12,Height=12,CornerRadius=new CornerRadius(6),Background=SocialBrush(GameActivity.ValidColor(player.Color)?player.Color!:"#56677D"),BorderBrush=SocialBrush("#D2DDEA"),BorderThickness=new Thickness(1),HorizontalAlignment=HorizontalAlignment.Right,VerticalAlignment=VerticalAlignment.Bottom,ToolTip=GameActivity.ValidColor(player.Color)?T("Цвет игрока","Player color"):T("Цвет пока не определён","Color is not available yet")});
            grid.Children.Add(marker);
            var names=new StackPanel();Grid.SetColumn(names,1);
            names.Children.Add(new TextBlock{Text=player.Profile?.DisplayName??player.Name,FontWeight=FontWeights.SemiBold,TextTrimming=TextTrimming.CharacterEllipsis});
            if(player.Profile is { } profile)
            {
                names.Children.Add(new TextBlock{Text="@"+profile.Nickname,FontSize=12,Foreground=SocialBrush("#8CB5E5"),Margin=new Thickness(0,3,0,0)});
                if(profile.DisplayName!=player.Name)names.Children.Add(new TextBlock{Text=T("В игре: ","In game: ")+player.Name,FontSize=12,Foreground=SocialBrush("#A8BBD2"),TextTrimming=TextTrimming.CharacterEllipsis,Margin=new Thickness(0,3,0,0)});
            }
            grid.Children.Add(names);
            var badge=new Border{Child=new TextBlock{Text=player.Bot?T("Бот","Bot"):player.Profile is not null?"Paw’s Launcher":T("Игрок","Player"),FontSize=11,Foreground=SocialBrush(player.Profile is not null?"#8FD8B7":"#C4D2E5")},Background=SocialBrush(player.Profile is not null?"#1E443E":"#243C56"),CornerRadius=new CornerRadius(5),Padding=new Thickness(7,3,7,3),Margin=new Thickness(10,0,0,0),VerticalAlignment=VerticalAlignment.Center};Grid.SetColumn(badge,2);grid.Children.Add(badge);
            if(player.Profile is { } linked)
            {
                var button=new Button{Content=grid,Style=(Style)FindResource("GameParticipantButton"),Tag=linked.Id,
                    ToolTip=T("Открыть профиль", "Open profile")};
                System.Windows.Automation.AutomationProperties.SetName(button,T("Открыть профиль: ","Open profile: ")+linked.DisplayName);
                button.Click+=async(_,e)=>{e.Handled=true;await OpenGameParticipantProfileAsync(linked);};
                group.Children.Add(new Border{Child=button,Margin=new Thickness(0,0,0,6),Tag=player.Key});
            }
            else group.Children.Add(new Border{Child=grid,Background=SocialBrush("#1A324D"),BorderBrush=SocialBrush("#2A4564"),BorderThickness=new Thickness(1),CornerRadius=new CornerRadius(8),Padding=new Thickness(12,10,12,10),Margin=new Thickness(0,0,0,6),Tag=player.Key});
            }
            GameActivityBody.Children.Add(group);
        }
    }
    private async void GameActivityClose_Click(object sender,RoutedEventArgs e)=>await DismissGameActivityAsync();
    private async Task DismissGameActivityAsync()
    {
        var generation=_gameActivityGeneration;GameActivityCard.IsHitTestVisible=false;
        if(await Motion.HideAsync(GameActivityOverlay)&&generation==_gameActivityGeneration){CloseGameActivity();SocialDetailsGameActivityButton.Focus();}
    }
    private void CloseGameActivity()
    {
        _gameActivityGeneration++;_gameActivityLifetime?.Cancel();_gameActivityLifetime?.Dispose();_gameActivityLifetime=null;
        _gameActivityTimer?.Stop();_gameActivityPeer=null;_gameActivityBusy=false;_gameActivityShown=null;_gameActivityRenderKey=null;
        _gameActivityOpeningProfile=false;_gameActivityAvatarViews.Clear();
        Motion.Collapse(GameActivityOverlay);GameActivityBody.Children.Clear();GameActivityStatus.Text="";
    }
}
