using System.Net.NetworkInformation;
using System.Windows;
using System.Windows.Threading;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private readonly DispatcherTimer _connectionTimer = new() { Interval = TimeSpan.FromSeconds(5) };
    private AccountService? _connectionService;
    private bool _connectionProbeBusy, _connectionBlocked;
    private bool AccountConnectionBlocked => _account?.Connection.Available == false;

    private void InitializeConnectionUi()
    {
        RenderConnectionUi();
        _connectionTimer.Tick += async (_, _) => await ProbeAccountConnectionAsync();
        Loaded += async (_, _) =>
        {
            if (ActivityStore.IsSmokeTest) return;
            NetworkChange.NetworkAvailabilityChanged += NetworkAvailabilityChanged;
            if (!NetworkInterface.GetIsNetworkAvailable()) _account.Connection.Complete(_account.Connection.Begin(), false);
            _connectionTimer.Start(); await ProbeAccountConnectionAsync();
        };
        Closed += (_, _) =>
        {
            _connectionTimer.Stop(); NetworkChange.NetworkAvailabilityChanged -= NetworkAvailabilityChanged;
            if (_connectionService is not null) _connectionService.Connection.Changed -= ServiceConnectionChanged;
        };
    }
    private void NetworkAvailabilityChanged(object? sender, NetworkAvailabilityEventArgs e)
    {
        if (_accountLifetime.IsCancellationRequested) return;
        Dispatcher.BeginInvoke(new Action(() =>
        {
            if (_accountLifetime.IsCancellationRequested) return;
            if (!e.IsAvailable) _account.Connection.Complete(_account.Connection.Begin(), false);
            else _ = ProbeAccountConnectionAsync(force: true);
        }));
    }
    private async Task ProbeAccountConnectionAsync(bool force = false)
    {
        if (_connectionProbeBusy || _accountLifetime.IsCancellationRequested || ActivityStore.IsSmokeTest) return;
        // Regular account/social traffic already establishes connectivity. Probe only while idle or offline.
        if (!force && !AccountConnectionBlocked && DateTimeOffset.UtcNow - _account.Connection.CheckedAt < TimeSpan.FromSeconds(30)) return;
        _connectionProbeBusy = true;
        try { await _account.ProbeConnectionAsync(_accountLifetime.Token); }
        finally { _connectionProbeBusy = false; }
    }
    private void ServiceConnectionChanged()
    {
        if (!_accountLifetime.IsCancellationRequested)
            Dispatcher.BeginInvoke(new Action(() => { if (!_accountLifetime.IsCancellationRequested) RenderConnectionUi(); }));
    }
    private void RenderConnectionUi()
    {
        if (_account is null) return;
        if (!ReferenceEquals(_connectionService, _account))
        {
            if (_connectionService is not null) _connectionService.Connection.Changed -= ServiceConnectionChanged;
            _connectionService = _account; _connectionService.Connection.Changed += ServiceConnectionChanged;
        }
        var blocked = AccountConnectionBlocked;
        ConnectionNoticeText.Text = T("Нет подключения · Переподключение…", "No connection · Reconnecting…");
        ConnectionNotice.ToolTip = T("Нет связи с сервером. Друзья и профиль будут доступны после восстановления соединения.",
            "Cannot reach the server. Friends and profile will be available when the connection returns.");
        FriendsPanel.IsEnabled = FriendsConversationScroll.IsEnabled = AccountPanel.IsEnabled = SocialDetailsCard.IsEnabled = !blocked;
        if (_connectionBlocked == blocked) return;
        _connectionBlocked = blocked;
        RefreshStatus();
        if (blocked)
        {
            CloseSocialMenu(); RemoveChatPopup(); ResetFriendsDialog();
            if (ConfirmationActive && _activePage is "friends" or "account") _ = CompleteConfirmationAsync(false);
            ConnectionNotice.Visibility = Visibility.Visible; Motion.Reveal(ConnectionNotice);
        }
        else
        {
            Motion.Collapse(ConnectionNotice);
            _socialRetryAfter = default; _socialNextPoll = default;
            if (!ActivityStore.IsSmokeTest && _account.State != AccountState.Guest) _ = RestoreAccountAsync(background: true);
        }
    }
}
