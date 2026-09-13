using System.Windows;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private bool _removeModsWithLauncher;
    private Func<Task> _scheduleLauncherRemoval = LauncherUninstaller.ScheduleAsync;
    private void ApplyRemovalLanguage()
    {
        RemovalTitleText.Text = T("Удаление", "Uninstall");
        RemovePatchButton.Content = T("Удалить патч", "Uninstall patch");
        RemoveLauncherButton.Content = T("Удалить лаунчер", "Uninstall launcher");
        RemovePatchDescriptionText.Text = T(
            "Убирает управляемые компоненты, включая установленный лаунчером Arcane Wars, и возвращает сохранённые исходные файлы. Сейвы и посторонние файлы не затрагиваются. Кэш и резервная копия для отката остаются.",
            "Removes managed components, including launcher-installed Arcane Wars, and restores backed-up originals. Saves and unrelated files are untouched. Cache and a rollback backup are retained.");
        RemoveLauncherDescriptionText.Text = T(
            "Удаляет лаунчер, его настройки и стандартный кеш. В окне подтверждения можно выбрать, удалить ли также установленные им патч и моды. Сохранения игры останутся.",
            "Removes the launcher, its settings and default cache. The confirmation lets you choose whether to remove its installed patch and mods as well. Game saves are kept.");
    }

    private async void RemovePatch_Click(object sender, RoutedEventArgs e)
    {
        if (_game is null || _busy || FeedBlocksActions || ConfirmationActive) return;
        var root = _game.Directory;
        var started = false;
        try
        {
            if (IsGameRunning()) throw new InvalidOperationException(T("Перед удалением патча закройте Kohan II.", "Close Kohan II before uninstalling the patch."));
            if (!await ConfirmRemovalAsync(false, root)) return;
            if (_busy || FeedBlocksActions || _game?.Directory != root) return;
            if (IsGameRunning()) throw new InvalidOperationException(T("Kohan II запущен. Удаление отменено.", "Kohan II is running. Uninstall cancelled."));
            started = true; SetBusy(true);
            ShowWorking(() => T("Удаляю патч и восстанавливаю исходные файлы…", "Uninstalling patch and restoring originals…"));
            await new ModuleInstaller(root).UninstallAsync();
            _settings.PreparedChannel = null; _settings.PreparedFeedFingerprint = null; _settings.PinnedRelease = null;
            _settingsStore.Save(_settings);
            InvalidateReadiness();
            _fileCheckFailed = false;
            ShowResult(() => T("Патч удалён. Исходные файлы восстановлены; резервная копия для отката сохранена.",
                "Patch uninstalled. Originals restored; rollback backup retained."));
        }
        catch (Exception ex) { ShowError(ex); }
        finally { if (started) { SetBusy(false); RefreshStatus(); } }
    }

    private async void RemoveLauncher_Click(object sender, RoutedEventArgs e)
    {
        if (_busy || FeedBlocksActions || ConfirmationActive) return;
        var started = false;
        try
        {
            var gameRoot = _game?.Directory;
            if (!await ConfirmLauncherRemovalAsync(Environment.ProcessPath ?? T("Текущий лаунчер", "Current launcher"))) return;
            if (_busy || FeedBlocksActions) return;
            if (_removeModsWithLauncher && gameRoot is not null)
            {
                if (_game?.Directory != gameRoot) throw new IOException(T("Папка игры изменилась. Повторите удаление.", "The game folder changed. Start uninstall again."));
                EnsureGameClosed();
            }
            started = true; SetBusy(true);
            if (_removeModsWithLauncher && gameRoot is not null)
            {
                ShowWorking(() => T("Удаляю патч и моды, восстанавливаю оригинальные файлы…", "Removing patch and mods, restoring original files…"));
                await new ModuleInstaller(gameRoot).UninstallAsync();
                _settings.PreparedChannel = _settings.PreparedFeedFingerprint = _settings.PinnedRelease = null;
                _settingsStore.Save(_settings);
                InvalidateReadiness();
            }
            await _scheduleLauncherRemoval();
            _updateTimer.Stop(); _gameTimer.Stop();
            _busy = false;
            Application.Current.Shutdown();
        }
        catch (Exception ex) { ShowError(ex); }
        finally { if (started) SetBusy(false); }
    }

    private async Task<bool> ConfirmLauncherRemovalAsync(string path)
    {
        var confirmation = ConfirmActionAsync(T("Удалить лаунчер?", "Uninstall launcher?"),
            RemoveLauncherDescriptionText.Text, T("ЭТОТ ФАЙЛ ЛАУНЧЕРА", "THIS LAUNCHER FILE"), path,
            T("Удалить лаунчер", "Uninstall launcher"));
        if (!ConfirmationActive) return false;
        ConfirmationRemoveModsToggle.Content = T("Удалить патч и моды", "Remove patch and mods");
        ConfirmationRemoveModsToggle.IsChecked = true;
        ConfirmationRemoveModsToggle.Visibility = Visibility.Visible;
        var accepted = await confirmation;
        _removeModsWithLauncher = accepted && ConfirmationRemoveModsToggle.IsChecked == true;
        return accepted;
    }
}
