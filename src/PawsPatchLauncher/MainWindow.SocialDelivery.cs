using System.Windows;
using System.Windows.Input;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private bool _socialDeliveryBusy, _socialExpiryBusy, _socialEnqueuing;
    private DateTimeOffset _socialNextPoll, _socialNextDelivery;

    private async Task SocialTickAsync()
    {
        if (_account.State == AccountState.Guest || !Guid.TryParse(_account.UserId, out var owner)) return;
        _ = PulseOffersAsync();
        if(_socialListReceived!=default && DateTimeOffset.UtcNow-_socialListReceived>TimeSpan.FromSeconds(40) && _socialPlayers.Any(p=>p.Presence!="offline"))
        {
            _socialPlayers=_socialPlayers.Select(p=>p with {Presence="offline",PlayingSince=null}).ToArray();
            RenderSocialRows();
        }
        if (!_socialExpiryBusy)
        {
            _socialExpiryBusy = true;
            try
            {
                var entries = await _socialOutbox.ReadAsync(owner, _accountLifetime.Token);
                foreach (var item in entries.Where(m => m.TimedOut(DateTimeOffset.UtcNow)))
                    await _socialOutbox.FailAttemptAsync(item, "delivery_timeout", _accountLifetime.Token);
                await ReloadSocialPendingAsync(owner);
            }
            catch (OperationCanceledException) { }
            catch { /* A local read failure must not start an unobserved timer exception. */ }
            finally { _socialExpiryBusy = false; }
        }
        if (DateTimeOffset.UtcNow >= _socialNextPoll && DateTimeOffset.UtcNow >= _socialRetryAfter)
        {
            _socialNextPoll = DateTimeOffset.UtcNow.AddSeconds(10);
            _ = RefreshSocialAsync();
        }
        if (DateTimeOffset.UtcNow >= _socialNextDelivery) await PumpSocialDeliveryAsync();
    }

    private async Task ReloadSocialPendingAsync(Guid owner)
    {
        var entries = await _socialOutbox.ReadAsync(owner, _accountLifetime.Token);
        if (_account.UserId != owner.ToString()) return;
        _socialPending = entries;
        RenderSocialRows();
        RenderSocialMessages();
    }

    private async Task PumpSocialDeliveryAsync()
    {
        if (_socialDeliveryBusy || _accountBusy || _account.State == AccountState.Guest || !Guid.TryParse(_account.UserId, out var owner)) return;
        _socialDeliveryBusy = true;
        try { await FlushSocialOutboxAsync(owner); }
        catch (OperationCanceledException) { }
        catch (AccountException error) { HandleEndedAccount(error.Code); }
        catch { /* The inline deadline/retry state remains durable even if transport fails. */ }
        finally { _socialNextDelivery = DateTimeOffset.UtcNow.AddSeconds(3); _socialDeliveryBusy = false; }
    }

    private async Task FlushSocialOutboxAsync(Guid owner)
    {
        foreach (var pending in (await _socialOutbox.ReadAsync(owner, _accountLifetime.Token)).Where(m => m.Error.Length == 0).Take(5))
        {
            if (_account.UserId != owner.ToString()) return;
            var remaining = pending.Deadline - DateTimeOffset.UtcNow;
            if (remaining <= TimeSpan.Zero)
            {
                await _socialOutbox.FailAttemptAsync(pending, "delivery_timeout", _accountLifetime.Token);
                continue;
            }
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(_accountLifetime.Token);
            timeout.CancelAfter(remaining);
            try
            {
                var sent = await _account.SendMessageAsync(pending.Target, pending.Id, pending.Body, pending.Kind, timeout.Token);
                ObserveChatMessage(owner,sent);
                await _socialOutbox.RemoveAsync(owner, pending.Id, _accountLifetime.Token);
                if (_account.UserId != owner.ToString()) return;
                if (_socialPeer == pending.Target && !_socialMessages.Any(m => m.SenderId == owner && m.MessageId == sent.MessageId))
                    AppendSentHistoryMessage(sent);
            }
            catch (OperationCanceledException) when (!_accountLifetime.IsCancellationRequested)
            { await _socialOutbox.FailAttemptAsync(pending, "delivery_timeout", _accountLifetime.Token); }
            catch (AccountException error) when (error.Code is "network" or "rate_limit" or "outcome_unknown")
            {
                if (pending.TimedOut(DateTimeOffset.UtcNow)) await _socialOutbox.FailAttemptAsync(pending, "delivery_timeout", _accountLifetime.Token);
                break;
            }
            catch (AccountException error) when (error.Code is not ("session_expired" or "session_replaced" or "unauthorized"))
            { await _socialOutbox.FailAttemptAsync(pending, error.Code, _accountLifetime.Token); }
        }
        await ReloadSocialPendingAsync(owner);
    }

    private async void FriendsSend_Click(object sender, RoutedEventArgs e) => await SendSocialAsync();
    internal static bool SendOnKey(Key key, ModifierKeys modifiers) => key == Key.Enter && !modifiers.HasFlag(ModifierKeys.Shift);
    private async void FriendsMessage_KeyDown(object sender, KeyEventArgs e)
    {
        if (!SendOnKey(e.Key, Keyboard.Modifiers)) return;
        e.Handled = true;
        await SendSocialAsync();
    }
    private async Task SendSocialAsync()
    {
        if (_socialEnqueuing || _accountBusy || _account.State == AccountState.Guest || _socialPeer is not Guid peer || !Guid.TryParse(_account.UserId, out var owner)) return;
        var text = FriendsMessageInput.Text.Trim();
        if (text.Length == 0) return;
        _socialEnqueuing = true;
        try
        {
            AccountService.ValidateMessage(text, "text");
            await _socialOutbox.AddAsync(new PendingSocialMessage(owner, peer, Guid.NewGuid(), text, "text"), _accountLifetime.Token);
            if (_account.UserId != owner.ToString()) return;
            if (_socialPeer == peer && FriendsMessageInput.Text.Trim() == text) FriendsMessageInput.Clear();
            await ReloadSocialPendingAsync(owner);
            ShowNewestCachedHistory();
        }
        catch (OperationCanceledException) { }
        catch (AccountException error) { ShowToast(() => SocialError(error.Code), true); }
        catch { ShowToast(() => T("Не удалось сохранить сообщение для отправки.", "Could not prepare the message for sending."), true); }
        finally { _socialEnqueuing = false; }
        _ = PumpSocialDeliveryAsync();
    }
    private async Task ChangePendingSocialAsync(PendingSocialMessage pending, bool retry)
    {
        if (_account.UserId != pending.Owner.ToString() || _account.State == AccountState.Guest) return;
        try
        {
            if (retry) await _socialOutbox.RetryAsync(pending.Owner, pending.Id, _accountLifetime.Token);
            else await _socialOutbox.RemoveAsync(pending.Owner, pending.Id, _accountLifetime.Token);
            await ReloadSocialPendingAsync(pending.Owner);
            if (retry) _ = PumpSocialDeliveryAsync();
        }
        catch (OperationCanceledException) { }
        catch { ShowToast(() => T("Не удалось изменить сообщение.", "Could not update the message."), true); }
    }
}
