using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
namespace PawsPatchLauncher;
public partial class MainWindow
{
    private string _moderationKey="",_banPopupKey="";
    private Border? _banPopup;
    private Border StatusPill(string text,string background,string foreground)=>new(){Background=SocialBrush(background),CornerRadius=new CornerRadius(5),Padding=new Thickness(7,3,7,3),Margin=new Thickness(8,0,0,0),VerticalAlignment=VerticalAlignment.Center,
        Child=new TextBlock{Text=text,FontSize=11,Foreground=SocialBrush(foreground)}};
    private Border AdministratorBadge(int level,bool inline=true)
    {
        var badge=StatusPill(T("Администратор","Administrator"),"#45391D","#F2D389");
        badge.HorizontalAlignment=HorizontalAlignment.Left;
        if(!inline)badge.Margin=new Thickness(0,5,0,2);
        badge.ToolTip=T("Администратор площадки · роль подтверждена сервером","Platform administrator · server-verified role");
        System.Windows.Automation.AutomationProperties.SetName(badge,badge.ToolTip.ToString());return badge;
    }
    private string BanDescription(DateTimeOffset? start,DateTimeOffset? until,string reason)
    {
        if(start is null)return "";
        var title=until is null?T("Постоянная блокировка","Permanent ban"):T("Временная блокировка","Temporary ban");
        var text=title+" · "+ChatDate(start.Value);
        if(until is DateTimeOffset deadline)
        {
            var remaining=deadline-DateTimeOffset.UtcNow;if(remaining<TimeSpan.Zero)remaining=TimeSpan.Zero;
            text+="\n"+T("До: ","Until: ")+ChatDate(deadline)+T(" · осталось "," · remaining ")+
                (remaining.Days>0?remaining.Days+T(" д ","d "):"")+remaining.ToString(@"hh\:mm\:ss");
        }
        if(!string.IsNullOrWhiteSpace(reason))text+="\n"+T("Причина: ","Reason: ")+reason;
        return text;
    }
    private Border RestrictionCard(string message)=>new(){Background=SocialBrush("#3F2530"),BorderBrush=SocialBrush("#B45F68"),BorderThickness=new Thickness(1),CornerRadius=new CornerRadius(9),Padding=new Thickness(14),Margin=new Thickness(0,0,0,12),
        Child=new TextBlock{Text=message,Foreground=SocialBrush("#FFBDC0"),FontSize=13,TextWrapping=TextWrapping.Wrap}};
    private void RenderModerationState()
    {
        var signed=_account.State!=AccountState.Guest;var restricted=signed&&_account.Restricted;
        AdminNav.Content=T("Админ-панель","Admin panel");AdminNav.Visibility=_account.AdminLevel>0?Visibility.Visible:Visibility.Collapsed;
        if(_adminOwner!=_account.UserId||_account.AdminLevel<1)
        {
            _adminOwner=_account.UserId;_adminRequest++;_adminData=null;_adminRows?.Children.Clear();
            if(_adminViewedPlayer is not null){_adminViewedPlayer=null;CloseSocialDetails();}
            if(_activePage=="admin")SetActivePage("home");
        }
        if(_activePage=="admin"&&_adminLanguage!=_text.Language){BuildAdminLayout();_ = LoadAdminAsync();}
        if(restricted&&_accountEditor is not ("" or "delete")){_accountEditor="";ClearAccountPasswords();RenderAccountProfile();}
        var key=$"{_account.UserId}|{_account.AdminLevel}|{_account.Banned}|{_account.DeletionPending}|{_account.BannedAt}|{_account.BanUntil}|{_account.BanReason}|{_text.Language}";
        if(_moderationKey!=key)
        {
            _moderationKey=key;AccountAdminBadge.Content=_account.AdminLevel>0?AdministratorBadge(_account.AdminLevel):null;
            var text=_account.Banned?T("Аккаунт заблокирован на площадке","Account banned on the platform")+"\n"+BanDescription(_account.BannedAt,_account.BanUntil,_account.BanReason):
                T("Аккаунт удалён. Восстановление через администратора доступно 7 дней.","Account deleted. An administrator can restore it within 7 days.");
            AccountModerationNotice.Content=restricted?RestrictionCard(text):null;
            FriendsModerationNotice.Content=restricted?RestrictionCard(text+"\n\n"+T("Друзья и общение недоступны. Игра и обновления работают.","Social features are unavailable. The game and updates still work.")):null;
            var popupKey=$"{_account.UserId}|{_account.BannedAt}|{_account.DeletedAt}";
            if(restricted&&_banPopupKey!=popupKey)
            {
                _banPopupKey=popupKey;
                if(_banPopup is not null)((Grid)ToastHost.Parent).Children.Remove(_banPopup);
                var content=new DockPanel();var close=new Button{Style=(Style)FindResource("GhostButton"),Content=new LauncherIcon{Kind=IconKind.Close,Width=16,Height=16},Width=28,Height=28,Padding=new Thickness(0),Margin=new Thickness(14,0,0,0),ToolTip=T("Закрыть","Close")};
                DockPanel.SetDock(close,Dock.Right);content.Children.Add(close);
                content.Children.Add(new TextBlock{Text=text+"\n"+T("Локальная игра и обновления остаются доступны.","Local game and updates remain available."),TextWrapping=TextWrapping.Wrap,Foreground=SocialBrush("#FFD0D0")});
                _banPopup=RestrictionCard("");_banPopup.Child=content;_banPopup.MaxWidth=650;_banPopup.HorizontalAlignment=HorizontalAlignment.Center;_banPopup.VerticalAlignment=VerticalAlignment.Center;_banPopup.Margin=new Thickness(24);
                var popup=_banPopup;close.Click+=async(_,_)=>{if(await Motion.HideAsync(popup))((Grid)ToastHost.Parent).Children.Remove(popup);};
                Grid.SetRowSpan(popup,2);Panel.SetZIndex(popup,1100);((Grid)ToastHost.Parent).Children.Add(popup);Motion.Reveal(popup);
            }
            if(!restricted){_banPopupKey="";if(_banPopup is not null){((Grid)ToastHost.Parent).Children.Remove(_banPopup);_banPopup=null;}}
        }
        FriendsSignedInPanel.IsEnabled=!restricted;FriendsConversationScroll.IsEnabled=!restricted;FriendsSearchButton.IsEnabled=!restricted;
        FriendsNav.ToolTip=restricted?T("Общение недоступно: аккаунт заблокирован или удалён","Social features unavailable: account banned or deleted"):null;
        RefreshModerationCountdowns();
    }
    private void RefreshModerationCountdowns()
    {
        if(_account.Restricted&&_account.Banned)
        {
            var text=T("Аккаунт заблокирован на площадке","Account banned on the platform")+"\n"+BanDescription(_account.BannedAt,_account.BanUntil,_account.BanReason);
            if(AccountModerationNotice.Content is Border {Child:TextBlock accountText})accountText.Text=text;
            if(FriendsModerationNotice.Content is Border {Child:TextBlock friendsText})friendsText.Text=text+"\n\n"+T("Друзья и общение недоступны. Игра и обновления работают.","Social features are unavailable. The game and updates still work.");
            if(_banPopup?.Child is DockPanel dock&&dock.Children.OfType<TextBlock>().FirstOrDefault() is TextBlock popupText)popupText.Text=text+"\n"+T("Локальная игра и обновления остаются доступны.","Local game and updates remain available.");
        }
        var player=_socialPlayers.FirstOrDefault(p=>p.Id==_socialDetailsPeer)??_adminViewedPlayer;
        if(SocialDetailsOverlay.Visibility==Visibility.Visible&&player?.Banned==true)
            SocialDetailsModerationText.Text=BanDescription(player.BannedAt,player.BanUntil,player.BanReason);
    }
    private static bool SocialContactAvailable(SocialPlayer? player)=>player?.Available==true;
    private string PlayerDisplayName(SocialPlayer p)=>p.Deleted?T("Удалённый аккаунт","Deleted account"):p.Name;
    private string PlayerUsername(SocialPlayer p)=>p.Deleted?"":"@"+p.Nickname;
    private string PlayerMarker(SocialPlayer p)=>p.Deleted?"":p.Banned?T(" · Заблокирован на площадке"," · Banned on platform"):p.AdminLevel>0?T(" · Администратор"," · Administrator"):"";
}
