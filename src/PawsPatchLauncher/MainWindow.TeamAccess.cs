using System.Windows;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private bool? _renderedTeamAccess;
    private bool? _renderedLiveTeamAccess;
    private bool LiveArcaneAccess => _account.CanUseArcaneWars && !AccountConnectionBlocked;
    private string? _storedArcaneKey;
    private readonly Dictionary<string, string> _storedArcaneReleases = new();
    private bool CanSelectArcaneWars => LiveArcaneAccess || _account.CanUseStoredArcaneWars && StoredArcaneReleases().Count > 0;
    private bool ArcaneAccessBlocked => GameMod.IsArcaneWars(_settings) && !CanUseArcaneSelection;
    private bool CanUseArcaneSelection => LiveArcaneAccess || _account.CanUseStoredArcaneWars
        && StoredArcaneReleases().TryGetValue(_settings.Channel, out var release)
        && (_settings.PinnedRelease is null || _settings.PinnedRelease == release);
    private string ArcaneAccessReason => _account.CanUseStoredArcaneWars && !LiveArcaneAccess ? T(
        "Без подключения доступна только уже установленная версия Arcane Wars. Для установки или обновления подключитесь к интернету.",
        "Only an already installed Arcane Wars release is available offline. Connect to the internet to install or update it.") : T(
        "Arcane Wars пока доступен только Paw's Team и администраторам. Открытие доступа для всех ожидает подтверждения автора мода Darquan Mortis.",
        "Arcane Wars is currently available to Paw's Team and administrators. Public access is awaiting confirmation from the mod author, Darquan Mortis.");

    private void EnsureModAccess(string mod)
    {
        if (mod == GameMod.ArcaneWars && !CanUseArcaneSelection)
            throw new InvalidOperationException(ArcaneAccessReason);
    }

    private void EnsureModDownloadAccess(string mod)
    {
        if (mod == GameMod.ArcaneWars && !LiveArcaneAccess)
            throw new InvalidOperationException(ArcaneAccessReason);
    }

    private IReadOnlyDictionary<string, string> StoredArcaneReleases()
    {
        if (_game is null) return new Dictionary<string, string>();
        try
        {
            var path = System.IO.Path.Combine(_game.Directory, ".pawpatch", "mod-library.json");
            var key = path + "|" + GameFileStamp.Read(path);
            if (_storedArcaneKey == key) return _storedArcaneReleases;
            _storedArcaneReleases.Clear();
            var installer = new ModuleInstaller(_game.Directory);
            foreach (var entry in new ModLibrary(_game.Directory).Load().Mods.Where(m => m.Mod == GameMod.ArcaneWars))
            {
                var release = _feedClient.LoadArchived(entry.ReleaseId, entry.Channel);
                if ((entry.ContentId == ModLibrary.ContentId(release, entry.Mod) || entry.ContentId == ModLibrary.LegacyContentId(release, entry.Mod))
                    && ModLibrary.Packages(release, entry.Mod).All(p => LocallyAvailable(installer, p)))
                    _storedArcaneReleases[entry.Channel] = entry.ReleaseId;
            }
            // A mode click reads just the small index stamp. Package preparation
            // still verifies every file before any settings are applied.
            _storedArcaneKey = key;
        }
        catch (Exception error) when (error is IOException or UnauthorizedAccessException or System.Text.Json.JsonException or System.Security.Cryptography.CryptographicException)
        { _storedArcaneReleases.Clear(); _storedArcaneKey = null; }
        return _storedArcaneReleases;
    }

    private void RefreshTeamAccess()
    {
        if (ArcaneWarsModRadio is null) return;
        ArcaneWarsModRadio.IsEnabled = !_busy && CanSelectArcaneWars;
        ArcaneWarsModRadio.ToolTip = null;
        ArcaneAccessButton.ToolTip = T("Доступ к Arcane Wars", "Arcane Wars access");
        System.Windows.Automation.AutomationProperties.SetName(ArcaneAccessButton, (string)ArcaneAccessButton.ToolTip);
        ModsDiscordButton.ToolTip = T("Discord · сообщество модов Kohan II", "Discord · Kohan II mod community");
        System.Windows.Automation.AutomationProperties.SetName(ModsDiscordButton, (string)ModsDiscordButton.ToolTip);
        if (GameMod.IsArcaneWars(_settings) && !LiveArcaneAccess) UpdateButton.IsEnabled = false;
        if (ArcaneAccessBlocked)
        {
            LaunchButton.IsEnabled = UpdateButton.IsEnabled = ApplySettingsButton.IsEnabled = false;
            ReadyStatusText.Text = T("Arcane Wars · доступ для команды", "Arcane Wars · team access");
            ReadyStatusText.Foreground = SocialBrush("#F2D389");
            ReadyStatusBadge.Background = SocialBrush("#40351E");
            ReadyStatusBadge.BorderBrush = SocialBrush("#A9873E");
        }
    }

    private void ArcaneAccess_Click(object sender, RoutedEventArgs e)
    {
        if (ConfirmationActive || ModNoticeOverlay.IsVisible) return;
        _socialDetailsPeer = null;
        _helpPreviousFocus = System.Windows.Input.Keyboard.FocusedElement;
        HelpTitleText.Text = T("Доступ к Arcane Wars", "Arcane Wars access");
        HelpBodyText.Text = ArcaneAccessReason;
        ArcaneWarsCreditPanel.Visibility = HelpLinkErrorText.Visibility = Visibility.Collapsed;
        Motion.Reveal(HelpOverlay);
        RevealDialogCard(HelpCard);
        HelpCloseButton.Focus();
    }

    private async void ModsDiscord_Click(object sender, RoutedEventArgs e)
    {
        if (_openingHelpLink) return;
        _openingHelpLink = true;
        try { await OpenConfirmedLinkAsync(ArcaneWarsDiscordInvite); }
        catch (Exception error) { ActivityStore.Log(error); ShowError(new IOException(T("Не удалось открыть Discord. Попробуйте ещё раз.", "Could not open Discord. Please try again."))); }
        finally { _openingHelpLink = false; }
    }
}
