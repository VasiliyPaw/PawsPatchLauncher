using System.Windows;
using System.Windows.Controls;
using Microsoft.Win32;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private Task<string?> ChooseModDbArchiveAsync(CancellationToken ct)
    {
        ct.ThrowIfCancellationRequested();
        string? selected = null;
        var dialog = CreateModDbArchiveDialog(path => selected = path);
        using var registration = ct.Register(() => dialog.Dispatcher.BeginInvoke(new Action(() => { if (dialog.IsVisible) dialog.Close(); })));
        dialog.ShowDialog();
        ct.ThrowIfCancellationRequested();
        return Task.FromResult(selected);
    }

    private Window CreateModDbArchiveDialog(Action<string> select)
    {
        var (dialog, body) = CreateCommunityDialog(T("Скачивание с ModDB", "Download from ModDB"), IconKind.Download, 620, 560);
        dialog.ResizeMode = ResizeMode.NoResize;
        dialog.MinHeight = 0;
        dialog.Height = double.NaN;
        dialog.MaxHeight = SystemParameters.WorkArea.Height - 32;
        dialog.SizeToContent = SizeToContent.Height;
        dialog.FontFamily = new System.Windows.Media.FontFamily("Arial");
        var panel = new StackPanel();
        body.Content = new ScrollViewer { Content = panel, VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled, MaxHeight = Math.Max(200, dialog.MaxHeight - 100) };
        panel.Children.Add(new TextBlock { Text = "ARCANE WARS  /  0.82 BETA", Foreground = SocialBrush("#D7AF56"),
            FontSize = 11, FontWeight = FontWeights.Bold, Margin = new Thickness(0, 4, 0, 10) });
        panel.Children.Add(new TextBlock
        {
            Text = T("Автоматическая загрузка недоступна. Скачайте мод через браузер, затем добавьте архив в лаунчер.",
                "Automatic download is unavailable. Download the mod in your browser, then add the archive to the launcher."),
            TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 0, 0, 20), FontSize = 14, LineHeight = 21,
            Foreground = SocialBrush("#AABBD0")
        });
        Button Step(string number, string title, string subtitle, string action, IconKind icon, bool primary)
        {
            var row = new Grid();
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            row.ColumnDefinitions.Add(new ColumnDefinition());
            row.Children.Add(new Border { Width = 30, Height = 30, CornerRadius = new CornerRadius(15), VerticalAlignment = VerticalAlignment.Top,
                Background = SocialBrush("#293746"), BorderBrush = SocialBrush("#756440"), BorderThickness = new Thickness(1), Margin = new Thickness(0,0,14,0),
                Child = new TextBlock { Text = number, Foreground = SocialBrush("#F3D487"), FontWeight = FontWeights.Bold,
                    HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Center } });
            var content = new StackPanel(); Grid.SetColumn(content, 1); row.Children.Add(content);
            content.Children.Add(new TextBlock { Text = title, FontSize = 16, FontWeight = FontWeights.SemiBold, TextWrapping = TextWrapping.Wrap });
            content.Children.Add(new TextBlock { Text = subtitle, FontSize = 12, Foreground = SocialBrush("#AABBD0"),
                TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 5, 0, 14) });
            var button = new Button { Content = new TextBlock { Text = action, Foreground = SocialBrush(primary ? "#151009" : "#F4F1E7") },
                Style = (Style)FindResource(primary ? "GoldButton" : "GhostButton"),
                Padding = new Thickness(14,10,14,10), HorizontalContentAlignment = HorizontalAlignment.Center };
            System.Windows.Automation.AutomationProperties.SetName(button, action);
            LauncherIcon.SetKind(button, icon); content.Children.Add(button);
            panel.Children.Add(new Border { Background = SocialBrush("#102238"), BorderBrush = SocialBrush("#354D68"),
                BorderThickness = new Thickness(1), CornerRadius = new CornerRadius(8), Padding = new Thickness(16), Margin = new Thickness(0,0,0,12), Child = row });
            return button;
        }
        var open = Step("1", T("Скачайте мод", "Download the mod"), "Arcane Wars 0.82 beta · Darquan Mortis\n" +
            T("Скачивание через ModDB помогает автору видеть интерес к моду по счётчику загрузок.",
                "Downloading through ModDB helps the author gauge interest in the mod through its download count."),
            T("Открыть ModDB", "Open ModDB"), IconKind.Download, false);
        var errorText = new TextBlock { Foreground = SocialBrush("#F0A08D"), TextWrapping = TextWrapping.Wrap, FontSize = 13,
            Margin = new Thickness(0,0,0,12), Visibility = Visibility.Collapsed };
        open.Click += async (_, _) =>
        {
            open.IsEnabled = false;
            errorText.Visibility = Visibility.Collapsed;
            try { await _openHelpLink(ModDbDownload.ArcanePage); }
            catch (Exception error) { ActivityStore.Log(error); errorText.Text = BrowserOpenError(); errorText.Visibility = Visibility.Visible; }
            finally { open.IsEnabled = true; }
        };
        Step("2", T("Добавьте архив", "Add the archive"), "Arcane_Wars_0.82beta.rar",
            T("Выбрать скачанный архив", "Select downloaded archive"), IconKind.Folder, true).Click += (_, _) =>
        {
            var picker = new OpenFileDialog { Title = "Arcane Wars 0.82 beta", Filter = "RAR (*.rar)|*.rar", CheckFileExists = true, Multiselect = false };
            // Cancelling the picker leaves this dialog open; it never restarts the download.
            if (picker.ShowDialog(dialog) != true) return;
            select(picker.FileName); dialog.DialogResult = true;
        };
        panel.Children.Add(errorText);
        var note = new Grid { Margin = new Thickness(2, 2, 2, 20) };
        note.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto }); note.ColumnDefinitions.Add(new ColumnDefinition());
        note.Children.Add(new LauncherIcon { Kind = IconKind.Shield, Width = 18, Height = 18, VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(0,0,10,0) });
        var noteText = new TextBlock { Text = T("Лаунчер проверит архив и автоматически установит патч Даркана.",
            "The launcher will verify the archive and apply Darquan’s patch automatically."), FontSize = 12, VerticalAlignment = VerticalAlignment.Center,
            Foreground = SocialBrush("#AABBD0"), TextWrapping = TextWrapping.Wrap };
        Grid.SetColumn(noteText,1); note.Children.Add(noteText); panel.Children.Add(note);
        var cancel = new Button { Content = T("Отмена", "Cancel"), Style = (Style)FindResource("GhostButton"),
            HorizontalAlignment = HorizontalAlignment.Right, MinWidth = 110 };
        panel.Children.Add(cancel);
        cancel.IsCancel = true;
        cancel.Click += (_, _) => dialog.Close();
        return dialog;
    }
}
