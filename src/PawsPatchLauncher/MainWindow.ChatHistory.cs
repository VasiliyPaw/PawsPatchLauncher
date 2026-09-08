using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private string? _historyScope;
    private long _historyRevision;
    private bool _historyMore, _historyTrimmed, _historyNavigating, _historyPreserveScroll;
    private int _historyViewStart, _historyGeneration;
    private bool _historyJumpVisible;
    private int _historyScrollDirection;
    private const int HistoryVisibleLimit = 200;
    private Func<Guid, SocialMessage?, Task<SocialMessagePage>>? _historyReadOverride = null;

    private void ResetSocialHistory()
    {
        _historyScope = null; _historyRevision = 0; _historyMore = _historyTrimmed = false;
        _historyViewStart = 0; _historyGeneration++;
        _historyScrollDirection = 0;
    }
    private void EnsureHistoryScope()
    {
        if (_historyScope == ChatArrivalScope) return;
        ResetSocialHistory(); _historyScope = ChatArrivalScope;
    }
    private Task<SocialMessagePage> ReadHistoryPageAsync(Guid peer, SocialMessage? before = null)
        => _historyReadOverride is not null ? _historyReadOverride(peer, before) : _account.GetMessagePageAsync(peer, before, _accountLifetime.Token);

    private bool HistoryAtNewest => _historyViewStart+HistoryVisibleLimit>=_socialMessages.Count;
    private void AppendSentHistoryMessage(SocialMessage sent)
    {
        var follow=HistoryAtNewest&&FriendsChatScroll.ScrollableHeight-FriendsChatScroll.VerticalOffset<=20;
        _socialMessages=_socialMessages.Append(sent).OrderBy(m=>m.CreatedAt).ThenBy(m=>m.Ordinal).ToArray();
        if(follow)_historyViewStart=Math.Max(0,_socialMessages.Count-HistoryVisibleLimit);
    }
    private void ShowNewestCachedHistory()
    {
        _historyViewStart=Math.Max(0,_socialMessages.Count-HistoryVisibleLimit);
        RenderSocialMessages();FriendsChatScroll.ScrollToEnd();
    }

    private bool MergeHistoryPage(SocialMessagePage page, bool older)
    {
        // A trim invalidates every cached page, not just the latest fifty rows.
        if (page.Revision < _historyRevision || older && page.Revision != _historyRevision) return false;
        var reset = page.Revision != _historyRevision;
        var atEnd = FriendsChatScroll.ScrollableHeight - FriendsChatScroll.VerticalOffset <= 20
            && _historyViewStart + HistoryVisibleLimit >= _socialMessages.Count;
        // After a long disconnection do not join two disjoint pages and pretend there is no gap.
        reset |= !older && page.Messages.Count == 50 && _socialMessages.Count > 0
            && !page.Messages.Any(m => _socialMessages.Any(old => old.Ordinal == m.Ordinal));
        if (reset) { _socialMessages = []; _socialOffers = []; _historyViewStart = 0; }
        var firstPage = _socialMessages.Count == 0;
        _socialMessages = _socialMessages.Concat(page.Messages).GroupBy(m => (m.SenderId,m.MessageId))
            .Select(g => g.Last()).OrderBy(m => m.CreatedAt).ThenBy(m => m.Ordinal).ToArray();
        _socialOffers = _socialOffers.Concat(page.Offers).GroupBy(o => o.Id).Select(g => g.Last())
            .Where(o => _socialMessages.Any(m => m.MessageId == o.Id && m.SenderId == o.Sender)).ToArray();
        _historyRevision = page.Revision; _historyTrimmed = page.Trimmed;
        if (older || firstPage || reset) _historyMore = page.More;
        if (older) _historyViewStart = 0;
        else if (atEnd || firstPage || reset) _historyViewStart = Math.Max(0, _socialMessages.Count - HistoryVisibleLimit);
        foreach (var offer in page.Offers)
            if (_sendingOffers.TryGetValue(offer.Id,out var local) && local.State != "sending") _sendingOffers.Remove(offer.Id);
        return true;
    }
    private async Task RefreshCachedOfferStatesAsync(Guid owner,Guid peer,int generation)
    {
        var ids=_socialOffers.Where(o=>o.State is "pending" or "uploading" or "applying")
            .Select(o=>o.Id).Distinct().ToArray();
        // Most polls need no extra request. Only still-active cards outside the newest page need refresh.
        var newest=_socialMessages.TakeLast(50).Select(m=>m.MessageId).ToHashSet();
        ids=ids.Where(id=>!newest.Contains(id)).Take(200).ToArray();
        if(ids.Length==0)return;
        var offers=await _account.GetOfferStatesAsync(peer,ids,_accountLifetime.Token);
        if(_account.UserId!=owner.ToString()||_socialPeer!=peer||generation!=_historyGeneration)return;
        _socialOffers=_socialOffers.Concat(offers).GroupBy(o=>o.Id).Select(g=>g.Last()).ToArray();
    }
    private void RenderHistoryControls()
    {
        RefreshHistoryJump();
        var known = _historyScope == ChatArrivalScope && _socialPeer is not null;
        FriendsHistoryNotice.Text = T("Более старые сообщения удалены автоматически. История ограничена 10 000 сообщениями на диалог.",
            "Older messages were removed automatically. History is limited to 10,000 messages per conversation.");
        FriendsHistoryNotice.Visibility = known && _historyTrimmed && !_historyMore && _historyViewStart == 0 ? Visibility.Visible : Visibility.Collapsed;
        FriendsHistoryOlder.Content = _historyNavigating ? T("Загрузка…", "Loading…") : T("Предыдущие сообщения", "Earlier messages");
        FriendsHistoryOlder.Visibility = known && (_historyMore || _historyViewStart > 0) ? Visibility.Visible : Visibility.Collapsed;
        FriendsHistoryNewer.Content = T("Следующие сообщения", "Later messages");
        FriendsHistoryNewer.Visibility = known && _historyViewStart + HistoryVisibleLimit < _socialMessages.Count ? Visibility.Visible : Visibility.Collapsed;
        FriendsHistoryOlder.IsEnabled = FriendsHistoryNewer.IsEnabled = !_historyNavigating && !_socialBusy;
    }
    private void RefreshHistoryJump()
    {
        var show = _socialPeer is not null && _socialSection == "chats" && _activePage == "friends"
            && (_historyViewStart+HistoryVisibleLimit<_socialMessages.Count || FriendsChatScroll.ScrollableHeight-FriendsChatScroll.VerticalOffset>200);
        FriendsChatJumpBottom.ToolTip=T("К последним сообщениям","Jump to latest messages");
        System.Windows.Automation.AutomationProperties.SetName(FriendsChatJumpBottom,FriendsChatJumpBottom.ToolTip.ToString());
        FriendsChatJumpBottom.IsEnabled=!_historyNavigating&&!_socialBusy&&!ConfirmationActive;
        if(show==_historyJumpVisible)return;
        _historyJumpVisible=show;
        if(show){FriendsChatJumpBottom.Visibility=Visibility.Visible;Motion.Reveal(FriendsChatJumpBottom);}
        else Motion.Hide(FriendsChatJumpBottom);
    }
    private async void FriendsChatJumpBottom_Click(object sender,RoutedEventArgs e) => await JumpToLatestHistoryAsync();
    private Task JumpToLatestHistoryAsync()
    {
        if(_historyNavigating||_socialBusy||ConfirmationActive||_socialPeer is null)return Task.CompletedTask;
        _historyNavigating=true;RefreshHistoryJump();
        try
        {
            // Latest loaded messages are retained while paging upward. Navigation needs no network,
            // and must still work offline; the ordinary poll fetches any newer arrivals.
            var start=Math.Max(0,_socialMessages.Count-HistoryVisibleLimit);
            if(start!=_historyViewStart)
            {
                _historyViewStart=start;_historyPreserveScroll=true;
                try{RenderSocialMessages();FriendsChatScroll.UpdateLayout();}
                finally{_historyPreserveScroll=false;}
            }
            SmoothScroll.ToBottom(FriendsChatScroll);
        }
        finally{_historyNavigating=false;RefreshHistoryJump();}
        return Task.CompletedTask;
    }
    private async void FriendsHistoryOlder_Click(object sender,RoutedEventArgs e) => await NavigateHistoryAsync(true);
    private async void FriendsHistoryNewer_Click(object sender,RoutedEventArgs e) => await NavigateHistoryAsync(false);

    private async Task NavigateHistoryAsync(bool older)
    {
        if (_historyNavigating || _socialBusy || ConfirmationActive || _socialPeer is not Guid peer || _account.Restricted
            || !Guid.TryParse(_account.UserId,out var owner) || _historyScope != ChatArrivalScope) return;
        if (older ? !_historyMore && _historyViewStart == 0 : _historyViewStart + HistoryVisibleLimit >= _socialMessages.Count) return;
        var generation = _historyGeneration;
        var anchor = FriendsMessagesPanel.Children.OfType<FrameworkElement>()
            .FirstOrDefault(row => row.Tag is Guid && row.TranslatePoint(new Point(),FriendsChatScroll).Y + row.ActualHeight > 0);
        var anchorId = anchor?.Tag; var anchorY = anchor?.TranslatePoint(new Point(),FriendsChatScroll).Y ?? 0;
        _historyNavigating = true; RenderHistoryControls();
        try
        {
            await SocialOperationAsync(async current =>
            {
                if (current != owner || generation != _historyGeneration || _socialPeer != peer) return;
                if (older && _historyViewStart == 0)
                {
                    var before = _socialMessages.FirstOrDefault();
                    if (before is null) return;
                    var page = await ReadHistoryPageAsync(peer,before);
                    if (_account.UserId != owner.ToString() || generation != _historyGeneration || _socialPeer != peer) return;
                    if (!MergeHistoryPage(page,true))
                    {
                        var latest = await ReadHistoryPageAsync(peer);
                        if (_account.UserId != owner.ToString() || generation != _historyGeneration || _socialPeer != peer) return;
                        MergeHistoryPage(latest,false);
                    }
                }
                else _historyViewStart = Math.Clamp(_historyViewStart + (older ? -50 : 50),0,Math.Max(0,_socialMessages.Count-HistoryVisibleLimit));
                _historyPreserveScroll = true;
                try
                {
                    _socialRenderedContext = null; RenderSocialMessages(); FriendsChatScroll.UpdateLayout();
                    var restored = FriendsMessagesPanel.Children.OfType<FrameworkElement>().FirstOrDefault(row => Equals(row.Tag,anchorId));
                    if (restored is not null) FriendsChatScroll.ScrollToVerticalOffset(FriendsChatScroll.VerticalOffset + restored.TranslatePoint(new Point(),FriendsChatScroll).Y-anchorY);
                }
                finally { _historyPreserveScroll = false; }
            },background:true);
            await Dispatcher.InvokeAsync(() => { },DispatcherPriority.Background);
        }
        finally { _historyNavigating = false; RenderHistoryControls(); }
    }
}
