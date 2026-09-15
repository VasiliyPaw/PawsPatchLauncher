using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using PawsPatchLauncher;

namespace PreviewRenderer;

internal static class MessageSelectionChecks
{
    internal static void Run(string output)
    {
        if (!ActivityStore.IsSmokeTest || ActivityStore.LocalTestProfile is not null)
            throw new InvalidOperationException("Disposable smoke profile required.");
        var panel = new StackPanel { Background = Brushes.SteelBlue, Margin = new(15) };
        var messages = new[] { "это дс", "не тянет", "мой комп", "First line\nДругий рядок :ch_mana_crystal: 🙂", "", "two trailing spaces  " }
            .Select(body => new ChatMessageText { Text = body, FontSize = 14, Foreground = Brushes.White, Margin = new(0, 5, 0, 5) }).ToArray();
        foreach (var message in messages) panel.Children.Add(message);
        var background = new Border { Height = 35, Background = Brushes.Navy, Focusable = false };
        var composer = new ChatComposer();
        panel.Children.Add(background); panel.Children.Add(composer);
        var window = new Window { Content = panel, Width = 460, Height = 420, Left = -32000, Top = -32000,
            ShowActivated = false, ShowInTaskbar = false, WindowStartupLocation = WindowStartupLocation.Manual };
        int checks = 0;
        void Check(bool ok, string why) { checks++; if (!ok) throw new Exception("Message selection: " + why); }
        MouseButtonEventArgs Click(UIElement source, MouseButton button = MouseButton.Left, bool handled = false)
        {
            var args = new MouseButtonEventArgs(Mouse.PrimaryDevice, 0, button) { RoutedEvent = Mouse.PreviewMouseDownEvent, Handled = handled };
            source.RaiseEvent(args); return args;
        }
        async Task Scenario()
        {
            window.Show(); window.UpdateLayout(); await Task.Delay(20);
            foreach (var message in messages)
            {
                var body = message.Text;
                message.SelectAll();
                Check(message.Selection.Start.CompareTo(message.Document.Blocks.FirstBlock.ContentStart) >= 0, "selection includes document prefix");
                Check(message.Selection.End.CompareTo(message.Document.Blocks.LastBlock.ContentEnd) <= 0, "selection includes empty paragraph tail");
                Check(message.SelectedText == body, "full selection changes text, spaces or glyphs");
                if (!body.Contains(":ch_")) Check(new TextRange(message.Selection.Start, message.Selection.End).Text == body, "invisible paragraph newline is selected");
                if (!message.Selection.IsEmpty)
                {
                    string? copied = null;
                    message.CopyTextRequested = value => { copied = value; return Task.FromResult(true); };
                    ApplicationCommands.Copy.Execute(null, message);
                    Check(copied == body, "copy lost content");
                }
            }
            var first = messages[0]; var second = messages[1];
            first.SelectAll(); second.SelectAll();
            Check(first.Selection.IsEmpty && second.SelectedText == second.Text, "two messages retain selection");
            var click = Click(background, handled: true);
            Check(second.Selection.IsEmpty && click.Handled, "handled background click does not clear selection");
            first.SelectAll(); click = Click(first, MouseButton.Right);
            Check(!first.Selection.IsEmpty && !click.Handled, "right click inside message consumes selection/input");
            first.ContextMenu!.Opacity = 0; first.ContextMenu.PlacementTarget = first;
            first.ContextMenu.Items.Add(new MenuItem { Header = "Copy" }); first.ContextMenu.IsOpen = true;
            await Task.Delay(20);
            var item = (MenuItem)first.ContextMenu.Items[0];
            window.RaiseEvent(new KeyboardFocusChangedEventArgs(Keyboard.PrimaryDevice, 0, first, item) { RoutedEvent = Keyboard.GotKeyboardFocusEvent });
            Check(!first.Selection.IsEmpty, "context-menu focus clears selection before copy");
            string? menuCopy = null; first.CopyTextRequested = value => { menuCopy = value; return Task.FromResult(true); };
            ApplicationCommands.Copy.Execute(null, first);
            Check(menuCopy == first.Text, "context menu copy failed");
            first.ContextMenu.IsOpen = false;
            first.SelectAll();
            composer.RaiseEvent(new KeyboardFocusChangedEventArgs(Keyboard.PrimaryDevice, 0, first, composer) { RoutedEvent = Keyboard.GotKeyboardFocusEvent });
            Check(first.Selection.IsEmpty, "keyboard focus in composer leaves message selected");
            composer.Text = "composer draft"; composer.SelectAll(); first.SelectAll();
            Check(composer.Selection.Text.TrimEnd('\r', '\n') == "composer draft", "message scope changes draft selection");
            first.Selection.Select(first.Document.ContentEnd, first.Document.ContentStart);
            Check(first.SelectedText == first.Text && first.Selection.End.CompareTo(first.Document.Blocks.LastBlock.ContentEnd) <= 0, "backwards selection includes tail");
            var run = first.Document.Blocks.OfType<Paragraph>().Single().Inlines.OfType<Run>().Single();
            first.Selection.Select(run.ContentStart.GetPositionAtOffset(4)!, run.ContentEnd);
            Check(first.SelectedText == "дс", "partial selection changed");
            // Keep a rendered example for visual review of the last-character boundary.
            first.IsInactiveSelectionHighlightEnabled = true;
            window.UpdateLayout(); Directory.CreateDirectory(output);
            var bitmap = new RenderTargetBitmap(430, 390, 96, 96, PixelFormats.Pbgra32); bitmap.Render(panel);
            var encoder = new PngBitmapEncoder(); encoder.Frames.Add(BitmapFrame.Create(bitmap));
            using (var stream = File.Create(Path.Combine(output, "message-selection.png"))) encoder.Save(stream);
            first.IsInactiveSelectionHighlightEnabled = false;
            first.Visibility = Visibility.Collapsed;
            Check(first.Selection.IsEmpty, "hidden message retains selection");
            first.Visibility = Visibility.Visible; window.UpdateLayout(); first.SelectAll();
            panel.Children.Remove(first); await Task.Delay(20);
            Check(first.Selection.IsEmpty, "unloaded message retains selection");
            Console.WriteLine($"MESSAGE SELECTION PASS {checks}");
        }
        SynchronizationContext.SetSynchronizationContext(new DispatcherSynchronizationContext(window.Dispatcher));
        try
        {
            var task = Scenario(); var frame = new DispatcherFrame();
            var timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(20) };
            timer.Tick += (_, _) => frame.Continue = false;
            _ = task.ContinueWith(_ => window.Dispatcher.BeginInvoke(new Action(() => frame.Continue = false)));
            timer.Start(); if (!task.IsCompleted) Dispatcher.PushFrame(frame); timer.Stop();
            if (!task.IsCompleted) throw new TimeoutException("Message selection checks");
            task.GetAwaiter().GetResult();
        }
        finally { window.Close(); SynchronizationContext.SetSynchronizationContext(null); }
    }
}
