using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Interop;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class ChatInteractionChecks
{
    internal static void Run(string language)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Isolated fixture required");
        new SettingsStore().Save(new UserSettings { ModNoticeSeen = true, Language = language });
        var w = new MainWindow(new LauncherConfiguration { FeedUrls = [], BetaFeedUrls = [] }, null);
        const BindingFlags flags = BindingFlags.NonPublic | BindingFlags.Instance;
        object? Call(string name, params object?[] args) => typeof(MainWindow).GetMethod(name, flags)!.Invoke(w, args);
        T Field<T>(string name) => (T)typeof(MainWindow).GetField(name, flags)!.GetValue(w)!;
        T C<T>(string name) => (T)w.FindName(name);
        var checks = 0;
        void Check(bool condition, string reason) { checks++; if (!condition) throw new Exception("Chat interaction: " + reason); }
        void Layout()
        {
            var root = (FrameworkElement)w.Content;
            root.Measure(new Size(1440, 900)); root.Arrange(new Rect(0, 0, 1440, 900)); root.UpdateLayout();
        }
        void Open() { Call("FriendsGlyph_Click", C<Button>("FriendsGlyphButton"), new RoutedEventArgs()); Layout(); }
        try
        {
            SocialChecks.Populate(w, "chat"); Layout();
            var composer = C<ChatComposer>("FriendsMessageInput");
            composer.Text = "Draft "; composer.CaretPosition = composer.Document.ContentEnd;
            Open();
            var overlay = Field<Grid>("_chatPopup");
            var card = Field<Border>("_chatPopupCard");
            Check(overlay.Parent == C<Grid>("WindowLayers"), "picker must cover the launcher in the same visual tree");
            Check(((StackPanel)card.Child).Children.Count == 2, "old shortcut footer remains");
            var buttons = ((WrapPanel)((StackPanel)card.Child).Children[1]).Children.OfType<Button>().ToArray();
            Check(buttons.Length == 26 && buttons.All(b => !b.ToolTip.ToString()!.Contains("Ctrl")), "picker shortcuts remain");
            foreach (var glyph in ChatGlyphs.All.Take(4)) Call("InsertPickerGlyph", glyph, ModifierKeys.Shift);
            Check(ReferenceEquals(Field<Grid>("_chatPopup"), overlay), "Shift closes the picker");
            Check(composer.Text == "Draft " + string.Concat(ChatGlyphs.All.Take(4).Select(g => g.Token)), "multiple selections lost draft/caret or duplicated glyphs");
            Call("InsertPickerGlyph", ChatGlyphs.All[4], ModifierKeys.None);
            Check(Field<Grid?>("_chatPopup") is null, "ordinary selection does not close picker");
            var text = composer.Text;
            string? copied = null;
            composer.CopyTextRequested = value => { copied = value; return Task.FromResult(true); };
            ApplicationCommands.SelectAll.Execute(null, composer);
            Check(!composer.Selection.IsEmpty, "select-all command unavailable");
            Check(ApplicationCommands.Copy.CanExecute(null, composer), "copy command disabled");
            ApplicationCommands.Copy.Execute(null, composer);
            Check(copied == text, "copy command lost text or glyph tokens");
            ApplicationCommands.Cut.Execute(null, composer);
            Check(composer.Text == "", "cut command unavailable");
            ApplicationCommands.Undo.Execute(null, composer);
            Check(composer.Text == text, "undo command unavailable");
            ApplicationCommands.Redo.Execute(null, composer);
            Check(composer.Text == "", "redo command unavailable");
            var clipboard = new DataObject(DataFormats.UnicodeText, "Paste :ch_sword:");
            composer.RaiseEvent(new DataObjectPastingEventArgs(clipboard, false, DataFormats.UnicodeText));
            Check(composer.Text == "Paste :ch_sword:", "plain-text paste path unavailable");
            // Routed events only: no real keyboard/mouse input and no user clipboard.
            using var source = new HwndSource(new HwndSourceParameters("Hidden key-event fixture") { Width = 1, Height = 1, WindowStyle = unchecked((int)0x80000000) });
            foreach (var key in Enumerable.Range((int)Key.A, (int)Key.Z - (int)Key.A + 1).Select(k => (Key)k))
            {
                var e = new KeyEventArgs(Keyboard.PrimaryDevice, source, 0, key) { RoutedEvent = Keyboard.PreviewKeyDownEvent };
                composer.RaiseEvent(e);
                Check(!e.Handled && composer.Text == "Paste :ch_sword:", "letter intercepted as a glyph: " + key);
            }
            foreach (var button in new[] { MouseButton.Left, MouseButton.Right, MouseButton.Middle })
            {
                Open(); overlay = Field<Grid>("_chatPopup");
                foreach (var name in new[] { "HomeNav", "DiscordHeaderButton", "CloseWindowButton", "FriendsSendButton", "FriendsMessageInput" })
                {
                    var target = w.FindName(name) as FrameworkElement;
                    if (target is null) continue;
                    var point = target.TranslatePoint(new Point(target.ActualWidth / 2, target.ActualHeight / 2), C<Grid>("WindowLayers"));
                    var hit = System.Windows.Media.VisualTreeHelper.HitTest(C<Grid>("WindowLayers"), point)?.VisualHit;
                    Check(ReferenceEquals(hit, overlay), "outside hit target for " + name + ": " + hit?.GetType().Name + "; overlay=" + overlay.RenderSize);
                }
                var down = new MouseButtonEventArgs(Mouse.PrimaryDevice, 0, button) { RoutedEvent = Mouse.PreviewMouseDownEvent };
                overlay.RaiseEvent(down);
                Check(down.Handled && ReferenceEquals(Field<Grid>("_chatPopup"), overlay), "outside press leaked or removed the layer before release");
                var up = new MouseButtonEventArgs(Mouse.PrimaryDevice, 1, button) { RoutedEvent = Mouse.PreviewMouseUpEvent };
                overlay.RaiseEvent(up);
                Check(up.Handled && Field<Grid?>("_chatPopup") is null, "outside release leaked or picker stayed open");
                Check(composer.Text == "Paste :ch_sword:", "outside click inserted a glyph");
            }
            Check(C<Button>("HomeNav").IsEnabled && C<Button>("CloseWindowButton").IsEnabled, "underlying buttons were disabled");
            Check(w.FindName("ConfirmationLocalizationToggle") is null, "localization copy toggle remains");
            Console.WriteLine($"CHAT INTERACTION PASS {checks} ({language}): Shift, dismissal press/release, standard edit commands, no glyph key interception");
        }
        finally { Call("RemoveChatPopup"); w.Close(); }
    }
}
