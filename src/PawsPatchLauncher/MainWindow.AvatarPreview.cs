using System.Windows;
using System.Windows.Automation;
using System.Windows.Input;
using System.Windows.Media;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private Guid? _avatarPreviewPeer;
    private string? _avatarPreviewOwner;
    private int _avatarPreviewGeneration;
    private bool _avatarPreviewClosing;

    private ImageBrush? ProfileAvatarPhoto(SocialPlayer player)
    {
        if(player.Deleted || player.AvatarRevision is null)return null;
        if(player.Id.ToString()==_account.UserId)
            return _accountAvatarOwner==_account.UserId && player.AvatarRevision==_account.AvatarChangedAt && player.AvatarRevision==_accountAvatarRevision ? _accountAvatar : null;
        // Reuse the decoded 256 px photo from the profile. A removed/replaced revision
        // must not expose a stale image retained for an earlier game participant list.
        if(_gameParticipantAvatars.TryGetValue(player.Id,out var participant)&&participant.revision==player.AvatarRevision)return participant.image;
        return _socialAvatars.TryGetValue(player.Id,out var friend)&&friend.revision==player.AvatarRevision?friend.image:null;
    }

    private void RefreshAvatarPreviewAvailability()
    {
        var player=SocialDetailsPlayer();
        var photo=player is null?null:ProfileAvatarPhoto(player);
        SocialDetailsAvatarButton.IsEnabled=photo is not null;
        SocialDetailsAvatarButton.ToolTip=photo is null?null:T("Посмотреть аватарку игрока","View player avatar");
        AutomationProperties.SetName(SocialDetailsAvatarButton,T("Посмотреть аватарку игрока","View player avatar"));
        if(_avatarPreviewPeer is not Guid peer)return;
        if(player?.Id!=peer || photo is null || _avatarPreviewOwner!=_account.UserId || SocialDetailsOverlay.Visibility!=Visibility.Visible)
        { CloseAvatarPreview(restoreFocus:true);return; }
        RenderAvatarPreview(player,photo);
    }

    private void SocialDetailsAvatar_Click(object sender,RoutedEventArgs e)
    {
        e.Handled=true;
        ShowAvatarPreview();
    }

    private void ShowAvatarPreview()
    {
        if(ConfirmationActive || _accountLifetime.IsCancellationRequested || SocialDetailsOverlay.Visibility!=Visibility.Visible
            || !SocialDetailsCard.IsHitTestVisible || GameActivityOverlay.Visibility==Visibility.Visible
            || SocialDetailsPlayer() is not { } player || ProfileAvatarPhoto(player) is not { } photo)return;
        if(_avatarPreviewPeer==player.Id && AvatarPreviewOverlay.Visibility==Visibility.Visible)return;
        _avatarPreviewGeneration++;
        _avatarPreviewPeer=player.Id;_avatarPreviewOwner=_account.UserId;_avatarPreviewClosing=false;
        RenderAvatarPreview(player,photo);
        AvatarPreviewCard.IsHitTestVisible=true;
        AvatarPreviewCard.Visibility=AvatarPreviewOverlay.Visibility=Visibility.Visible;AvatarPreviewOverlay.UpdateLayout();
        Motion.Reveal(AvatarPreviewOverlay);RevealDialogCard(AvatarPreviewCard);
        AvatarPreviewClose.Focus();
    }

    private void RenderAvatarPreview(SocialPlayer player,ImageBrush photo)
    {
        AvatarPreviewName.Text=player.Name;AvatarPreviewName.ToolTip=player.Name;
        AvatarPreviewUsername.Text="@"+player.Nickname;
        AvatarPreviewPhoto.Fill=photo;
        AvatarPreviewClose.ToolTip=T("Закрыть просмотр аватарки","Close avatar preview");
        AutomationProperties.SetName(AvatarPreviewClose,(string)AvatarPreviewClose.ToolTip);
        AutomationProperties.SetName(AvatarPreviewCard,T("Аватарка игрока: ","Player avatar: ")+player.Name);
        AutomationProperties.SetName(AvatarPreviewPhoto,T("Аватарка игрока: ","Player avatar: ")+player.Name);
    }

    private void CloseAvatarPreview(bool restoreFocus=false)
    {
        var peer=_avatarPreviewPeer;var owner=_avatarPreviewOwner;
        _avatarPreviewGeneration++;_avatarPreviewPeer=null;_avatarPreviewOwner=null;_avatarPreviewClosing=false;
        Motion.Collapse(AvatarPreviewOverlay);Motion.Collapse(AvatarPreviewCard);
        AvatarPreviewCard.RenderTransform=Transform.Identity;AvatarPreviewCard.IsHitTestVisible=true;
        AvatarPreviewPhoto.Fill=null;AvatarPreviewName.Text=AvatarPreviewUsername.Text="";
        AvatarPreviewName.ToolTip=null;
        AutomationProperties.SetName(AvatarPreviewCard,"");AutomationProperties.SetName(AvatarPreviewPhoto,"");
        if(restoreFocus && peer==_socialDetailsPeer && owner==_account.UserId && SocialDetailsOverlay.Visibility==Visibility.Visible)
        {
            if(SocialDetailsAvatarButton.IsEnabled)SocialDetailsAvatarButton.Focus();
            else SocialDetailsClose.Focus();
        }
    }

    private async Task DismissAvatarPreviewAsync()
    {
        if(ConfirmationActive || _avatarPreviewPeer is null || _avatarPreviewClosing)return;
        var generation=_avatarPreviewGeneration;
        _avatarPreviewClosing=true;AvatarPreviewCard.IsHitTestVisible=false;
        if(await Motion.HideAsync(AvatarPreviewOverlay) && generation==_avatarPreviewGeneration)CloseAvatarPreview(restoreFocus:true);
    }

    private async void AvatarPreviewClose_Click(object sender,RoutedEventArgs e)
    {
        e.Handled=true;
        await DismissAvatarPreviewAsync();
    }

    private async void SocialDetails_PreviewKeyDown(object sender,KeyEventArgs e)
    {
        if(e.Handled || ConfirmationActive || SocialDetailsOverlay.Visibility!=Visibility.Visible)return;
        if(AvatarPreviewOverlay.Visibility==Visibility.Visible)
        {
            if(e.Key==Key.Tab){e.Handled=true;AvatarPreviewClose.Focus();}
            else if(e.Key==Key.Escape){e.Handled=true;await DismissAvatarPreviewAsync();}
            return;
        }
        if(e.Key!=Key.Escape)return;
        e.Handled=true;
        if(GameActivityOverlay.Visibility==Visibility.Visible)await DismissGameActivityAsync();
        else await DismissSocialDetailsAsync();
    }
}
