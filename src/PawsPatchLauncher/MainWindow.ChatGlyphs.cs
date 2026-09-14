using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Shell;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private Grid? _chatPopup;
    private Border? _chatPopupCard;
    private bool _chatPopupClosing, _chatPopupHidden;
    private MouseButton? _chatPopupDismissButton;

    private void FriendsGlyph_Click(object sender, RoutedEventArgs e)
    {
        if (_chatPopup is not null) { _ = CloseChatPopupAsync(); return; }
        if (AccountConnectionBlocked || !FriendsMessageInput.IsEnabled) return;
        var rows = new WrapPanel { Width = 294 };
        var body = new StackPanel();
        body.Children.Add(new TextBlock { Text = T("Значки Kohan II", "Kohan II glyphs"), Foreground = SocialBrush("#F4F1E7"), FontSize = 15, Margin = new(4,0,4,10) });
        body.Children.Add(rows);
        var card = new Border { Background = SocialBrush("#111F33"), BorderBrush = SocialBrush("#526882"), BorderThickness = new(1), CornerRadius = new(10), Padding = new(12), Child = body,
            HorizontalAlignment = HorizontalAlignment.Left, VerticalAlignment = VerticalAlignment.Top };
        foreach (var glyph in ChatGlyphs.All)
        {
            var label = T(glyph.Ru,glyph.En);
            var button = new Button { Name = "InsertGameGlyph", Style = (Style)FindResource("GhostButton"), Width = 42, Height = 38, Padding = new(4),
                Content = ChatGlyphs.CreateImage(glyph, _text.Language), ToolTip = label };
            System.Windows.Automation.AutomationProperties.SetName(button, label);
            button.Click += (_, _) => InsertPickerGlyph(glyph, Keyboard.Modifiers);
            rows.Children.Add(button);
        }
        ShowChatPopup(card, FriendsGlyphButton);
    }

    private void ShowChatPopup(Border card, FrameworkElement anchorControl)
    {
        RemoveChatPopup(); CloseSocialMenu();
        // Both composer menus use the same full-window dismissal layer, including the final MouseUp.
        var overlay = new Grid { Background = Brushes.Transparent };
        Grid.SetRowSpan(overlay, WindowLayers.RowDefinitions.Count);
        Panel.SetZIndex(overlay, 250);
        WindowChrome.SetIsHitTestVisibleInChrome(overlay, true);
        overlay.Children.Add(card);
        _chatPopup = overlay; _chatPopupCard = card;
        _chatPopupClosing = _chatPopupHidden = false; _chatPopupDismissButton = null;
        overlay.PreviewMouseDown += ChatPopup_MouseDown;
        overlay.PreviewMouseUp += ChatPopup_MouseUp;
        overlay.PreviewMouseWheel += (_, e) => { e.Handled = true; if (!InsideCard(e.OriginalSource as DependencyObject, card)) _ = CloseChatPopupAsync(); };
        Closed += ChatPopup_WindowClosed; Deactivated += ChatPopup_WindowClosed;
        SizeChanged += ChatPopup_WindowResized; PreviewKeyDown += ChatPopup_KeyDown;
        WindowLayers.Children.Add(overlay);
        card.Measure(new Size(double.PositiveInfinity, double.PositiveInfinity));
        var anchor = anchorControl.TranslatePoint(new Point(0, 0), WindowLayers);
        var x = Math.Clamp(anchor.X + anchorControl.ActualWidth - card.DesiredSize.Width, 8, Math.Max(8, WindowLayers.ActualWidth - card.DesiredSize.Width - 8));
        var y = Math.Clamp(anchor.Y - card.DesiredSize.Height - 8, 8, Math.Max(8, WindowLayers.ActualHeight - card.DesiredSize.Height - 8));
        card.Margin = new(x, y, 0, 0);
        RevealDialogCard(card);
    }

    private void InsertPickerGlyph(ChatGlyph glyph, ModifierKeys modifiers)
    {
        if (_chatPopup is null || _chatPopupClosing) return;
        FriendsMessageInput.InsertGlyph(glyph);
        ActionJournal.Record("chat.glyph.insert", glyph.Id);
        if (!modifiers.HasFlag(ModifierKeys.Shift)) _ = CloseChatPopupAsync();
    }

    private void ChatPopup_MouseDown(object sender, MouseButtonEventArgs e)
    {
        if (_chatPopup is null || !_chatPopupClosing && InsideCard(e.OriginalSource as DependencyObject, _chatPopupCard!)) return;
        e.Handled = true;
        _chatPopupDismissButton = e.ChangedButton;
        Mouse.Capture(_chatPopup, CaptureMode.Element);
        _ = CloseChatPopupAsync();
    }

    private void ChatPopup_MouseUp(object sender, MouseButtonEventArgs e)
    {
        if (_chatPopupDismissButton is null) return;
        e.Handled = true;
        if (_chatPopupDismissButton != e.ChangedButton) return;
        _chatPopupDismissButton = null;
        if (_chatPopupHidden) RemoveChatPopup();
    }

    private async Task CloseChatPopupAsync()
    {
        if (_chatPopup is null || _chatPopupClosing) return;
        var overlay = _chatPopup;
        _chatPopupClosing = true;
        _chatPopupCard!.IsHitTestVisible = false;
        await Motion.HideAsync(_chatPopupCard);
        if (!ReferenceEquals(_chatPopup, overlay)) return;
        _chatPopupHidden = true;
        // Do not let an underlying MouseUp action fire after a long held click.
        if (_chatPopupDismissButton is null) RemoveChatPopup();
    }

    private void RemoveChatPopup()
    {
        var overlay = _chatPopup;
        if (overlay is null) return;
        _chatPopup = null; _chatPopupCard = null;
        _chatPopupClosing = _chatPopupHidden = false; _chatPopupDismissButton = null;
        if (ReferenceEquals(Mouse.Captured, overlay)) Mouse.Capture(null);
        WindowLayers.Children.Remove(overlay);
        Closed -= ChatPopup_WindowClosed; Deactivated -= ChatPopup_WindowClosed;
        SizeChanged -= ChatPopup_WindowResized; PreviewKeyDown -= ChatPopup_KeyDown;
    }

    private void ChatPopup_WindowClosed(object? sender, EventArgs e) => RemoveChatPopup();
    private void ChatPopup_WindowResized(object sender, SizeChangedEventArgs e) => RemoveChatPopup();
    private void ChatPopup_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key != Key.Escape) return;
        e.Handled = true; _ = CloseChatPopupAsync();
    }
}
