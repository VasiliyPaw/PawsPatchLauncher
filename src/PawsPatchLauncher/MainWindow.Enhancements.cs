using Microsoft.Win32;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Media;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private Border _storageCard = null!;
    private TextBlock _storageSummary = null!;
    private Button _cleanStorageButton = null!, _comparisonDetailsButton = null!;
    private CheckBox _cleanCache = null!, _cleanBackups = null!;
    private StoragePlan? _storagePlan;
    private MultiplayerComparison? _detailedComparison;
    private Exception? _presentedException;
    private FriendlyError? _presentedError;
    private bool _errorFromFeed;

    private Button EnhancementButton(Panel parent, string ru, string en, RoutedEventHandler action, string name = "", IconKind icon = IconKind.None)
    {
        var button = new Button { Style = (Style)FindResource("GhostButton"), Padding = new Thickness(12, 7, 12, 7),
            Margin = new Thickness(0, 0, 0, 9), HorizontalAlignment = HorizontalAlignment.Left };
        _reliabilityLabels.Add((s => button.Content = s, ru, en)); button.Content = T(ru, en);
        LauncherIcon.SetKind(button, icon);
        button.Click += action; parent.Children.Add(button); _reliabilityActions.Add(button);
        if (name.Length > 0) RegisterName(name, button);
        return button;
    }
    private TextBlock EnhancementText(Panel parent, string ru, string en, bool title = false)
    {
        var text = title ? new TextBlock { Style = (Style)FindResource("CardTitle") }
            : new TextBlock { Style = (Style)FindResource("CardDescription"), Margin = new Thickness(0, 0, 0, 10) };
        _reliabilityLabels.Add((s => text.Text = s, ru, en)); text.Text = T(ru, en); parent.Children.Add(text); return text;
    }
    private void InitializeEnhancementsUi()
    {
        var multiplayer = (StackPanel)_multiplayerCard.Child;
        var divider = new Border { Height = 1, Background = new SolidColorBrush(Color.FromRgb(64, 83, 110)), Margin = new Thickness(0, 14, 0, 14) };
        multiplayer.Children.Add(divider); RegisterName("DetailedComparisonDivider", divider);
        var comparisonTitle = EnhancementText(multiplayer, "Подробное сравнение", "Detailed comparison", true);
        comparisonTitle.Style = (Style)FindResource("CardSubtitle"); RegisterName("DetailedComparisonTitle", comparisonTitle);
        EnhancementText(multiplayer,
            "Сохраните отчёт и отправьте его другу, затем откройте его отчёт здесь. Внутри находятся настройки, версии и хеши файлов, без содержимого игры, сохранений, имени Windows и абсолютных путей. Короткий отпечаток выше по-прежнему работает, но не раскрывает различия.",
            "Save a report and send it to a friend, then open their report here. It contains settings, versions and file hashes, not game contents, saves, Windows usernames or absolute paths. The short fingerprint above still works but cannot explain differences.");
        EnhancementButton(multiplayer, "Сохранить отчёт для друга", "Save report for a friend", ExportMultiplayerReport_Click, "ExportMultiplayerReportButton", IconKind.Save);
        EnhancementButton(multiplayer, "Открыть отчёт друга и сравнить", "Open friend's report and compare", ImportMultiplayerReport_Click, "ImportMultiplayerReportButton", IconKind.Folder);
        _comparisonDetailsButton = EnhancementButton(multiplayer, "Показать различия", "Show differences", (_, _) => ShowComparisonDetails(), icon: IconKind.Compare);
        _comparisonDetailsButton.IsEnabled = false;

        var storage = new StackPanel();
        _storageCard = new Border { Style = (Style)FindResource("Card"), Margin = new Thickness(0, 0, 0, 14), Child = storage, Visibility = Visibility.Collapsed };
        RegisterName("StorageCard", _storageCard); ReliabilityPanels.Children.Add(_storageCard);
        EnhancementText(storage, "Место на диске", "Disk storage", true);
        EnhancementText(storage,
            "Очистка удаляет только распознанные устаревшие данные старше 7 дней. Текущие и закреплённые версии, исходные файлы для удаления патча, последняя резервная копия и незавершённые операции сохраняются. Кеш текущих компонентов остаётся для переключения без скачивания.",
            "Cleanup removes only recognized obsolete data older than 7 days. Current and pinned versions, uninstall originals, the latest backup and interrupted operations are retained. Current component caches stay available for offline switching.");
        _storageSummary = EnhancementText(storage, "Нажмите «Посчитать размер».", "Click Calculate size.");
        _reliabilityLabels.RemoveAt(_reliabilityLabels.Count - 1);
        EnhancementButton(storage, "Посчитать размер", "Calculate size", ScanStorage_Click, "ScanStorageButton", IconKind.Search);
        _cleanCache = StorageCheck(storage, "Устаревший кеш скачиваний и пакетов", "Obsolete download and package caches");
        _cleanBackups = StorageCheck(storage, "Старые завершённые резервные копии", "Old completed backups");
        _cleanStorageButton = EnhancementButton(storage, "Очистить выбранное…", "Clean selected…", CleanStorage_Click, "CleanStorageButton", IconKind.Trash);
        _cleanStorageButton.IsEnabled = false;
    }
    private CheckBox StorageCheck(Panel panel, string ru, string en)
    {
        var check = new CheckBox { Foreground = (Brush)FindResource("TextMainBrush"), IsChecked = true, Margin = new Thickness(0, 0, 0, 10) };
        var text = new TextBlock { TextWrapping = TextWrapping.Wrap, HorizontalAlignment = HorizontalAlignment.Left, TextAlignment = TextAlignment.Left };
        _reliabilityLabels.Add((s => text.Text = s, ru, en)); text.Text = T(ru, en); check.Content = text;
        panel.Children.Add(check); return check;
    }
    private void RefreshEnhancements()
    {
        if (_storageCard is null) return;
        _storageCard.Visibility = _activePage == "settings" ? Visibility.Visible : Visibility.Collapsed;
        _comparisonDetailsButton.IsEnabled = !_busy && _detailedComparison is not null;
        _cleanStorageButton.IsEnabled = !_busy && !_checkingFeed && _storagePlan is { CleanableBytes: > 0 };
        _cleanCache.IsEnabled = _cleanBackups.IsEnabled = !_busy && !_checkingFeed;
        if (_storagePlan is not null)
        {
            var cache = _storagePlan.Entries.Where(x => x.Kind is "downloads" or "packages" or "launcher-cache").Sum(x => x.Bytes);
            var backups = _storagePlan.TotalBytes - cache;
            _storageSummary.Text = T("Кеш архивов и пакетов: ", "Archive and package cache: ") + FormatBytes(cache)
                + "\n" + T("Резервные и исходные файлы: ", "Backups and originals: ") + FormatBytes(backups)
                + "\n" + T("Можно безопасно освободить: ", "Safe to reclaim: ") + FormatBytes(_storagePlan.CleanableBytes);
        }
        RefreshErrorActions();
    }

    private async void ExportMultiplayerReport_Click(object sender, RoutedEventArgs e)
    {
        if (_busy || _checkingFeed) return;
        try
        {
            await CheckReadinessAsync();
            if (_readiness?.Details is not { } report) return;
            var dialog = new SaveFileDialog { Title = T("Отчёт для сравнения", "Comparison report"), Filter = "Paw multiplayer report (*.pawmp.json)|*.pawmp.json",
                FileName = $"Paw-Multiplayer-{DateTime.Now:yyyyMMdd-HHmmss}.pawmp.json", AddExtension = true, DefaultExt = ".pawmp.json" };
            if (dialog.ShowDialog(this) != true) return;
            await MultiplayerDetails.SaveAsync(dialog.FileName, report);
            ShowResult(() => T("Отчёт сохранён. Отправьте его другу.", "Report saved. Send it to your friend."));
            ShowToast(() => T("Отчёт сохранён. Его можно отправить другу.", "Report saved. You can send it to your friend."));
        }
        catch (Exception ex) { ShowError(ex); }
    }
    private async void ImportMultiplayerReport_Click(object sender, RoutedEventArgs e)
    {
        if (_busy || _checkingFeed) return;
        var dialog = new OpenFileDialog { Title = T("Отчёт друга", "Friend's report"), Filter = "Paw multiplayer report (*.pawmp.json)|*.pawmp.json|JSON (*.json)|*.json" };
        if (dialog.ShowDialog(this) != true) return;
        try
        {
            var peer = await MultiplayerDetails.LoadAsync(dialog.FileName);
            await CheckReadinessAsync();
            if (_readiness?.Details is not { } local) return;
            _detailedComparison = MultiplayerDetails.Compare(local, peer);
            _comparisonText.Text = _detailedComparison.Matches
                ? T("Проверенные конфигурации совпадают. Это не гарантия отсутствия рассинхронов в игре.", "The checked configurations match. This does not guarantee a desync-free game.")
                : T("Найдено различий: ", "Differences found: ") + _detailedComparison.Differences.Count;
            _comparisonText.Foreground = (Brush)FindResource(_detailedComparison.Matches ? "SuccessBrush" : "DangerBrush");
            RefreshEnhancements(); ShowComparisonDetails();
        }
        catch (Exception ex) { ShowError(ex); }
    }
    private void ShowComparisonDetails() => CreateComparisonDialog()?.ShowDialog();
    private Window? CreateComparisonDialog()
    {
        if (_detailedComparison is null) return null;
        var grid = new Grid { Margin = new Thickness(18), Background = (Brush)FindResource("NightBrush") };
        grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        grid.RowDefinitions.Add(new RowDefinition());
        var explanation = new TextBlock { TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 0, 0, 12),
            Text = _detailedComparison.Matches ? T("Конфигурации совпадают. Сравнены версии, настройки и проверенные файлы.", "Configurations match: versions, settings and checked files.")
                : T("Показаны только различия. «Не указан» означает, что файла нет в отчёте, «Отсутствует» означает, что проверка не нашла его на диске. Отчёты являются снимками на момент проверки.", "Only differences are shown. Not listed means the file is absent from the report; Missing means the check could not find it on disk. Reports are snapshots at check time.") };
        grid.Children.Add(explanation);
        var search = new TextBox { Margin = new Thickness(0, 0, 0, 12), Padding = new Thickness(8), Background = (Brush)FindResource("NightRaisedBrush"), Foreground = (Brush)FindResource("TextMainBrush"),
            BorderBrush = (Brush)FindResource("TextMutedBrush"), ToolTip = T("Поиск по имени, компоненту или хешу", "Search name, component or hash") };
        Grid.SetRow(search, 1); grid.Children.Add(search);
        var table = new DataGrid { AutoGenerateColumns = false, IsReadOnly = true, CanUserAddRows = false, CanUserDeleteRows = false,
            EnableRowVirtualization = true, HeadersVisibility = DataGridHeadersVisibility.Column, FontFamily = new FontFamily("Arial"),
            Background = (Brush)FindResource("NightRaisedBrush"), Foreground = (Brush)FindResource("TextMainBrush"), RowBackground = (Brush)FindResource("NightRaisedBrush"),
            AlternatingRowBackground = (Brush)FindResource("PanelBrush"), GridLinesVisibility = DataGridGridLinesVisibility.Horizontal,
            HorizontalGridLinesBrush = new SolidColorBrush(Color.FromRgb(61, 84, 115)), BorderBrush = (Brush)FindResource("TextMutedBrush") };
        var header = new Style(typeof(System.Windows.Controls.Primitives.DataGridColumnHeader));
        header.Setters.Add(new Setter(Control.BackgroundProperty, FindResource("PanelBrush")));
        header.Setters.Add(new Setter(Control.ForegroundProperty, FindResource("TextMainBrush")));
        header.Setters.Add(new Setter(Control.PaddingProperty, new Thickness(8)));
        table.ColumnHeaderStyle = header;
        foreach (var (name, label, width) in new[] { ("Kind", T("Тип", "Type"), .65), ("Name", T("Компонент / файл", "Component / file"), 1.7), ("Local", T("У меня", "Mine"), 1d), ("Peer", T("У друга", "Friend"), 1d) })
        {
            var style = new Style(typeof(TextBlock)); style.Setters.Add(new Setter(TextBlock.TextWrappingProperty, TextWrapping.Wrap));
            style.Setters.Add(new Setter(FrameworkElement.MarginProperty, new Thickness(6)));
            table.Columns.Add(new DataGridTextColumn { Header = label, Binding = new Binding(name), MinWidth = name == "Kind" ? 85 : 140, Width = new DataGridLength(width, DataGridLengthUnitType.Star), ElementStyle = style });
        }
        string Value(string value) => value switch { "MISSING" => T("Отсутствует", "Missing"), "NOT_LISTED" => T("Не указан", "Not listed"), "ERROR" => T("Ошибка проверки", "Verification error"), _ => value };
        string Kind(string kind) => kind switch { "file" => T("Файл", "File"), "module" => T("Компонент", "Component"), "integrity" => T("Проверка", "Integrity"), _ => T("Настройка", "Setting") };
        string Name(string name) => name switch {
            "Channel" => T("Канал", "Channel"), "Independent hostility" => T("Вражда независимых", name),
            "Roaming spawn" => T("Частота блуждающих рот", name), "New roaming companies" => T("Новые блуждающие роты", name),
            "Siege balance" => T("Баланс осадных машин", name), "Large maps" => T("Большие карты", name),
            "Russian localization" => T("Русская локализация", name), "Player colors" => T("Цвета игроков", name),
            "Desync handling" => T("Обработка рассинхрона", name), "Disable Powers and Shards" => T("Отключение Powers и Shards", name), _ => name };
        string DisplayValue(MultiplayerDifference row, string value)
        {
            if (row.Kind != "setting") return Value(value);
            if (row.Name == "Channel") return ChannelPresentation.Name(value, _text.Language);
            if (value is "SP1" or "SP4") return value == "SP1" ? T("Стандартно", "Standard") : "×4";
            if (value is "OOS0" or "OOS1") return value == "OOS0" ? T("Остановить игру", "Stop game") : T("Продолжать", "Continue");
            if (value.Length == 3 && value[..2] is "IW" or "RM" or "SG" or "LM" or "RU" or "CL" or "PS") return value.EndsWith('1') ? T("Включено", "Enabled") : T("Выключено", "Disabled");
            return value;
        }
        var rows = _detailedComparison.Differences.Select(x => new { Kind = Kind(x.Kind), Name = Name(x.Name), Local = DisplayValue(x, x.Local), Peer = DisplayValue(x, x.Peer) }).ToList();
        table.ItemsSource = rows;
        search.TextChanged += (_, _) => table.ItemsSource = rows.Where(x => (x.Kind + x.Name + x.Local + x.Peer).Contains(search.Text, StringComparison.OrdinalIgnoreCase)).ToList();
        Grid.SetRow(table, 2); grid.Children.Add(table);
        var area = SystemParameters.WorkArea;
        return new Window { Owner = IsLoaded ? this : null, Title = T("Сравнение с другом", "Compare with friend"), FontFamily = new FontFamily("Arial"),
            Background = (Brush)FindResource("NightBrush"), Width = Math.Min(1080, area.Width - 30), Height = Math.Min(700, area.Height - 30),
            WindowStartupLocation = WindowStartupLocation.CenterOwner, Content = grid };
    }

    private StorageOptions GetStorageOptions()
    {
        var feeds = new[] { _channel, _latestChannel }.Where(x => x is not null).Cast<ChannelManifest>()
            .Concat(_feedClient.Archived("stable").Take(1)).Concat(_feedClient.Archived("beta").Take(1)).ToList();
        if (_settings.PinnedRelease is not null) feeds.Add(_feedClient.LoadArchived(_settings.PinnedRelease, _settings.Channel));
        return new(_feedClient.CacheDirectory, _game?.Directory, Environment.ProcessPath,
            feeds.SelectMany(x => x.Packages).ToList(), feeds.Select(x => x.Launcher).ToList());
    }
    private async void ScanStorage_Click(object sender, RoutedEventArgs e)
    {
        if (_busy || _checkingFeed || ConfirmationActive) return;
        try
        {
            SetBusy(true, T("Считаю размер кеша и резервных копий…", "Calculating cache and backup sizes…"));
            var options = GetStorageOptions(); _storagePlan = await Task.Run(() => StorageMaintenance.Scan(options));
            ShowResult(() => T("Размеры рассчитаны. Ничего не удалено.", "Sizes calculated. Nothing was deleted."));
        }
        catch (Exception ex) { _storagePlan = null; ShowError(ex); }
        finally { SetBusy(false); RefreshEnhancements(); }
    }
    private async void CleanStorage_Click(object sender, RoutedEventArgs e)
        => await CleanStorageAsync();

    private async Task CleanStorageAsync()
    {
        if (_busy || _checkingFeed || ConfirmationActive || _storagePlan is null) return;
        var ownsOperation = false;
        try
        {
            if (IsGameRunning()) throw new IOException(T("Сначала закройте Kohan II.", "Close Kohan II first."));
            var cache = _cleanCache.IsChecked == true; var backups = _cleanBackups.IsChecked == true;
            ownsOperation = true; SetBusy(true, T("Проверяю безопасную очистку…", "Checking safe cleanup…"));
            var options = GetStorageOptions(); var approved = await Task.Run(() => StorageMaintenance.Scan(options));
            _storagePlan = approved;
            var bytes = approved.Entries.Where(x => x.Cleanable && (x.Kind == "backups" ? backups : cache)).Sum(x => x.Bytes);
            if (bytes == 0) { _storagePlan = approved; ShowResult(() => T("Для выбранных категорий нет устаревших данных.", "No obsolete data in the selected categories.")); return; }
            SetBusy(false); ownsOperation = false;
            if (!await ConfirmStorageCleanupAsync(approved, cache, backups))
            {
                if (!_busy && !_checkingFeed) ShowResult(() => T("Очистка отменена. Ничего не удалено.", "Cleanup cancelled. Nothing was deleted."));
                return;
            }
            if (_busy || _checkingFeed || ConfirmationActive) return;
            ownsOperation = true; SetBusy(true, T("Очищаю устаревшие данные…", "Cleaning up obsolete data…"));
            if (IsGameRunning()) throw new IOException(T("Игра запущена. Очистка отменена.", "The game is running. Cleanup cancelled."));
            // Re-read pinned/installed release metadata after the confirmation dialog.
            options = GetStorageOptions();
            var result = await Task.Run(() => StorageMaintenance.Clean(options, approved, cache, backups));
            _storagePlan = await Task.Run(() => StorageMaintenance.Scan(options));
            ShowResult(() => T("Освобождено: ", "Reclaimed: ") + FormatBytes(result.Bytes) + T(". Пропущено изменившихся или занятых объектов: ", ". Changed or busy items skipped: ") + result.Skipped);
        }
        catch (Exception ex) { _storagePlan = null; ShowError(ex); }
        finally { if (ownsOperation) SetBusy(false); RefreshEnhancements(); }
    }

    private void SetFriendlyError(Exception exception, bool fromFeed = false)
    {
        _presentedException = exception; _presentedError = FriendlyErrors.Describe(exception); _errorFromFeed = fromFeed;
        RefreshErrorActions();
    }
    private void ClearFriendlyError()
    {
        _presentedException = null; _presentedError = null; _errorFromFeed = false; RefreshErrorActions();
    }
    private void RefreshErrorActions()
    {
        if (ErrorActionButton is null) return;
        var visible = _presentedError is not null && !_busy && !_checkingFeed;
        ErrorActionsPanel.Visibility = visible ? Visibility.Visible : Visibility.Collapsed;
        if (_presentedError is not null) ErrorActionButton.Content = _presentedError.ActionText(_text.Language);
        ErrorDetailsButton.Content = T("Объяснение и подробности", "Explanation and details");
    }
    private async void ErrorAction_Click(object sender, RoutedEventArgs e)
    {
        if (_busy || _checkingFeed || _presentedError is null) return;
        var action = _presentedError.Action;
        switch (action)
        {
            case ErrorAction.CheckUpdates: await CheckFeedAsync(); break;
            case ErrorAction.Storage: SetActivePage("settings"); _storageCard.BringIntoView(); ScanStorage_Click(sender, e); break;
            case ErrorAction.Settings: SetActivePage("settings"); break;
            case ErrorAction.Diagnostics: DiagnosticsButton_Click(sender, e); break;
        }
    }
    private void ErrorDetails_Click(object sender, RoutedEventArgs e) => ShowFriendlyErrorDialog();
    private void ShowFriendlyErrorDialog() => CreateFriendlyErrorDialog()?.ShowDialog();
    private Window? CreateFriendlyErrorDialog()
    {
        if (_presentedError is not { } error || _presentedException is not { } exception) return null;
        var panel = new StackPanel { Margin = new Thickness(20) };
        panel.Children.Add(new TextBlock { Text = error.Title(_text.Language), FontSize = 20, FontWeight = FontWeights.Bold, TextWrapping = TextWrapping.Wrap });
        panel.Children.Add(new TextBlock { Text = error.Body(_text.Language), FontSize = 13, LineHeight = 20, TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 12, 0, 16) });
        var action = new Button { Style = (Style)FindResource("GoldButton"), Content = error.ActionText(_text.Language), Margin = new Thickness(0, 0, 0, 10) };
        var copy = new Button { Style = (Style)FindResource("GhostButton"), Content = T("Скопировать технические подробности", "Copy technical details") };
        var details = exception.ToString();
        panel.Children.Add(action); panel.Children.Add(copy);
        var copyNotice = new TextBlock { TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 9, 0, 0), Visibility = Visibility.Collapsed };
        panel.Children.Add(copyNotice);
        copy.Click += async (_, _) =>
        {
            copyNotice.Visibility = Visibility.Collapsed;
            await CopyTextAsync(details, () => T("Подробности скопированы.", "Details copied."), (message, failed) =>
            {
                copyNotice.Text = message(); copyNotice.Visibility = Visibility.Visible;
                copyNotice.Foreground = (Brush)FindResource(failed ? "DangerBrush" : "SuccessBrush");
            });
        };
        panel.Children.Add(new Expander { Header = T("Технические подробности", "Technical details"), Margin = new Thickness(0, 14, 0, 0), Foreground = (Brush)FindResource("TextMutedBrush"),
            Content = new TextBox { Text = details[..Math.Min(details.Length, 12000)], IsReadOnly = true, TextWrapping = TextWrapping.Wrap, Height = 140, VerticalScrollBarVisibility = ScrollBarVisibility.Auto } });
        var dialog = new Window { Owner = IsLoaded ? this : null, Title = T("Понятная ошибка", "Error help"), FontFamily = new FontFamily("Arial"), Width = Math.Min(590, SystemParameters.WorkArea.Width - 30),
            MaxHeight = SystemParameters.WorkArea.Height - 30, SizeToContent = SizeToContent.Height, WindowStartupLocation = WindowStartupLocation.CenterOwner,
            Background = (Brush)FindResource("NightBrush"), Content = new ScrollViewer { Background = (Brush)FindResource("NightBrush"), Content = panel, VerticalScrollBarVisibility = ScrollBarVisibility.Auto } };
        action.Click += (_, e) => { dialog.Close(); Dispatcher.BeginInvoke(new Action(() => ErrorAction_Click(action, e))); };
        return dialog;
    }
}
