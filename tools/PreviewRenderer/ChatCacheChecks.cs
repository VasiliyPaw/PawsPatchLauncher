using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class ChatCacheChecks
{
    internal static void Run(string language)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Chat cache fixtures require smoke mode.");
        var w = new MainWindow();
        const BindingFlags flags = BindingFlags.NonPublic | BindingFlags.Instance;
        object? Call(string name, params object?[] args) => typeof(MainWindow).GetMethod(name, flags)!.Invoke(w, args);
        T Field<T>(string name) => (T)typeof(MainWindow).GetField(name, flags)!.GetValue(w)!;
        void Set(string name, object? value) => typeof(MainWindow).GetField(name, flags)!.SetValue(w, value);
        T Control<T>(string name) => (T)w.FindName(name);
        Task Open(SocialPlayer p) => (Task)Call("OpenSocialChatAsync", p)!;
        int n = 0;
        void Check(bool ok, string why) { n++; if (!ok) throw new Exception("Chat cache UI: " + why); }
        async Task Scenario()
        {
            Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language); Call("ApplyLanguage");
            SocialChecks.Populate(w, "chat");
            var owner = Guid.Parse(Field<AccountService>("_account").UserId);
            var a = new SocialPlayer(Guid.NewGuid(), "Alpha", "friend", LastMessageOrdinal: 50);
            var b = new SocialPlayer(Guid.NewGuid(), "Bravo", "friend", LastMessageOrdinal: 50);
            Set("_socialPlayers", (IReadOnlyList<SocialPlayer>)new[] { a, b });
            Set("_socialPeer", null); Set("_socialMessages", (IReadOnlyList<SocialMessage>)Array.Empty<SocialMessage>());
            Set("_socialOffers", (IReadOnlyList<SocialOffer>)Array.Empty<SocialOffer>());
            Set("_socialPending", (IReadOnlyList<PendingSocialMessage>)Array.Empty<PendingSocialMessage>());
            Set("_socialLoadedChat", null); Call("ResetSocialHistory"); Call("RenderSocialIdentity");
            var requests = new List<(Guid Peer, SocialMessage? Before, TaskCompletionSource<SocialMessagePage> Reply)>();
            Set("_historyReadOverride", (Func<Guid, SocialMessage?, Task<SocialMessagePage>>)((peer, before) =>
            {
                var reply = new TaskCompletionSource<SocialMessagePage>(TaskCreationOptions.RunContinuationsAsynchronously);
                requests.Add((peer, before, reply)); return reply.Task;
            }));
            var epoch = DateTimeOffset.UtcNow.AddHours(-1);
            SocialMessage Message(Guid peer, int i) => new(peer, new Guid(i, 0, 0, new byte[8]), owner, peer + " / " + i, "text", epoch.AddSeconds(i), i);
            SocialMessagePage Page(Guid peer, int first = 1, int count = 50, long revision = 0) => new(Enumerable.Range(first, count).Select(i => Message(peer, i)).ToArray(), [], first > 1, revision, revision > 0);
            IReadOnlyList<SocialMessage> Messages() => Field<IReadOnlyList<SocialMessage>>("_socialMessages");
            int MemoryCount() => (int)Field<object>("_chatMemory").GetType().GetProperty("Count", flags)!.GetValue(Field<object>("_chatMemory"))!;

            var openingA = Open(a);
            Check(!openingA.IsCompleted && requests.Count == 1 && Messages().Count == 0, "first conversation did not start an asynchronous fetch");
            Check(Control<TextBlock>("FriendsChatLoadState").Visibility == Visibility.Visible, "first fetch has no loading state");
            Check(!Field<bool>("_socialBusy") && Control<StackPanel>("FriendsRowsPanel").IsEnabled, "message read blocks switching");
            var simultaneousPoll = (Task)Call("LoadSocialChatAsync", owner)!;
            Check(requests.Count == 1, "poll duplicates an in-flight opening request");
            requests[^1].Reply.SetResult(Page(a.Id)); await openingA; await simultaneousPoll;
            Check(Messages().Count == 50 && MemoryCount() == 1, "first page was not cached");
            Check(Control<TextBlock>("FriendsChatLoadState").Visibility == Visibility.Collapsed, "loading state remains after success");
            var openingB = Open(b);
            Check(Messages().Count == 0 && Field<Guid?>("_socialPeer") == b.Id, "previous peer's messages leak into new chat");
            requests[^1].Reply.SetResult(Page(b.Id)); await openingB;
            var reopeningA = Open(a);
            Check(!reopeningA.IsCompleted && Messages().Count == 50 && Messages().All(m => m.SenderId == a.Id), "cached conversation waits for server");
            Check(Control<TextBlock>("FriendsChatLoadState").Visibility == Visibility.Collapsed, "cached refresh displays a loading overlay");
            var sameRow = Control<StackPanel>("FriendsMessagesPanel").Children[0];
            requests[^1].Reply.SetResult(Page(a.Id)); await reopeningA;
            Check(ReferenceEquals(sameRow, Control<StackPanel>("FriendsMessagesPanel").Children[0]), "unchanged background result rebuilds message controls");

            // Open A again while its previous visit still has an outstanding response.
            var oldB = Open(b); var abandoned = requests[^1];
            var latestA = Open(a); var active = requests[^1];
            await oldB.WaitAsync(TimeSpan.FromSeconds(2));
            abandoned.Reply.SetResult(Page(b.Id, 500));
            Check(Field<Guid?>("_socialPeer") == a.Id && Messages().All(m => m.SenderId == a.Id), "late peer response changes active history");
            active.Reply.SetResult(Page(a.Id, 2)); await latestA;
            Check(Messages().Count == 51 && Messages()[^1].Ordinal == 51, "refresh did not merge newer message without duplicates");

            // Closing the selected conversation retains its history for the next visit.
            await Open(a); Check(Field<Guid?>("_socialPeer") is null && Messages().Count == 0, "second click did not close chat");
            var offlineA = Open(a);
            Check(Messages().Count == 51, "closing discarded cached history");
            requests[^1].Reply.SetException(new AccountException("network")); await offlineA;
            Check(Messages().Count == 51 && Control<TextBlock>("FriendsChatLoadState").Visibility == Visibility.Visible, "offline refresh erased history or failed silently");
            Check(Field<DateTimeOffset>("_socialRetryAfter") > DateTimeOffset.UtcNow, "failed refresh has no backoff");

            // Cached messages must not be labelled NEW using a newer server unread count.
            a = a with { Unread = 1, LastMessageOrdinal = 52 };
            Set("_socialPlayers", (IReadOnlyList<SocialPlayer>)new[] { a, b });
            var bAgain = Open(b); requests[^1].Reply.SetResult(Page(b.Id)); await bAgain;
            var unreadA = Open(a);
            Check(Call("ChatUnreadBoundary") is null, "an old cached message is incorrectly marked new");
            requests[^1].Reply.SetResult(Page(a.Id, 3)); await unreadA;
            Check((Guid?)Call("ChatUnreadBoundary") == Message(a.Id, 52).MessageId, "new marker did not attach to newly fetched message");

            // Retention revisions and disconnected page gaps must invalidate old cached messages.
            var trim = (Task)Call("LoadSocialChatAsync", owner)!;
            requests[^1].Reply.SetResult(Page(a.Id, 100, 50, 1)); await trim;
            Check(Messages().Count == 50 && Messages()[0].Ordinal == 100 && Field<bool>("_historyTrimmed"), "retention revision retained deleted rows");
            var gap = (Task)Call("LoadSocialChatAsync", owner)!;
            requests[^1].Reply.SetResult(Page(a.Id, 300, 50, 1)); await gap;
            Check(Messages().Count == 50 && Messages()[0].Ordinal == 300, "disjoint latest page is joined with old cache");

            // An older-page request must not mutate a later visit or leave its paging controls busy.
            var older = (Task)Call("NavigateHistoryAsync", true)!;
            Check(requests[^1].Before?.Ordinal == 300, "older history request has wrong anchor");
            var oldPage = requests[^1];
            var duringPaging = Open(b); var newPage = requests[^1];
            await older.WaitAsync(TimeSpan.FromSeconds(2));
            Check(!Field<bool>("_historyNavigating"), "abandoned paging leaves new conversation busy");
            oldPage.Reply.SetResult(Page(a.Id, 250, 50, 1));
            newPage.Reply.SetResult(Page(b.Id)); await duringPaging;
            Check(Messages().All(m => m.SenderId == b.Id), "old history page crossed conversations");

            // A send confirmed after switching updates that conversation's cached tail.
            var sent = Message(a.Id, 350) with { SenderId = owner, RecipientId = a.Id };
            var memory = Field<object>("_chatMemory");
            memory.GetType().GetMethod("AppendSent", flags)!.Invoke(memory, [owner, a.Id, sent]);
            var sentA = Open(a);
            Check(Messages().Any(m => m.MessageId == sent.MessageId && m.SenderId == owner), "background send confirmation disappeared on return");
            requests[^1].Reply.SetResult(new SocialMessagePage(Page(a.Id, 301, 49, 1).Messages.Append(sent).ToArray(), [], true, 1, true)); await sentA;
            Check(Messages().Count(m => m.MessageId == sent.MessageId) == 1, "send acknowledgement and server page are duplicated");

            var rapid = new List<Task>();
            for (var i = 0; i < 40; i++)
            {
                var target = i % 2 == 0 ? b : a;
                rapid.Add(Open(target));
                Check(Messages().All(m => m.SenderId == target.Id || m.RecipientId == target.Id), "rapid switching exposed a different peer");
            }
            requests[^1].Reply.SetResult(Page(a.Id, 301, 50, 1));
            await Task.WhenAll(rapid).WaitAsync(TimeSpan.FromSeconds(3));
            Check(Field<Guid?>("_socialPeer") == a.Id && !Field<bool>("_socialBusy"), "rapid switching left wrong selection or busy state");

            Set("_socialPlayers", (IReadOnlyList<SocialPlayer>)new[] { a }); Call("PruneChatMemory");
            Check(MemoryCount() == 1, "removed friend still has a cached conversation");
            var beforeLogout = (Task)Call("LoadSocialChatAsync", owner)!; var finalResponse = requests[^1];
            AccountChecks.Populate(w, "avatar"); Call("RenderSocialIdentity");
            await beforeLogout.WaitAsync(TimeSpan.FromSeconds(2));
            finalResponse.Reply.SetResult(Page(a.Id));
            Check(MemoryCount() == 0 && Messages().Count == 0 && Field<Guid?>("_socialPeer") is null, "account switch leaked cached messages or a late reply");
            Check(!w.IsVisible, "fixture opened an interactive window");
            Console.WriteLine($"CHAT CACHE UI PASS {n} {language}: immediate reopen, coalescing, offline, cancellation, unread, retention, paging, send, 40 rapid switches, owner isolation; mocked network, no visible window");
        }
        try
        {
            var task = w.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();
            var frame = new DispatcherFrame();
            var watchdog = new DispatcherTimer { Interval = TimeSpan.FromSeconds(30) };
            watchdog.Tick += (_, _) => frame.Continue = false;
            task.ContinueWith(_ => w.Dispatcher.BeginInvoke(() => frame.Continue = false), TaskScheduler.Default);
            watchdog.Start(); Dispatcher.PushFrame(frame); watchdog.Stop();
            if (!task.IsCompleted) throw new TimeoutException("Chat cache checks timed out");
            task.GetAwaiter().GetResult();
        }
        finally { w.Close(); }
    }
}
