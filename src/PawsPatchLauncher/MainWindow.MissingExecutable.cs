using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private MissingGameExecutable? _missingExecutable;

    private void RefreshMissingExecutable(InstallState? state)
    {
        var directory = _game?.Directory ?? _settings.GamePath;
        _missingExecutable = MissingGameExecutable.Find(directory);
        if (_missingExecutable is null && _game is not null && state is not null)
        {
            try { _missingExecutable = MissingGameExecutable.Find(directory, ResolveLaunchExecutable(_game.Directory), state); }
            catch (Exception error) when (error is InvalidOperationException or InvalidDataException or FrequencyUnavailableException) { }
        }
        MissingExecutableCard.Visibility = _missingExecutable is not null && !_busy ? Visibility.Visible : Visibility.Collapsed;
        MissingExecutableTitle.Text = MissingExecutableTitleText();
        MissingExecutableBody.Text = T("Антивирус мог переместить файл в карантин. Проверьте его журнал — причина пока не подтверждена.",
            "Your antivirus may have quarantined the file. Check its history; the cause is not confirmed yet.");
        MissingExecutableName.Text = _missingExecutable?.FileName ?? "";
        MissingExecutableDetailsButton.Content = T("Как восстановить", "How to restore it");
        MissingExecutableRecheckButton.Content = T("Проверить снова", "Check again");
        MissingExecutableDetailsButton.IsEnabled = MissingExecutableRecheckButton.IsEnabled = !_busy;
    }

    private string MissingExecutableTitleText() => _missingExecutable?.IsPatchHelper == true
        ? T("Не найден запускатель патча", "Patch launcher is missing")
        : T("Не найден файл игры", "Game executable is missing");

    private void MissingExecutableDetails_Click(object sender, RoutedEventArgs e)
    {
        if (!_busy && !ConfirmationActive && _missingExecutable is not null) CreateMissingExecutableDialog().ShowDialog();
    }

    private void MissingExecutableRecheck_Click(object sender, RoutedEventArgs e)
    {
        if (_busy) return;
        LocateGame(); RefreshStatus();
        var recovered = _game is not null && _missingExecutable is null;
        ShowToast(() => recovered ? T("Файлы запуска снова доступны.", "Launch files are available again.")
            : T("Файл пока не найден. Проверьте карантин или восстановите файлы игры.", "The file is still missing. Check quarantine or restore the game files."), !recovered);
    }

    private Window CreateMissingExecutableDialog()
    {
        var missing = _missingExecutable ?? throw new InvalidOperationException("No missing executable.");
        var (window, host) = CreateCommunityDialog(MissingExecutableTitleText(), IconKind.Warning, 650, 570);
        window.MinWidth = 440; window.MinHeight = 470;
        var body = new StackPanel();
        TextBlock Text(string value, double size = 13, string color = "#B5C7DC") => new()
        { Text = value, TextWrapping = TextWrapping.Wrap, FontSize = size, Foreground = SocialBrush(color) };
        body.Children.Add(Text(T("Запуск остановлен: нужного EXE нет в выбранной папке.", "Launch stopped: the required executable is not in the selected folder."), 14));
        var file = new StackPanel();
        file.Children.Add(Text(missing.FileName, 20, "#F0CC78"));
        var path = Text(missing.Path, 12); path.Margin = new Thickness(0, 8, 0, 0); file.Children.Add(path);
        body.Children.Add(new Border { Background = SocialBrush("#1A2C41"), BorderBrush = SocialBrush("#405570"), BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(8), Padding = new Thickness(14), Margin = new Thickness(0, 16, 0, 16), Child = file });
        void Step(string number, string title, string description)
        {
            var row = new Grid { Margin = new Thickness(0, 0, 0, 16) };
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(37) }); row.ColumnDefinitions.Add(new ColumnDefinition());
            row.Children.Add(Text(number, 18, "#D7B45D"));
            var words = new StackPanel(); words.Children.Add(Text(title, 14, "#E8EDF5"));
            var detail = Text(description); detail.Margin = new Thickness(0, 5, 0, 0); words.Children.Add(detail);
            Grid.SetColumn(words, 1); row.Children.Add(words); body.Children.Add(row);
        }
        Step("1", T("Проверьте карантин антивируса", "Check antivirus quarantine"),
            T("Откройте журнал защиты или карантин и найдите запись с этим именем файла. Его отсутствие не доказывает, что виноват антивирус.",
                "Open protection history or quarantine and look for this filename. A missing file alone does not prove that antivirus removed it."));
        Step("2", T("Восстановите доверенный файл", "Restore a trusted file"),
            T("Если файл попал в карантин и вы доверяете его источнику, восстановите его. Не скачивайте отдельный EXE с посторонних сайтов.",
                "If the file was quarantined and you trust its source, restore it. Do not download a replacement executable from an unrelated website."));
        Step("3", missing.IsPatchHelper ? T("Заново примените настройки патча", "Reapply patch settings") : T("Если файла нет в карантине", "If the file is not in quarantine"),
            missing.IsPatchHelper
                ? T("В лаунчере нажмите «Применить настройки»: недостающий запускатель восстановится из проверенных пакетов.",
                    "Click Apply settings in the launcher to restore the missing patch launcher from verified packages.")
                : T("В Steam откройте свойства Kohan II → Установленные файлы → Проверьте целостность файлов игры. Затем вернитесь в лаунчер.",
                    "In Steam, open Kohan II Properties → Installed Files → Verify integrity of game files. Then return to the launcher."));
        var note = Text(T("После восстановления нажмите «Проверить снова». Полностью отключать антивирус для проверки не требуется.",
            "After restoring the file, click Check again. You do not need to turn off antivirus protection to check this."), 12, "#D4C59E");
        body.Children.Add(new Border { Background = SocialBrush("#302D21"), CornerRadius = new CornerRadius(7), Padding = new Thickness(12), Child = note });
        var actions = new WrapPanel { HorizontalAlignment = HorizontalAlignment.Right, Margin = new Thickness(0, 16, 0, 0) };
        var folder = new Button { Content = T("Открыть папку", "Open folder"), Style = (Style)FindResource("GhostButton"), Margin = new Thickness(0, 0, 8, 0) };
        folder.Click += async (_, _) => { try { await _openGameFolder(missing.Directory); } catch (Exception error) { ShowError(error); } }; actions.Children.Add(folder);
        var recheck = new Button { Content = T("Проверить снова", "Check again"), Style = (Style)FindResource("GoldButton") };
        recheck.Click += (_, _) => { window.Close(); MissingExecutableRecheck_Click(recheck, new RoutedEventArgs()); }; actions.Children.Add(recheck);
        var layout = new Grid(); layout.RowDefinitions.Add(new RowDefinition()); layout.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        layout.Children.Add(new ScrollViewer { Content = body, VerticalScrollBarVisibility = ScrollBarVisibility.Auto });
        Grid.SetRow(actions, 1); layout.Children.Add(actions); host.Content = layout;
        return window;
    }
}
