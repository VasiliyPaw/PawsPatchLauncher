using System.Windows;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private void ApplyRemovalLanguage()
    {
        RemovalTitleText.Text = T("Удаление", "Uninstall");
        RemovePatchButton.Content = T("Удалить патч", "Uninstall patch");
        RemoveLauncherButton.Content = T("Удалить лаунчер", "Uninstall launcher");
        RemovePatchDescriptionText.Text = T(
            "Убирает управляемые компоненты, включая установленный лаунчером Arcane Wars, и возвращает сохранённые исходные файлы. Сейвы и посторонние файлы не затрагиваются. Кэш и резервная копия для отката остаются.",
            "Removes managed components, including launcher-installed Arcane Wars, and restores backed-up originals. Saves and unrelated files are untouched. Cache and a rollback backup are retained.");
        RemoveLauncherDescriptionText.Text = T(
            "Закрывает и удаляет этот EXE лаунчера, его резервные EXE, настройки и стандартный кэш. Игра и установленный патч остаются. Другие копии лаунчера, внешняя конфигурация и нестандартный кэш не удаляются.",
            "Closes and removes this launcher EXE, its update copies, settings and default cache. The game and installed patch remain. Other launcher copies, external configuration and custom caches are retained.");
    }

    private async void RemovePatch_Click(object sender, RoutedEventArgs e)
    {
        if (_game is null || _busy || _checkingFeed) return;
        var root = _game.Directory;
        try
        {
            if (IsGameRunning()) throw new InvalidOperationException(T("Перед удалением патча закройте Kohan II.", "Close Kohan II before uninstalling the patch."));
            SetBusy(true);
            if (MessageBox.Show(this, T("Удалить управляемые компоненты патча из папки:\n", "Uninstall managed patch components from:\n") + root + "\n\n" + RemovePatchDescriptionText.Text,
                T("Удаление патча", "Uninstall patch"), MessageBoxButton.YesNo, MessageBoxImage.Warning, MessageBoxResult.No) != MessageBoxResult.Yes) return;
            if (IsGameRunning()) throw new InvalidOperationException(T("Kohan II запущен. Удаление отменено.", "Kohan II is running. Uninstall cancelled."));
            OperationText.Text = T("Удаляю патч и восстанавливаю исходные файлы…", "Uninstalling patch and restoring originals…");
            await new ModuleInstaller(root).UninstallAsync();
            _settings.PreparedChannel = null; _settings.PreparedFeedFingerprint = null; _settings.PinnedRelease = null;
            _settingsStore.Save(_settings);
            InvalidateReadiness();
            OperationText.Text = T("Патч удалён. Исходные файлы восстановлены; резервная копия для отката сохранена.",
                "Patch uninstalled. Originals restored; rollback backup retained.");
        }
        catch (Exception ex) { ShowError(ex); }
        finally { SetBusy(false); RefreshStatus(); }
    }

    private async void RemoveLauncher_Click(object sender, RoutedEventArgs e)
    {
        if (_busy || _checkingFeed) return;
        try
        {
            SetBusy(true);
            if (MessageBox.Show(this, RemoveLauncherDescriptionText.Text + "\n\n" + Environment.ProcessPath + "\n\n" + T("Продолжить?", "Continue?"),
                T("Удаление лаунчера", "Uninstall launcher"), MessageBoxButton.YesNo, MessageBoxImage.Warning, MessageBoxResult.No) != MessageBoxResult.Yes) return;
            await LauncherUninstaller.ScheduleAsync();
            _updateTimer.Stop(); _gameTimer.Stop();
            _busy = false;
            Application.Current.Shutdown();
        }
        catch (Exception ex) { ShowError(ex); }
        finally { SetBusy(false); }
    }
}
