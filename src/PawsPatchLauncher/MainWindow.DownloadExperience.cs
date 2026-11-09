using System.Text.Json;
using System.Windows;
using System.Windows.Controls;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private readonly PendingInstallationStore _pendingInstallStore = new();
    private PendingInstallation? _pendingInstall;
    private bool _downloadUiReady, _downloadUiChanging, _closingPausedDownload;
    private string? _downloadUiLanguage;
    private static readonly int[] DownloadLimits = [0, 256, 1024, 5120, 10240];
    private sealed record SettingOption(string Label) { public override string ToString() => Label; }

    private void InitializeDownloadExperience()
    {
        _pendingInstall = _pendingInstallStore.Load();
        _feedClient.Downloads.LimitKiB = _settings.DownloadLimitKiB;
        _downloadUiReady = true; RefreshDownloadControls();
        Closed += (_, _) => { _closingPausedDownload = true; _downloadCancellation?.Cancel(); _feedClient.Downloads.Resume(); };
    }

    private void RefreshDownloadControls()
    {
        if (!_downloadUiReady) return;
        var active = _downloadCancellation is not null && _activeTransfer is not null;
        var paused = _feedClient.Downloads.IsPaused;
        DownloadControls.Visibility = active ? Visibility.Visible : Visibility.Collapsed;
        PauseDownloadButton.Content = paused ? T("Продолжить", "Resume") : T("Пауза", "Pause");
        CancelDownloadButton.Content = T("Остановить", "Stop");
        CancelDownloadButton.ToolTip = T("Частично скачанные файлы сохранятся для продолжения.", "Partial files are kept so the download can continue later.");
        if (_downloadUiLanguage != _text.Language)
        {
            _downloadUiChanging = true;
            DownloadLimitCombo.Items.Clear();
            foreach (var limit in DownloadLimits) DownloadLimitCombo.Items.Add(new SettingOption(limit == 0 ? T("Без ограничений", "Unlimited")
                : limit < 1024 ? limit + T(" КБ/с", " KiB/s") : limit / 1024 + T(" МБ/с", " MiB/s")));
            DownloadLimitCombo.SelectedIndex = Math.Max(0, Array.IndexOf(DownloadLimits, _settings.DownloadLimitKiB));
            _downloadUiChanging = false; _downloadUiLanguage = _text.Language;
        }
        DownloadSettingsTitle.Text = T("Загрузка файлов", "File downloads");
        DownloadLimitLabel.Text = T("Ограничение скорости", "Speed limit");
        DownloadSettingsHint.Text = T("Лимит действует только на скачивание файлов. Чат и статусы работают независимо. Частично скачанные файлы сохраняются после остановки и перезапуска.",
            "The limit applies only to file downloads. Chat and presence work independently. Partial files survive stopping and restarting.");
        DownloadResumeHint.Text = paused ? T("На паузе · полученные данные сохранены", "Paused · received data is saved")
            : T("Пауза и остановка не удаляют скачанные данные", "Pausing and stopping keep downloaded data");
        ResumeInstallationButton.Content = T("Продолжить установку", "Resume installation");
        DismissInstallationButton.Content = T("Убрать", "Dismiss");
        PendingInstallationCard.Visibility = !_busy && _pendingInstall is not null ? Visibility.Visible : Visibility.Collapsed;
        RefreshOperationPlacement();
        PendingInstallationText.Text = T("Незавершённая установка", "Unfinished installation");
        PendingInstallationHint.Text = _pendingInstall is { } pending && FriendConfiguration.TryParse(pending.Configuration, pending.Channel, out var settings)
            ? GameMod.Name(settings.Mod, _text.Language == "ru") + " · " + (pending.Channel == "beta" ? T("Бета", "Beta") : T("Релиз", "Release"))
                + "\n" + T("Продолжим с сохранённых файлов после проверки.", "Saved files will be verified and reused.") : "";
        if (paused && active) { SetTransferDetails(T("Загрузка на паузе. Можно продолжить или закрыть лаунчер.", "Download paused. You can resume or close the launcher.")); }
    }

    private void PauseDownload_Click(object sender, RoutedEventArgs e)
    {
        if (_downloadCancellation is null || _activeTransfer is null) return;
        if (_feedClient.Downloads.IsPaused) _feedClient.Downloads.Resume(); else _feedClient.Downloads.Pause();
        RefreshDownloadControls();
    }

    private void DownloadLimit_Changed(object sender, SelectionChangedEventArgs e)
    {
        if (!_downloadUiReady || _downloadUiChanging || DownloadLimitCombo.SelectedIndex < 0) return;
        _settings.DownloadLimitKiB = DownloadLimits[DownloadLimitCombo.SelectedIndex];
        _feedClient.Downloads.LimitKiB = _settings.DownloadLimitKiB;
        _settingsStore.Save(_settings);
    }

    private void RememberInstallation(ChannelManifest channel)
    {
        if (_game is null) return;
        _pendingInstall = new(_game.Directory, ConfigurationCode.Create(_settings), channel.Channel, ChannelFingerprint.Create(channel), DateTimeOffset.UtcNow, _settings.PinnedRelease);
        _pendingInstallStore.Save(_pendingInstall);
    }

    private void ForgetInstallation()
    {
        _pendingInstallStore.Clear(); _pendingInstall = null; RefreshDownloadControls();
    }
    private void DismissInstallation_Click(object sender, RoutedEventArgs e) { if (!_busy) ForgetInstallation(); }

    private async void ResumeInstallation_Click(object sender, RoutedEventArgs e) => await ResumeInstallationAsync();
    private async Task ResumeInstallationAsync()
    {
        if (_busy || FeedBlocksActions || ConfirmationActive || _pendingInstall is not { } pending) return;
        if (_game is null || !string.Equals(Path.GetFullPath(_game.Directory).TrimEnd('\\'), Path.GetFullPath(pending.GameDirectory).TrimEnd('\\'), StringComparison.OrdinalIgnoreCase))
        { ShowToast(() => T("Выберите прежнюю папку игры, чтобы продолжить эту установку.", "Select the original game folder to resume this installation."), true); return; }
        try
        {
            var channel = _feedClient.LoadArchived(pending.ReleaseId, pending.Channel);
            var selected = JsonSerializer.Deserialize<UserSettings>(JsonSerializer.Serialize(_settings))!;
            ConfigurationCode.Apply(ConfigurationCode.Parse(pending.Configuration), selected);
            SetBusy(true, T("Продолжаю установку…", "Resuming installation…"));
            await ApplyConfigurationSnapshotAsync(channel, true, selected);
            ConfigurationCode.Apply(selected, _settings);
            _settings.PreparedChannel = selected.PreparedChannel; _settings.PreparedFeedFingerprint = selected.PreparedFeedFingerprint;
            _settings.PinnedRelease = pending.PinnedRelease; _settingsStore.Save(_settings); _channel = channel;
            ForgetInstallation(); ApplyLanguage(); ShowResult(() => T("Установка завершена.", "Installation complete."));
        }
        catch (Exception error) { ShowError(error); }
        finally { SetBusy(false); RefreshStatus(); }
    }
}
