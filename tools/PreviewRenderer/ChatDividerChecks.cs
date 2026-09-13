using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class ChatDividerChecks
{
    internal static void Run(string language, string output)
    {
        var w = new MainWindow(); var checks = 0;
        const BindingFlags flags = BindingFlags.Instance | BindingFlags.NonPublic;
        object? Call(string name, params object?[] args) => typeof(MainWindow).GetMethod(name, flags)!.Invoke(w, args);
        T Field<T>(string name) => (T)typeof(MainWindow).GetField(name, flags)!.GetValue(w)!;
        void Set(string name, object? value) => typeof(MainWindow).GetField(name, flags)!.SetValue(w, value);
        void Check(bool ok, string why) { checks++; if (!ok) throw new Exception("Chat divider: " + why); }
        var panel = (StackPanel)w.FindName("FriendsMessagesPanel");
        FrameworkElement[] Rows() => panel.Children.OfType<FrameworkElement>().ToArray();
        int NewCount() => Rows().Count(r => Equals(r.Tag, "chat-new-divider"));
        try
        {
            Field<PawsPatchLauncher.Localization>("_text").SetLanguage(language); Call("ApplyLanguage");
            SocialChecks.Populate(w, "chat");
            Call("ResetSocialHistory");
            var owner = Guid.Parse(Field<AccountService>("_account").UserId);
            var peer = Field<IReadOnlyList<SocialPlayer>>("_socialPlayers").First(p => p.Relation == "friend") with { Unread = 1, LastMessageOrdinal = 3 };
            var day = new DateTimeOffset(DateTime.Today.AddHours(15));
            SocialMessage Message(Guid sender, long ordinal, string body, DateTimeOffset date) => new(sender, Guid.NewGuid(), sender == owner ? peer.Id : owner, body, "text", date, ordinal);
            var messages = new[] {
                Message(peer.Id, 1, "Сегодня играем?", day.AddDays(-1)),
                Message(owner, 2, "Да, проверяю настройки.", day.AddDays(-1).AddMinutes(1)),
                Message(peer.Id, 3, "Добрый день! Я готов.", day)
            };
            Set("_socialPending", (IReadOnlyList<PendingSocialMessage>)Array.Empty<PendingSocialMessage>());
            Set("_socialPlayers", (IReadOnlyList<SocialPlayer>)new[] { peer });
            Set("_socialMessages", (IReadOnlyList<SocialMessage>)messages); Call("RenderSocialMessages");
            Check(Rows().Count(r => Equals(r.Tag, "chat-date-divider")) == 2, "one centered separator per local date");
            Check(NewCount() == 1, "missing NEW boundary");
            var index = Array.FindIndex(Rows(), r => Equals(r.Tag, "chat-new-divider"));
            Check(Equals(Rows()[index + 1].Tag, messages[2].MessageId), "NEW not immediately before incoming unread message");
            Set("_socialPlayers", (IReadOnlyList<SocialPlayer>)new[] { peer with { Unread = 0 } }); Call("RenderSocialMessages");
            Check(NewCount() == 1, "server acknowledgement removed divider during visit");
            var content = (FrameworkElement)w.Content;
            content.Measure(new Size(1250, 800)); content.Arrange(new Rect(0, 0, 1250, 800)); content.UpdateLayout();
            var bmp = new RenderTargetBitmap(1250, 800, 96, 96, PixelFormats.Pbgra32); bmp.Render(content);
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!);
            using (var stream = File.Create(output)) { var encoder = new PngBitmapEncoder(); encoder.Frames.Add(BitmapFrame.Create(bmp)); encoder.Save(stream); }
            Field<ChatUnreadDivider>("_chatUnreadDivider").Dismiss(); Call("RenderSocialMessages");
            Check(NewCount() == 0, "reply dismissal did not rerender");
            Set("_socialPlayers", (IReadOnlyList<SocialPlayer>)new[] { peer });
            Call("SetActivePage", "components"); Call("SetActivePage", "friends"); Call("RenderSocialMessages");
            Check(NewCount() == 0, "old divider reappeared after reentry");
            var live = messages.Append(Message(peer.Id, 4, "Новое сообщение в открытом чате", day.AddMinutes(1))).ToArray();
            Set("_socialMessages", (IReadOnlyList<SocialMessage>)live); Call("RenderSocialMessages");
            Check(NewCount() == 0, "live incoming message created marker in open chat");
            Call("SetActivePage", "components");
            var future = live.Append(Message(peer.Id, 5, "Сообщение, пока чат закрыт", day.AddMinutes(2))).ToArray();
            Set("_socialMessages", (IReadOnlyList<SocialMessage>)future);
            Set("_socialPlayers", (IReadOnlyList<SocialPlayer>)new[] { peer with { Unread = 1, LastMessageOrdinal = 5 } });
            Call("SetActivePage", "friends"); Call("RenderSocialMessages");
            Check(NewCount() == 1, "future closed-chat incoming message lost divider");
            Console.WriteLine($"CHAT DIVIDERS PASS {checks} {language}");
        }
        finally { w.Close(); }
    }
}
