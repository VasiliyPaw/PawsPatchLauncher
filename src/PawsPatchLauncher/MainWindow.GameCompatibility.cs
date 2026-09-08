using System.Windows;
using System.Windows.Controls;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private GameCompatibilityState _compatibilityState;
    private string _compatibilityKey="",_compatibilityPopupKey="",_compatibilityLanguage="";
    private CancellationTokenSource? _compatibilityCancellation;
    private DateTimeOffset _compatibilityRetry;
    private Border? _compatibilityPopup;
    private bool _compatibilityClosed,_launchStarting;
    private bool CompatibilityBlocksLaunch => _compatibilityState is GameCompatibilityState.Checking or GameCompatibilityState.Unsupported or GameCompatibilityState.Unavailable;

    private string CompatibilityKey(GameInstallation game,GameRequirement requirement)
    {
        GameFileStamp stamp;try{stamp=GameFileStamp.Read(game.ExecutablePath);}catch{stamp=new(-1,0);}
        return game.ExecutablePath+"|"+stamp+"|"+requirement.Version+"|"+requirement.SteamBuild+"|"+string.Join(",",requirement.K2ExeSha256).ToUpperInvariant();
    }
    private void RefreshCompatibility()
    {
        if(_compatibilityClosed)return;
        if(!ActivityStore.IsSmokeTest&&!_busy)
        {
            if(_game is not null&&_channel is not null)
            {
                var key=CompatibilityKey(_game,_channel.Game);
                if(key!=_compatibilityKey||_compatibilityState==GameCompatibilityState.Unavailable&&DateTimeOffset.UtcNow>=_compatibilityRetry)
                    _=CheckGameCompatibilityAsync(false);
            }
            else if(_compatibilityKey.Length>0)
            {
                _compatibilityCancellation?.Cancel();_compatibilityKey="";
                _compatibilityState=GameCompatibilityState.Unchecked;
            }
        }
        RenderCompatibility();
    }
    private async Task<bool> CheckGameCompatibilityAsync(bool force)
    {
        if(_game is null||_channel is null||_compatibilityClosed)return false;
        var game=_game;var requirement=_channel.Game;var hashes=requirement.K2ExeSha256.ToArray();
        var key=CompatibilityKey(game,requirement);
        if(!force&&key==_compatibilityKey&&_compatibilityState is not (GameCompatibilityState.Unchecked or GameCompatibilityState.Unavailable))
            return _compatibilityState==GameCompatibilityState.Supported;
        _compatibilityCancellation?.Cancel();
        var cancellation=new CancellationTokenSource();_compatibilityCancellation=cancellation;
        _compatibilityKey=key;_compatibilityState=GameCompatibilityState.Checking;
        RenderCompatibility();LaunchButton.IsEnabled=false;
        try
        {
            // Disk reads/hashing never run synchronously on the UI thread.
            var state=await Task.Run(()=>GameCompatibility.CheckAsync(game.ExecutablePath,hashes,cancellation.Token));
            if(cancellation.IsCancellationRequested||_compatibilityClosed||!ReferenceEquals(_compatibilityCancellation,cancellation))return false;
            if(_game is null||_channel is null||key!=CompatibilityKey(_game,_channel.Game))
            {
                _compatibilityKey="";_compatibilityState=GameCompatibilityState.Checking;
                return false;
            }
            _compatibilityState=state;_compatibilityRetry=DateTimeOffset.UtcNow.AddSeconds(10);
            return state is GameCompatibilityState.Supported or GameCompatibilityState.Unchecked;
        }
        catch(OperationCanceledException){return false;}
        finally
        {
            if(ReferenceEquals(_compatibilityCancellation,cancellation)&&!_compatibilityClosed)RefreshStatus();
            cancellation.Dispose();
            if(ReferenceEquals(_compatibilityCancellation,cancellation))_compatibilityCancellation=null;
        }
    }
    private string SupportedGameDescription()
    {
        var game=_channel?.Game;
        return game is null?"":T("Поддерживается Kohan II ","Supported Kohan II version: ")+game.Version+" · Steam build "+game.SteamBuild;
    }
    private void RenderCompatibility()
    {
        var unsupported=_compatibilityState==GameCompatibilityState.Unsupported;
        var unreadable=_compatibilityState==GameCompatibilityState.Unavailable;
        GameCompatibilityHint.Text=unsupported?T("Версия игры не подходит для этого патча.","This game version is not supported by this patch."):
            unreadable?T("Не удалось проверить файлы игры. Запуск недоступен.","Could not verify game files. Launch unavailable."):"";
        GameCompatibilityHint.ToolTip=SupportedGameDescription();
        GameCompatibilityHint.Visibility=unsupported||unreadable?Visibility.Visible:Visibility.Collapsed;
        if(unsupported||unreadable)
        {
            ReadyStatusText.Text=unsupported?T("Версия игры не подходит","Unsupported game version"):T("Нужна проверка файлов","File check required");
            ReadyStatusText.Foreground=SocialBrush("#FF9D9D");ReadyStatusBadge.Background=SocialBrush("#3B2226");ReadyStatusBadge.BorderBrush=SocialBrush("#844B50");
        }
        if(!unsupported)
        {
            if(_compatibilityState!=GameCompatibilityState.Checking)
            {
                if(_compatibilityPopup is not null)((Grid)ToastHost.Parent).Children.Remove(_compatibilityPopup);
                _compatibilityPopup=null;_compatibilityPopupKey="";
            }
            return;
        }
        var show=_compatibilityPopupKey!=_compatibilityKey;
        var relanguage=_compatibilityPopup is not null&&_compatibilityLanguage!=_text.Language;
        if(!show&&!relanguage)return;
        _compatibilityPopupKey=_compatibilityKey;_compatibilityLanguage=_text.Language;
        if(_compatibilityPopup is not null)((Grid)ToastHost.Parent).Children.Remove(_compatibilityPopup);
        var body=new StackPanel();var heading=new DockPanel();
        var close=new Button{Style=(Style)FindResource("GhostButton"),Content=new LauncherIcon{Kind=IconKind.Close},Width=30,Height=30,Padding=new Thickness(0),Margin=new Thickness(14,0,0,0),ToolTip=T("Закрыть","Close")};
        DockPanel.SetDock(close,Dock.Right);heading.Children.Add(close);
        heading.Children.Add(new TextBlock{Text=T("Версия игры не поддерживается","Unsupported game version"),FontSize=20,FontWeight=FontWeights.SemiBold,Foreground=SocialBrush("#FFD0D0"),TextWrapping=TextWrapping.Wrap});
        body.Children.Add(heading);
        body.Children.Add(new TextBlock{Text=SupportedGameDescription(),FontSize=14,Foreground=SocialBrush("#FFE3DC"),Margin=new Thickness(0,16,0,10),TextWrapping=TextWrapping.Wrap});
        body.Children.Add(new TextBlock{Text=T("Установленный k2.exe не соответствует поддерживаемой версии. Если игра обновилась в Steam, дождитесь обновления патча под новую версию игры. Проверка и установка обновлений патча остаются доступны.",
            "The installed k2.exe does not match a supported version. If Steam updated the game, wait for a patch update compatible with the new game version. Checking for and installing patch updates remains available."),Foreground=SocialBrush("#E9B9BC"),FontSize=13,TextWrapping=TextWrapping.Wrap,LineHeight=21});
        var popup=RestrictionCard("");popup.Child=body;popup.MaxWidth=650;popup.Padding=new Thickness(22);popup.Margin=new Thickness(24);popup.HorizontalAlignment=HorizontalAlignment.Center;popup.VerticalAlignment=VerticalAlignment.Center;
        _compatibilityPopup=popup;
        close.Click+=async(_,_)=>{if(await Motion.HideAsync(popup)){((Grid)ToastHost.Parent).Children.Remove(popup);if(ReferenceEquals(_compatibilityPopup,popup))_compatibilityPopup=null;}};
        Grid.SetRowSpan(popup,2);Panel.SetZIndex(popup,950);((Grid)ToastHost.Parent).Children.Add(popup);Motion.Reveal(popup);
    }
}
