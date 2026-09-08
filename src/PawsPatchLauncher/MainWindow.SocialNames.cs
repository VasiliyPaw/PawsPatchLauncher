using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
namespace PawsPatchLauncher;
public partial class MainWindow
{
    private FrameworkElement SocialNameLabel(SocialPlayer player)
    {
        var stack=new StackPanel{VerticalAlignment=VerticalAlignment.Center};
        stack.Children.Add(new TextBlock{Text=PlayerDisplayName(player),FontSize=13,FontWeight=FontWeights.SemiBold,TextTrimming=TextTrimming.CharacterEllipsis});
        var username=new TextBlock{Text=PlayerUsername(player),FontSize=11,Foreground=SocialBrush("#9EB5CE"),VerticalAlignment=VerticalAlignment.Center,TextTrimming=TextTrimming.CharacterEllipsis,Margin=new Thickness(0,2,0,0),
            LineStackingStrategy=LineStackingStrategy.BlockLineHeight,LineHeight=19};
        if(!player.Deleted&&player.AdminLevel>0)
        {
            username.Margin=new Thickness(0);
            var badge=AdministratorBadge(player.AdminLevel);badge.Margin=new Thickness(0);badge.Padding=new Thickness(6,2,6,2);
            if(badge.Child is TextBlock label)label.TextTrimming=TextTrimming.CharacterEllipsis;
            var line=new SocialIdentityLine{Margin=new Thickness(0,2,0,0)};
            line.Children.Add(username);line.Children.Add(badge);stack.Children.Add(line);
        }
        else stack.Children.Add(username);
        if(player.Banned)stack.Children.Add(new TextBlock{Text=T("Заблокирован на площадке","Banned on platform"),Foreground=SocialBrush("#FFB1A8"),FontSize=11,Margin=new Thickness(0,4,0,0)});
        return stack;
    }
    private void OpenSocialContextAt(FrameworkElement anchor,Guid id)
    {
        if(_busy||_accountBusy||ConfirmationActive)return;
        var friend=_socialPlayers.FirstOrDefault(p=>p.Id==id&&p.Relation=="friend");if(friend is null)return;
        CloseSocialMenu();
        var menu=CreateSocialMenu(new Button(),friend);
        menu.PlacementTarget=anchor;menu.Placement=PlacementMode.MousePoint;menu.HorizontalOffset=menu.VerticalOffset=0;
        RevealSocialMenu(menu);
    }
    private bool ShowingIncomingChat(Guid id)=>_socialPeer==id&&IsActive&&WindowState!=WindowState.Minimized
        &&_activePage=="friends"&&_socialSection=="chats"&&FriendsChatCard.Visibility==Visibility.Visible
        &&!ConfirmationActive&&SocialDetailsOverlay.Visibility!=Visibility.Visible&&HelpOverlay.Visibility!=Visibility.Visible
        &&BroadcastOverlay.Visibility!=Visibility.Visible&&FriendsDialogOverlay.Visibility!=Visibility.Visible;
    private int VisibleUnread(SocialPlayer player)=>ShowingIncomingChat(player.Id)?0:player.Unread;
}
