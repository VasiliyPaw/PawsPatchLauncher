using System.Windows;
using System.Windows.Controls;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private bool _applySettingsVisible;

    private void RefreshApplySettingsVisibility()
    {
        // Track the target state so status refreshes do not restart an active fade.
        var visible = _settingsPending && _patchInstalled;
        ApplySettingsButton.IsHitTestVisible = visible;
        ApplySettingsButton.IsTabStop = visible;
        if (_applySettingsVisible == visible)
        {
            if (!visible && !Motion.IsHiding(ApplySettingsButton)) Motion.Collapse(ApplySettingsButton);
            return;
        }
        _applySettingsVisible = visible;
        if (visible) Motion.Reveal(ApplySettingsButton);
        else Motion.Hide(ApplySettingsButton);
    }

    private void RefreshActionLayout()
    {
        var shortWindow = (ActualHeight > 0 ? ActualHeight : Height) < 780;
        BrandMark.Width = BrandMark.Height = shortWindow ? 76 : 108;
        BrandGapRow.Height = new GridLength(shortWindow ? 14 : 36);
        var compact = (WindowState == WindowState.Maximized && ActualWidth > 0 ? ActualWidth : Width) < 1250;
        Grid.SetRow(ApplySettingsButton, compact ? 0 : 1);
        Grid.SetColumn(ApplySettingsButton, compact ? 4 : 3);
        ApplySettingsButton.Margin = compact ? new Thickness(0, 0, 0, 8) : new Thickness(10, 0, 10, 0);
    }

    private sealed class GameAlreadyRunningException : InvalidOperationException { }
    private sealed class FrequencyUnavailableException(string message) : InvalidOperationException(message) { }
    private bool FrequencyUnavailable => GameMod.IsArcaneWars(_settings) && _channel is not null && _settings.RoamingSpawnMode.Equals("x2", StringComparison.OrdinalIgnoreCase) && !SupportsX2(_channel);
    private string FrequencyUnavailableText => T(
        "В выбранном выпуске патча нет режима ×2. Выберите последнюю версию патча либо частоту «Стандартная» или ×4.",
        "This patch release does not include ×2. Select the latest patch release or use Standard or ×4 frequency.");

    private void EnsureFrequencyAvailable(ChannelManifest channel)
    {
        if (GameMod.IsArcaneWars(_settings) && _settings.RoamingSpawnMode.Equals("x2", StringComparison.OrdinalIgnoreCase) && !SupportsX2(channel))
            throw new FrequencyUnavailableException(FrequencyUnavailableText);
    }

    private void EnsureGameClosed()
    {
        if (IsGameRunning()) throw new GameAlreadyRunningException();
    }

    private static bool SupportsX2(ChannelManifest? channel)
        => channel is not null && new[] { "roaming-profile-x2-with-new", "roaming-profile-x2-no-new" }
            .All(id => channel.Packages.Any(package => package.Id.Equals(id, StringComparison.OrdinalIgnoreCase)));

    private async void ApplySettingsButton_Click(object sender, RoutedEventArgs e) => await ApplySettingsAsync();

    private async Task ApplySettingsAsync()
    {
        if (_busy || FeedBlocksActions || ArcaneAccessBlocked || !_patchInstalled || _game is null || (_channel is null && !GameMod.IsVanilla(_settings)) || ConfirmationActive) return;
        try
        {
            EnsureGameClosed();
            if (GameMod.IsVanilla(_settings) && !_settings.RussianLocalization)
            {
                SetBusy(true);
                await ApplyVanillaConfigurationAsync(_settings);
                ShowResult(() => T("Ванилла готова к запуску.", "Vanilla ready to play."));
                return;
            }
            var state = new ModuleInstaller(_game.Directory).LoadState();
            if (!UpdateDetector.HasSettingsChanges(state, ResolveSelectedPackages(_channel!), GetEffectiveSettings())) return;
            SetBusy(true, T("Применяю настройки…", "Applying settings…"));
            await ApplySelectedConfigurationAsync(_channel!, false);
            ShowResult(() => T("Настройки применены. Можно запускать игру.", "Settings applied. Ready to launch the game."));
        }
        catch (Exception error) { ShowError(error); }
        finally { SetBusy(false); RefreshStatus(); }
    }
}
