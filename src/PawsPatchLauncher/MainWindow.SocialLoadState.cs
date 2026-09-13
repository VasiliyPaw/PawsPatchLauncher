using System.Windows;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private bool _accountStartupPending = !ActivityStore.IsSmokeTest;
    private bool _socialListLoading, _socialListFailed;

    private async Task RestoreStartupAccountAsync()
    {
        _accountStartupPending = true;
        RenderAccount();
        // Startup must read the saved identity even when the connection probe has
        // already reported offline. Otherwise it stays Guest and reconnect never resumes it.
        try { await RestoreAccountAsync(background: true); }
        finally
        {
            _accountStartupPending = false;
            if (!_accountLifetime.IsCancellationRequested) { RenderAccount(); LoadInitialFriendsAfterAccount(); }
        }
    }

    private void RenderSocialListState(bool? noMatches = null)
    {
        var received = _socialListReceived != default;
        var guest = _account.State == AccountState.Guest;
        var connecting = _accountStartupPending || !received && (_accountBusy || _accountRefreshing);
        var unavailable = !connecting && !received && !_socialListLoading && (_socialListFailed || _account.State == AccountState.Offline);
        var loading = connecting || !guest && !received && !unavailable;
        var showList = !guest || connecting;
        var showState = showList && !_account.Restricted;
        FriendsGuestPanel.Visibility = showList ? Visibility.Collapsed : Visibility.Visible;
        FriendsSignedInPanel.Visibility = showList ? Visibility.Visible : Visibility.Collapsed;
        FriendsSearchPanel.Visibility = received ? Visibility.Visible : Visibility.Collapsed;
        FriendsListLoadingIndicator.Visibility = showState && loading ? Visibility.Visible : Visibility.Collapsed;
        var query = FriendsSearchInput.Text.Trim().TrimStart('@');
        var empty = noMatches ?? !_socialPlayers.Any(p => p.Relation == "friend" && (query.Length == 0
            || p.Name.Contains(query, StringComparison.OrdinalIgnoreCase) || p.Nickname.Contains(query, StringComparison.OrdinalIgnoreCase)));
        FriendsListEmptyText.Text = connecting ? T("Подключаю аккаунт…", "Connecting your account…")
            : unavailable ? T("Не удалось загрузить список друзей.", "Could not load your friends.")
            : !received ? T("Загружаю друзей…", "Loading friends…")
            : query.Length > 0 ? T("Никого не найдено", "No matches") : T("Друзей пока нет", "No friends yet");
        FriendsListEmptyText.Visibility = showState && (!received || empty) ? Visibility.Visible : Visibility.Collapsed;
        FriendsListRetryButton.Content = T("Повторить", "Retry");
        FriendsListRetryButton.Visibility = showState && unavailable ? Visibility.Visible : Visibility.Collapsed;
        FriendsListRetryButton.IsEnabled = !_accountBusy && !_accountRefreshing && !_socialListLoading && !_socialBusy;
    }

    private void LoadInitialFriendsAfterAccount()
    {
        // A Friends click during account restoration cannot enter the social gate.
        // Start that deferred first read now instead of waiting for the next poll.
        if (_activePage == "friends" && _account.State == AccountState.SignedIn && !_account.Restricted
            && _socialListReceived == default && !_socialListLoading && !_accountBusy && !_accountRefreshing
            && DateTimeOffset.UtcNow >= _socialRetryAfter) _ = RefreshSocialAsync();
    }

    private async void FriendsListRetry_Click(object sender, RoutedEventArgs e)
    {
        if (_accountBusy || _accountRefreshing || _socialBusy || _socialListLoading) return;
        if (_account.State == AccountState.Offline) await RestoreAccountAsync(background: false);
        else if (_account.State == AccountState.SignedIn) await RefreshSocialAsync();
    }
}
