using System.Windows;
using System.Windows.Input;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private TaskCompletionSource<bool>? _confirmation;
    private bool _confirmationFinishing;
    private IInputElement? _confirmationPreviousFocus;
    private bool ConfirmationActive => _confirmation is not null;

    private void InitializeConfirmation()
    {
        PreviewKeyDown += (_, e) =>
        {
            if (ConfirmationActive && e.Key == Key.Escape)
            {
                e.Handled = true;
                _ = CompleteConfirmationAsync(false);
            }
        };
        Closed += (_, _) => { _confirmation?.TrySetResult(false); _confirmation = null; };
    }

    private Task<bool> ConfirmRemovalAsync(bool launcher, string path)
        => ConfirmActionAsync(
            launcher ? T("Удалить лаунчер?", "Uninstall launcher?") : T("Удалить патч?", "Uninstall patch?"),
            launcher ? RemoveLauncherDescriptionText.Text : RemovePatchDescriptionText.Text,
            launcher ? T("ЭТОТ ФАЙЛ ЛАУНЧЕРА", "THIS LAUNCHER FILE") : T("ПАПКА ИГРЫ", "GAME FOLDER"), path,
            launcher ? T("Удалить лаунчер", "Uninstall launcher") : T("Удалить патч", "Uninstall patch"));

    private Task<bool> ConfirmStorageCleanupAsync(StoragePlan plan, bool cache, bool backups)
    {
        var cacheBytes = cache ? plan.Entries.Where(x => x.Cleanable && x.Kind != "backups").Sum(x => x.Bytes) : 0;
        var backupBytes = backups ? plan.Entries.Where(x => x.Cleanable && x.Kind == "backups").Sum(x => x.Bytes) : 0;
        if (cacheBytes + backupBytes == 0) return Task.FromResult(false);
        var lines = new List<string>();
        if (cacheBytes > 0) lines.Add(T("Устаревший кеш: ", "Obsolete caches: ") + FormatBytes(cacheBytes));
        if (backupBytes > 0) lines.Add(T("Старые резервные копии: ", "Old backups: ") + FormatBytes(backupBytes));
        lines.Add(T("Всего: ", "Total: ") + FormatBytes(cacheBytes + backupBytes));
        var body = T(
            "Будут удалены только выбранные устаревшие данные старше 7 дней. Игра, сохранения, текущие и закреплённые версии, исходные файлы и последняя резервная копия останутся.",
            "Only the selected obsolete data older than 7 days will be removed. The game, saves, current and pinned versions, original files and latest backup will be retained.");
        if (backupBytes > 0) body += "\n\n" + T("Удалённые старые резервные копии нельзя восстановить.", "Deleted old backups cannot be restored.");
        if (cacheBytes > 0) body += (backupBytes > 0 ? " " : "\n\n") + T("Кеш при необходимости можно скачать снова.", "Caches can be downloaded again if needed.");
        return ConfirmActionAsync(T("Очистить устаревшие данные?", "Clean up obsolete data?"), body,
            T("БУДЕТ УДАЛЕНО", "TO BE REMOVED"), string.Join("\n", lines), T("Очистить", "Clean up"));
    }

    private Task<bool> ConfirmActionAsync(string title, string body, string detailsLabel, string details, string action)
    {
        // Confirmation reserves the UI, but is not an installation/removal operation.
        if (ConfirmationActive || _busy || _checkingFeed) return Task.FromResult(false);
        _confirmation = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        _confirmationPreviousFocus = Keyboard.FocusedElement;
        HelpOverlay.Visibility = Visibility.Collapsed;
        MainBody.IsEnabled = TitleBar.IsEnabled = false;
        ConfirmationCard.IsEnabled = true;
        ConfirmationEyebrowText.Text = T("ПОДТВЕРЖДЕНИЕ ДЕЙСТВИЯ", "CONFIRM ACTION");
        ConfirmationTitleText.Text = title;
        ConfirmationBodyText.Text = body;
        ConfirmationPathLabel.Text = detailsLabel;
        ConfirmationPathText.Text = details;
        ConfirmationCancelButton.Content = T("Отмена", "Cancel");
        ConfirmationDeleteButton.Content = action;
        ConfirmationCloseButton.ToolTip = T("Отмена", "Cancel");
        System.Windows.Automation.AutomationProperties.SetName(ConfirmationCloseButton, T("Отмена", "Cancel"));
        Motion.Reveal(ConfirmationOverlay);
        ConfirmationCancelButton.Focus();
        return _confirmation.Task;
    }

    private async Task CompleteConfirmationAsync(bool accepted)
    {
        if (_confirmation is null || _confirmationFinishing) return;
        var completion = _confirmation;
        _confirmationFinishing = true;
        ConfirmationCard.IsEnabled = false;
        Motion.Hide(ConfirmationOverlay);
        if (IsLoaded && SystemParameters.ClientAreaAnimation) await Task.Delay(130);
        ConfirmationOverlay.Visibility = Visibility.Collapsed;
        MainBody.IsEnabled = TitleBar.IsEnabled = true;
        _confirmation = null;
        _confirmationFinishing = false;
        if (IsLoaded && _confirmationPreviousFocus is UIElement { IsVisible: true, IsEnabled: true } previous) previous.Focus();
        _confirmationPreviousFocus = null;
        completion.TrySetResult(accepted);
    }

    private async void ConfirmationCancel_Click(object sender, RoutedEventArgs e) => await CompleteConfirmationAsync(false);
    private async void ConfirmationDelete_Click(object sender, RoutedEventArgs e) => await CompleteConfirmationAsync(true);
}
