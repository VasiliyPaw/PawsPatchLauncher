using System.Windows;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private readonly ChatMemoryCache _chatMemory = new();
    private CancellationTokenSource? _chatViewLifetime;
    private Task? _chatLoadTask;
    private int _chatLoadGeneration = -1;
    private bool _chatLoading;
    private bool _chatAwaitingLatest;
    private string? _chatLoadError;

    private void ResetChatLoad()
    {
        _chatViewLifetime?.Cancel(); _chatViewLifetime?.Dispose(); _chatViewLifetime = null;
        _chatLoadTask = null; _chatLoadGeneration = -1;
        _chatLoading = _chatAwaitingLatest = false; _chatLoadError = null;
    }
    private bool CurrentChatLoad(Guid owner, Guid peer, int generation) => !_accountLifetime.IsCancellationRequested
        && _account.UserId == owner.ToString() && !_account.Restricted && _account.State != AccountState.Guest
        && _socialPeer == peer && _historyGeneration == generation;

    private void SaveCurrentChat()
    {
        if (_account.Restricted || _socialPeer is not Guid peer || !Guid.TryParse(_account.UserId, out var owner)
            || _historyScope != ChatArrivalScope || _socialLoadedChat != ChatArrivalScope
            || !_socialPlayers.Any(p => p.Id == peer && p.Relation == "friend" && p.Available)) return;
        _chatMemory.SetOwner(owner);
        _chatMemory.Store(owner, peer, new(_socialMessages, _socialOffers, _historyRevision, _historyMore, _historyTrimmed));
    }
    private void RestoreChat(Guid owner, Guid peer)
    {
        EnsureHistoryScope(); _chatMemory.SetOwner(owner); _chatAwaitingLatest = true;
        if (!_chatMemory.TryRead(owner, peer, out var snapshot)) return;
        _socialMessages = snapshot.Messages; _socialOffers = snapshot.Offers;
        _historyRevision = snapshot.Revision; _historyMore = snapshot.More; _historyTrimmed = snapshot.Trimmed;
        _historyViewStart = Math.Max(0, _socialMessages.Count - HistoryVisibleLimit);
        _socialLoadedChat = ChatArrivalScope;
    }
    private void PruneChatMemory() => _chatMemory.Prune(_socialPlayers.Where(p => p.Relation == "friend" && p.Available).Select(p => p.Id));

    private void RenderChatLoadState()
    {
        var firstLoad = _socialLoadedChat != ChatArrivalScope && _socialMessages.Count == 0;
        FriendsChatLoadState.Text = _chatLoadError is not null
            ? T("Не удалось обновить переписку. Повторим подключение автоматически.", "Could not refresh the conversation. Reconnecting automatically.")
            : T("Загрузка сообщений…", "Loading messages…");
        FriendsChatLoadState.Visibility = _socialPeer is not null && (_chatLoadError is not null || firstLoad && _chatLoading)
            ? Visibility.Visible : Visibility.Collapsed;
    }

    private Task LoadSocialChatAsync(Guid owner)
    {
        if (_socialPeer is not Guid peer || _account.UserId != owner.ToString() || _account.Restricted) return Task.CompletedTask;
        EnsureHistoryScope();
        if (_chatLoadGeneration == _historyGeneration && _chatLoadTask is { IsCompleted: false }) return _chatLoadTask;
        _chatLoadGeneration = _historyGeneration;
        _chatViewLifetime ??= CancellationTokenSource.CreateLinkedTokenSource(_accountLifetime.Token);
        return _chatLoadTask = LoadSocialChatCoreAsync(owner, peer, _historyGeneration, _chatViewLifetime.Token);
    }
    private async Task LoadSocialChatCoreAsync(Guid owner, Guid peer, int generation, CancellationToken ct)
    {
        _chatLoading = true; _chatLoadError = null; RenderChatLoadState();
        try
        {
            if (!ActivityStore.IsSmokeTest || _historyReadOverride is not null)
            {
                var page = await ReadHistoryPageAsync(peer, ct: ct);
                if (!CurrentChatLoad(owner, peer, generation)) return;
                MergeHistoryPage(page, false);
            }
            else
            {
                var messages = await _account.GetMessagesAsync(peer, ct);
                if (!CurrentChatLoad(owner, peer, generation)) return;
                _socialMessages = messages;
            }
            _chatAwaitingLatest = false; _socialLoadedChat = ChatArrivalScope;
            SaveCurrentChat(); RenderSocialMessages();
            if (!ActivityStore.IsSmokeTest) await RefreshCachedOfferStatesAsync(owner, peer, generation, ct);
            if (!CurrentChatLoad(owner, peer, generation)) return;
            var pending = await _socialOutbox.ReadAsync(owner, ct);
            if (!CurrentChatLoad(owner, peer, generation)) return;
            _socialPending = pending;
            _socialFailures = 0; _socialRetryAfter = default;
            SaveCurrentChat(); RenderSocialRows(); RenderSocialMessages();
        }
        catch (OperationCanceledException) when (ct.IsCancellationRequested) { }
        catch (Exception error)
        {
            if (!CurrentChatLoad(owner, peer, generation)) return;
            var code = (error as AccountException)?.Code ?? "network";
            HandleEndedAccount(code);
            if (!CurrentChatLoad(owner, peer, generation)) return;
            _chatLoadError = code;
            if (code is "friend_required" or "player_unavailable")
            {
                _chatMemory.Remove(peer); _socialMessages = []; _socialOffers = []; _socialLoadedChat = null;
                RenderSocialMessages();
            }
            _socialFailures = Math.Min(5, _socialFailures + 1);
            _socialRetryAfter = DateTimeOffset.UtcNow.AddSeconds(code == "rate_limit" ? 60 : Math.Min(120, 5 * Math.Pow(2, _socialFailures)));
        }
        finally
        {
            if (CurrentChatLoad(owner, peer, generation)) { _chatLoading = false; RenderChatLoadState(); }
        }
    }
}
