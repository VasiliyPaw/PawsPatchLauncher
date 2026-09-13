using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Input;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class ConnectionUiChecks
{
    private const BindingFlags Flags = BindingFlags.NonPublic | BindingFlags.Instance;
    private static object? Call(MainWindow w, string name, params object?[] args) => typeof(MainWindow).GetMethod(name, Flags)!.Invoke(w, args);
    private static T Field<T>(MainWindow w, string name) => (T)typeof(MainWindow).GetField(name, Flags)!.GetValue(w)!;
    private static T Control<T>(MainWindow w, string name) => (T)w.FindName(name);
    private static void Connection(MainWindow w, bool connected)
    {
        var account = Field<AccountService>(w, "_account");
        var status = typeof(AccountService).GetProperty("Connection", Flags)!.GetValue(account)!;
        var request = status.GetType().GetMethod("Begin", Flags)!.Invoke(status, null);
        status.GetType().GetMethod("Complete", Flags)!.Invoke(status, [request, connected]);
        Call(w, "RenderConnectionUi");
    }
    private static void Layout(MainWindow w, Size size)
    {
        var root = (FrameworkElement)w.Content;
        root.Measure(size); root.Arrange(new Rect(size)); root.UpdateLayout();
    }
    private static MainWindow Create(string language)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Isolated preview required");
        var w = new MainWindow(new LauncherConfiguration { FeedUrls = [], BetaFeedUrls = [] }, null);
        Field<PawsPatchLauncher.Localization>(w, "_text").SetLanguage(language); Call(w, "ApplyLanguage");
        SocialChecks.Populate(w, "chat"); Connection(w, true);
        Control<ChatComposer>(w, "FriendsMessageInput").Text = "Привет!";
        return w;
    }
    internal static void Preview(string language)
    {
        var w = Create(language);
        w.Title = "Проверка интерфейса — изолированный тест подключения";
        var controls = new StackPanel { Orientation=Orientation.Horizontal, HorizontalAlignment=HorizontalAlignment.Left, VerticalAlignment=VerticalAlignment.Center, Margin=new(280,0,0,0) };
        System.Windows.Shell.WindowChrome.SetIsHitTestVisibleInChrome(controls, true);
        foreach (var connected in new[] { false, true })
        {
            var button = new Button { Content=connected?"Тест: сеть есть":"Тест: нет сети", Margin=new(3,0,3,0), Padding=new(5), Style=(Style)w.FindResource("GhostButton") };
            button.Click += (_, _) => Connection(w, connected); controls.Children.Add(button);
        }
        Control<Grid>(w, "TitleBar").Children.Add(controls);
        w.PreviewKeyDown += (_, e) =>
        {
            if (e.Key == Key.F6) { Connection(w, false); e.Handled = true; }
            if (e.Key == Key.F7) { Connection(w, true); e.Handled = true; }
            if (e.Key == Key.F8) { Control<ChatComposer>(w, "FriendsMessageInput").Text = "Привет! Проверка строки."; e.Handled = true; }
            if (e.Key == Key.F9) { Control<ChatComposer>(w, "FriendsMessageInput").Text = "Первая строка\nВторая строка"; e.Handled = true; }
        };
        w.Closed += (_, _) => Application.Current.Shutdown();
        w.Show();
    }
    internal static void Run(string language)
    {
        var w = Create(language); int checks = 0;
        void Check(bool ok, string why) { checks++; if (!ok) throw new Exception("Connection/composer UI: " + why); }
        try
        {
            foreach (var size in new[] { new Size(1050, 680), new Size(1600, 1000) })
            {
                Layout(w, size);
                var body = Control<Grid>(w, "MainBody"); var origin = body.TranslatePoint(new Point(), Control<Grid>(w, "WindowLayers")); var dimensions = body.RenderSize;
                var messages = Field<IReadOnlyList<SocialMessage>>(w, "_socialMessages");
                Call(w, "FriendsComposerMore_Click", Control<Button>(w, "FriendsComposerMoreButton"), new RoutedEventArgs()); Layout(w, size);
                Check(Field<Grid?>(w, "_chatPopup") is not null, "composer menu did not use outside-click overlay");
                Check(((StackPanel)Field<Border>(w, "_chatPopupCard").Child).Children.Count == 2, "composer actions missing");
                Connection(w, false); Layout(w, size);
                Check(Control<Border>(w, "ConnectionNotice").Visibility == Visibility.Visible, "offline banner is hidden");
                Check(body.TranslatePoint(new Point(), Control<Grid>(w, "WindowLayers")) == origin && body.RenderSize == dimensions, "offline banner shifts the interface");
                Check(!Control<StackPanel>(w, "FriendsPanel").IsEnabled && !Control<Grid>(w, "FriendsConversationScroll").IsEnabled
                    && !Control<StackPanel>(w, "AccountPanel").IsEnabled && !Control<Border>(w, "SocialDetailsCard").IsEnabled, "offline account/friends actions remain interactive");
                Check(Control<Button>(w, "SettingsNav").IsEnabled && Control<Button>(w, "FriendsNav").IsEnabled, "offline state blocks unrelated navigation");
                Check(Field<Grid?>(w, "_chatPopup") is null, "offline state leaves a popup interactive");
                Check(ReferenceEquals(messages, Field<IReadOnlyList<SocialMessage>>(w, "_socialMessages")), "disconnect erased cached messages");
                var banner = Control<Border>(w, "ConnectionNotice");
                var actions = Control<StackPanel>(w, "TitleActions");
                Console.WriteLine($"BANNER {size.Width}: x={banner.TranslatePoint(new Point(), Control<Grid>(w, "WindowLayers")).X:F2} width={banner.ActualWidth:F2} actions={actions.TranslatePoint(new Point(), Control<Grid>(w, "WindowLayers")).X:F2}");
                Check(banner.TranslatePoint(new Point(), Control<Grid>(w, "WindowLayers")).X + banner.ActualWidth <= actions.TranslatePoint(new Point(), Control<Grid>(w, "WindowLayers")).X, "banner covers title buttons");
                Connection(w, true); Layout(w, size);
                Check(banner.Visibility == Visibility.Collapsed && Control<StackPanel>(w, "FriendsPanel").IsEnabled && Control<StackPanel>(w, "AccountPanel").IsEnabled, "reconnect did not unlock views");
                var composer = Control<ChatComposer>(w, "FriendsMessageInput");
                foreach (var text in new[] { "Ag", "Привет!", "Первая строка\nВторая строка", "line\nline\nline" })
                {
                    composer.Text = text; Layout(w, size);
                    var top = composer.Document.ContentStart.GetInsertionPosition(LogicalDirection.Forward).GetCharacterRect(LogicalDirection.Forward).Top;
                    var bottom = composer.Document.ContentEnd.GetInsertionPosition(LogicalDirection.Backward).GetCharacterRect(LogicalDirection.Backward).Bottom;
                    Console.WriteLine($"COMPOSER {size.Width} lines={text.Split('\n').Length}: height={composer.ActualHeight:F2} top={top:F2} bottom={bottom:F2} center-delta={(top + bottom - composer.ActualHeight)/2:F2}");
                    Check(Math.Abs(top + bottom - composer.ActualHeight) <= 2.5, "text block is not vertically centered");
                }
                composer.Text = string.Join("\n", Enumerable.Repeat("line", 30)); Layout(w, size);
                Check(composer.ActualHeight <= 132 && composer.ExtentHeight > composer.ViewportHeight, "long draft lost its height cap or scrolling");
            }
            Console.WriteLine($"CONNECTION / COMPOSER UI PASS {checks} {language}: offline/reconnect, no layout shift, action blocking, popup cleanup, centered one/multiple lines, bounded long draft");
        }
        finally { w.Close(); }
    }
}
