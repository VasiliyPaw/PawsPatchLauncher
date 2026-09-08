using Microsoft.Win32;
using System.Windows;
using System.Windows.Media;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
namespace PawsPatchLauncher;
public partial class MainWindow
{
    private ImageBrush? _accountAvatar;
    private string _accountAvatarOwner = "";
    private DateTimeOffset? _accountAvatarRevision;
    private bool _accountAvatarLoaded;

    private void RenderAccountAvatar()
    {
        var own = _account.State != AccountState.Guest && _account.UserId == _accountAvatarOwner;
        if (!own) { _accountAvatar = null; _accountAvatarLoaded = false; _accountAvatarOwner = ""; _accountAvatarRevision = null; }
        var visible = own && _accountAvatar is not null;
        AccountAvatarPicture.Fill = AccountProfileAvatarPicture.Fill = visible ? _accountAvatar : null;
        AccountAvatarPicture.Visibility = AccountProfileAvatarPicture.Visibility = visible ? Visibility.Visible : Visibility.Collapsed;
        AccountAvatarPlaceholder.Visibility = AccountProfileAvatarPlaceholder.Visibility = visible ? Visibility.Collapsed : Visibility.Visible;
        AccountAvatarEditButton.ToolTip = T("Изменить аватарку", "Change avatar");
        System.Windows.Automation.AutomationProperties.SetName(AccountAvatarEditButton, (string)AccountAvatarEditButton.ToolTip);
        AccountAvatarEditButton.IsEnabled = _account.State == AccountState.SignedIn && !_accountBusy && !_account.Restricted;
        AccountPersonalSectionText.Text = T("ПРОФИЛЬ", "PROFILE");
        AccountSecuritySectionText.Text = T("БЕЗОПАСНОСТЬ", "SECURITY");
        AccountDeleteButton.Content = T("Удалить аккаунт", "Delete account");
        AccountDeleteButton.IsEnabled = _account.State == AccountState.SignedIn && !_accountBusy && !_account.ProtectedAdmin;
    }

    private void AccountAvatarEdit_Click(object sender, RoutedEventArgs e)
    {
        if (!AccountAvatarEditButton.IsEnabled || ConfirmationActive) return;
        CloseSocialMenu();
        var owner = _account.UserId;
        var menu = new ContextMenu { Style = (Style)FindResource("SocialContextMenu"),
            PlacementTarget = AccountAvatarEditButton, Placement = PlacementMode.Bottom, VerticalOffset = 8 };
        var upload = new MenuItem { Header = T("Загрузить новую аватарку", "Upload new avatar"),
            Style = (Style)FindResource("SocialMenuItem"), Icon = new LauncherIcon { Kind = IconKind.Camera, Width = 19, Height = 19 } };
        var remove = new MenuItem { Header = T("Удалить аватарку", "Remove avatar"),
            Style = (Style)FindResource("SocialMenuItem"), Foreground = SocialBrush("#F3AA96"),
            Icon = new LauncherIcon { Kind = IconKind.Trash, Width = 19, Height = 19, Foreground = SocialBrush("#F3AA96") },
            IsEnabled = _accountAvatar is not null || _account.AvatarChangedAt is not null };
        upload.Click += (_, _) => { CloseSocialMenu(); if (_account.UserId == owner) AccountAvatarChoose_Click(sender, e); };
        remove.Click += (_, _) => { CloseSocialMenu(); if (_account.UserId == owner && !_accountBusy && !ConfirmationActive) AccountAvatarRemove_Click(sender, e); };
        menu.Items.Add(upload); menu.Items.Add(remove);
        _socialMenu = menu; menu.IsOpen = true;
    }

    private void SetAccountAvatar(string owner, byte[]? jpeg)
    {
        if (_account.UserId != owner || _account.State == AccountState.Guest) return;
        ImageBrush? brush = jpeg is null ? null : new ImageBrush(AccountAvatarImage.Decode(jpeg, normalized: true)) { Stretch = Stretch.UniformToFill };
        brush?.Freeze(); _accountAvatar = brush; _accountAvatarOwner = owner; _accountAvatarLoaded = true;
        _accountAvatarRevision = _account.AvatarChangedAt;
        RenderAccountAvatar();
        _socialRenderedContext=null;RenderSocialMessages();
        if (jpeg is not null) { Motion.Reveal(AccountAvatarPicture); Motion.Reveal(AccountProfileAvatarPicture); }
    }

    private async Task RefreshAccountAvatarAsync()
    {
        if (_account.State != AccountState.SignedIn || _accountAvatarLoaded && _accountAvatarOwner == _account.UserId && _accountAvatarRevision == _account.AvatarChangedAt) return;
        var owner = _account.UserId;
        try { SetAccountAvatar(owner, await _account.GetAvatarAsync(_accountLifetime.Token)); }
        catch (AccountException error) when (error.Code is not ("session_expired" or "session_replaced" or "unauthorized")) { } // Cosmetic download failures must not hide a revoked session.
    }

    private async void AccountAvatarChoose_Click(object sender, RoutedEventArgs e)
    {
        if (_accountBusy || ConfirmationActive || _account.State != AccountState.SignedIn) return;
        var dialog = new OpenFileDialog { Filter = T("Изображения (*.png;*.jpg;*.jpeg)|*.png;*.jpg;*.jpeg", "Images (*.png;*.jpg;*.jpeg)|*.png;*.jpg;*.jpeg"), CheckFileExists = true, Multiselect = false };
        if (dialog.ShowDialog(this) != true) return;
        await AccountOperationAsync(async () =>
        {
            using var file = new FileStream(dialog.FileName, FileMode.Open, FileAccess.Read, FileShare.Read);
            if (file.Length > AccountAvatarImage.MaxInputBytes) throw new AccountException("avatar_too_large");
            var original = new byte[(int)file.Length]; await file.ReadExactlyAsync(original, _accountLifetime.Token);
            var jpeg = AccountAvatarImage.Normalize(original);
            var owner = _account.UserId;
            await _account.SetAvatarAsync(jpeg, _accountLifetime.Token);
            SetAccountAvatar(owner, jpeg); _accountMessage = "avatar_saved";
        });
    }
    private async void AccountAvatarRemove_Click(object sender, RoutedEventArgs e)
    {
        await AccountOperationAsync(async () => {
            var owner = _account.UserId; await _account.RemoveAvatarAsync(_accountLifetime.Token);
            SetAccountAvatar(owner, null); _accountMessage = "avatar_removed";
        });
    }
}
