using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class SocialRefreshChecks
{
    internal static void Run(string language)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Refresh fixtures require smoke mode.");
        var window = new MainWindow();
        const BindingFlags flags = BindingFlags.NonPublic | BindingFlags.Instance;
        object? Invoke(string method, params object?[] args) => typeof(MainWindow).GetMethod(method, flags)!.Invoke(window, args);
        void Set(string name, object value) => typeof(MainWindow).GetField(name, flags)!.SetValue(window, value);
        T Field<T>(string name) => (T)typeof(MainWindow).GetField(name, flags)!.GetValue(window)!;
        T Control<T>(string name) => (T)window.FindName(name);
        Task Social(Func<Guid, Task> action, bool background) => (Task)Invoke("SocialOperationAsync", action, background)!;
        Task Account(Func<Task> action, bool background) => (Task)Invoke("AccountOperationAsync", action, background)!;
        int checks = 0;
        void Check(bool condition, string message) { checks++; if (!condition) throw new Exception("Refresh UI: " + message); }

        async Task Scenario()
        {
            Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language); Invoke("ApplyLanguage");
            SocialChecks.Populate(window, "chat");
            var add = Control<Button>("FriendsAddButton");
            var transitions = 0; add.IsEnabledChanged += (_, _) => transitions++;
            var row = Control<StackPanel>("FriendsRowsPanel").Children[0];
            var bubble = Control<StackPanel>("FriendsMessagesPanel").Children[0];
            var pendingRow = Control<StackPanel>("FriendsMessagesPanel").Children[2];
            var brush = Control<Button>("FriendsRequestsTab").Background;
            for (var i = 0; i < 20; i++) await Social(_ => Task.CompletedTask, true);
            Check(transitions == 0 && add.IsEnabled, "background polling toggles enabled state");
            Check(ReferenceEquals(row, Control<StackPanel>("FriendsRowsPanel").Children[0]), "poll rebuilds row");
            Invoke("RenderSocialMessages");
            Check(ReferenceEquals(bubble, Control<StackPanel>("FriendsMessagesPanel").Children[0]) && ReferenceEquals(pendingRow, Control<StackPanel>("FriendsMessagesPanel").Children[2]), "unchanged conversation/pending controls rebuilt");
            Check(ReferenceEquals(brush, Control<Button>("FriendsRequestsTab").Background), "poll restarts tab brush animation");
            var delayed = new TaskCompletionSource();
            var poll = Social(_ => delayed.Task, true);
            Check(!poll.IsCompleted && !Field<bool>("_socialBusy") && add.IsEnabled, "read poll dims buttons");
            var mutationCount = 0;
            var mutation = Social(_ => { mutationCount++; return Task.CompletedTask; }, false);
            Check(!mutation.IsCompleted && mutationCount == 0, "click raced an existing read");
            await Social(_ => { mutationCount++; return Task.CompletedTask; }, false);
            delayed.SetResult(); await poll; await mutation;
            Check(mutationCount == 1 && add.IsEnabled, "click lost or double-executed");
            Check(transitions == 2, "only the actual click may disable and restore controls");

            var avatar = Control<Button>("AccountAvatarEditButton");
            var accountTransitions = 0; avatar.IsEnabledChanged += (_, _) => accountTransitions++;
            var accountDelay = new TaskCompletionSource();
            var restore = Account(() => accountDelay.Task, true);
            Check(avatar.IsEnabled && !Field<bool>("_accountBusy") && Field<bool>("_accountRefreshing"), "account refresh dims profile");
            Check(accountTransitions == 0, "account background enabled-state transition");
            var accountMutations = 0;
            var avatarAction = Account(() => { accountMutations++; Set("_accountMessage", "avatar_saved"); return Task.CompletedTask; }, false);
            await Account(() => { accountMutations++; return Task.CompletedTask; }, false);
            accountDelay.SetResult(); await restore; await avatarAction;
            Check(accountMutations == 1 && avatar.IsEnabled && accountTransitions == 2, "account click dropped/doubled");
            var toast = Field<OperationFeedback>("_toast");
            Check(toast.Message == (language == "ru" ? "Аватарка успешно изменена." : "Avatar updated successfully."), "short avatar toast missing");
            Check(!toast.Failed && toast.HasExpiry, "success is not transient");
            Check(Control<Border>("AccountMessageCard").Visibility == Visibility.Collapsed, "success adds persistent card");
            Check(Control<Border>("ToastPanel").Background.ToString() == "#FF142F28", "success color");

            Invoke("ShowWorking", (Func<string>)(() => "ongoing fixture operation"));
            await Account(() => Task.FromException(new AccountException("invalid_credentials")), false);
            Check(toast.Failed && toast.HasExpiry && Control<Border>("ToastPanel").Background.ToString() == "#FF332024", "error toast missing/color");
            Check(Control<Border>("AccountMessageCard").Visibility == Visibility.Visible, "actionable account error disappeared");
            Check(Field<OperationFeedback>("_feedback").Working, "account notification changed unrelated operation");
            var priorMessage = toast.Message;
            await Social(_ => Task.FromException(new AccountException("network")), true);
            Check(toast.Message == priorMessage, "background poll spams notifications");
            await Social(_ => Task.FromException(new AccountException("player_unavailable")), false);
            Check(toast.Failed && toast.Message != priorMessage, "interactive social error did not notify");
            Invoke("ShowResult", (Func<string>)(() => "operation result"), false, null);
            Check(toast.Message == "operation result", "general operation result did not notify");

            // An account change while a read is in flight must discard a queued action for the old owner.
            var identityDelay = new TaskCompletionSource();
            var oldPoll = Social(_ => identityDelay.Task, true);
            var oldActions = 0;
            var queued = Social(_ => { oldActions++; return Task.CompletedTask; }, false);
            var oldService = Field<AccountService>("_account");
            Set("_account", new AccountService(new AccountSessionStore(System.IO.Path.Combine(ActivityStore.Root, "new-identity-fixture-" + Guid.NewGuid()))));
            oldService.Dispose(); Invoke("RenderAccount");
            identityDelay.SetResult(); await oldPoll; await queued;
            Check(oldActions == 0, "queued action ran as another account");
            Check(Control<Border>("FriendsNavBadge").Visibility == Visibility.Collapsed, "account switch leaked badge");
            Console.WriteLine($"REFRESH + TOAST UI PASS {checks} {language}: background no-flicker, serialized clicks, no duplicates, owner isolation, timed feedback; no real network");
        }
        try
        {
            var task = window.Dispatcher.InvokeAsync(Scenario).Task.Unwrap();
            var frame = new DispatcherFrame();
            var watchdog = new DispatcherTimer { Interval = TimeSpan.FromSeconds(20) };
            watchdog.Tick += (_, _) => frame.Continue = false;
            task.ContinueWith(_ => window.Dispatcher.BeginInvoke(() => frame.Continue = false), TaskScheduler.Default);
            watchdog.Start(); Dispatcher.PushFrame(frame); watchdog.Stop();
            if (!task.IsCompleted) throw new TimeoutException("Refresh checks timed out.");
            task.GetAwaiter().GetResult();
        }
        finally { window.Close(); }
    }
}
