using System.Windows;
using System.Windows.Input;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private string _friendsDialog = "";
    private string _friendsDialogSignature = "";
    private IInputElement? _friendsDialogPreviousFocus;

    private void ResetFriendsDialog()
    {
        _friendsDialog = ""; _friendsDialogSignature = "";
        Motion.Collapse(FriendsDialogOverlay);
        FriendsDialogRows.Children.Clear();
        RenderSocialNotifications();
    }

    private void OpenFriendsDialog(string kind)
    {
        if (_account.State != AccountState.SignedIn || _account.Restricted || _socialBusy || _accountBusy || ConfirmationActive) return;
        CloseSocialMenu();
        _friendsDialogPreviousFocus = Keyboard.FocusedElement;
        _friendsDialog = kind; _friendsDialogSignature = "";
        FriendsDialogCard.MaxWidth = kind == "add" ? 430 : 590;
        FriendsAddPanel.Visibility = kind == "add" ? Visibility.Visible : Visibility.Collapsed;
        FriendsDialogScroll.Visibility = kind == "add" ? Visibility.Collapsed : Visibility.Visible;
        RenderFriendsDialogRows(); RenderSocialNotifications();
        Motion.Reveal(FriendsDialogOverlay);
        if (kind == "add") FriendsNicknameInput.Focus(); else FriendsDialogClose.Focus();
    }

    private void RenderFriendsDialogRows()
    {
        if (_friendsDialog.Length == 0 || FriendsDialogRows is null) return;
        FriendsDialogTitle.Text = _friendsDialog == "add" ? T("Добавить друга", "Add friend")
            : _friendsDialog == "blocked" ? T("Заблокированные", "Blocked") : T("Заявки в друзья", "Friend requests");
        if (_friendsDialog == "add") return;
        var relation = _friendsDialog == "blocked" ? "blocked" : _socialRequestSection;
        var players = _socialPlayers.Where(p => p.Relation == relation).ToArray();
        var scope = _account.UserId + "|" + _friendsDialog + "|" + relation;
        var arrived = _requestArrivals.Observe(scope, players.Select(p => p.Id), _socialListReceived != default);
        var signature = scope + "|" + _text.Language + "|" + _socialAvatarGeneration + "|" +
            string.Join(";", players.Select(p => $"{p.Id}:{p.Name}:{p.Nickname}:{p.AvatarRevision}:{p.AdminLevel}:{p.Banned}:{p.Deleted}"));
        if (signature == _friendsDialogSignature) return;
        _friendsDialogSignature = signature;
        var generation = ++_requestArrivalVersion;
        FriendsDialogRows.Children.Clear();
        FriendsDialogEmpty.Text = relation == "blocked" ? T("Заблокированных пользователей нет", "No blocked users")
            : relation == "incoming" ? T("Входящих заявок пока нет", "No incoming requests") : T("Исходящих заявок пока нет", "No outgoing requests");
        FriendsDialogEmpty.Visibility = players.Length == 0 ? Visibility.Visible : Visibility.Collapsed;
        var animated = 0;
        foreach (var player in players)
        {
            var card = RenderSocialRequest(player);
            if (arrived.Contains(player.Id) && animated++ < 4)
                ScheduleSocialArrival(card, FriendsDialogScroll, () => generation == _requestArrivalVersion && _friendsDialog.Length > 0);
        }
    }

    private async Task CloseFriendsDialogAsync()
    {
        if (ConfirmationActive) return;
        var kind = _friendsDialog;
        await Motion.HideAsync(FriendsDialogOverlay);
        if (_friendsDialog != kind || FriendsDialogOverlay.Visibility == Visibility.Visible) return;
        ResetFriendsDialog();
        if (_friendsDialogPreviousFocus is UIElement { IsVisible: true, IsEnabled: true } previous) previous.Focus();
    }
    private async void FriendsDialog_MouseDown(object sender, MouseButtonEventArgs e)
    {
        if (InsideCard(e.OriginalSource as DependencyObject, FriendsDialogCard)) return;
        e.Handled = true; await CloseFriendsDialogAsync();
    }
    private async void FriendsDialog_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key != Key.Escape || ConfirmationActive) return;
        e.Handled = true; await CloseFriendsDialogAsync();
    }
}
